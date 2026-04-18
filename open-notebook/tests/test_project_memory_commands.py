from unittest.mock import AsyncMock, call, patch

import pytest

from commands.project_memory_commands import (
    ProjectRefreshMemoryInput,
    refresh_project_memory_command,
)
from open_notebook.jobs import ExecutionContext


@pytest.mark.asyncio
@patch("commands.project_memory_commands.mark_project_memory_status", new_callable=AsyncMock)
@patch("commands.project_memory_commands.rebuild_project_memories", new_callable=AsyncMock)
async def test_refresh_project_memory_command_marks_failed_status(
    mock_rebuild_project_memories,
    mock_mark_project_memory_status,
):
    mock_rebuild_project_memories.side_effect = RuntimeError("memory rebuild failed")

    input_data = ProjectRefreshMemoryInput(
        project_id="project:demo",
        execution_context=ExecutionContext(
            command_id="command:memory:1",
            app_name="open_notebook",
            command_name="refresh_memory",
        ),
    )

    with pytest.raises(RuntimeError, match="memory rebuild failed"):
        await refresh_project_memory_command(input_data)

    assert mock_mark_project_memory_status.await_args_list == [
        call(
            "project:demo",
            "running",
            command_id="command:memory:1",
            error_message=None,
        ),
        call(
            "project:demo",
            "failed",
            command_id="command:memory:1",
            error_message="memory rebuild failed",
        ),
    ]
