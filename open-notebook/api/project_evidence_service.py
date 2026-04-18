from __future__ import annotations

import asyncio
from typing import Any, Literal, Optional
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from api.schemas import (
    AskResponse,
    EvidenceThreadDetail,
    EvidenceThreadMessage,
    EvidenceThreadSummary,
)
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.evidence import build_evidence_cards
from open_notebook.exceptions import InvalidInputError, NotFoundError
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.seekdb import seekdb_business_store
from open_notebook.utils.evidence_builder import (
    VISUAL_QUERY_TERMS,
    build_multimodal_evidence,
)
from open_notebook.utils.text_utils import extract_text_content

from . import project_workspace_service

ProjectAskMode = Literal["auto", "text", "visual", "mixed"]
SelectedAskMode = Literal["text", "visual", "mixed"]

NO_EVIDENCE_CONTEXT = (
    "当前检索没有找到足够证据。请明确告诉用户现有项目资料不足以支撑确定结论，"
    "并建议缩小问题范围、指定资料或补充文档。不要编造细节或引用。"
)


def _normalize_session_id(thread_id: str) -> str:
    if thread_id.startswith("chat_session:"):
        return thread_id
    return f"chat_session:{thread_id}"


def _default_thread_title(question: str) -> str:
    normalized = " ".join((question or "").strip().split())
    return normalized[:80] if normalized else "Project Evidence Thread"


def _is_visual_query(question: str) -> bool:
    lowered = (question or "").lower()
    return any(term in question or term in lowered for term in VISUAL_QUERY_TERMS)


def _row_has_visual_signal(row: dict[str, Any]) -> bool:
    return bool(row.get("has_visual_summary") or row.get("page_image_path"))


def select_project_ask_mode(
    requested_mode: ProjectAskMode,
    question: str,
    results: list[dict[str, Any]],
) -> SelectedAskMode:
    if requested_mode == "text":
        return "text"
    if requested_mode == "visual":
        return "visual"
    if requested_mode == "mixed":
        return "mixed"

    visual_query = _is_visual_query(question)
    has_visual = any(_row_has_visual_signal(row) for row in results)
    has_nonvisual = any(not _row_has_visual_signal(row) for row in results)

    if visual_query and has_visual and has_nonvisual:
        return "mixed"
    if visual_query and has_visual:
        return "visual"
    if has_visual and has_nonvisual:
        return "mixed"
    return "text"


def _normalize_score(row: dict[str, Any]) -> Optional[float]:
    raw_score = (
        row.get("final_score")
        or row.get("relevance")
        or row.get("similarity")
        or row.get("score")
    )
    if raw_score is None:
        return None

    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None

    if score < 0:
        return 0.0
    if score <= 1:
        return score
    return min(score / 5.0, 1.0)


def _estimate_confidence(results: list[dict[str, Any]], mode: SelectedAskMode) -> float:
    if not results:
        return 0.22

    scores = [_normalize_score(row) for row in results[:4]]
    normalized_scores = [score for score in scores if score is not None]
    base = sum(normalized_scores) / len(normalized_scores) if normalized_scores else 0.55

    if len(results) >= 3:
        base += 0.05
    if mode == "mixed":
        base += 0.03
    if mode == "visual" and any(_row_has_visual_signal(row) for row in results):
        base += 0.05

    return round(min(max(base, 0.22), 0.92), 2)


def _build_suggested_followups(
    question: str,
    mode: SelectedAskMode,
    source_names: list[str],
    has_evidence: bool,
) -> list[str]:
    if not has_evidence:
        return [
            "先告诉我这个问题最需要补充哪几类资料。",
            "把问题缩小到一个文件、一个章节或一页再试一次。",
            "列出当前项目里最相关的资料，方便我指定范围。",
        ]

    first_source = source_names[0] if source_names else "当前资料"
    followups = [
        f"把 {first_source} 里最关键的证据再展开解释一下。",
        "这些证据之间有没有冲突、缺口或需要人工复核的地方？",
        "如果只保留最稳妥的结论，应该怎么表述？",
    ]

    if mode in {"visual", "mixed"}:
        followups[1] = "这页图表、版面或截图具体支持了哪些判断？"

    return followups


async def _resolve_project_scope(
    project_id: str,
) -> tuple[Any, Notebook, list[str], list[str]]:
    project = await project_workspace_service.get_project(project_id)
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Project not found")

    sources = await notebook.get_sources()
    notes = await notebook.get_notes()
    source_ids = [str(source.id) for source in sources if source.id]
    note_ids = [str(note.id) for note in notes if note.id]
    return project, notebook, source_ids, note_ids


async def _get_or_create_thread(
    project_id: str,
    question: str,
    thread_id: Optional[str] = None,
) -> ChatSession:
    if thread_id:
        session = await ChatSession.get(_normalize_session_id(thread_id))
        if not session:
            raise NotFoundError("Thread not found")

        relation_exists = await seekdb_business_store.relation_exists(
            "refers_to",
            str(session.id),
            project_id,
        )
        if not relation_exists:
            raise NotFoundError("Thread not found")
        return session

    session = ChatSession(title=_default_thread_title(question))
    await session.save()
    await session.relate_to_notebook(project_id)
    return session


async def _thread_messages(session_id: str) -> list[EvidenceThreadMessage]:
    thread_state = await asyncio.to_thread(
        chat_graph.get_state,
        config=RunnableConfig(configurable={"thread_id": session_id}),
    )

    if not thread_state or not thread_state.values:
        return []

    messages = []
    for index, message in enumerate(thread_state.values.get("messages", []), start=1):
        messages.append(
            EvidenceThreadMessage(
                id=getattr(message, "id", f"msg_{index}"),
                type=message.type if hasattr(message, "type") else "unknown",
                content=extract_text_content(message.content)
                if hasattr(message, "content")
                else str(message),
                timestamp=None,
            )
        )
    return messages


def _thread_summary_from_messages(
    *,
    session: ChatSession,
    project_id: str,
    messages: list[EvidenceThreadMessage],
) -> EvidenceThreadSummary:
    last_question = next(
        (message.content for message in reversed(messages) if message.type == "human"),
        None,
    )
    last_answer = next(
        (message.content for message in reversed(messages) if message.type == "ai"),
        None,
    )

    return EvidenceThreadSummary(
        id=str(session.id or ""),
        project_id=project_id,
        title=session.title or "Untitled Thread",
        created_at=str(session.created),
        updated_at=str(session.updated),
        message_count=len(messages),
        last_question=last_question,
        last_answer_preview=last_answer[:200] if last_answer else None,
    )


async def _latest_response_for_thread(
    project_id: str,
    messages: list[EvidenceThreadMessage],
    thread_id: str,
) -> Optional[AskResponse]:
    last_question = next(
        (message.content for message in reversed(messages) if message.type == "human"),
        None,
    )
    last_answer = next(
        (message.content for message in reversed(messages) if message.type == "ai"),
        None,
    )

    if not last_question or not last_answer:
        return None

    _, _, source_ids, note_ids = await _resolve_project_scope(project_id)
    evidence = await build_multimodal_evidence(
        last_question,
        source_ids=source_ids or None,
        note_ids=note_ids or None,
        include_sources=True,
        include_notes=True,
        limit=8,
        minimum_score=0.2,
    )
    results = evidence.get("results") or []
    selected_mode = select_project_ask_mode("auto", last_question, results)
    evidence_cards = build_evidence_cards(
        project_id=project_id,
        thread_id=thread_id,
        rows=results,
        mode=selected_mode,
    )

    return AskResponse(
        answer=last_answer,
        confidence=_estimate_confidence(results, selected_mode),
        evidence_cards=evidence_cards,
        memory_updates=[],
        run_id=None,
        suggested_followups=_build_suggested_followups(
            last_question,
            selected_mode,
            [card.source_name for card in evidence_cards],
            bool(evidence_cards),
        ),
        mode=selected_mode,
        thread_id=thread_id,
    )


async def _generate_answer_for_thread(
    *,
    session: ChatSession,
    notebook: Notebook,
    question: str,
    context_text: str,
) -> str:
    full_session_id = str(session.id or "")
    current_state = await asyncio.to_thread(
        chat_graph.get_state,
        config=RunnableConfig(configurable={"thread_id": full_session_id}),
    )

    state_values = current_state.values if current_state else {}
    state_values["messages"] = state_values.get("messages", [])
    state_values["notebook"] = notebook
    state_values["context"] = context_text
    state_values["context_config"] = {
        "project_id": str(notebook.id or ""),
    }
    state_values["model_override"] = getattr(session, "model_override", None)
    state_values["messages"].append(HumanMessage(content=question))

    result = chat_graph.invoke(
        input=state_values,  # type: ignore[arg-type]
        config=RunnableConfig(configurable={"thread_id": full_session_id}),
    )
    await session.save()

    for message in reversed(result.get("messages", [])):
        if hasattr(message, "type") and message.type == "ai":
            return extract_text_content(message.content)

    raise InvalidInputError("No answer generated")


async def ask_project(
    project_id: str,
    question: str,
    *,
    mode: ProjectAskMode = "auto",
    thread_id: Optional[str] = None,
) -> AskResponse:
    if not question or not question.strip():
        raise InvalidInputError("Question cannot be empty")

    _, notebook, source_ids, note_ids = await _resolve_project_scope(project_id)
    session = await _get_or_create_thread(project_id, question, thread_id=thread_id)
    run_id = f"run:{uuid4().hex[:12]}"

    evidence = await build_multimodal_evidence(
        question,
        source_ids=source_ids or None,
        note_ids=note_ids or None,
        include_sources=True,
        include_notes=True,
        limit=8,
        minimum_score=0.2,
    )
    results = evidence.get("results") or []
    selected_mode = select_project_ask_mode(mode, question, results)
    evidence_cards = build_evidence_cards(
        project_id=project_id,
        thread_id=str(session.id or ""),
        rows=results,
        mode=selected_mode,
    )
    source_names = [card.source_name for card in evidence_cards]
    context_text = (evidence.get("context_text") or "").strip()
    if not results:
        context_text = NO_EVIDENCE_CONTEXT

    answer = await _generate_answer_for_thread(
        session=session,
        notebook=notebook,
        question=question,
        context_text=context_text,
    )

    if not results and "证据" not in answer and "资料" not in answer:
        answer = (
            "我暂时没有在当前项目资料里找到足够证据来支持明确结论。"
            "建议缩小问题范围、指定文件，或先补充更相关的资料后再问。"
        )

    return AskResponse(
        answer=answer,
        confidence=_estimate_confidence(results, selected_mode),
        evidence_cards=evidence_cards,
        memory_updates=[],
        run_id=run_id,
        suggested_followups=_build_suggested_followups(
            question,
            selected_mode,
            source_names,
            bool(evidence_cards),
        ),
        mode=selected_mode,
        thread_id=str(session.id or ""),
    )


async def list_project_threads(project_id: str) -> list[EvidenceThreadSummary]:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Project not found")

    sessions = await notebook.get_chat_sessions()
    summaries: list[EvidenceThreadSummary] = []

    for session in sessions:
        messages = await _thread_messages(str(session.id or ""))
        summaries.append(
            _thread_summary_from_messages(
                session=session,
                project_id=project_id,
                messages=messages,
            )
        )

    summaries.sort(key=lambda item: item.updated_at, reverse=True)
    return summaries


async def get_project_thread(project_id: str, thread_id: str) -> EvidenceThreadDetail:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Project not found")

    session = await ChatSession.get(_normalize_session_id(thread_id))
    if not session:
        raise NotFoundError("Thread not found")

    relation_exists = await seekdb_business_store.relation_exists(
        "refers_to",
        str(session.id),
        project_id,
    )
    if not relation_exists:
        raise NotFoundError("Thread not found")

    messages = await _thread_messages(str(session.id or ""))
    summary = _thread_summary_from_messages(
        session=session,
        project_id=project_id,
        messages=messages,
    )

    return EvidenceThreadDetail(
        **summary.model_dump(),
        messages=messages,
        latest_response=await _latest_response_for_thread(
            project_id,
            messages,
            str(session.id or ""),
        ),
    )


async def followup_project_thread(
    project_id: str,
    thread_id: str,
    question: str,
    *,
    mode: ProjectAskMode = "auto",
) -> AskResponse:
    return await ask_project(
        project_id,
        question,
        mode=mode,
        thread_id=thread_id,
    )
