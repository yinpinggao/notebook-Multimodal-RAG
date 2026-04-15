"""VRAG LangGraph workflow — parallel search, bbox, summarize, answer.

This module defines the LangGraph workflow for VRAG, featuring:
- Parallel search execution (text + image search)
- Conditional branching based on LLM decision
- Streaming DAG state updates
- Multimodal memory graph integration
"""

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

def agent_node(state: VRAGState, tools: VRAGTools) -> dict:
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
        llm_response = _llm_invoke(
            llm_client=tools.llm_client,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3,
        )
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


def search_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute search action — multimodal retrieval.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary.
    """
    try:
        result = tools.search(
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
        img_summaries = [img.get("summary", "") for img in result.images[:3]]
        node_id = state.memory_graph.add_node(
            node_type="search",
            summary=f"Search for '{state.question}': found {result.total_image_hits} images",
            images=[img.get("image_path", "") for img in result.images[:2]],
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
                {"page_no": img.get("page_no"), "summary": img.get("summary", "")[:100]}
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


def bbox_crop_action_node(state: VRAGState, tools: VRAGTools) -> dict:
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
        result = tools.bbox_crop(
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


def summarize_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute summarize action — analyze evidence and update memory.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary.
    """
    try:
        result = tools.summarize(
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


def answer_action_node(state: VRAGState, tools: VRAGTools) -> dict:
    """Execute answer action — generate final answer.

    Args:
        state: Current VRAG state.
        tools: VRAG tools instance.

    Returns:
        Updated state dictionary with final answer.
    """
    try:
        answer = tools.answer(
            question=state.question,
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
        return {
            "error": str(e),
            "final_answer": f"Failed to generate answer: {e}",
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

    def _agent_node_wrapper(state: VRAGState) -> dict:
        return agent_node(state, tools)

    def _search_wrapper(state: VRAGState) -> dict:
        return search_action_node(state, tools)

    def _bbox_wrapper(state: VRAGState) -> dict:
        return bbox_crop_action_node(state, tools)

    def _summarize_wrapper(state: VRAGState) -> dict:
        return summarize_action_node(state, tools)

    def _answer_wrapper(state: VRAGState) -> dict:
        return answer_action_node(state, tools)

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

def stream_graph_updates(graph, initial_state: VRAGState):
    """Stream graph execution updates for SSE.

    This generator yields state updates as they occur, enabling
    real-time UI updates on the frontend.

    Args:
        graph: Compiled LangGraph.
        initial_state: Initial VRAGState.

    Yields:
        State update dictionaries with dag_updates for frontend rendering.
    """
    # Run the graph with streaming
    for event in graph.stream(initial_state):
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
