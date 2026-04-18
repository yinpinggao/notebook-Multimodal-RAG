from unittest.mock import AsyncMock, patch

import pytest

from api.project_overview_service import (
    get_project_overview,
    queue_project_overview_rebuild,
)
from api.schemas import ArtifactRecord, ProjectSummary
from open_notebook.domain.projects import ProjectTimelineEvent
from open_notebook.project_os.overview_service import ProjectOverviewSnapshot


@pytest.mark.asyncio
@patch(
    "api.project_overview_service.project_os_overview_service.mark_project_overview_status",
    new_callable=AsyncMock,
)
@patch("api.project_overview_service.async_submit_command", new_callable=AsyncMock)
@patch("api.project_overview_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_queue_project_overview_rebuild_submits_command(
    mock_get_project,
    mock_submit_command,
    mock_mark_status,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T08:00:00Z",
        updated_at="2026-04-18T09:00:00Z",
        source_count=1,
        artifact_count=0,
        memory_count=0,
    )
    mock_submit_command.return_value = "command:overview:1"
    mock_mark_status.return_value = None

    response = await queue_project_overview_rebuild("project:demo")

    assert response == {
        "project_id": "project:demo",
        "status": "queued",
        "message": "Project overview rebuild queued.",
        "command_id": "command:overview:1",
    }
    mock_submit_command.assert_awaited_once_with(
        "open_notebook",
        "build_overview",
        {"project_id": "project:demo"},
    )


@pytest.mark.asyncio
@patch(
    "api.project_overview_service.project_os_artifact_service.list_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_overview_service._source_runtime_rows", new_callable=AsyncMock)
@patch(
    "api.project_overview_service.project_os_overview_service.load_project_overview_snapshot",
    new_callable=AsyncMock,
)
@patch("api.project_overview_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_get_project_overview_prefers_snapshot_data(
    mock_get_project,
    mock_load_snapshot,
    mock_source_runtime_rows,
    mock_list_artifacts,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T08:00:00Z",
        updated_at="2026-04-18T09:00:00Z",
        source_count=2,
        artifact_count=2,
        memory_count=0,
    )
    mock_source_runtime_rows.return_value = (
        [
            {
                "id": "source:1",
                "title": "demo.pdf",
                "topics": ["legacy topic"],
                "updated": "2026-04-18T08:30:00Z",
            }
        ],
        {
            "processing_source_count": 0,
            "embedded_source_count": 1,
            "visual_ready_count": 1,
        },
    )
    mock_load_snapshot.return_value = ProjectOverviewSnapshot(
        project_id="project:demo",
        status="completed",
        command_id="command:overview:1",
        topics=["Extracted topic"],
        keywords=["Extracted keyword"],
        risks=["Extracted risk"],
        timeline_events=[
            ProjectTimelineEvent(
                id="timeline:demo:1",
                title="Extracted event",
                description="A snapshot timeline event.",
                occurred_at="2026-04-18",
                source_refs=["source:1#p2"],
            )
        ],
        recommended_questions=["What is the strongest evidence?"],
    )
    mock_list_artifacts.return_value = [
        ArtifactRecord(
            id="artifact:demo",
            project_id="project:demo",
            artifact_type="project_summary",
            title="Demo Summary",
            content_md="# Demo",
            source_refs=["source:1#p2"],
            created_by_run_id="run:artifact001",
            created_at="2026-04-18T09:30:00Z",
            updated_at="2026-04-18T09:31:00Z",
            status="ready",
        )
    ]

    response = await get_project_overview("project:demo")

    assert response.topics == ["Extracted topic"]
    assert response.keywords == ["Extracted keyword"]
    assert response.risks == ["Extracted risk"]
    assert response.timeline_events[0].title == "Extracted event"
    assert response.recommended_questions == ["What is the strongest evidence?"]
    assert response.artifact_count == 2
    assert response.recent_artifacts[0].id == "artifact:demo"
    assert response.recent_artifacts[0].created_by_run_id == "run:artifact001"


@pytest.mark.asyncio
@patch(
    "api.project_overview_service.project_os_artifact_service.list_project_artifacts",
    new_callable=AsyncMock,
)
@patch("api.project_overview_service._source_runtime_rows", new_callable=AsyncMock)
@patch(
    "api.project_overview_service.project_os_overview_service.load_project_overview_snapshot",
    new_callable=AsyncMock,
)
@patch("api.project_overview_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_get_project_overview_handles_absent_artifacts(
    mock_get_project,
    mock_load_snapshot,
    mock_source_runtime_rows,
    mock_list_artifacts,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T08:00:00Z",
        updated_at="2026-04-18T09:00:00Z",
        source_count=2,
        artifact_count=0,
        memory_count=0,
    )
    mock_source_runtime_rows.return_value = (
        [
            {
                "id": "source:1",
                "title": "demo.pdf",
                "topics": ["legacy topic"],
                "updated": "2026-04-18T08:30:00Z",
            }
        ],
        {
            "processing_source_count": 0,
            "embedded_source_count": 1,
            "visual_ready_count": 1,
        },
    )
    mock_load_snapshot.return_value = ProjectOverviewSnapshot(
        project_id="project:demo"
    )
    mock_list_artifacts.return_value = []

    response = await get_project_overview("project:demo")

    assert response.artifact_count == 0
    assert response.recent_artifacts == []
