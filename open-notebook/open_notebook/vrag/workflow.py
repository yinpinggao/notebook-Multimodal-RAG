"""VRAG LangGraph workflow — parallel search, bbox, summarize, answer."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, StateGraph

from open_notebook.vrag.memory import MultimodalMemoryGraph
from open_notebook.vrag.prompts import SYSTEM_PROMPT
from open_notebook.vrag.tools import VRAGTools

logger = logging.getLogger(__name__)

WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS = 45
FOLLOW_UP_LANGUAGE_MARKERS = (
    "用中文",
    "中文回答",
    "翻译成中文",
    "改成中文",
    "换成中文",
    "用英文",
    "英文回答",
    "翻译成英文",
    "answer in chinese",
    "respond in chinese",
    "in chinese",
    "answer in english",
    "respond in english",
    "in english",
    "translate to chinese",
    "translate into chinese",
    "translate to english",
    "translate into english",
)
VISUAL_INVENTORY_MARKERS = (
    "什么图片",
    "哪些图片",
    "什么图",
    "哪些图",
    "看见什么",
    "看到什么",
    "能看见什么",
    "能看到什么",
    "what images",
    "which images",
    "what figures",
    "which figures",
    "what charts",
    "which charts",
    "what can you see",
    "what do you see",
)
VISUAL_DETAIL_FOLLOW_UP_MARKERS = (
    "详细讲",
    "详细说",
    "详细描述",
    "具体讲",
    "展开讲",
    "多讲点",
    "详细一点",
    "讲讲图片",
    "讲讲图",
    "图片内容",
    "图片细节",
    "图里有什么",
    "图表内容",
    "表格内容",
    "describe the image",
    "describe the picture",
    "describe the chart",
    "describe the table",
    "explain the image",
    "go into detail",
    "more detail",
    "tell me more about the image",
)


def _normalize_follow_up_question(question: str) -> str:
    return " ".join((question or "").strip().lower().split())


def _looks_like_language_follow_up(question: str) -> bool:
    normalized = _normalize_follow_up_question(question)
    if not normalized or len(normalized) > 40:
        return False
    return any(marker in normalized for marker in FOLLOW_UP_LANGUAGE_MARKERS)


def _has_reusable_evidence(state: "VRAGState") -> bool:
    node_order = getattr(state.memory_graph, "node_order", None) or []
    return bool(state.collected_evidence or node_order)


def _looks_like_visual_inventory_question(question: str) -> bool:
    normalized = _normalize_follow_up_question(question)
    if not normalized or len(normalized) > 80:
        return False
    return any(marker in normalized for marker in VISUAL_INVENTORY_MARKERS)


def _looks_like_visual_detail_follow_up(question: str) -> bool:
    normalized = _normalize_follow_up_question(question)
    if not normalized or len(normalized) > 80:
        return False
    return any(marker in normalized for marker in VISUAL_DETAIL_FOLLOW_UP_MARKERS)


def _has_search_hits(state: "VRAGState") -> bool:
    for evidence in state.collected_evidence:
        if evidence.get("type") != "search":
            continue
        if evidence.get("images") or evidence.get("texts"):
            return True
    return False


def _should_reuse_previous_question(question: str) -> bool:
    return _looks_like_language_follow_up(question) or _looks_like_visual_detail_follow_up(
        question
    )


def _message_type(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("type") or message.get("role") or "").lower()
    return str(getattr(message, "type", getattr(message, "role", "")) or "").lower()


def _message_content(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content") or "")
    content = getattr(message, "content", "")
    if isinstance(content, list):
        text_parts = [
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(part for part in text_parts if part)
    return str(content or "")


def _effective_question_for_answer(state: "VRAGState") -> str:
    if not _should_reuse_previous_question(state.question):
        return state.question

    for message in reversed(state.messages or []):
        if _message_type(message) not in {"human", "user"}:
            continue
        content = _message_content(message).strip()
        if not content or _should_reuse_previous_question(content):
            continue
        return f"{content}\n\n补充要求：{state.question}"

    return state.question


async def _run_sync_call_with_timeout(func, *args, **kwargs):
    return await asyncio.wait_for(
        asyncio.to_thread(func, *args, **kwargs),
        timeout=WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS,
    )


# --- State Schema ---

@dataclass
class VRAGState:
    """State schema for the VRAG LangGraph workflow."""
    question: str
    context: str = ""  # Initial context (Source content)
    source_ids: list[str] = field(default_factory=list)
    messages: list[BaseMessage] = field(default_factory=list)
    memory_graph: MultimodalMemoryGraph = field(default_factory=MultimodalMemoryGraph)
    search_results: list = field(default_factory=list)  # Collected search results
    collected_evidence: list[dict] = field(default_factory=list)
    current_step: str = "start"  # Current workflow step
    # bbox_input is set when agent decides bbox_crop — passed to bbox_crop_action_node
    bbox_input: dict = field(default_factory=dict)
    steps_remaining: int = 10
    max_steps: int = 10
    consecutive_useless_searches: int = 0  # Track consecutive searches with no useful images
    is_complete: bool = False
    final_answer: str = ""
    dag_updates: list[dict] = field(default_factory=list)  # For streaming DAG node updates
    error: Optional[str] = None


# --- LLM invocation helper ---

def _llm_invoke(
    llm_client: Any,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.3,
    **kwargs,
) -> str:
    """Invoke the LLM with a unified interface.

    Supports both LangChain chat models (from provision_langchain_model)
    and raw OpenAI SDK clients.
    """
    if hasattr(llm_client, "invoke"):
        lc_messages = []
        for msg in messages:
            content = msg["content"]
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            lc_messages.append(HumanMessage(content=content))

        result = llm_client.invoke(lc_messages, config={"max_tokens": max_tokens})
        return result.content if hasattr(result, "content") else str(result)
    else:
        model = kwargs.get("model", "gpt-4o")
        response = llm_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


# --- Node Functions ---

async def agent_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Agent decision node — LLM decides what to do next.

    This node uses the LLM to analyze the current state and decide
    which tool to call next (search, bbox_crop, summarize, or answer).

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance (provides llm_client).

    Returns:
        Dictionary with agent decision and updates to state.
    """

    # Build recent history
    history_parts = []
    for ev in state.collected_evidence[-3:]:
        ev_type = ev.get("type", "unknown")
        if ev_type == "search":
            imgs = ev.get("images", [])
            history_parts.append(f"- Search: found {len(imgs)} images")
        elif ev_type == "bbox_crop":
            history_parts.append(f"- BBox crop: {ev.get('description', '')[:100]}")

    history_str = "\n".join(history_parts) or "No previous actions yet."
    memory_str = state.memory_graph.get_context_for_answer()

    prompt = f"""{SYSTEM_PROMPT}

## Current Task

Question: {state.question}
Steps remaining: {state.steps_remaining}/{state.max_steps}

## Recent Actions
{history_str}

## Memory (Visual Evidence Accumulated)
{memory_str}

---

Based on the current state, decide the next action:

1. <search>query</search> — If you need to find more visual evidence
2. <bbox_crop>{{"image_path": "...", "bbox": [x1,y1,x2,y2]}}</bbox_crop> — If you need to zoom into an image region
3. <summarize></summarize> — If you have gathered enough evidence and need to analyze it
4. <answer></answer> — If you can answer the question with the current evidence

Your decision (output ONLY the tool call, no extra text):"""

    # Guard: short follow-up prompts like "use Chinese" should reuse evidence.
    if _has_reusable_evidence(state) and _looks_like_language_follow_up(state.question):
        logger.info("Agent direct-answer: short language follow-up detected")
        return {
            "current_step": "answer",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "answer",
                "thought": "Reuse existing evidence for language follow-up",
            }],
        }

    if _has_search_hits(state) and _looks_like_visual_inventory_question(state.question):
        logger.info("Agent direct-answer: visual inventory question already has hits")
        return {
            "current_step": "answer",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "answer",
                "thought": "Enough evidence gathered for visual inventory question",
            }],
        }

    if _has_search_hits(state) and _looks_like_visual_detail_follow_up(state.question):
        logger.info("Agent direct-answer: visual detail follow-up detected")
        return {
            "current_step": "answer",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "answer",
                "thought": "Reuse existing evidence for visual detail follow-up",
            }],
        }

    # Guard: force answer if steps exhausted or useless searches exceeded
    if state.steps_remaining <= 0 or state.consecutive_useless_searches >= 2:
        logger.info(f"Agent force-answer: steps_remaining={state.steps_remaining}, useless={state.consecutive_useless_searches}")
        return {
            "current_step": "answer",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "answer",
                "thought": "Steps exhausted, forcing answer",
            }],
        }

    try:
        llm_response = await _run_sync_call_with_timeout(
            _llm_invoke,
            llm_client=tools.llm_client,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3,
        )
    except asyncio.TimeoutError:
        logger.error("LLM decision timed out, falling back to answer")
        return {
            "current_step": "answer",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "answer",
                "thought": "LLM decision timeout",
            }],
        }
    except Exception as e:
        logger.error(f"LLM decision failed: {e}, falling back to answer")
        return {
            "current_step": "answer",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "answer",
                "thought": f"LLM failed: {e}",
            }],
        }

    # Parse tool calls from LLM response
    tool_pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
    matches = list(tool_pattern.finditer(llm_response))

    if not matches:
        # No tool call found — default to search
        logger.warning(f"No tool call in LLM response, defaulting to search")
        return {
            "current_step": "search",
            "dag_updates": state.dag_updates + [{
                "type": "decision",
                "step": state.max_steps - state.steps_remaining,
                "action": "search",
                "thought": "No tool call found, defaulting to search",
            }],
        }

    # Execute the first tool call
    match = matches[0]
    tool_name = match.group(1)
    tool_input_str = match.group(2).strip()

    # Parse tool input
    tool_input: dict = {}
    if tool_input_str.startswith("{"):
        try:
            tool_input = json.loads(tool_input_str)
        except json.JSONDecodeError:
            tool_input = {"query": tool_input_str}
    else:
        tool_input = {"query": tool_input_str}

    # Normalize tool name
    if tool_name in ("bbox", "bbox_crop"):
        tool_name = "bbox_crop"

    dag_update = {
        "type": "decision",
        "step": state.max_steps - state.steps_remaining,
        "action": tool_name,
        "thought": llm_response[:200],
    }

    if tool_name == "bbox_crop":
        # bbox_crop needs special handling — pass the input through state
        return {
            "current_step": tool_name,
            "bbox_input": tool_input,
            "dag_updates": state.dag_updates + [dag_update],
        }
    else:
        return {
            "current_step": tool_name,
            "dag_updates": state.dag_updates + [dag_update],
        }


def trigger_condition(state: VRAGState) -> str:
    """Conditional routing based on the agent's decision."""
    return state.current_step


async def search_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute search action — multimodal retrieval.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary.
    """
    try:
        result = await tools.search(
            query=state.question,
            source_ids=state.source_ids,
        )

        state.search_results.append(result)
        state.collected_evidence.append({
            "type": "search",
            "query": state.question,
            "images": [img for img in result.images],
            "texts": result.texts,
        })

        # Detect useless searches
        has_images = result.total_image_hits > 0
        current_useless = state.consecutive_useless_searches
        if has_images:
            consecutive_useless = 0
        else:
            consecutive_useless = current_useless + 1

        logger.info(f"Search result: images={result.total_image_hits}, texts={result.total_text_hits}, consecutive_useless: {current_useless} -> {consecutive_useless}")

        # Add to memory graph
        node_images = [
            img.get("file_url") or img.get("image_path")
            for img in result.images[:2]
            if img.get("file_url") or img.get("image_path")
        ]
        img_summaries = [img.get("summary", "") for img in result.images[:3]]
        node_id = state.memory_graph.add_node(
            node_type="search",
            summary=f"Search for '{state.question}': found {result.total_image_hits} images",
            images=node_images,
            priority=0.7,
            is_useful=has_images,
            key_insight="; ".join(img_summaries[:2]) if img_summaries else "No relevant images found",
        )

        dag_update = {
            "type": "search",
            "step": state.max_steps - state.steps_remaining,
            "node_id": node_id,
            "images_found": result.total_image_hits,
            "texts_found": result.total_text_hits,
            "top_images": [
                {
                    "chunk_id": img.get("chunk_id"),
                    "asset_id": img.get("asset_id"),
                    "file_url": img.get("file_url"),
                    "page_no": img.get("page_no"),
                    "summary": img.get("summary", "")[:100],
                    "image_path": img.get("image_path", ""),
                    "score": img.get("score"),
                    "asset_type": img.get("asset_type"),
                    "is_native_image": img.get("is_native_image"),
                }
                for img in result.images[:3]
            ],
        }

        logger.info(f"Search action: found {result.total_image_hits} images, {result.total_text_hits} texts")

        # Force answer after 2 consecutive useless searches
        if consecutive_useless >= 2:
            logger.info(f"Consecutive useless searches: {consecutive_useless}, forcing answer")
            state.steps_remaining = 0  # Zero out to prevent further loops
            return {
                "search_results": state.search_results,
                "collected_evidence": state.collected_evidence,
                "dag_updates": state.dag_updates + [dag_update],
                "current_step": "answer",
                "steps_remaining": 0,
                "consecutive_useless_searches": consecutive_useless,
            }

        return {
            "search_results": state.search_results,
            "collected_evidence": state.collected_evidence,
            "dag_updates": state.dag_updates + [dag_update],
            "current_step": "agent",
            "steps_remaining": state.steps_remaining - 1,
            "consecutive_useless_searches": consecutive_useless,
        }

    except Exception as e:
        logger.error(f"Search action failed: {e}")
        return {
            "error": str(e),
            "current_step": "agent",
            "steps_remaining": state.steps_remaining - 1,
            "consecutive_useless_searches": state.consecutive_useless_searches + 1,
        }


async def bbox_crop_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute bbox crop action — crop a region from an image.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary.
    """
    bbox_input = state.bbox_input or {}
    image_path = bbox_input.get("image_path", "")
    bbox = bbox_input.get("bbox", [0, 0, 1, 1])
    padding = bbox_input.get("padding", 0.02)

    if not image_path:
        return {"error": "No image_path provided for bbox_crop"}

    try:
        result = await _run_sync_call_with_timeout(
            tools.bbox_crop,
            image_path=image_path,
            bbox=bbox,
            padding=padding,
        )

        state.collected_evidence.append({
            "type": "bbox_crop",
            "image_path": image_path,
            "bbox": bbox,
            "cropped_path": result.cropped_image_path,
            "description": result.description,
        })

        # Add to memory graph
        node_id = state.memory_graph.add_node(
            node_type="bbox_crop",
            summary=result.description[:200] if result.description else f"BBox crop on {image_path}",
            images=[result.cropped_image_path] if result.cropped_image_path else [],
            bboxes=[bbox],
            priority=0.6,
            is_useful=bool(result.description),
            key_insight=result.description[:200] if result.description else "",
        )

        dag_update = {
            "type": "bbox_crop",
            "step": state.max_steps - state.steps_remaining,
            "node_id": node_id,
            "description": result.description,
            "bbox": bbox,
        }

        logger.info(f"BBox crop action: {bbox} from {image_path}")

        return {
            "collected_evidence": state.collected_evidence,
            "dag_updates": state.dag_updates + [dag_update],
            "current_step": "agent",
            "steps_remaining": state.steps_remaining - 1,
        }

    except Exception as e:
        logger.error(f"BBox crop action failed: {e}")
        return {
            "error": str(e),
            "current_step": "agent",
            "steps_remaining": state.steps_remaining - 1,
            "consecutive_useless_searches": state.consecutive_useless_searches,
        }


async def summarize_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute summarize action — analyze evidence and update memory.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary.
    """
    try:
        result = await _run_sync_call_with_timeout(
            tools.summarize,
            search_results=state.search_results,
            question=state.question,
            memory_graph=[],  # Will use current memory graph
        )

        # Add to memory graph
        node_id = state.memory_graph.add_node(
            node_type="summarize",
            summary=result.get("summary", ""),
            priority=0.9,
            is_useful=True,
            key_insight=result.get("summary", "")[:200],
        )

        dag_update = {
            "type": "summarize",
            "step": state.max_steps - state.steps_remaining,
            "node_id": node_id,
            "summary": result.get("summary", ""),
            "need_more": result.get("need_more", "none"),
        }

        logger.info(f"Summarize action: {result.get('summary', '')[:100]}")

        return {
            "dag_updates": state.dag_updates + [dag_update],
            "current_step": "answer" if result.get("need_more") == "none" else "agent",
            "steps_remaining": state.steps_remaining - 1,
        }

    except Exception as e:
        logger.error(f"Summarize action failed: {e}")
        return {
            "error": str(e),
            "current_step": "answer",
            "steps_remaining": state.steps_remaining - 1,
        }


async def answer_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute answer action — generate final answer.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary with final answer.
    """
    try:
        effective_question = _effective_question_for_answer(state)
        answer = await _run_sync_call_with_timeout(
            tools.answer,
            question=effective_question,
            memory_entries=[],  # Will use memory graph
            collected_evidence=state.collected_evidence,
        )

        # Add to memory graph
        node_id = state.memory_graph.add_node(
            node_type="answer",
            summary=answer[:200],
            priority=1.0,
            is_useful=True,
            key_insight=answer[:200],
        )

        dag_update = {
            "type": "answer",
            "step": state.max_steps - state.steps_remaining,
            "node_id": node_id,
            "answer_preview": answer[:200],
        }

        logger.info(f"Answer action: generated answer of length {len(answer)}")

        return {
            "final_answer": answer,
            "is_complete": True,
            "current_step": "end",
            "dag_updates": state.dag_updates + [dag_update],
            "steps_remaining": state.steps_remaining - 1,
        }

    except Exception as e:
        logger.error(f"Answer action failed: {e}")
        error_message = (
            "回答生成超时，请重试。"
            if isinstance(e, asyncio.TimeoutError)
            else f"Failed to generate answer: {e}"
        )
        return {
            "error": str(e),
            "final_answer": error_message,
            "is_complete": True,
            "current_step": "end",
            "steps_remaining": state.steps_remaining - 1,
        }


# --- Graph Construction ---

def create_vrag_graph(tools: VRAGTools) -> StateGraph:
    """Create the VRAG LangGraph workflow.

    Args:
        tools: VRAGTools instance.

    Returns:
        Compiled StateGraph for VRAG workflow.
    """

    async def _agent_node_wrapper(state: VRAGState) -> dict:
        return await agent_node(state, tools)

    async def _search_wrapper(state: VRAGState) -> dict:
        return await search_action_node(state, tools)

    async def _bbox_wrapper(state: VRAGState) -> dict:
        return await bbox_crop_action_node(state, tools)

    async def _summarize_wrapper(state: VRAGState) -> dict:
        return await summarize_action_node(state, tools)

    async def _answer_wrapper(state: VRAGState) -> dict:
        return await answer_action_node(state, tools)

    # Define the graph
    workflow = StateGraph(VRAGState)

    # Add nodes
    workflow.add_node("agent", _agent_node_wrapper)
    workflow.add_node("search", _search_wrapper)
    workflow.add_node("bbox_crop", _bbox_wrapper)
    workflow.add_node("summarize", _summarize_wrapper)
    workflow.add_node("answer", _answer_wrapper)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edges from agent
    workflow.add_conditional_edges(
        "agent",
        lambda state: state.current_step,
        {
            "search": "search",
            "bbox_crop": "bbox_crop",  # Fixed: was incorrectly routing to "search"
            "summarize": "summarize",
            "answer": "answer",
            "agent": "agent",  # Loop back for another decision
        },
    )

    # Edges from actions back to agent
    workflow.add_edge("search", "agent")
    workflow.add_edge("bbox_crop", "agent")
    workflow.add_edge("summarize", "agent")
    workflow.add_edge("answer", END)

    return workflow.compile()


# --- Streaming support ---

async def stream_graph_updates(graph, initial_state: VRAGState):
    """Stream graph execution updates for SSE.

    This async generator yields state updates as they occur, enabling
    real-time UI updates on the frontend.

    Args:
        graph: Compiled LangGraph.
        initial_state: Initial VRAGState.

    Yields:
        State update dictionaries with dag_updates for frontend rendering.
    """
    # Run the graph with async streaming
    async for event in graph.astream(initial_state):
        for node_name, node_output in event.items():
            if "dag_updates" in node_output:
                for update in node_output["dag_updates"]:
                    yield {
                        "node": node_name,
                        "update": update,
                        "is_complete": node_output.get("is_complete", False),
                        "final_answer": node_output.get("final_answer", ""),
                    }


# --- Public API ---

def create_vrag_workflow(tools: VRAGTools, max_steps: int = 10) -> tuple:
    """Create a VRAG workflow instance.

    Args:
        tools: VRAGTools instance.
        max_steps: Maximum reasoning steps.

    Returns:
        Tuple of (compiled graph, initial state factory).
    """
    graph = create_vrag_graph(tools)

    def create_initial_state(
        question: str,
        source_ids: Optional[list[str]] = None,
        context: str = "",
    ) -> VRAGState:
        return VRAGState(
            question=question,
            source_ids=source_ids or [],
            context=context,
            max_steps=max_steps,
            steps_remaining=max_steps,
            consecutive_useless_searches=0,
            memory_graph=MultimodalMemoryGraph(),
        )

    return graph, create_initial_state
