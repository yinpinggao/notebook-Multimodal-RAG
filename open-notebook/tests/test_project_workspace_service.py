from unittest.mock import AsyncMock, patch

import pytest

from api.project_workspace_service import (
    create_demo_project,
    get_project,
    list_projects,
)
from api.schemas import ProjectSummary


@pytest.mark.asyncio
@patch(
    "api.project_workspace_service.project_os_artifact_service.count_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_workspace_service.count_project_memories", new_callable=AsyncMock)
@patch("api.project_workspace_service.get_project_last_run_at", new_callable=AsyncMock)
@patch("api.project_workspace_service.seekdb_business_store.notebook_rows", new_callable=AsyncMock)
async def test_list_projects_populates_artifact_counts(
    mock_notebook_rows,
    mock_get_project_last_run_at,
    mock_count_memories,
    mock_count_artifacts,
):
    mock_notebook_rows.return_value = [
        {
            "id": "project:demo",
            "name": "Demo Project",
            "description": "Notebook-backed project",
            "archived": False,
            "created": "2026-04-18T08:00:00Z",
            "updated": "2026-04-18T09:00:00Z",
            "source_count": 2,
        },
        {
            "id": "project:ops",
            "name": "Ops Project",
            "description": "Archived project",
            "archived": True,
            "created": "2026-04-18T07:00:00Z",
            "updated": "2026-04-18T08:30:00Z",
            "source_count": 1,
        },
    ]
    mock_count_artifacts.side_effect = [3, 1]
    mock_count_memories.side_effect = [2, 0]
    mock_get_project_last_run_at.side_effect = [
        "2026-04-18T09:30:00Z",
        None,
    ]

    projects = await list_projects()

    assert [project.artifact_count for project in projects] == [3, 1]
    assert [project.memory_count for project in projects] == [2, 0]
    assert [project.last_run_at for project in projects] == [
        "2026-04-18T09:30:00Z",
        None,
    ]
    assert projects[0].status == "active"
    assert projects[1].status == "archived"


@pytest.mark.asyncio
@patch(
    "api.project_workspace_service.project_os_artifact_service.count_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_workspace_service.count_project_memories", new_callable=AsyncMock)
@patch("api.project_workspace_service.get_project_last_run_at", new_callable=AsyncMock)
@patch("api.project_workspace_service.seekdb_business_store.notebook_row", new_callable=AsyncMock)
async def test_get_project_populates_artifact_count(
    mock_notebook_row,
    mock_get_project_last_run_at,
    mock_count_memories,
    mock_count_artifacts,
):
    mock_notebook_row.return_value = {
        "id": "project:demo",
        "name": "Demo Project",
        "description": "Notebook-backed project",
        "archived": False,
        "created": "2026-04-18T08:00:00Z",
        "updated": "2026-04-18T09:00:00Z",
        "source_count": 2,
    }
    mock_count_artifacts.return_value = 4
    mock_count_memories.return_value = 3
    mock_get_project_last_run_at.return_value = "2026-04-18T09:45:00Z"

    project = await get_project("project:demo")

    assert project.id == "project:demo"
    assert project.artifact_count == 4
    assert project.memory_count == 3
    assert project.last_run_at == "2026-04-18T09:45:00Z"


@pytest.mark.asyncio
@patch("api.project_workspace_service.get_project", new_callable=AsyncMock)
@patch("api.project_workspace_service.ensure_demo_project", new_callable=AsyncMock)
async def test_create_demo_project_returns_project_summary(
    mock_ensure_demo_project,
    mock_get_project,
):
    mock_ensure_demo_project.return_value = "project:demo"
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="智研舱 Demo 项目",
        description="用于 3 分钟比赛演示的预置项目空间。",
        status="active",
        created_at="2026-04-19T08:00:00Z",
        updated_at="2026-04-19T08:05:00Z",
        source_count=2,
        artifact_count=1,
        memory_count=2,
        last_run_at="2026-04-19T08:05:00Z",
    )

    project = await create_demo_project()

    assert project.id == "project:demo"
    assert project.name == "智研舱 Demo 项目"
    mock_ensure_demo_project.assert_awaited_once_with()
    mock_get_project.assert_awaited_once_with("project:demo")
