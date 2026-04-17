"""Canonical Visual RAG API.

New endpoints live under `/api/visual-rag/*`; `/api/vrag/*` is kept as a
deprecated compatibility alias by including the same route set twice.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.jobs import async_submit_command
from open_notebook.storage.visual_assets import visual_asset_store
from open_notebook.storage.visual_rag import visual_rag_session_store
from open_notebook.vrag.memory import MultimodalMemoryGraph
from open_notebook.vrag.tools import VRAGTools
from open_notebook.vrag.workflow import create_vrag_graph, create_vrag_workflow
from open_notebook.visual_rag.search_engine import VisualAssetSearchEngine


class VisualRAGChatRequest(BaseModel):
    question: str = Field(..., description="User question")
    notebook_id: str = Field(..., description="Notebook ID")
    source_ids: Optional[list[str]] = Field(default=None)
    context: Optional[str] = Field(default="")
    session_id: Optional[str] = Field(default=None)
    max_steps: int = Field(default=10, ge=1, le=20)
    stream: bool = Field(default=True)


class VisualRAGSearchRequest(BaseModel):
    query: str
    source_ids: Optional[list[str]] = None
    image_top_k: int = Field(default=5, ge=1, le=20)
    text_top_k: int = Field(default=5, ge=1, le=20)
    include_image_base64: bool = False


class VisualIndexRequest(BaseModel):
    source_id: str
    generate_summaries: bool = True
    dpi: Optional[int] = None


routes = APIRouter()
router = APIRouter(prefix="/visual-rag", tags=["visual-rag"])
legacy_router = APIRouter(prefix="/vrag", tags=["vrag"])
asset_router = APIRouter(prefix="/visual-assets", tags=["visual-assets"])


def _default_session_title(question: str) -> str:
    normalized = " ".join((question or "").strip().split())
    return normalized[:80] if normalized else "Visual RAG Chat"


def _make_message(message_type: str, content: str, index: int) -> dict[str, str]:
    prefix = "ai" if message_type == "ai" else "human"
    return {
        "id": f"{prefix}-{index}",
        "type": message_type,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _build_session_metadata(
    question: str,
    *,
    title: Optional[str] = None,
    is_complete: bool,
    total_steps: int,
    answer: str = "",
    error: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "title": title or _default_session_title(question),
        "last_question": question,
        "current_answer": answer,
        "last_answer_preview": answer[:200] if answer else "",
        "is_complete": is_complete,
        "total_steps": total_steps,
        "last_error": error,
    }


def _extract_session_title(session: Optional[dict[str, Any]], question: str) -> str:
    metadata = session.get("metadata") if session else None
    if isinstance(metadata, dict) and metadata.get("title"):
        return str(metadata["title"])
    return _default_session_title(question)


async def _build_visual_rag_tools(
    *,
    include_image_base64: bool,
    image_top_k: int = 5,
) -> VRAGTools:
    from open_notebook.ai.provision import provision_langchain_model

    llm = await provision_langchain_model(content="", model_id=None, default_type="chat")
    search_engine = VisualAssetSearchEngine(default_top_k=image_top_k)
    return VRAGTools(
        search_engine=search_engine,
        llm_client=llm,
        include_image_base64=include_image_base64,
    )


def _normalize_dag_update(update: dict[str, Any]) -> dict[str, Any]:
    node_type = update.get("node_type") or update.get("type")
    summary = (
        update.get("summary")
        or update.get("key_insight")
        or update.get("answer_preview")
        or update.get("thought")
        or ""
    )
    if not summary and node_type == "search":
        images_found = int(update.get("images_found") or 0)
        texts_found = int(update.get("texts_found") or 0)
        summary = f"找到 {images_found} 张图片，{texts_found} 段文本"
    elif not summary and node_type == "bbox_crop":
        summary = str(update.get("description") or "已分析局部图片区域")
    elif not summary and node_type == "summarize":
        summary = "已汇总当前证据"
    return {
        **update,
        "node_type": node_type,
        "summary": summary,
    }


def _graph_step_count(memory_graph: Any) -> int:
    node_order = getattr(memory_graph, "node_order", None)
    if isinstance(node_order, list):
        return len(node_order)

    legacy_order = getattr(memory_graph, "order", None)
    if isinstance(legacy_order, list):
        return len(legacy_order)

    nodes = getattr(memory_graph, "nodes", None)
    if isinstance(nodes, dict):
        return len(nodes)
    if isinstance(nodes, list):
        return len(nodes)

    return 0


async def stream_visual_rag_events(
    question: str,
    notebook_id: str,
    source_ids: Optional[list[str]],
    context: str,
    max_steps: int,
    tools: VRAGTools,
    session_id: str,
) -> AsyncIterator[str]:
    session = await visual_rag_session_store.load_session(session_id)
    session_title = _extract_session_title(session, question)
    memory_graph = await visual_rag_session_store.load_memory_graph(session_id)
    if memory_graph is None:
        memory_graph = MultimodalMemoryGraph()

    evidence = await visual_rag_session_store.load_collected_evidence(session_id)
    existing_messages = await visual_rag_session_store.load_messages(session_id)
    user_message = _make_message("human", question, len(existing_messages) + 1)
    persisted_messages = existing_messages + [user_message]

    await visual_rag_session_store.save_session(
        session_id,
        notebook_id,
        metadata=_build_session_metadata(
            question,
            title=session_title,
            is_complete=False,
            total_steps=_graph_step_count(memory_graph),
        ),
    )
    await visual_rag_session_store.checkpoint_state(
        session_id=session_id,
        memory_graph=memory_graph,
        evidence=evidence,
        messages=persisted_messages,
    )

    _, create_initial_state = create_vrag_workflow(tools, max_steps=max_steps)
    initial_state = create_initial_state(
        question=question,
        source_ids=source_ids or [],
        context=context,
    )
    initial_state.messages = list(persisted_messages)
    initial_state.memory_graph = memory_graph
    initial_state.collected_evidence = evidence
    final_answer = ""
    stream_error: Optional[str] = None
    complete_emitted = False
    seen_dag_updates: set[str] = set()
    graph = create_vrag_graph(tools)

    try:
        async for event in graph.astream(initial_state):
            for node_name, node_output in event.items():
                if "dag_updates" in node_output:
                    for update in node_output["dag_updates"]:
                        normalized_update = _normalize_dag_update(update)
                        update_key = json.dumps(
                            normalized_update,
                            sort_keys=True,
                            ensure_ascii=False,
                        )
                        if update_key in seen_dag_updates:
                            continue
                        seen_dag_updates.add(update_key)
                        update_type = normalized_update.get("type")
                        payload = {
                            "type": "dag_update",
                            "node": node_name,
                            "update_type": update_type,
                            **{
                                key: value
                                for key, value in normalized_update.items()
                                if key != "type"
                            },
                        }
                        await visual_rag_session_store.append_event(
                            session_id,
                            "dag_update",
                            payload,
                        )
                        yield f"data: {json.dumps(payload)}\n\n"
                if node_output.get("is_complete"):
                    final_answer = node_output.get("final_answer", "") or final_answer
                    complete_emitted = True
                    yield f"data: {json.dumps({'type': 'complete', 'answer': final_answer})}\n\n"
                if node_output.get("error"):
                    logger.warning(
                        "Visual RAG node %s reported recoverable error: %s",
                        node_name,
                        node_output["error"],
                    )

        final_answer = final_answer or getattr(initial_state, "final_answer", "") or ""
        workflow_complete = bool(getattr(initial_state, "is_complete", False)) or bool(
            final_answer
        )
        if workflow_complete and stream_error is None and not complete_emitted:
            complete_emitted = True
            yield f"data: {json.dumps({'type': 'complete', 'answer': final_answer})}\n\n"

        final_messages = list(persisted_messages)
        if final_answer:
            final_messages.append(_make_message("ai", final_answer, len(final_messages) + 1))
        await visual_rag_session_store.checkpoint_state(
            session_id=session_id,
            memory_graph=initial_state.memory_graph,
            evidence=initial_state.collected_evidence,
            messages=final_messages,
        )
        await visual_rag_session_store.save_session(
            session_id,
            notebook_id,
            metadata=_build_session_metadata(
                question,
                title=session_title,
                is_complete=stream_error is None and workflow_complete,
                total_steps=_graph_step_count(initial_state.memory_graph),
                answer=final_answer,
                error=stream_error,
            ),
        )
    except Exception as e:
        logger.error(f"Visual RAG streaming failed: {e}")
        await visual_rag_session_store.save_session(
            session_id,
            notebook_id,
            metadata=_build_session_metadata(
                question,
                title=session_title,
                is_complete=False,
                total_steps=_graph_step_count(initial_state.memory_graph),
                error=str(e),
            ),
        )
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@routes.post("/chat/stream")
async def visual_rag_chat_stream(request: VisualRAGChatRequest):
    tools = await _build_visual_rag_tools(
        include_image_base64=True,
        image_top_k=5,
    )
    session_id = request.session_id or f"visual_rag_{uuid.uuid4().hex[:12]}"
    existing_session = (
        await visual_rag_session_store.load_session(session_id)
        if request.session_id
        else None
    )
    session_title = _extract_session_title(existing_session, request.question)
    await visual_rag_session_store.save_session(
        session_id,
        request.notebook_id,
        metadata=_build_session_metadata(
            request.question,
            title=session_title,
            is_complete=False,
            total_steps=0,
        ),
    )

    if request.stream:
        return StreamingResponse(
            stream_visual_rag_events(
                question=request.question,
                notebook_id=request.notebook_id,
                source_ids=request.source_ids,
                context=request.context or "",
                max_steps=request.max_steps,
                tools=tools,
                session_id=session_id,
            ),
            media_type="text/event-stream",
            headers={"X-Session-ID": session_id},
        )

    from open_notebook.vrag.agent import VRAGAgent

    agent = VRAGAgent(tools=tools, llm_client=tools.llm_client, max_steps=request.max_steps)
    result = await agent.run(
        question=request.question,
        source_ids=request.source_ids,
        context=request.context or "",
        memory_graph=await visual_rag_session_store.load_memory_graph(session_id),
        collected_evidence=await visual_rag_session_store.load_collected_evidence(session_id),
        messages=await visual_rag_session_store.load_messages(session_id),
    )
    await visual_rag_session_store.checkpoint_state(
        session_id=session_id,
        memory_graph=result.memory_graph,
        evidence=result.collected_evidence,
        messages=result.messages,
    )
    await visual_rag_session_store.save_session(
        session_id,
        request.notebook_id,
        metadata=_build_session_metadata(
            request.question,
            title=session_title,
            is_complete=result.is_complete and not result.error,
            total_steps=len(result.actions),
            answer=result.current_answer,
            error=result.error,
        ),
    )
    return {
        "session_id": session_id,
        "answer": result.current_answer,
        "memory_graph": result.memory_graph.to_dag_json(),
        "total_steps": len(result.actions),
        "is_complete": result.is_complete,
        "error": result.error,
    }


@routes.post("/search")
async def visual_rag_search(request: VisualRAGSearchRequest):
    tools = await _build_visual_rag_tools(
        include_image_base64=request.include_image_base64,
        image_top_k=request.image_top_k,
    )
    result = await tools.search(
        query=request.query,
        source_ids=request.source_ids,
        image_top_k=request.image_top_k,
        text_top_k=request.text_top_k,
    )
    return result.to_dict()


@routes.post("/index")
async def visual_rag_index(request: VisualIndexRequest):
    import commands.visual_rag_commands  # noqa: F401

    command_id = await async_submit_command(
        "open_notebook",
        "index_visual_source",
        {
            "source_id": request.source_id,
            "regenerate": False,
            "generate_summaries": request.generate_summaries,
            "dpi": request.dpi,
        },
    )
    await visual_asset_store.mark_source_index_status(
        request.source_id,
        status="queued",
        command_id=command_id,
    )
    return {"source_id": request.source_id, "command_id": command_id, "status": "queued"}


@routes.post("/reindex")
async def visual_rag_reindex(request: VisualIndexRequest):
    import commands.visual_rag_commands  # noqa: F401

    command_id = await async_submit_command(
        "open_notebook",
        "index_visual_source",
        {
            "source_id": request.source_id,
            "regenerate": True,
            "generate_summaries": request.generate_summaries,
            "dpi": request.dpi,
        },
    )
    await visual_asset_store.mark_source_index_status(
        request.source_id,
        status="queued",
        command_id=command_id,
    )
    return {"source_id": request.source_id, "command_id": command_id, "status": "queued"}


@routes.get("/sessions")
async def visual_rag_list_sessions(
    notebook_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    sessions = await visual_rag_session_store.list_sessions(notebook_id, limit)
    return {"sessions": sessions}


@routes.get("/sessions/{session_id}")
async def visual_rag_get_session(session_id: str):
    session = await visual_rag_session_store.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    memory_graph = await visual_rag_session_store.load_memory_graph(session_id)
    return {
        "session": session,
        "memory_graph": memory_graph.to_dag_json() if memory_graph else None,
        "evidence": await visual_rag_session_store.load_collected_evidence(session_id),
        "messages": await visual_rag_session_store.load_messages(session_id),
    }


@routes.get("/sessions/{session_id}/graph")
async def visual_rag_get_graph(session_id: str):
    memory_graph = await visual_rag_session_store.load_memory_graph(session_id)
    if not memory_graph:
        raise HTTPException(status_code=404, detail="Session not found")
    return memory_graph.to_dag_json()


@routes.delete("/sessions/{session_id}")
async def visual_rag_delete_session(session_id: str):
    deleted = await visual_rag_session_store.delete_session(session_id)
    return {"session_id": session_id, "deleted": deleted}


@asset_router.get("/{asset_id:path}/file")
async def visual_asset_file(asset_id: str):
    asset = await visual_asset_store.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Visual asset not found")
    file_path = visual_asset_store.resolve_file_path(asset)
    if not file_path:
        raise HTTPException(status_code=404, detail="Visual asset file not available")
    return FileResponse(file_path)


router.include_router(routes)
legacy_router.include_router(routes)
