from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.projects import router
from api.schemas import ProjectOverviewResponse, ProjectSummary, ProjectTimelineEvent
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch("api.routers.projects.project_workspace_service.list_projects", new_callable=AsyncMock)
def test_get_projects_returns_project_contract(mock_list_projects, client):
    mock_list_projects.return_value = [
        ProjectSummary(
            id="project:demo",
            name="Demo Project",
            description="Notebook-backed project",
            status="active",
            created_at="2026-04-18T08:00:00Z",
            updated_at="2026-04-18T09:00:00Z",
            source_count=2,
            artifact_count=0,
            memory_count=0,
        )
    ]

    response = client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert data == [
        {
            "id": "project:demo",
            "name": "Demo Project",
            "description": "Notebook-backed project",
            "status": "active",
            "created_at": "2026-04-18T08:00:00Z",
            "updated_at": "2026-04-18T09:00:00Z",
            "source_count": 2,
            "artifact_count": 0,
            "memory_count": 0,
            "last_run_at": None,
        }
    ]


@patch("api.routers.projects.project_workspace_service.create_project", new_callable=AsyncMock)
def test_create_project_returns_project_summary(mock_create_project, client):
    mock_create_project.return_value = ProjectSummary(
        id="project:new",
        name="New Project",
        description="Created from API",
        status="active",
        created_at="2026-04-18T10:00:00Z",
        updated_at="2026-04-18T10:00:00Z",
        source_count=0,
        artifact_count=0,
        memory_count=0,
    )

    response = client.post(
        "/api/projects",
        json={"name": "New Project", "description": "Created from API"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "project:new"
    assert data["name"] == "New Project"
    assert data["description"] == "Created from API"


@patch(
    "api.routers.projects.project_workspace_service.create_demo_project",
    new_callable=AsyncMock,
)
def test_create_demo_project_returns_project_summary(mock_create_demo_project, client):
    mock_create_demo_project.return_value = ProjectSummary(
        id="project:demo",
        name="智研舱 Demo 项目",
        description="用于 3 分钟比赛演示的预置项目空间。",
        status="active",
        created_at="2026-04-19T08:00:00Z",
        updated_at="2026-04-19T08:05:00Z",
        source_count=2,
        artifact_count=1,
        memory_count=2,
        last_run_at="2026-04-19T08:05:00Z",
    )

    response = client.post("/api/projects/demo")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "project:demo"
    assert data["name"] == "智研舱 Demo 项目"
    assert data["artifact_count"] == 1


@patch(
    "api.routers.projects.project_overview_service.get_project_overview",
    new_callable=AsyncMock,
)
def test_get_project_overview_returns_stable_shape(mock_get_project_overview, client):
    mock_get_project_overview.return_value = ProjectOverviewResponse(
        project=ProjectSummary(
            id="project:demo",
            name="Demo Project",
            description="Notebook-backed project",
            status="active",
            created_at="2026-04-18T08:00:00Z",
            updated_at="2026-04-18T09:00:00Z",
            source_count=1,
            artifact_count=0,
            memory_count=0,
        ),
        source_count=1,
        artifact_count=0,
        memory_count=0,
        topics=["评分标准"],
        keywords=["评分标准", "项目画像"],
        risks=["视觉资料还没有建立索引，图表、版面和截图相关问题暂时不够稳。"],
        timeline_events=[
            ProjectTimelineEvent(
                id="timeline:1",
                title="创建项目空间",
                description="项目工作台已经建立，可以开始整理资料和沉淀证据。",
                occurred_at="2026-04-18T08:00:00Z",
                source_refs=[],
            )
        ],
        recommended_questions=["围绕“评分标准”目前最扎实的证据是什么？"],
        recent_runs=[],
        recent_artifacts=[],
    )

    response = client.get("/api/projects/project:demo/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["project"]["id"] == "project:demo"
    assert data["topics"] == ["评分标准"]
    assert data["timeline_events"][0]["id"] == "timeline:1"
    assert data["recent_runs"] == []
    assert data["recent_artifacts"] == []


@patch(
    "api.routers.projects.project_overview_service.queue_project_overview_rebuild",
    new_callable=AsyncMock,
)
def test_rebuild_project_overview_returns_queued(mock_rebuild, client):
    mock_rebuild.return_value = {
        "project_id": "project:demo",
        "status": "queued",
        "message": "Project overview rebuild queued.",
        "command_id": "command:overview:1",
    }

    response = client.post("/api/projects/project:demo/overview/rebuild")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "project:demo",
        "status": "queued",
        "message": "Project overview rebuild queued.",
        "command_id": "command:overview:1",
    }


@patch(
    "api.routers.projects.project_overview_service.get_project_overview",
    new_callable=AsyncMock,
)
def test_get_project_overview_returns_404_when_project_missing(
    mock_get_project_overview, client
):
    mock_get_project_overview.side_effect = NotFoundError("Project not found")

    response = client.get("/api/projects/project:missing/overview")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}
