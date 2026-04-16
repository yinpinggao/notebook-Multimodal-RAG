"""VRAG API — FastAPI router for VRAG multimodal retrieval and reasoning.

Provides endpoints for:
- VRAG chat streaming (SSE)
- Session management
- Multimodal search
- Source indexing
- DAG state retrieval
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from open_notebook.seekdb import (
    ai_retrieval_service,
    seekdb_client,
)
from open_notebook.utils.clip_embedding import embed_image, embed_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vrag", tags=["vrag"])


# --- Request/Response Models ---

class VRAGChatRequest(BaseModel):
    """Request model for VRAG chat."""
    question: str = Field(..., description="User's question")
    notebook_id: str = Field(..., description="Notebook ID")
    source_ids: Optional[list[str]] = Field(default=None, description="Source IDs to search within")
    context: Optional[str] = Field(default="", description="Additional context")
    session_id: Optional[str] = Field(default=None, description="Existing session ID")
    max_steps: int = Field(default=10, ge=1, le=20, description="Max reasoning steps")
    stream: bool = Field(default=True, description="Enable SSE streaming")


class VRAGSearchRequest(BaseModel):
    """Request model for direct multimodal search."""
    query: str = Field(..., description="Search query")
    source_ids: Optional[list[str]] = Field(default=None)
    image_top_k: int = Field(default=5, ge=1, le=20)
    text_top_k: int = Field(default=5, ge=1, le=20)
    include_image_base64: bool = Field(default=False)


class VRAGIndexRequest(BaseModel):
    """Request model for indexing a source."""
    source_id: str = Field(..., description="Source ID to index")
    source_path: str = Field(..., description="Path to the source file")
    source_type: str = Field(default="pdf")
    generate_summaries: bool = Field(default=True)
    dpi: Optional[int] = Field(default=None)


class VRAGBBoxCropRequest(BaseModel):
    """Request model for bbox crop."""
    image_path: str = Field(..., description="Path to the source image")
    bbox: list[float] = Field(..., description="Normalized bbox [x1, y1, x2, y2]")
    padding: float = Field(default=0.02)
    output_path: Optional[str] = Field(default=None)
    describe: bool = Field(default=True)


def _embedding_model_name(embedding_model: Any) -> str:
    return str(getattr(embedding_model, "model_name", "") or "").lower()


def _supports_multimodal_embedding_model(embedding_model: Any) -> bool:
    return "clip" in _embedding_model_name(embedding_model)


def _default_session_title(question: str) -> str:
    normalized = " ".join((question or "").strip().split())
    if not normalized:
        return "VRAG Chat"
    return normalized[:80]


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


async def _build_vrag_components(
    *,
    include_image_base64: bool,
    image_top_k: int = 5,
):
    from open_notebook.ai.models import model_manager
    from open_notebook.ai.provision import provision_langchain_model
    from open_notebook.vrag.search_engine import VRAGSearchEngine
    from open_notebook.vrag.tools import VRAGTools

    embedding_model = await model_manager.get_default_model("embedding")
    llm = await provision_langchain_model(content="", model_id=None, default_type="chat")

    if _supports_multimodal_embedding_model(embedding_model):
        embed_text_fn = None
        embed_image_fn = None
    else:
        embed_text_fn = embed_text
        embed_image_fn = embed_image

    search_engine = VRAGSearchEngine(
        retrieval_service=ai_retrieval_service,
        embedding_dim=768,
        default_top_k=image_top_k,
        embed_text_fn=embed_text_fn,
        embed_image_fn=embed_image_fn,
        embedding_model=embedding_model,
    )

    tools = VRAGTools(
        search_engine=search_engine,
        llm_client=llm,
        include_image_base64=include_image_base64,
    )

    return embedding_model, llm, tools


# --- Streaming helpers ---

async def stream_vrag_events(
    question: str,
    notebook_id: str,
    source_ids: Optional[list[str]],
    context: str,
    max_steps: int,
    tools,
    checkpoint_saver,
    session_id: str,
) -> AsyncIterator[str]:
    """Stream VRAG execution events as SSE.

    Yields events as JSON-encoded SSE messages.
    """
    from open_notebook.vrag.memory import MultimodalMemoryGraph
    from open_notebook.vrag.workflow import create_vrag_graph, create_vrag_workflow

    session = checkpoint_saver.load_session(session_id)
    session_title = _extract_session_title(session, question)
    memory_graph = checkpoint_saver.load_memory_graph(session_id)
    if memory_graph is None:
        memory_graph = MultimodalMemoryGraph()

    evidence = checkpoint_saver.load_collected_evidence(session_id)
    existing_messages = checkpoint_saver.load_messages(session_id)
    user_message = _make_message("human", question, len(existing_messages) + 1)
    persisted_messages = existing_messages + [user_message]

    checkpoint_saver.save_session(
        session_id,
        notebook_id,
        metadata=_build_session_metadata(
            question,
            title=session_title,
            is_complete=False,
            total_steps=len(memory_graph.order),
        ),
    )
    checkpoint_saver.checkpoint_state(
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
    initial_state.memory_graph = memory_graph
    initial_state.collected_evidence = evidence
    final_answer = ""
    stream_error: Optional[str] = None

    graph = create_vrag_graph(tools)

    try:
        async for event in graph.astream(initial_state):
            for node_name, node_output in event.items():
                if "dag_updates" in node_output:
                    for update in node_output["dag_updates"]:
                        yield f"data: {json.dumps({'type': 'dag_update', 'node': node_name, **update})}\n\n"
                if node_output.get("is_complete"):
                    final_answer = node_output.get("final_answer", "") or final_answer
                    yield f"data: {json.dumps({'type': 'complete', 'answer': final_answer})}\n\n"
                if node_output.get("error"):
                    stream_error = node_output["error"]
                    yield f"data: {json.dumps({'type': 'error', 'error': stream_error})}\n\n"

        final_messages = list(persisted_messages)
        if final_answer:
            final_messages.append(_make_message("ai", final_answer, len(final_messages) + 1))
        checkpoint_saver.checkpoint_state(
            session_id=session_id,
            memory_graph=initial_state.memory_graph,
            evidence=initial_state.collected_evidence,
            messages=final_messages,
        )
        checkpoint_saver.save_session(
            session_id,
            notebook_id,
            metadata=_build_session_metadata(
                question,
                title=session_title,
                is_complete=stream_error is None and bool(final_answer),
                total_steps=len(initial_state.memory_graph.order),
                answer=final_answer,
                error=stream_error,
            ),
        )
    except Exception as e:
        logger.error(f"VRAG streaming failed: {e}")
        checkpoint_saver.save_session(
            session_id,
            notebook_id,
            metadata=_build_session_metadata(
                question,
                title=session_title,
                is_complete=False,
                total_steps=len(initial_state.memory_graph.order),
                error=str(e),
            ),
        )
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


# --- Endpoints ---

@router.post("/chat/stream")
async def vrag_chat_stream(request: VRAGChatRequest):
    """Start a VRAG chat with streaming response (SSE).

    Uses domestic Chinese embedding models (tongyi, zhipu, wenxin, etc.) via Esperanto
    and domestic vision/language models, as configured in Settings → Models.
    Falls back to OpenAI CLIP and GPT-4o if no domestic models are configured.
    """
    from fastapi.responses import StreamingResponse

    from open_notebook.vrag.checkpoint import SeekDBSaver

    embedding_model, llm, tools = await _build_vrag_components(
        include_image_base64=True,
        image_top_k=5,
    )
    logger.info(f"VRAG embedding model: {embedding_model}")
    logger.info(f"VRAG LLM model: {llm}")

    checkpoint_saver = SeekDBSaver(seekdb_client)
    session_id = request.session_id or f"vrag_{uuid.uuid4().hex[:12]}"
    existing_session = checkpoint_saver.load_session(session_id) if request.session_id else None
    session_title = _extract_session_title(existing_session, request.question)
    checkpoint_saver.save_session(
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
            stream_vrag_events(
                question=request.question,
                notebook_id=request.notebook_id,
                source_ids=request.source_ids,
                context=request.context,
                max_steps=request.max_steps,
                tools=tools,
                checkpoint_saver=checkpoint_saver,
                session_id=session_id,
            ),
            media_type="text/event-stream",
            headers={"X-Session-ID": session_id},
        )

    # Non-streaming path
    from open_notebook.vrag.agent import VRAGAgent

    existing_memory_graph = checkpoint_saver.load_memory_graph(session_id)
    existing_evidence = checkpoint_saver.load_collected_evidence(session_id)
    existing_messages = checkpoint_saver.load_messages(session_id)

    agent = VRAGAgent(
        tools=tools,
        llm_client=llm,
        max_steps=request.max_steps,
    )
    result = await agent.run(
        question=request.question,
        source_ids=request.source_ids,
        context=request.context,
        memory_graph=existing_memory_graph,
        collected_evidence=existing_evidence,
        messages=existing_messages,
    )
    checkpoint_saver.checkpoint_state(
        session_id=session_id,
        memory_graph=result.memory_graph,
        evidence=result.collected_evidence,
        messages=result.messages,
    )
    checkpoint_saver.save_session(
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


@router.post("/search")
async def vrag_search(request: VRAGSearchRequest):
    """Perform direct multimodal search without going through the agent.

    Uses domestic Chinese embedding models (tongyi, zhipu, wenxin, etc.) via Esperanto.
    Falls back to OpenAI CLIP if no domestic models are configured.
    """
    _, _, tools = await _build_vrag_components(
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


@router.post("/index")
async def vrag_index(request: VRAGIndexRequest):
    """Trigger multimodal indexing for a source.

    Uses domestic Chinese embedding models (tongyi, zhipu, wenxin, etc.) via Esperanto
    and domestic vision models for image summarization, as configured in Settings → Models.
    Falls back to OpenAI CLIP and GPT-4o if no domestic models are configured.
    """
    from open_notebook.ai.models import model_manager
    from open_notebook.vrag.indexer import VRAGIndexer

    # Get embedding and vision models via model_manager (supports domestic Chinese models)
    embedding_model = await model_manager.get_default_model("embedding")
    vision_model = await model_manager.get_default_model("vision")
    use_legacy_clip = not _supports_multimodal_embedding_model(embedding_model)

    indexer = VRAGIndexer(
        retrieval_service=ai_retrieval_service,
        seekdb_client=seekdb_client,
        embed_text_fn=embed_text if use_legacy_clip else None,
        embed_image_fn=embed_image if use_legacy_clip else None,
        # Domestic models via Esperanto (preferred)
        embedding_model=embedding_model,
        vision_model=vision_model,
    )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: indexer.index_source(
            source_id=request.source_id,
            source_path=request.source_path,
            source_type=request.source_type,
            generate_summaries=request.generate_summaries,
            dpi=request.dpi,
        ),
    )
    return {"source_id": request.source_id, "indexing_result": result}


@router.post("/bbox/crop")
async def vrag_bbox_crop(request: VRAGBBoxCropRequest):
    """Crop a region from an image using bbox coordinates.

    Uses domestic vision models for describing the cropped region.
    Falls back to OpenAI GPT-4o if no domestic models are configured.
    """
    _, _, tools = await _build_vrag_components(
        include_image_base64=False,
        image_top_k=5,
    )

    result = tools.bbox_crop(
        image_path=request.image_path,
        bbox=request.bbox,
        padding=request.padding,
        output_path=request.output_path,
        describe=request.describe,
    )
    return result.to_dict()


@router.get("/sessions")
async def vrag_list_sessions(
    notebook_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List VRAG sessions."""
    from open_notebook.vrag.checkpoint import SeekDBSaver

    checkpoint_saver = SeekDBSaver(seekdb_client)
    sessions = checkpoint_saver.list_sessions(notebook_id=notebook_id, limit=limit)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def vrag_get_session(session_id: str):
    """Get a VRAG session with its full state."""
    from open_notebook.vrag.checkpoint import SeekDBSaver

    checkpoint_saver = SeekDBSaver(seekdb_client)
    session = checkpoint_saver.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory_graph = checkpoint_saver.load_memory_graph(session_id)
    evidence = checkpoint_saver.load_collected_evidence(session_id)
    messages = checkpoint_saver.load_messages(session_id)

    return {
        "session": session,
        "memory_graph": memory_graph.to_dag_json() if memory_graph else None,
        "evidence": evidence,
        "messages": messages,
    }


@router.get("/sessions/{session_id}/graph")
async def vrag_get_graph(session_id: str):
    """Get the DAG graph for a VRAG session."""
    from open_notebook.vrag.checkpoint import SeekDBSaver

    checkpoint_saver = SeekDBSaver(seekdb_client)
    memory_graph = checkpoint_saver.load_memory_graph(session_id)
    if not memory_graph:
        raise HTTPException(status_code=404, detail="Session not found")
    return memory_graph.to_dag_json()


@router.delete("/sessions/{session_id}")
async def vrag_delete_session(session_id: str):
    """Delete a VRAG session and all its state."""
    from open_notebook.vrag.checkpoint import SeekDBSaver

    checkpoint_saver = SeekDBSaver(seekdb_client)
    deleted = checkpoint_saver.delete_session(session_id)
    return {"session_id": session_id, "deleted": deleted}


@router.post("/reindex")
async def vrag_rebuild_index(request: VRAGIndexRequest):
    """Rebuild the VRAG index for a source.

    Uses domestic Chinese embedding models (tongyi, zhipu, wenxin, etc.) via Esperanto
    and domestic vision models for image summarization, as configured in Settings → Models.
    Falls back to OpenAI CLIP and GPT-4o if no domestic models are configured.
    """
    from open_notebook.ai.models import model_manager
    from open_notebook.vrag.indexer import VRAGIndexer

    # Get embedding and vision models via model_manager (supports domestic Chinese models)
    embedding_model = await model_manager.get_default_model("embedding")
    vision_model = await model_manager.get_default_model("vision")
    use_legacy_clip = not _supports_multimodal_embedding_model(embedding_model)

    indexer = VRAGIndexer(
        retrieval_service=ai_retrieval_service,
        seekdb_client=seekdb_client,
        embed_text_fn=embed_text if use_legacy_clip else None,
        embed_image_fn=embed_image if use_legacy_clip else None,
        # Domestic models via Esperanto (preferred)
        embedding_model=embedding_model,
        vision_model=vision_model,
    )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: indexer.rebuild_index(
            source_id=request.source_id,
            regenerate_embeddings=True,
            regenerate_summaries=request.generate_summaries,
        ),
    )
    return {"source_id": request.source_id, "rebuild_result": result}
