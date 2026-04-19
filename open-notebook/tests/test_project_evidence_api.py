from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.project_evidence import router
from api.schemas import (
    AskResponse,
    EvidenceCard,
    EvidenceThreadDetail,
    EvidenceThreadMessage,
    EvidenceThreadSummary,
)
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@patch("api.routers.project_evidence.project_evidence_service.ask_project", new_callable=AsyncMock)
def test_project_ask_endpoint_returns_ask_response(mock_ask_project, client):
    mock_ask_project.return_value = AskResponse(
        thread_id="chat_session:demo",
        answer="这是一个证据优先的项目。",
        confidence=0.84,
        evidence_cards=[
            EvidenceCard(
                source_name="spec.pdf",
                source_id="source:alpha",
                page_no=2,
                excerpt="系统强调证据优先回答。",
                citation_text="引用：spec.pdf（第2页） | 内部引用：[source:alpha]",
                internal_ref="source:alpha#p2",
            )
        ],
        memory_updates=[],
        run_id="run:demo",
        suggested_followups=["把关键证据页展开解释一下。"],
        mode="text",
    )

    response = client.post(
        "/api/projects/project:demo/ask",
        json={
            "question": "这个项目的主要特点是什么？",
            "mode": "auto",
            "source_ids": ["source:alpha"],
            "note_ids": [],
            "memory_ids": ["memory:demo"],
            "agent": "research",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "chat_session:demo"
    assert data["mode"] == "text"
    assert data["evidence_cards"][0]["source_id"] == "source:alpha"
    mock_ask_project.assert_awaited_once_with(
        "project:demo",
        "这个项目的主要特点是什么？",
        mode="auto",
        thread_id=None,
        source_ids=["source:alpha"],
        note_ids=[],
        memory_ids=["memory:demo"],
        agent="research",
    )


@patch(
    "api.routers.project_evidence.project_evidence_service.list_project_threads",
    new_callable=AsyncMock,
)
def test_get_project_threads_returns_thread_summaries(mock_list_threads, client):
    mock_list_threads.return_value = [
        EvidenceThreadSummary(
            id="chat_session:demo",
            project_id="project:demo",
            title="Main Contribution",
            created_at="2026-04-18T10:00:00Z",
            updated_at="2026-04-18T10:05:00Z",
            message_count=2,
            last_question="What is the main contribution?",
            last_answer_preview="The main contribution is...",
        )
    ]

    response = client.get("/api/projects/project:demo/threads")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "chat_session:demo"
    assert data[0]["message_count"] == 2


@patch(
    "api.routers.project_evidence.project_evidence_service.get_project_thread",
    new_callable=AsyncMock,
)
def test_get_project_thread_returns_detail(mock_get_thread, client):
    mock_get_thread.return_value = EvidenceThreadDetail(
        id="chat_session:demo",
        project_id="project:demo",
        title="Main Contribution",
        created_at="2026-04-18T10:00:00Z",
        updated_at="2026-04-18T10:05:00Z",
        message_count=2,
        last_question="What is the main contribution?",
        last_answer_preview="The main contribution is...",
        messages=[
            EvidenceThreadMessage(
                id="msg:1",
                type="human",
                content="What is the main contribution?",
            ),
            EvidenceThreadMessage(
                id="msg:2",
                type="ai",
                content="The main contribution is evidence-grounded QA.",
            ),
        ],
        latest_response=AskResponse(
            thread_id="chat_session:demo",
            answer="The main contribution is evidence-grounded QA.",
            confidence=0.8,
            evidence_cards=[],
            memory_updates=[],
            run_id=None,
            suggested_followups=[],
            mode="text",
        ),
    )

    response = client.get("/api/projects/project:demo/threads/chat_session:demo")

    assert response.status_code == 200
    data = response.json()
    assert data["messages"][0]["type"] == "human"
    assert data["latest_response"]["mode"] == "text"


@patch(
    "api.routers.project_evidence.project_evidence_service.followup_project_thread",
    new_callable=AsyncMock,
)
def test_followup_project_thread_returns_response(mock_followup, client):
    mock_followup.return_value = AskResponse(
        thread_id="chat_session:demo",
        answer="这页图表主要展示了系统结构。",
        confidence=0.78,
        evidence_cards=[],
        memory_updates=[],
        run_id="run:followup",
        suggested_followups=["把这页里的关键元素逐个解释。"],
        mode="visual",
    )

    response = client.post(
        "/api/projects/project:demo/threads/chat_session:demo/followup",
        json={
            "question": "这张图表说明了什么？",
            "mode": "auto",
            "source_ids": ["source:vision"],
            "note_ids": [],
            "memory_ids": [],
            "agent": "visual",
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "visual"
    mock_followup.assert_awaited_once_with(
        "project:demo",
        "chat_session:demo",
        "这张图表说明了什么？",
        mode="auto",
        source_ids=["source:vision"],
        note_ids=[],
        memory_ids=[],
        agent="visual",
    )


@patch(
    "api.routers.project_evidence.project_evidence_service.get_project_thread",
    new_callable=AsyncMock,
)
def test_get_project_thread_returns_404_for_missing_thread(mock_get_thread, client):
    mock_get_thread.side_effect = NotFoundError("Thread not found")

    response = client.get("/api/projects/project:demo/threads/chat_session:missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Thread not found"}
