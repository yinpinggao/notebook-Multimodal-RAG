from unittest.mock import AsyncMock, patch

import pytest

from api.command_service import CommandService
from open_notebook.jobs import JobRecord


@pytest.mark.asyncio
@patch.object(CommandService, "_ensure_commands_loaded")
@patch("api.command_service.job_store.update_job", new_callable=AsyncMock)
@patch("api.command_service.async_submit_command", new_callable=AsyncMock)
@patch("api.command_service.job_store.get_job_record", new_callable=AsyncMock)
async def test_retry_command_job_increments_retry_count(
    mock_get_job_record,
    mock_async_submit_command,
    mock_update_job,
    mock_ensure_commands_loaded,
):
    mock_get_job_record.return_value = JobRecord(
        job_id="command:failed:1",
        app_name="open_notebook",
        command_name="run_project_eval",
        status="failed",
        args={"project_id": "project:demo", "run_id": "run:stale"},
        result=None,
        error_message="boom",
        created="2026-04-19 08:00:00",
        updated="2026-04-19 08:01:00",
        progress=None,
        retry_count=2,
        started_at="2026-04-19 08:00:01",
        completed_at="2026-04-19 08:01:00",
    )
    mock_async_submit_command.return_value = "command:retry:3"

    job_id = await CommandService.retry_command_job("command:failed:1")

    assert job_id == "command:retry:3"
    mock_ensure_commands_loaded.assert_called_once_with()
    mock_async_submit_command.assert_awaited_once_with(
        "open_notebook",
        "run_project_eval",
        {"project_id": "project:demo"},
    )
    mock_update_job.assert_awaited_once_with(
        "command:retry:3",
        retry_count=3,
    )


@pytest.mark.asyncio
@patch("api.command_service.job_store.get_job_record", new_callable=AsyncMock)
async def test_get_command_status_returns_extended_record_fields(mock_get_job_record):
    mock_get_job_record.return_value = JobRecord(
        job_id="command:eval:1",
        app_name="open_notebook",
        command_name="run_project_eval",
        status="completed",
        args={"project_id": "project:demo"},
        result={"summary": "ok"},
        error_message=None,
        created="2026-04-19 08:00:00",
        updated="2026-04-19 08:00:05",
        progress=None,
        retry_count=1,
        started_at="2026-04-19 08:00:01",
        completed_at="2026-04-19 08:00:05",
    )

    status = await CommandService.get_command_status("command:eval:1")

    assert status == {
        "job_id": "command:eval:1",
        "status": "completed",
        "result": {"summary": "ok"},
        "error_message": None,
        "created": "2026-04-19 08:00:00",
        "updated": "2026-04-19 08:00:05",
        "progress": None,
        "started_at": "2026-04-19 08:00:01",
        "completed_at": "2026-04-19 08:00:05",
        "retry_count": 1,
        "app_name": "open_notebook",
        "command_name": "run_project_eval",
    }
