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


# --- Streaming helpers ---

async def stream_vrag_events(
    question: str,
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

    memory_graph = checkpoint_saver.load_memory_graph(session_id)
    if memory_graph is None:
        memory_graph = MultimodalMemoryGraph()

    evidence = checkpoint_saver.load_collected_evidence(session_id)

    _, create_initial_state = create_vrag_workflow(tools, max_steps=max_steps)
    initial_state = create_initial_state(
        question=question,
        source_ids=source_ids or [],
        context=context,
    )
    initial_state.memory_graph = memory_graph
    initial_state.collected_evidence = evidence

    graph = create_vrag_graph(tools)

    try:
        async for event in graph.astream(initial_state):
            for node_name, node_output in event.items():
                if "dag_updates" in node_output:
                    for update in node_output["dag_updates"]:
                        yield f"data: {json.dumps({'type': 'dag_update', 'node': node_name, **update})}\n\n"
                if node_output.get("is_complete"):
                    yield f"data: {json.dumps({'type': 'complete', 'answer': node_output.get('final_answer', '')})}\n\n"
                if node_output.get("error"):
                    yield f"data: {json.dumps({'type': 'error', 'error': node_output['error']})}\n\n"

        checkpoint_saver.checkpoint_state(
            session_id=session_id,
            memory_graph=initial_state.memory_graph,
            evidence=initial_state.collected_evidence,
        )
    except Exception as e:
        logger.error(f"VRAG streaming failed: {e}")
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

    from open_notebook.ai.models import model_manager
    from open_notebook.ai.provision import provision_langchain_model
    from open_notebook.vrag.checkpoint import SeekDBSaver
    from open_notebook.vrag.search_engine import VRAGSearchEngine
    from open_notebook.vrag.tools import VRAGTools

    # Get embedding model via model_manager (supports domestic Chinese models)
    embedding_model = await model_manager.get_default_model("embedding")
    logger.info(f"VRAG embedding model: {embedding_model}")

    search_engine = VRAGSearchEngine(
        retrieval_service=ai_retrieval_service,
        embedding_dim=768,
        default_top_k=5,
        # Legacy OpenAI CLIP functions (used if embedding_model is not available)
        embed_text_fn=embed_text,
        embed_image_fn=embed_image,
        # Domestic embedding model via Esperanto (preferred)
        embedding_model=embedding_model,
    )
    logger.info(f"VRAG search engine created with embedding_model: {embedding_model}")

    llm = await provision_langchain_model(content="", model_id=None, default_type="chat")
    logger.info(f"VRAG LLM model: {llm}")

    tools = VRAGTools(
        search_engine=search_engine,
        llm_client=llm,
        include_image_base64=False,
    )

    checkpoint_saver = SeekDBSaver(seekdb_client)
    session_id = request.session_id or f"vrag_{uuid.uuid4().hex[:12]}"
    checkpoint_saver.save_session(session_id, request.notebook_id)

    if request.stream:
        return StreamingResponse(
            stream_vrag_events(
                question=request.question,
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

    agent = VRAGAgent(
        tools=tools,
        llm_client=llm,
        max_steps=request.max_steps,
    )
    result = agent.run(
        question=request.question,
        source_ids=request.source_ids,
    )
    checkpoint_saver.checkpoint_state(
        session_id=session_id,
        memory_graph=result.memory_graph,
        evidence=result.collected_evidence,
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
    from open_notebook.ai.models import model_manager
    from open_notebook.ai.provision import provision_langchain_model
    from open_notebook.vrag.search_engine import VRAGSearchEngine
    from open_notebook.vrag.tools import VRAGTools

    # Get embedding model via model_manager (supports domestic Chinese models)
    embedding_model = await model_manager.get_default_model("embedding")

    search_engine = VRAGSearchEngine(
        retrieval_service=ai_retrieval_service,
        embedding_dim=768,
        default_top_k=request.image_top_k,
        # Legacy OpenAI CLIP functions (used if embedding_model is not available)
        embed_text_fn=embed_text,
        embed_image_fn=embed_image,
        # Domestic embedding model via Esperanto (preferred)
        embedding_model=embedding_model,
    )

    llm = await provision_langchain_model(content="", model_id=None, default_type="chat")

    tools = VRAGTools(
        search_engine=search_engine,
        llm_client=llm,
        include_image_base64=request.include_image_base64,
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

    indexer = VRAGIndexer(
        retrieval_service=ai_retrieval_service,
        seekdb_client=seekdb_client,
        # Legacy OpenAI CLIP functions (used if embedding_model is not available)
        embed_text_fn=embed_text,
        embed_image_fn=embed_image,
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
    from open_notebook.ai.models import model_manager
    from open_notebook.ai.provision import provision_langchain_model
    from open_notebook.vrag.search_engine import VRAGSearchEngine
    from open_notebook.vrag.tools import VRAGTools

    # Get embedding model via model_manager (supports domestic Chinese models)
    embedding_model = await model_manager.get_default_model("embedding")

    search_engine = VRAGSearchEngine(
        retrieval_service=ai_retrieval_service,
        # Legacy OpenAI CLIP functions (used if embedding_model is not available)
        embed_text_fn=embed_text,
        embed_image_fn=embed_image,
        # Domestic embedding model via Esperanto (preferred)
        embedding_model=embedding_model,
    )

    llm = await provision_langchain_model(content="", model_id=None, default_type="chat")

    tools = VRAGTools(
        search_engine=search_engine,
        llm_client=llm,
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

    indexer = VRAGIndexer(
        retrieval_service=ai_retrieval_service,
        seekdb_client=seekdb_client,
        # Legacy OpenAI CLIP functions (used if embedding_model is not available)
        embed_text_fn=embed_text,
        embed_image_fn=embed_image,
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
