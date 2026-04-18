from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.project_runs import router
from open_notebook.domain.runs import AgentRun
from open_notebook.exceptions import NotFoundError


def _run(run_id: str = "run:demo") -> AgentRun:
    return AgentRun(
        id=run_id,
        project_id="project:demo",
        run_type="ask",
        status="completed",
        input_summary="项目现在最关键的证据是什么？",
        selected_skill="answer_with_evidence",
        created_at="2026-04-18T12:00:00Z",
        completed_at="2026-04-18T12:00:03Z",
    )


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch(
    "api.routers.project_runs.project_run_service.list_runs",
    new_callable=AsyncMock,
)
def test_list_project_runs_returns_records(mock_list_runs, client):
    mock_list_runs.return_value = [_run()]

    response = client.get("/api/projects/project:demo/runs")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "run:demo"
    assert response.json()[0]["selected_skill"] == "answer_with_evidence"


@patch(
    "api.routers.project_runs.project_run_service.get_run",
    new_callable=AsyncMock,
)
def test_get_project_run_returns_record(mock_get_run, client):
    mock_get_run.return_value = _run()

    response = client.get("/api/projects/project:demo/runs/run:demo")

    assert response.status_code == 200
    assert response.json()["id"] == "run:demo"
    assert response.json()["run_type"] == "ask"


@patch(
    "api.routers.project_runs.project_run_service.get_run",
    new_callable=AsyncMock,
)
def test_get_project_run_returns_404_when_missing(mock_get_run, client):
    mock_get_run.side_effect = NotFoundError("Run not found")

    response = client.get("/api/projects/project:demo/runs/run:missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}
