from __future__ import annotations

import asyncio
from typing import Any, Literal, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, Field

from api.schemas import (
    AskResponse,
    EvidenceThreadDetail,
    EvidenceThreadMessage,
    EvidenceThreadSummary,
)
from open_notebook.agent_harness import (
    create_project_run,
    mark_run_completed,
    mark_run_failed,
    mark_run_running,
    record_answer_step,
    record_evidence_read,
    record_tool_call,
)
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.evidence import build_evidence_cards
from open_notebook.exceptions import InvalidInputError, NotFoundError
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.memory_center import list_project_memories
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


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectEvidenceThreadState(_Model):
    thread_id: str
    project_id: str
    latest_response: Optional[AskResponse] = Field(default=None)
    source_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    agent: Optional[str] = Field(default=None)


def _thread_state_record_id(thread_id: str) -> str:
    return f"project_evidence_thread:{thread_id}"


def _strip_singleton_metadata(data: dict, *, public_id: str | None = None) -> dict:
    payload = {
        key: value for key, value in data.items() if key not in {"created", "updated"}
    }
    payload.pop("id", None)
    if public_id is not None:
        payload["thread_id"] = public_id
    return payload


async def _load_thread_state(thread_id: str) -> ProjectEvidenceThreadState | None:
    data = await seekdb_business_store.get_singleton(_thread_state_record_id(thread_id))
    if not data:
        return None
    return ProjectEvidenceThreadState.model_validate(
        _strip_singleton_metadata(data, public_id=thread_id)
    )


async def _save_thread_state(
    thread_id: str,
    project_id: str,
    *,
    latest_response: AskResponse,
    source_ids: Optional[list[str]] = None,
    note_ids: Optional[list[str]] = None,
    memory_ids: Optional[list[str]] = None,
    agent: Optional[str] = None,
) -> ProjectEvidenceThreadState:
    state = ProjectEvidenceThreadState(
        thread_id=thread_id,
        project_id=project_id,
        latest_response=latest_response,
        source_ids=source_ids or [],
        note_ids=note_ids or [],
        memory_ids=memory_ids or [],
        agent=agent,
    )
    saved = await seekdb_business_store.upsert_singleton(
        _thread_state_record_id(thread_id),
        state.model_dump(mode="json"),
    )
    return ProjectEvidenceThreadState.model_validate(
        _strip_singleton_metadata(saved, public_id=thread_id)
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


def _normalize_selected_ids(values: Optional[list[str]]) -> Optional[list[str]]:
    if values is None:
        return None

    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def _filter_scope_ids(
    requested_ids: Optional[list[str]],
    available_ids: list[str],
) -> list[str]:
    normalized_ids = _normalize_selected_ids(requested_ids)
    if normalized_ids is None:
        return list(available_ids)

    available = set(available_ids)
    return [item for item in normalized_ids if item in available]


async def _build_memory_context(
    project_id: str,
    memory_ids: Optional[list[str]],
) -> tuple[list[str], str]:
    normalized_ids = _normalize_selected_ids(memory_ids)
    if normalized_ids is None:
        return [], ""

    memories = await list_project_memories(project_id, include_deprecated=True)
    by_id = {memory.id: memory for memory in memories}
    selected = [by_id[memory_id] for memory_id in normalized_ids if memory_id in by_id]
    if not selected:
        return [], ""

    blocks = []
    selected_ids: list[str] = []
    for index, memory in enumerate(selected, start=1):
        selected_ids.append(memory.id)
        refs = "；".join(
            ref.citation_text or ref.internal_ref
            for ref in memory.source_refs[:2]
            if ref.citation_text or ref.internal_ref
        )
        suffix = f"；来源：{refs}" if refs else ""
        blocks.append(
            f"[Memory {index}] 类型：{memory.type}；状态：{memory.status}；内容：{memory.text}{suffix}"
        )

    return selected_ids, "## Selected Project Memories\n" + "\n".join(blocks)


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
    stored_state = await _load_thread_state(thread_id)
    if stored_state and stored_state.project_id == project_id and stored_state.latest_response:
        return stored_state.latest_response

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
    source_ids: Optional[list[str]] = None,
    note_ids: Optional[list[str]] = None,
    memory_ids: Optional[list[str]] = None,
    agent: Optional[str] = None,
) -> AskResponse:
    if not question or not question.strip():
        raise InvalidInputError("Question cannot be empty")

    _, notebook, available_source_ids, available_note_ids = await _resolve_project_scope(
        project_id
    )
    scoped_source_ids = _filter_scope_ids(source_ids, available_source_ids)
    scoped_note_ids = _filter_scope_ids(note_ids, available_note_ids)
    selected_memory_ids, memory_context_text = await _build_memory_context(
        project_id,
        memory_ids,
    )
    explicit_source_scope = source_ids is not None
    explicit_note_scope = note_ids is not None

    session = await _get_or_create_thread(project_id, question, thread_id=thread_id)
    run = await create_project_run(
        project_id,
        run_type="ask",
        input_json={
            "question": question,
            "mode": mode,
            "agent": agent,
            "thread_id": str(session.id or ""),
            "source_ids": scoped_source_ids,
            "note_ids": scoped_note_ids,
            "memory_ids": selected_memory_ids,
        },
    )
    await mark_run_running(run.id)

    try:
        include_sources = not explicit_source_scope or bool(scoped_source_ids)
        include_notes = not explicit_note_scope or bool(scoped_note_ids)

        if include_sources or include_notes:
            evidence = await build_multimodal_evidence(
                question,
                source_ids=scoped_source_ids or None,
                note_ids=scoped_note_ids or None,
                include_sources=include_sources,
                include_notes=include_notes,
                limit=8,
                minimum_score=0.2,
            )
        else:
            evidence = {
                "results": [],
                "context_text": "",
            }

        results = evidence.get("results") or []
        selected_mode = select_project_ask_mode(mode, question, results)
        evidence_cards = build_evidence_cards(
            project_id=project_id,
            thread_id=str(session.id or ""),
            rows=results,
            mode=selected_mode,
        )
        evidence_refs = [card.internal_ref for card in evidence_cards]
        source_names = [card.source_name for card in evidence_cards]
        context_text_parts = [
            (evidence.get("context_text") or "").strip(),
            memory_context_text.strip(),
        ]
        context_text = "\n\n".join(part for part in context_text_parts if part)
        if not results and not memory_context_text.strip():
            context_text = NO_EVIDENCE_CONTEXT

        await record_tool_call(
            run.id,
            title="检索项目证据",
            tool_name="build_multimodal_evidence",
            agent_name="evidence_agent",
            input_json={
                "question": question,
                "requested_mode": mode,
                "agent": agent,
                "source_ids": scoped_source_ids,
                "note_ids": scoped_note_ids,
                "memory_ids": selected_memory_ids,
            },
            output_json={
                "result_count": len(results),
                "selected_memory_count": len(selected_memory_ids),
                "selected_mode": selected_mode,
            },
            evidence_refs=evidence_refs,
        )
        await record_evidence_read(
            run.id,
            title="整理证据卡片",
            agent_name="evidence_agent",
            output_json={
                "evidence_card_count": len(evidence_cards),
                "selected_memory_count": len(selected_memory_ids),
            },
            evidence_refs=evidence_refs,
        )

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

        confidence = _estimate_confidence(results, selected_mode)
        suggested_followups = _build_suggested_followups(
            question,
            selected_mode,
            source_names,
            bool(evidence_cards),
        )

        await record_tool_call(
            run.id,
            title="生成项目回答",
            tool_name="chat_graph.invoke",
            agent_name="answer_agent",
            input_json={
                "thread_id": str(session.id or ""),
                "agent": agent,
                "mode": selected_mode,
            },
            output_json={
                "answer_length": len(answer),
                "confidence": confidence,
            },
            evidence_refs=evidence_refs,
            output_refs=[str(session.id or "")],
        )
        response = AskResponse(
            answer=answer,
            confidence=confidence,
            evidence_cards=evidence_cards,
            memory_updates=[],
            run_id=run.id,
            suggested_followups=suggested_followups,
            mode=selected_mode,
            thread_id=str(session.id or ""),
        )
        await _save_thread_state(
            str(session.id or ""),
            project_id,
            latest_response=response,
            source_ids=scoped_source_ids,
            note_ids=scoped_note_ids,
            memory_ids=selected_memory_ids,
            agent=agent,
        )

        await record_answer_step(
            run.id,
            title="返回回答结果",
            agent_name="answer_agent",
            output_json={
                "agent": agent,
                "mode": selected_mode,
                "suggested_followup_count": len(suggested_followups),
            },
            evidence_refs=evidence_refs,
            output_refs=[str(session.id or "")],
        )
        await mark_run_completed(
            run.id,
            output_json={
                "agent": agent,
                "mode": selected_mode,
                "confidence": confidence,
                "evidence_card_count": len(evidence_cards),
                "memory_context_count": len(selected_memory_ids),
                "thread_id": str(session.id or ""),
            },
            tool_calls=["build_multimodal_evidence", "chat_graph.invoke"],
            evidence_reads=evidence_refs,
            outputs=[str(session.id or "")],
        )

        return response
    except Exception as exc:
        await mark_run_failed(run.id, str(exc))
        raise


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
    source_ids: Optional[list[str]] = None,
    note_ids: Optional[list[str]] = None,
    memory_ids: Optional[list[str]] = None,
    agent: Optional[str] = None,
) -> AskResponse:
    return await ask_project(
        project_id,
        question,
        mode=mode,
        thread_id=thread_id,
        source_ids=source_ids,
        note_ids=note_ids,
        memory_ids=memory_ids,
        agent=agent,
    )
