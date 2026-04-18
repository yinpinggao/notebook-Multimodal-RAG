from unittest.mock import AsyncMock, patch

import pytest

from api.project_run_service import get_run, list_runs
from open_notebook.domain.projects import ProjectSummary
from open_notebook.domain.runs import AgentRun


def _project() -> ProjectSummary:
    return ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        source_count=2,
        artifact_count=1,
        memory_count=1,
    )


def _run(run_id: str = "run:demo") -> AgentRun:
    return AgentRun(
        id=run_id,
        project_id="project:demo",
        run_type="compare",
        status="completed",
        input_summary="A vs B",
        selected_skill="compare_sources",
        created_at="2026-04-18T12:00:00Z",
        completed_at="2026-04-18T12:00:05Z",
    )


@pytest.mark.asyncio
@patch("api.project_run_service.list_project_runs", new_callable=AsyncMock)
@patch("api.project_run_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_list_runs_returns_project_runs(mock_get_project, mock_list_project_runs):
    mock_get_project.return_value = _project()
    mock_list_project_runs.return_value = [_run()]

    runs = await list_runs("project:demo")

    assert len(runs) == 1
    assert runs[0].id == "run:demo"
    mock_list_project_runs.assert_awaited_once_with("project:demo")


@pytest.mark.asyncio
@patch("api.project_run_service.load_agent_run_for_project", new_callable=AsyncMock)
@patch("api.project_run_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_get_run_returns_single_run(mock_get_project, mock_load_run):
    mock_get_project.return_value = _project()
    mock_load_run.return_value = _run()

    run = await get_run("project:demo", "run:demo")

    assert run.id == "run:demo"
    mock_load_run.assert_awaited_once_with("project:demo", "run:demo")
