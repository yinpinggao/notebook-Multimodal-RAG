import operator
from typing import Annotated, List

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.evidence_builder import build_multimodal_evidence
from open_notebook.utils.text_utils import extract_text_content


class SubGraphState(TypedDict):
    question: str
    term: str
    instructions: str
    results: list[dict]
    context_text: str
    answer: str
    ids: list  # Added for provide_answer function


class Search(BaseModel):
    term: str
    instructions: str = Field(
        description="Tell the answeting LLM what information you need extracted from this search"
    )


class Strategy(BaseModel):
    reasoning: str
    searches: List[Search] = Field(
        default_factory=list,
        description="You can add up to five searches to this strategy",
    )


class ThreadState(TypedDict):
    question: str
    strategy: Strategy
    answers: Annotated[list, operator.add]
    final_answer: str


async def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        parser = PydanticOutputParser(pydantic_object=Strategy)
        system_prompt = Prompter(prompt_template="ask/entry", parser=parser).render(  # type: ignore[arg-type]
            data=state  # type: ignore[arg-type]
        )
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("strategy_model"),
            "tools",
            max_tokens=2000,
            structured=dict(type="json"),
        )
        # model = model.bind_tools(tools)
        # First get the raw response from the model
        ai_message = await model.ainvoke(system_prompt)

        # Clean the thinking content from the response
        message_content = extract_text_content(ai_message.content)
        cleaned_content = clean_thinking_content(message_content)

        # Parse the cleaned JSON content
        strategy = parser.parse(cleaned_content)

        return {"strategy": strategy}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


async def trigger_queries(state: ThreadState, config: RunnableConfig):
    return [
        Send(
            "provide_answer",
            {
                "question": state["question"],
                "instructions": s.instructions,
                "term": s.term,
                # "type": s.type,
            },
        )
        for s in state["strategy"].searches
    ]


async def provide_answer(state: SubGraphState, config: RunnableConfig) -> dict:
    try:
        evidence = await build_multimodal_evidence(
            state["term"],
            include_sources=True,
            include_notes=True,
            limit=8,
            minimum_score=0.2,
        )
        results = evidence["results"]
        if len(results) == 0:
            return {"answers": []}
        ids = [
            r.get("internal_ref") or r.get("parent_id") or r.get("id")
            for r in results
            if r.get("internal_ref") or r.get("parent_id") or r.get("id")
        ]
        context_text = evidence["context_text"]
        system_prompt = f"""
You are a research assistant answering a focused sub-question over retrieved evidence.

Original user question:
{state["question"]}

Current search term:
{state["term"]}

Instructions from the strategy model:
{state["instructions"]}

Retrieved evidence:
{context_text}

Allowed internal references:
{ids}

Requirements:
1. Answer only from the evidence above.
2. Be concise but complete.
3. When citing a PDF page, use this exact style: 引用：[n]（文件名，第X页）；内部引用：[source:xxxx]
4. If the evidence has no page number, do not invent one. Use only the internal reference.
5. Do not invent any source, page number, filename, or internal reference.
6. If the evidence explicitly says `视觉证据：已包含页面图像摘要`, treat it as image-derived evidence from the PDF page. Do not say you cannot view or parse the PDF image in that case. Instead describe what the page-image evidence shows.
"""
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("answer_model"),
            "tools",
            max_tokens=2000,
        )
        ai_message = await model.ainvoke(system_prompt)
        ai_content = extract_text_content(ai_message.content)
        return {"answers": [clean_thinking_content(ai_content)]}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


async def write_final_answer(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        system_prompt = f"""
You are the final answering agent for a knowledge-base question.

User question:
{state["question"]}

Search strategy:
{state["strategy"]}

Intermediate answers:
{state["answers"]}

Write a final answer that:
1. Synthesizes the intermediate answers into one coherent response.
2. Preserves any valid citations already present.
3. Uses dual citations whenever available:
   引用：[n]（文件名，第X页）；内部引用：[source:xxxx]
4. Never invent filenames, page numbers, or internal references.
5. If evidence is insufficient, say so clearly.
6. If any intermediate answer uses evidence marked as visual page evidence, do not claim that you cannot see or parse images. Summarize the visual evidence that was retrieved.
"""
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("final_answer_model"),
            "tools",
            max_tokens=2000,
        )
        ai_message = await model.ainvoke(system_prompt)
        final_content = extract_text_content(ai_message.content)
        return {"final_answer": clean_thinking_content(final_content)}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_node("provide_answer", provide_answer)
agent_state.add_node("write_final_answer", write_final_answer)
agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges("agent", trigger_queries, ["provide_answer"])
agent_state.add_edge("provide_answer", "write_final_answer")
agent_state.add_edge("write_final_answer", END)

graph = agent_state.compile()
