from unittest.mock import AsyncMock, patch

import pytest

from api.project_workspace_service import get_project, list_projects


@pytest.mark.asyncio
@patch(
    "api.project_workspace_service.project_os_artifact_service.count_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_workspace_service.seekdb_business_store.notebook_rows", new_callable=AsyncMock)
async def test_list_projects_populates_artifact_counts(
    mock_notebook_rows,
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

    projects = await list_projects()

    assert [project.artifact_count for project in projects] == [3, 1]
    assert projects[0].status == "active"
    assert projects[1].status == "archived"


@pytest.mark.asyncio
@patch(
    "api.project_workspace_service.project_os_artifact_service.count_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_workspace_service.seekdb_business_store.notebook_row", new_callable=AsyncMock)
async def test_get_project_populates_artifact_count(
    mock_notebook_row,
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

    project = await get_project("project:demo")

    assert project.id == "project:demo"
    assert project.artifact_count == 4
