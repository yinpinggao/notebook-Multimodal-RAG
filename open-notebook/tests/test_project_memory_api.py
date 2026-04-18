from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.project_memory import router
from open_notebook.domain.memory import MemoryRecord, SourceReference
from open_notebook.exceptions import NotFoundError


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


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch(
    "api.routers.project_memory.project_memory_service.list_memory_records",
    new_callable=AsyncMock,
)
def test_get_project_memory_returns_records(mock_list_memory, client):
    mock_list_memory.return_value = [_memory_record()]

    response = client.get("/api/projects/project:demo/memory")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "mem:demo"
    assert response.json()[0]["source_refs"][0]["source_id"] == "source:1"


@patch(
    "api.routers.project_memory.project_memory_service.update_memory_record",
    new_callable=AsyncMock,
)
def test_patch_project_memory_returns_record(mock_update_memory, client):
    mock_update_memory.return_value = _memory_record()

    response = client.patch(
        "/api/projects/project:demo/memory/mem:demo",
        json={"status": "accepted", "text": "评审要求需要明确列出技术路线。"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "mem:demo"


@patch(
    "api.routers.project_memory.project_memory_service.delete_memory_record",
    new_callable=AsyncMock,
)
def test_delete_project_memory_returns_deleted(mock_delete_memory, client):
    mock_delete_memory.return_value = {
        "project_id": "project:demo",
        "memory_id": "mem:demo",
        "status": "deleted",
    }

    response = client.delete("/api/projects/project:demo/memory/mem:demo")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "project:demo",
        "memory_id": "mem:demo",
        "status": "deleted",
    }


@patch(
    "api.routers.project_memory.project_memory_service.queue_project_memory_rebuild",
    new_callable=AsyncMock,
)
def test_rebuild_project_memory_returns_queued(mock_queue_rebuild, client):
    mock_queue_rebuild.return_value = {
        "project_id": "project:demo",
        "status": "queued",
        "message": "Project memory rebuild queued.",
        "command_id": "command:memory:1",
        "run_id": "run:memory001",
    }

    response = client.post("/api/projects/project:demo/memory/rebuild")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "project:demo",
        "status": "queued",
        "message": "Project memory rebuild queued.",
        "command_id": "command:memory:1",
        "run_id": "run:memory001",
    }


@patch(
    "api.routers.project_memory.project_memory_service.list_memory_records",
    new_callable=AsyncMock,
)
def test_get_project_memory_returns_404_when_project_missing(mock_list_memory, client):
    mock_list_memory.side_effect = NotFoundError("Project not found")

    response = client.get("/api/projects/project:missing/memory")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}
