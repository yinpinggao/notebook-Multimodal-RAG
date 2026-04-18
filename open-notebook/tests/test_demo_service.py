from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.project_os.demo_service import (
    DEMO_PROJECT_DESCRIPTION,
    DEMO_PROJECT_NAME,
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
