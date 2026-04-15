"""VRAG agent — ReAct agent for visual reasoning.

Adapted from VRAG/demo/vimrag_agent.py — replacing local model calls with
cloud VLM API (GPT-4o / Claude) through the Esperanto abstraction layer.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from langchain_core.messages import HumanMessage

from open_notebook.vrag.memory import MultimodalMemoryGraph
from open_notebook.vrag.prompts import (
    ANSWER_PROMPT_TEMPLATE,
    SUMMARY_PROMPT,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from open_notebook.vrag.tools import MemoryEntry, SearchResult, VRAGTools

logger = logging.getLogger(__name__)

# Maximum reasoning steps to prevent infinite loops
DEFAULT_MAX_STEPS = 10


@dataclass
class AgentAction:
    """A single action taken by the VRAG agent."""
    tool_name: str  # "search" | "bbox_crop" | "summarize" | "answer"
    tool_input: dict
    tool_output: Any
    step: int

    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "input": self.tool_input,
            "output": self.tool_output,
            "step": self.step,
        }


@dataclass
class AgentThought:
    """A reasoning step from the VRAG agent."""
    thought: str
    action: Optional[AgentAction] = None
    step: int = 0

    def to_dict(self) -> dict:
        return {
            "thought": self.thought,
            "action": self.action.to_dict() if self.action else None,
            "step": self.step,
        }


@dataclass
class VRAGAgentState:
    """State maintained during VRAG agent inference."""
    question: str
    context: str = ""
    source_ids: list[str] = field(default_factory=list)
    memory_graph: MultimodalMemoryGraph = field(default_factory=MultimodalMemoryGraph)
    search_results: list[SearchResult] = field(default_factory=list)
    collected_evidence: list[dict] = field(default_factory=list)
    actions: list[AgentAction] = field(default_factory=list)
    thoughts: list[AgentThought] = field(default_factory=list)
    current_answer: str = ""
    max_steps: int = DEFAULT_MAX_STEPS
    steps_remaining: int = DEFAULT_MAX_STEPS
    is_complete: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "context": self.context,
            "source_ids": self.source_ids,
            "memory_graph": self.memory_graph.to_dict(),
            "search_results_count": len(self.search_results),
            "collected_evidence_count": len(self.collected_evidence),
            "actions": [a.to_dict() for a in self.actions],
            "current_answer": self.current_answer,
            "steps_remaining": self.steps_remaining,
            "is_complete": self.is_complete,
            "error": self.error,
        }


class VRAGAgent:
    """ReAct-style agent for vision-perception RAG.

    The agent uses a loop of:
    1. Think: Analyze the current state and decide what to do next
    2. Act: Execute a tool (search, bbox_crop, summarize, answer)
    3. Observe: Update the state based on the tool output
    4. Repeat until the answer is generated or max_steps is reached
    """

    def __init__(
        self,
        tools: VRAGTools,
        llm_client: Any,
        system_prompt: str = SYSTEM_PROMPT,
        max_steps: int = DEFAULT_MAX_STEPS,
    ):
        """Initialize the VRAG agent.

        Args:
            tools: VRAGTools instance for executing actions.
            llm_client: LLM client for reasoning (GPT-4o / Claude).
            system_prompt: System prompt for the agent.
            max_steps: Maximum number of reasoning steps.
        """
        self.tools = tools
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.max_steps = max_steps

    def _parse_tool_calls(self, text: str) -> list[tuple[str, dict]]:
        """Parse tool calls from LLM response text.

        Supports formats like:
        - <search>query</search>
        - <bbox_crop>{"image_path": "...", "bbox": [...]}</bbox_crop>
        - <answer>...</answer>

        Args:
            text: LLM response text containing tool calls.

        Returns:
            List of (tool_name, tool_input_dict) tuples.
        """
        tool_calls = []

        # Match <tool_name>...</tool_name> patterns
        tool_pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
        for match in tool_pattern.finditer(text):
            tool_name = match.group(1)
            tool_input_str = match.group(2).strip()

            # Parse the tool input as JSON or plain text
            tool_input = {}
            if tool_input_str.startswith("{"):
                try:
                    tool_input = json.loads(tool_input_str)
                except json.JSONDecodeError:
                    tool_input = {"query": tool_input_str}
            else:
                tool_input = {"query": tool_input_str}

            tool_calls.append((tool_name, tool_input))

        return tool_calls

    def _think_and_act(self, state: VRAGAgentState) -> AgentThought:
        """Let the LLM think about the next action and return it.

        Args:
            state: Current agent state.

        Returns:
            AgentThought with the LLM's reasoning and action.
        """
        # Build context for the LLM
        history_parts = []

        # Previous actions
        if state.actions:
            history_parts.append("## Previous Actions:")
            for action in state.actions[-5:]:  # Last 5 actions
                output_preview = str(action.tool_output)[:300]
                history_parts.append(
                    f"- Step {action.step}: {action.tool_name} -> {output_preview}..."
                )

        # Memory graph summary
        memory_summary = state.memory_graph.get_context_for_answer()

        # Search results summary
        search_summary = ""
        if state.search_results:
            for i, sr in enumerate(state.search_results):
                search_summary += f"\nSearch {i + 1}: {sr.total_image_hits} images, {sr.total_text_hits} texts"
                for img in sr.images[:2]:
                    search_summary += f"\n  - Page {img['page_no']}: {img.get('summary', 'No summary')[:100]}"

        prompt = f"""{self.system_prompt}

## Current State

Question: {state.question}
Steps remaining: {state.steps_remaining}/{self.max_steps}

{chr(10).join(history_parts) if history_parts else "No previous actions yet."}

## Memory Graph (visual evidence accumulated so far)

{memory_summary}

## Recent Search Results

{search_summary if search_summary else "No searches performed yet."}

---

Based on the question and current state, decide what to do next.

Available tools:
- <search>query</search> — Search for relevant images and text in the documents
- <bbox_crop>{{"image_path": "...", "bbox": [x1, y1, x2, y2]}}</bbox_crop> — Crop a specific region from an image
- <summarize></summarize> — Analyze gathered evidence and decide what to remember
- <answer></answer> — Generate the final answer with image references

Think step by step about what visual information you need. Use <search> to find images, <bbox_crop> to zoom into specific regions, and <answer> only when you have enough evidence.

If you have gathered sufficient visual evidence, use <answer> to provide the final response.

Your response:"""

        try:
            thought_text = self._llm_invoke(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            thought_text = f"LLM error: {e}"

        # Parse tool calls from the response
        tool_calls = self._parse_tool_calls(thought_text)

        if not tool_calls:
            # No tool call found — try to interpret as an answer
            logger.info("No tool call found in LLM response, attempting direct answer")
            return AgentThought(
                thought=thought_text,
                action=None,
                step=0,
            )

        # Execute the first tool call
        tool_name, tool_input = tool_calls[0]
        tool_output = self._execute_tool(tool_name, tool_input, state)

        return AgentThought(
            thought=thought_text,
            action=AgentAction(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                step=0,
            ),
            step=0,
        )

    def _llm_invoke(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:
        """Invoke the LLM with a unified interface.

        Supports both LangChain chat models (from provision_langchain_model)
        and raw OpenAI SDK clients.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            The generated text content.
        """
        if hasattr(self.llm_client, "invoke"):
            # LangChain chat model
            lc_messages = []
            for msg in messages:
                content = msg["content"]
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                lc_messages.append(HumanMessage(content=content))

            result = self.llm_client.invoke(lc_messages, config={"max_tokens": max_tokens})
            return result.content if hasattr(result, "content") else str(result)
        else:
            # Raw OpenAI SDK client
            model = kwargs.get("model", "gpt-4o")
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

    def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        state: VRAGAgentState,
    ) -> Any:
        """Execute a tool and update the state.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Input arguments for the tool.
            state: Current agent state.

        Returns:
            Tool output (can be any type).
        """
        if tool_name == "search":
            query = tool_input.get("query", state.question)
            result = self.tools.search(
                query=query,
                source_ids=state.source_ids,
            )
            state.search_results.append(result)
            state.collected_evidence.append({
                "type": "search",
                "query": query,
                "images": [img.to_dict() if hasattr(img, 'to_dict') else img for img in result.images],
                "texts": result.texts,
            })
            return result.to_dict()

        elif tool_name == "bbox_crop":
            image_path = tool_input.get("image_path", "")
            bbox = tool_input.get("bbox", [0, 0, 1, 1])
            padding = tool_input.get("padding", 0.02)

            result = self.tools.bbox_crop(
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
            return result.to_dict()

        elif tool_name == "summarize":
            summary_result = self.tools.summarize(
                search_results=state.search_results,
                question=state.question,
                memory_graph=[MemoryEntry(**m.to_dict()) for m in state.memory_graph.get_useful_nodes()],
            )

            # Update memory graph with summarize results
            node_id = state.memory_graph.add_node(
                node_type="summarize",
                summary=summary_result.get("summary", ""),
                parent_ids=[state.actions[-1].action.node_id if state.actions else None],
                priority=0.8,
                is_useful=True,
                key_insight=summary_result.get("summary", "")[:200],
            )

            return summary_result

        elif tool_name == "answer":
            # Generate the final answer
            answer = self.tools.answer(
                question=state.question,
                memory_entries=[MemoryEntry(**m.to_dict()) for m in state.memory_graph.get_useful_nodes()],
                collected_evidence=state.collected_evidence,
            )
            state.current_answer = answer
            state.is_complete = True

            # Add answer node to memory graph
            state.memory_graph.add_node(
                node_type="answer",
                summary=answer[:200],
                priority=1.0,
                is_useful=True,
                key_insight=answer[:200],
            )

            return answer

        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

    def run(self, question: str, source_ids: Optional[list[str]] = None) -> VRAGAgentState:
        """Run the VRAG agent to answer a question.

        Args:
            question: The user's question.
            source_ids: Optional list of source IDs to search within.

        Returns:
            VRAGAgentState with the final answer and reasoning trace.
        """
        state = VRAGAgentState(
            question=question,
            source_ids=source_ids or [],
            max_steps=self.max_steps,
            steps_remaining=self.max_steps,
        )

        logger.info(f"VRAG Agent starting: question='{question}', sources={source_ids}")

        while not state.is_complete and state.steps_remaining > 0:
            state.steps_remaining -= 1

            thought = self._think_and_act(state)

            if thought.action:
                state.thoughts.append(thought)
                state.actions.append(thought.action)
                logger.info(
                    f"Step {len(state.actions)}: {thought.action.tool_name} -> "
                    f"{str(thought.action.tool_output)[:100]}..."
                )

                # Check if answer was generated
                if thought.action.tool_name == "answer":
                    state.is_complete = True
                    break
            else:
                # No valid tool call — try direct answer
                logger.warning(f"No valid tool call found. Attempting direct answer.")
                try:
                    answer = self.tools.answer(
                        question=state.question,
                        memory_entries=[MemoryEntry(**m.to_dict()) for m in state.memory_graph.get_useful_nodes()],
                        collected_evidence=state.collected_evidence,
                    )
                    state.current_answer = answer
                    state.is_complete = True
                except Exception as e:
                    state.error = str(e)
                    logger.error(f"Direct answer failed: {e}")

        if not state.is_complete:
            logger.warning(f"VRAG Agent reached max steps ({self.max_steps}) without completing")
            # Try to generate an answer anyway
            try:
                answer = self.tools.answer(
                    question=state.question,
                    memory_entries=[MemoryEntry(**m.to_dict()) for m in state.memory_graph.get_useful_nodes()],
                    collected_evidence=state.collected_evidence,
                )
                state.current_answer = answer
                state.is_complete = True
            except Exception as e:
                state.error = f"Max steps reached, answer generation failed: {e}"

        logger.info(f"VRAG Agent complete: answer_length={len(state.current_answer)}")
        return state
