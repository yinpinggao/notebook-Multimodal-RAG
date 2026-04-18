from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.project_artifacts import router
from open_notebook.domain.artifacts import ArtifactRecord, ProjectArtifactCreateResponse
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch(
    "api.routers.project_artifacts.project_artifact_service.queue_project_artifact",
    new_callable=AsyncMock,
)
def test_create_project_artifact_returns_queued(mock_queue_artifact, client):
    mock_queue_artifact.return_value = ProjectArtifactCreateResponse(
        artifact_id="artifact:demo",
        status="queued",
        command_id="command:artifact:1",
        created_by_run_id="run:artifact001",
    )

    response = client.post(
        "/api/projects/project:demo/artifacts",
        json={
            "artifact_type": "project_summary",
            "origin_kind": "overview",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "artifact_id": "artifact:demo",
        "status": "queued",
        "command_id": "command:artifact:1",
        "created_by_run_id": "run:artifact001",
    }


@patch(
    "api.routers.project_artifacts.project_artifact_service.list_project_artifacts",
    new_callable=AsyncMock,
)
def test_list_project_artifacts_returns_records(mock_list_artifacts, client):
    mock_list_artifacts.return_value = [
        ArtifactRecord(
            id="artifact:demo",
            project_id="project:demo",
            artifact_type="project_summary",
            title="Demo Summary",
            content_md="# Demo",
            source_refs=["source:1#p1"],
            created_by_run_id="run:artifact001",
            created_at="2026-04-18T12:00:00Z",
            updated_at="2026-04-18T12:00:01Z",
            status="ready",
            origin_kind="overview",
        )
    ]

    response = client.get("/api/projects/project:demo/artifacts")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "artifact:demo"
    assert response.json()[0]["artifact_type"] == "project_summary"


@patch(
    "api.routers.project_artifacts.project_artifact_service.get_project_artifact",
    new_callable=AsyncMock,
)
def test_get_project_artifact_returns_record(mock_get_artifact, client):
    mock_get_artifact.return_value = ArtifactRecord(
        id="artifact:demo",
        project_id="project:demo",
        artifact_type="qa_cards",
        title="QA Cards",
        content_md="# QA",
        source_refs=["source:1#p1"],
        created_by_run_id="run:artifact001",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:01Z",
        status="ready",
        origin_kind="thread",
        origin_id="thread:demo",
        thread_id="thread:demo",
    )

    response = client.get("/api/projects/project:demo/artifacts/artifact:demo")

    assert response.status_code == 200
    assert response.json()["id"] == "artifact:demo"
    assert response.json()["origin_kind"] == "thread"


@patch(
    "api.routers.project_artifacts.project_artifact_service.regenerate_project_artifact",
    new_callable=AsyncMock,
)
def test_regenerate_project_artifact_returns_queued(mock_regenerate_artifact, client):
    mock_regenerate_artifact.return_value = ProjectArtifactCreateResponse(
        artifact_id="artifact:demo",
        status="queued",
        command_id="command:artifact:2",
        created_by_run_id="run:artifact002",
    )

    response = client.post("/api/projects/project:demo/artifacts/artifact:demo/regenerate")

    assert response.status_code == 200
    assert response.json()["command_id"] == "command:artifact:2"


@patch(
    "api.routers.project_artifacts.project_artifact_service.get_project_artifact",
    new_callable=AsyncMock,
)
def test_get_project_artifact_returns_404_when_missing(mock_get_artifact, client):
    mock_get_artifact.side_effect = NotFoundError("Artifact not found")

    response = client.get("/api/projects/project:demo/artifacts/artifact:missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Artifact not found"}
