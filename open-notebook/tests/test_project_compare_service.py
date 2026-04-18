from unittest.mock import AsyncMock, patch

import pytest

from api.project_compare_service import export_project_compare, queue_project_compare
from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.domain.evidence import CompareSummary
from open_notebook.domain.projects import ProjectSummary
from open_notebook.exceptions import InvalidInputError


@pytest.mark.asyncio
@patch(
    "api.project_compare_service.project_os_compare_service.mark_project_compare_status",
    new_callable=AsyncMock,
)
@patch("api.project_compare_service.async_submit_command", new_callable=AsyncMock)
@patch(
    "api.project_compare_service.project_os_compare_service.initialize_project_compare",
    new_callable=AsyncMock,
)
@patch("api.project_compare_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_queue_project_compare_submits_command(
    mock_get_project,
    mock_initialize_compare,
    mock_submit_command,
    mock_mark_status,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="",
        status="active",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        source_count=2,
        artifact_count=0,
        memory_count=0,
    )
    mock_initialize_compare.return_value = ProjectCompareRecord(
        id="cmp_demo",
        project_id="project:demo",
        compare_mode="general",
        source_a_id="source:a",
        source_b_id="source:b",
        source_a_title="A",
        source_b_title="B",
        status="queued",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        result=None,
    )
    mock_submit_command.return_value = "command:compare:1"
    mock_mark_status.return_value = ProjectCompareRecord(
        id="cmp_demo",
        project_id="project:demo",
        compare_mode="general",
        source_a_id="source:a",
        source_b_id="source:b",
        source_a_title="A",
        source_b_title="B",
        status="queued",
        command_id="command:compare:1",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:01Z",
        result=None,
    )

    response = await queue_project_compare(
        "project:demo",
        source_a_id="source:a",
        source_b_id="source:b",
        compare_mode="general",
    )

    assert response.compare_id == "cmp_demo"
    assert response.status == "queued"
    assert response.command_id == "command:compare:1"
    mock_submit_command.assert_awaited_once_with(
        "open_notebook",
        "compare_sources",
        {
          "project_id": "project:demo",
          "compare_id": "cmp_demo",
          "source_a_id": "source:a",
          "source_b_id": "source:b",
          "compare_mode": "general",
        },
    )


@pytest.mark.asyncio
@patch("api.project_compare_service.get_project_compare", new_callable=AsyncMock)
async def test_export_project_compare_returns_markdown(mock_get_compare):
    mock_get_compare.return_value = ProjectCompareRecord(
        id="cmp_demo",
        project_id="project:demo",
        compare_mode="general",
        source_a_id="source:a",
        source_b_id="source:b",
        source_a_title="A",
        source_b_title="B",
        status="completed",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:01Z",
        result=CompareSummary(summary="done"),
    )

    response = await export_project_compare("project:demo", "cmp_demo")

    assert response.compare_id == "cmp_demo"
    assert response.format == "markdown"
    assert "# 对比报告" in response.content


@pytest.mark.asyncio
@patch("api.project_compare_service.get_project_compare", new_callable=AsyncMock)
async def test_export_project_compare_rejects_unready_result(mock_get_compare):
    mock_get_compare.return_value = ProjectCompareRecord(
        id="cmp_demo",
        project_id="project:demo",
        compare_mode="general",
        source_a_id="source:a",
        source_b_id="source:b",
        source_a_title="A",
        source_b_title="B",
        status="queued",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:01Z",
        result=None,
    )

    with pytest.raises(InvalidInputError, match="not ready"):
        await export_project_compare("project:demo", "cmp_demo")
