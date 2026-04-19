from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.project_os.demo_service import (
    DEMO_PROJECT_DESCRIPTION,
    DEMO_PROJECT_NAME,
    _index_demo_source,
    _upsert_demo_note_index,
    ensure_demo_project,
)


@pytest.mark.asyncio
@patch("open_notebook.project_os.demo_service._ensure_demo_artifact", new_callable=AsyncMock)
@patch("open_notebook.project_os.demo_service._ensure_demo_memories", new_callable=AsyncMock)
@patch("open_notebook.project_os.demo_service._ensure_demo_compare", new_callable=AsyncMock)
@patch(
    "open_notebook.project_os.demo_service.build_and_store_project_overview",
    new_callable=AsyncMock,
)
@patch("open_notebook.project_os.demo_service._ensure_demo_notes", new_callable=AsyncMock)
@patch("open_notebook.project_os.demo_service._ensure_demo_sources", new_callable=AsyncMock)
@patch(
    "open_notebook.project_os.demo_service.seekdb_business_store.notebook_rows",
    new_callable=AsyncMock,
)
async def test_ensure_demo_project_repairs_existing_project(
    mock_notebook_rows,
    mock_ensure_demo_sources,
    mock_ensure_demo_notes,
    mock_build_overview,
    mock_ensure_demo_compare,
    mock_ensure_demo_memories,
    mock_ensure_demo_artifact,
):
    mock_notebook_rows.return_value = [
        {
            "id": "project:demo",
            "name": DEMO_PROJECT_NAME,
            "description": DEMO_PROJECT_DESCRIPTION,
        }
    ]
    mock_ensure_demo_sources.return_value = [
        SimpleNamespace(id="source:1"),
        SimpleNamespace(id="source:2"),
    ]
    mock_ensure_demo_compare.return_value = SimpleNamespace(id="compare:1")

    project_id = await ensure_demo_project()

    assert project_id == "project:demo"
    mock_ensure_demo_sources.assert_awaited_once_with("project:demo")
    mock_ensure_demo_notes.assert_awaited_once_with("project:demo")
    mock_build_overview.assert_awaited_once_with("project:demo")
    mock_ensure_demo_compare.assert_awaited_once()
    mock_ensure_demo_memories.assert_awaited_once_with("project:demo")
    mock_ensure_demo_artifact.assert_awaited_once()


@pytest.mark.asyncio
@patch("open_notebook.project_os.demo_service.ai_index_store.upsert_source_chunks", new_callable=AsyncMock)
@patch("open_notebook.project_os.demo_service.generate_embeddings", new_callable=AsyncMock)
async def test_index_demo_source_generates_chunk_embeddings(
    mock_generate_embeddings,
    mock_upsert_source_chunks,
):
    mock_generate_embeddings.return_value = [[0.1, 0.2]]
    source = SimpleNamespace(
        id="source:demo",
        title="创新点答辩备忘",
        full_text="创新点在于项目主线和证据卡片。",
        updated="2026-04-19 17:00:00",
    )

    await _index_demo_source(
        source,
        project_id="project:demo",
        filename="innovation_brief.md",
    )

    mock_generate_embeddings.assert_awaited_once()
    mock_upsert_source_chunks.assert_awaited_once()
    assert mock_upsert_source_chunks.await_args.args[3] == [[0.1, 0.2]]
    assert mock_upsert_source_chunks.await_args.kwargs["chunk_metadata"][0]["filename"] == "innovation_brief.md"


@pytest.mark.asyncio
@patch("open_notebook.project_os.demo_service.ai_index_store.upsert_note_index", new_callable=AsyncMock)
@patch("open_notebook.project_os.demo_service.generate_embedding", new_callable=AsyncMock)
async def test_upsert_demo_note_index_generates_note_embedding(
    mock_generate_embedding,
    mock_upsert_note_index,
):
    mock_generate_embedding.return_value = [0.3, 0.4]
    note = SimpleNamespace(
        id="note:demo",
        title="评委追问清单",
        content="如果只剩一分钟，先保 overview、evidence、outputs。",
        updated="2026-04-19 17:00:00",
    )

    await _upsert_demo_note_index(note, "project:demo")

    mock_generate_embedding.assert_awaited_once()
    assert mock_upsert_note_index.await_args.kwargs["embedding"] == [0.3, 0.4]
