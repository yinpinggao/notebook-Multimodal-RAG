from unittest.mock import AsyncMock, patch

import pytest

from api.project_memory_service import (
    delete_memory_record,
    list_memory_records,
    queue_project_memory_rebuild,
    update_memory_record,
)
from open_notebook.domain.memory import MemoryRecord, SourceReference
from open_notebook.domain.projects import ProjectSummary


def _memory_record(memory_id: str = "mem:demo") -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        scope="project",
        type="fact",
        text="评审要求需要明确列出技术路线。",
        confidence=0.78,
        freshness="2026-04-18T12:00:00Z",
        source_refs=[
            SourceReference(
                source_id="source:1",
                source_name="规则文档",
                page_no=2,
                internal_ref="source:1#p2",
                citation_text="引用：规则文档（第2页）",
            )
        ],
        status="draft",
        decay_policy="normal",
    )


@pytest.mark.asyncio
@patch("api.project_memory_service.list_project_memories", new_callable=AsyncMock)
@patch("api.project_memory_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_list_memory_records_returns_memory_items(
    mock_get_project,
    mock_list_memories,
):
    mock_get_project.return_value = ProjectSummary(
        id="project:demo",
        name="Demo",
        description="Demo project",
        status="active",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:00Z",
        source_count=2,
        artifact_count=1,
        memory_count=0,
    )
    mock_list_memories.return_value = [_memory_record()]

    records = await list_memory_records("project:demo")

    assert len(records) == 1
    assert records[0].id == "mem:demo"
    mock_list_memories.assert_awaited_once_with(
        "project:demo",
        include_deprecated=True,
    )


@pytest.mark.asyncio
@patch("api.project_memory_service.update_project_memory", new_callable=AsyncMock)
@patch("api.project_memory_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_update_memory_record_normalizes_text(
    mock_get_project,
    mock_update_memory,
):
    mock_get_project.return_value = ProjectSummary(
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
    mock_update_memory.return_value = _memory_record()

    await update_memory_record(
        "project:demo",
        "mem:demo",
        text="  评审要求   需要明确列出技术路线。 ",
        status="accepted",
    )

    mock_update_memory.assert_awaited_once_with(
        "project:demo",
        "mem:demo",
        text="评审要求 需要明确列出技术路线。",
        status="accepted",
    )


@pytest.mark.asyncio
@patch("api.project_memory_service.delete_project_memory", new_callable=AsyncMock)
@patch("api.project_memory_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_delete_memory_record_returns_deleted_payload(
    mock_get_project,
    mock_delete_memory,
):
    mock_get_project.return_value = ProjectSummary(
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

    payload = await delete_memory_record("project:demo", "mem:demo")

    assert payload == {
        "project_id": "project:demo",
        "memory_id": "mem:demo",
        "status": "deleted",
    }
    mock_delete_memory.assert_awaited_once_with("project:demo", "mem:demo")


@pytest.mark.asyncio
@patch("api.project_memory_service.record_step", new_callable=AsyncMock)
@patch("api.project_memory_service.mark_project_memory_status", new_callable=AsyncMock)
@patch("api.project_memory_service.async_submit_command", new_callable=AsyncMock)
@patch("api.project_memory_service.create_project_run", new_callable=AsyncMock)
@patch("api.project_memory_service.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_queue_project_memory_rebuild_submits_command(
    mock_get_project,
    mock_create_run,
    mock_submit_command,
    mock_mark_memory_status,
    mock_record_step,
):
    mock_get_project.return_value = ProjectSummary(
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
    mock_create_run.return_value = type(
        "Run",
        (),
        {"id": "run:memory001"},
    )()
    mock_submit_command.return_value = "command:memory:1"

    response = await queue_project_memory_rebuild("project:demo")

    assert response == {
        "project_id": "project:demo",
        "status": "queued",
        "message": "Project memory rebuild queued.",
        "command_id": "command:memory:1",
        "run_id": "run:memory001",
    }
    mock_submit_command.assert_awaited_once_with(
        "open_notebook",
        "refresh_memory",
        {
            "project_id": "project:demo",
            "run_id": "run:memory001",
        },
    )
    mock_mark_memory_status.assert_awaited_once_with(
        "project:demo",
        "queued",
        command_id="command:memory:1",
        error_message=None,
    )
    mock_record_step.assert_awaited_once()
