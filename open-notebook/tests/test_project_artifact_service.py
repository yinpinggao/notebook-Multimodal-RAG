from unittest.mock import AsyncMock, patch

import pytest

from api.project_artifact_service import (
    queue_project_artifact,
    regenerate_project_artifact,
)
from open_notebook.domain.artifacts import ArtifactRecord
from open_notebook.domain.projects import ProjectSummary
from open_notebook.project_os.artifact_service import ArtifactSourceSnapshot


@pytest.mark.asyncio
@patch(
    "api.project_artifact_service.project_os_artifact_service.mark_project_artifact_status",
    new_callable=AsyncMock,
)
@patch("api.project_artifact_service.async_submit_command", new_callable=AsyncMock)
@patch(
    "api.project_artifact_service.project_os_artifact_service.initialize_project_artifact",
    new_callable=AsyncMock,
)
@patch("api.project_artifact_service._resolve_source_snapshot", new_callable=AsyncMock)
@patch("api.project_artifact_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_queue_project_artifact_submits_generation_command(
    mock_get_project,
    mock_resolve_snapshot,
    mock_initialize_artifact,
    mock_submit_command,
    mock_mark_status,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        source_count=2,
        artifact_count=0,
        memory_count=0,
    )
    mock_resolve_snapshot.return_value = ArtifactSourceSnapshot(
        origin_kind="overview",
        label="Demo Project",
        summary="Demo summary",
        source_refs=["source:1#p1"],
    )
    mock_initialize_artifact.return_value = ArtifactRecord(
        id="artifact:demo",
        project_id="project:demo",
        artifact_type="project_summary",
        title="Demo Summary",
        content_md="",
        source_refs=["source:1#p1"],
        created_by_run_id="run:artifact001",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        status="queued",
        origin_kind="overview",
    )
    mock_submit_command.return_value = "command:artifact:1"
    mock_mark_status.return_value = ArtifactRecord(
        id="artifact:demo",
        project_id="project:demo",
        artifact_type="project_summary",
        title="Demo Summary",
        content_md="",
        source_refs=["source:1#p1"],
        created_by_run_id="run:artifact001",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:01Z",
        status="queued",
        origin_kind="overview",
        command_id="command:artifact:1",
    )

    response = await queue_project_artifact(
        "project:demo",
        artifact_type="project_summary",
        origin_kind="overview",
    )

    assert response.artifact_id == "artifact:demo"
    assert response.command_id == "command:artifact:1"
    assert response.status == "queued"
    mock_submit_command.assert_awaited_once_with(
        "open_notebook",
        "generate_artifact",
        {
            "project_id": "project:demo",
            "artifact_id": "artifact:demo",
        },
    )


@pytest.mark.asyncio
@patch(
    "api.project_artifact_service.project_os_artifact_service.mark_project_artifact_status",
    new_callable=AsyncMock,
)
@patch("api.project_artifact_service.async_submit_command", new_callable=AsyncMock)
@patch(
    "api.project_artifact_service.project_os_artifact_service.update_project_artifact_source_snapshot",
    new_callable=AsyncMock,
)
@patch("api.project_artifact_service._resolve_source_snapshot", new_callable=AsyncMock)
@patch(
    "api.project_artifact_service.project_os_artifact_service.load_project_artifact_for_project",
    new_callable=AsyncMock,
)
@patch("api.project_artifact_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_regenerate_project_artifact_reuses_origin_and_requeues(
    mock_get_project,
    mock_load_artifact,
    mock_resolve_snapshot,
    mock_update_snapshot,
    mock_submit_command,
    mock_mark_status,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        source_count=2,
        artifact_count=0,
        memory_count=0,
    )
    mock_load_artifact.return_value = ArtifactRecord(
        id="artifact:demo",
        project_id="project:demo",
        artifact_type="diff_report",
        title="Demo Diff",
        content_md="# Old",
        source_refs=["source:1#p1"],
        created_by_run_id="run:artifact001",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:10Z",
        status="ready",
        origin_kind="compare",
        origin_id="cmp_demo",
    )
    mock_resolve_snapshot.return_value = ArtifactSourceSnapshot(
        origin_kind="compare",
        origin_id="cmp_demo",
        label="A vs B",
        summary="Diff summary",
        source_refs=["source:1#p1", "source:2#p2"],
    )
    mock_submit_command.return_value = "command:artifact:2"
    mock_mark_status.side_effect = [
        ArtifactRecord(
            id="artifact:demo",
            project_id="project:demo",
            artifact_type="diff_report",
            title="Demo Diff",
            content_md="",
            source_refs=["source:1#p1", "source:2#p2"],
            created_by_run_id="run:artifact002",
            created_at="2026-04-18T12:00:00Z",
            updated_at="2026-04-18T12:00:11Z",
            status="queued",
            origin_kind="compare",
            origin_id="cmp_demo",
        ),
        ArtifactRecord(
            id="artifact:demo",
            project_id="project:demo",
            artifact_type="diff_report",
            title="Demo Diff",
            content_md="",
            source_refs=["source:1#p1", "source:2#p2"],
            created_by_run_id="run:artifact002",
            created_at="2026-04-18T12:00:00Z",
            updated_at="2026-04-18T12:00:12Z",
            status="queued",
            origin_kind="compare",
            origin_id="cmp_demo",
            command_id="command:artifact:2",
        ),
    ]

    response = await regenerate_project_artifact("project:demo", "artifact:demo")

    assert response.artifact_id == "artifact:demo"
    assert response.command_id == "command:artifact:2"
    assert response.created_by_run_id == "run:artifact002"
    mock_update_snapshot.assert_awaited_once()
    mock_submit_command.assert_awaited_once_with(
        "open_notebook",
        "generate_artifact",
        {
            "project_id": "project:demo",
            "artifact_id": "artifact:demo",
        },
    )
