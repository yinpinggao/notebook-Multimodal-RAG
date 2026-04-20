from unittest.mock import AsyncMock, patch

import pytest

from api.project_workspace_service import (
    create_demo_project,
    derive_project_phase,
    get_project,
    list_projects,
)
from api.schemas import ArtifactRecord, ProjectSummary
from open_notebook.domain.runs import AgentRun


@pytest.mark.asyncio
@patch(
    "api.project_workspace_service.project_os_artifact_service.list_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_workspace_service.count_project_memories", new_callable=AsyncMock)
@patch("api.project_workspace_service.list_project_runs", new_callable=AsyncMock)
@patch("api.project_workspace_service.seekdb_business_store.notebook_rows", new_callable=AsyncMock)
async def test_list_projects_populates_artifact_counts(
    mock_notebook_rows,
    mock_list_project_runs,
    mock_count_memories,
    mock_list_artifacts,
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
    mock_list_artifacts.side_effect = [
        [
            ArtifactRecord(
                id="artifact:1",
                project_id="project:demo",
                artifact_type="project_summary",
                title="Demo Summary",
                content_md="# Demo",
                source_refs=[],
                created_by_run_id="run:artifact:1",
                created_at="2026-04-18T09:10:00Z",
                updated_at="2026-04-18T09:10:00Z",
                status="ready",
            ),
            ArtifactRecord(
                id="artifact:2",
                project_id="project:demo",
                artifact_type="defense_outline",
                title="Defense Outline",
                content_md="# Outline",
                source_refs=[],
                created_by_run_id="run:artifact:2",
                created_at="2026-04-18T09:20:00Z",
                updated_at="2026-04-18T09:20:00Z",
                status="draft",
            ),
            ArtifactRecord(
                id="artifact:3",
                project_id="project:demo",
                artifact_type="qa_cards",
                title="Archived Cards",
                content_md="# Archived",
                source_refs=[],
                created_by_run_id="run:artifact:3",
                created_at="2026-04-18T09:25:00Z",
                updated_at="2026-04-18T09:25:00Z",
                status="archived",
            ),
        ],
        [
            ArtifactRecord(
                id="artifact:ops:1",
                project_id="project:ops",
                artifact_type="project_summary",
                title="Ops Summary",
                content_md="# Ops",
                source_refs=[],
                created_by_run_id="run:ops:1",
                created_at="2026-04-18T08:20:00Z",
                updated_at="2026-04-18T08:20:00Z",
                status="ready",
            )
        ],
    ]
    mock_count_memories.side_effect = [2, 0]
    mock_list_project_runs.side_effect = [
        [
            AgentRun(
                id="run:ask:1",
                project_id="project:demo",
                run_type="ask",
                status="completed",
                created_at="2026-04-18T09:30:00Z",
            )
        ],
        [],
    ]

    projects = await list_projects()

    assert [project.artifact_count for project in projects] == [2, 1]
    assert [project.memory_count for project in projects] == [2, 0]
    assert [project.last_run_at for project in projects] == [
        "2026-04-18T09:30:00Z",
        None,
    ]
    assert [project.phase for project in projects] == ["ask", "outputs"]
    assert [project.latest_output_title for project in projects] == [
        "Demo Summary",
        "Ops Summary",
    ]
    assert [project.latest_run_status for project in projects] == ["completed", None]
    assert projects[0].status == "active"
    assert projects[1].status == "archived"


@pytest.mark.asyncio
@patch(
    "api.project_workspace_service.project_os_artifact_service.list_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_workspace_service.count_project_memories", new_callable=AsyncMock)
@patch("api.project_workspace_service.list_project_runs", new_callable=AsyncMock)
@patch("api.project_workspace_service.seekdb_business_store.notebook_row", new_callable=AsyncMock)
async def test_get_project_populates_artifact_count(
    mock_notebook_row,
    mock_list_project_runs,
    mock_count_memories,
    mock_list_artifacts,
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
    mock_list_artifacts.return_value = [
        ArtifactRecord(
            id="artifact:1",
            project_id="project:demo",
            artifact_type="project_summary",
            title="Demo Summary",
            content_md="# Demo",
            source_refs=[],
            created_by_run_id="run:artifact:1",
            created_at="2026-04-18T09:20:00Z",
            updated_at="2026-04-18T09:20:00Z",
            status="ready",
        ),
        ArtifactRecord(
            id="artifact:2",
            project_id="project:demo",
            artifact_type="defense_outline",
            title="Defense Outline",
            content_md="# Outline",
            source_refs=[],
            created_by_run_id="run:artifact:2",
            created_at="2026-04-18T09:22:00Z",
            updated_at="2026-04-18T09:22:00Z",
            status="draft",
        ),
        ArtifactRecord(
            id="artifact:3",
            project_id="project:demo",
            artifact_type="qa_cards",
            title="Failed Cards",
            content_md="# Failed",
            source_refs=[],
            created_by_run_id="run:artifact:3",
            created_at="2026-04-18T09:23:00Z",
            updated_at="2026-04-18T09:23:00Z",
            status="failed",
        ),
    ]
    mock_count_memories.return_value = 3
    mock_list_project_runs.return_value = [
        AgentRun(
            id="run:compare:1",
            project_id="project:demo",
            run_type="compare",
            status="running",
            created_at="2026-04-18T09:45:00Z",
        )
    ]

    project = await get_project("project:demo")

    assert project.id == "project:demo"
    assert project.artifact_count == 2
    assert project.memory_count == 3
    assert project.last_run_at == "2026-04-18T09:45:00Z"
    assert project.phase == "compare"
    assert project.latest_output_title == "Demo Summary"
    assert project.latest_run_status == "running"


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


@pytest.mark.parametrize(
    ("source_count", "memory_count", "latest_run", "latest_artifact", "expected"),
    [
        (0, 0, None, None, "collect"),
        (1, 0, None, None, "ask"),
        (1, 2, None, None, "memory"),
        (
            1,
            0,
            None,
            ArtifactRecord(
                id="artifact:1",
                project_id="project:demo",
                artifact_type="project_summary",
                title="Summary",
                content_md="# Summary",
                source_refs=[],
                created_by_run_id="run:artifact:1",
                created_at="2026-04-18T09:00:00Z",
                updated_at="2026-04-18T09:00:00Z",
                status="ready",
            ),
            "outputs",
        ),
        (
            2,
            1,
            AgentRun(
                id="run:compare:1",
                project_id="project:demo",
                run_type="compare",
                status="running",
                created_at="2026-04-18T09:00:00Z",
            ),
            None,
            "compare",
        ),
        (
            2,
            1,
            AgentRun(
                id="run:ask:1",
                project_id="project:demo",
                run_type="ask",
                status="failed",
                created_at="2026-04-18T09:00:00Z",
            ),
            None,
            "runs",
        ),
    ],
)
def test_derive_project_phase(
    source_count,
    memory_count,
    latest_run,
    latest_artifact,
    expected,
):
    assert (
        derive_project_phase(
            source_count=source_count,
            memory_count=memory_count,
            latest_run=latest_run,
            latest_artifact=latest_artifact,
        )
        == expected
    )
