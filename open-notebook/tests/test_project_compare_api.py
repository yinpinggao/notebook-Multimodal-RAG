from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.project_compare import router
from open_notebook.domain.compare import (
    ProjectCompareCreateResponse,
    ProjectCompareExportResponse,
    ProjectCompareRecord,
)
from open_notebook.domain.evidence import CompareSummary
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch(
    "api.routers.project_compare.project_compare_service.queue_project_compare",
    new_callable=AsyncMock,
)
def test_create_project_compare_returns_queued(mock_queue_compare, client):
    mock_queue_compare.return_value = ProjectCompareCreateResponse(
        compare_id="cmp_demo",
        status="queued",
        command_id="command:compare:1",
    )

    response = client.post(
        "/api/projects/project:demo/compare",
        json={
            "source_a_id": "source:a",
            "source_b_id": "source:b",
            "compare_mode": "general",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "compare_id": "cmp_demo",
        "status": "queued",
        "command_id": "command:compare:1",
    }


@patch(
    "api.routers.project_compare.project_compare_service.queue_project_compare",
    new_callable=AsyncMock,
)
def test_create_project_compare_accepts_prd_alias_fields(mock_queue_compare, client):
    mock_queue_compare.return_value = ProjectCompareCreateResponse(
        compare_id="cmp_demo",
        status="queued",
        command_id="command:compare:1",
    )

    response = client.post(
        "/api/projects/project:demo/compare",
        json={
            "left_source_id": "source:left",
            "right_source_id": "source:right",
            "compare_mode": "general",
        },
    )

    assert response.status_code == 200
    mock_queue_compare.assert_awaited_once_with(
        "project:demo",
        source_a_id="source:left",
        source_b_id="source:right",
        compare_mode="general",
    )


@patch(
    "api.routers.project_compare.project_compare_service.get_project_compare",
    new_callable=AsyncMock,
)
def test_get_project_compare_returns_record(mock_get_compare, client):
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

    response = client.get("/api/projects/project:demo/compare/cmp_demo")

    assert response.status_code == 200
    assert response.json()["id"] == "cmp_demo"
    assert response.json()["result"]["summary"] == "done"


@patch(
    "api.routers.project_compare.project_compare_service.export_project_compare",
    new_callable=AsyncMock,
)
def test_export_project_compare_returns_markdown(mock_export_compare, client):
    mock_export_compare.return_value = ProjectCompareExportResponse(
        compare_id="cmp_demo",
        format="markdown",
        content="# demo",
    )

    response = client.post("/api/projects/project:demo/compare/cmp_demo/export")

    assert response.status_code == 200
    assert response.json() == {
        "compare_id": "cmp_demo",
        "format": "markdown",
        "content": "# demo",
    }


@patch(
    "api.routers.project_compare.project_compare_service.get_project_compare",
    new_callable=AsyncMock,
)
def test_get_project_compare_returns_404_when_missing(mock_get_compare, client):
    mock_get_compare.side_effect = NotFoundError("Compare record not found")

    response = client.get("/api/projects/project:demo/compare/cmp_missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Compare record not found"}
