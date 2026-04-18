from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.commands import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch("api.routers.commands.CommandService.submit_command_job", new_callable=AsyncMock)
def test_execute_command_returns_job_id(mock_submit_command_job, client):
    mock_submit_command_job.return_value = "command:eval:1"

    response = client.post(
        "/api/commands/jobs",
        json={
            "app": "open_notebook",
            "command": "run_project_eval",
            "input": {"project_id": "project:demo"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "command:eval:1",
        "status": "submitted",
        "message": "Command 'run_project_eval' submitted successfully",
    }


@patch("api.routers.commands.CommandService.retry_command_job", new_callable=AsyncMock)
def test_retry_command_returns_404_for_missing_job(mock_retry_command_job, client):
    mock_retry_command_job.side_effect = ValueError("Command job not found")

    response = client.post("/api/commands/jobs/command:missing/retry")

    assert response.status_code == 404
    assert response.json() == {"detail": "Command job not found"}


@patch("api.routers.commands.CommandService.get_command_status", new_callable=AsyncMock)
def test_get_command_status_returns_extended_fields(mock_get_command_status, client):
    mock_get_command_status.return_value = {
        "job_id": "command:eval:1",
        "status": "completed",
        "result": {"passed_metrics": 3, "available_metrics": 3},
        "error_message": None,
        "created": "2026-04-19T08:00:00Z",
        "updated": "2026-04-19T08:00:05Z",
        "progress": None,
        "started_at": "2026-04-19T08:00:01Z",
        "completed_at": "2026-04-19T08:00:05Z",
        "retry_count": 1,
        "app_name": "open_notebook",
        "command_name": "run_project_eval",
    }

    response = client.get("/api/commands/jobs/command:eval:1")

    assert response.status_code == 200
    assert response.json()["retry_count"] == 1
    assert response.json()["command_name"] == "run_project_eval"
    assert response.json()["completed_at"] == "2026-04-19T08:00:05Z"
