from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.project_evidence_service import (
    _load_thread_state,
    _latest_response_for_thread,
    ask_project,
    select_project_ask_mode,
)
from open_notebook.evidence.evidence_card_service import build_evidence_cards
from open_notebook.exceptions import InvalidInputError


def test_select_project_ask_mode_prefers_visual_when_visual_hits_exist():
    mode = select_project_ask_mode(
        "auto",
        "这张图表说明了什么？",
        [
            {
                "source_id": "source:1",
                "filename": "demo.pdf",
                "page": 3,
                "match": "图表显示模型表现优于基线。",
                "has_visual_summary": True,
                "page_image_path": "/tmp/page-3.png",
            }
        ],
    )

    assert mode == "visual"


def test_select_project_ask_mode_honors_explicit_mode_override():
    mode = select_project_ask_mode(
        "visual",
        "这段正文主要讲了什么？",
        [{"source_id": "source:1", "filename": "report.pdf", "match": "正文内容"}],
    )

    assert mode == "visual"


def test_select_project_ask_mode_returns_mixed_for_multimodal_hits():
    mode = select_project_ask_mode(
        "auto",
        "这张图和正文一起说明了什么？",
        [
            {
                "source_id": "source:1",
                "filename": "deck.pdf",
                "page": 3,
                "match": "图表显示模型表现优于基线。",
                "has_visual_summary": True,
            },
            {
                "source_id": "source:2",
                "filename": "report.pdf",
                "page": 5,
                "match": "正文解释了指标定义与实验条件。",
            },
        ],
    )

    assert mode == "mixed"


def test_build_evidence_cards_maps_page_and_internal_ref():
    cards = build_evidence_cards(
        project_id="project:demo",
        thread_id="chat_session:demo",
        rows=[
            {
                "source_id": "source:alpha",
                "parent_id": "source:alpha",
                "filename": "spec.pdf",
                "page": 5,
                "match": "系统强调证据优先回答。",
                "score": 0.86,
            }
        ],
        mode="text",
    )

    assert len(cards) == 1
    assert cards[0].page_no == 5
    assert cards[0].internal_ref == "source:alpha#p5"
    assert "spec.pdf" in cards[0].citation_text


def test_build_evidence_cards_tolerates_non_numeric_page_metadata():
    cards = build_evidence_cards(
        project_id="project:demo",
        thread_id="chat_session:demo",
        rows=[
            {
                "source_id": "source:appendix",
                "parent_id": "source:appendix",
                "filename": "appendix.pdf",
                "page": "S-1",
                "match": "附录页提供了补充说明。",
            }
        ],
        mode="text",
    )

    assert len(cards) == 1
    assert cards[0].page_no is None
    assert cards[0].internal_ref == "source:appendix"
    assert cards[0].citation_text == "引用：appendix.pdf | 内部引用：[source:appendix]"
    assert cards[0].relevance_reason == "这段内容与当前问题的关键词和语义最相关。"


@pytest.mark.asyncio
@patch("api.project_evidence_service.mark_run_completed", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_answer_step", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_tool_call", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_evidence_read", new_callable=AsyncMock)
@patch("api.project_evidence_service.mark_run_running", new_callable=AsyncMock)
@patch("api.project_evidence_service.create_project_run", new_callable=AsyncMock)
@patch("api.project_evidence_service._save_thread_state", new_callable=AsyncMock)
@patch("api.project_evidence_service._generate_answer_for_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service.build_multimodal_evidence", new_callable=AsyncMock)
@patch("api.project_evidence_service._get_or_create_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service.list_project_memories", new_callable=AsyncMock)
@patch("api.project_evidence_service._resolve_project_scope", new_callable=AsyncMock)
async def test_ask_project_uses_selected_scope_and_memory_context(
    mock_resolve_project_scope,
    mock_list_project_memories,
    mock_get_or_create_thread,
    mock_build_multimodal_evidence,
    mock_generate_answer_for_thread,
    mock_save_thread_state,
    mock_create_run,
    mock_mark_run_running,
    mock_record_evidence_read,
    mock_record_tool_call,
    mock_record_answer_step,
    mock_mark_run_completed,
):
    mock_resolve_project_scope.return_value = (
        SimpleNamespace(id="project:demo"),
        SimpleNamespace(id="project:demo"),
        ["source:selected", "source:other"],
        ["note:1"],
    )
    mock_list_project_memories.return_value = [
        SimpleNamespace(
            id="memory:demo",
            type="fact",
            status="accepted",
            text="用户更关注证据链完整性。",
            source_refs=[],
        )
    ]
    mock_get_or_create_thread.return_value = SimpleNamespace(id="chat_session:scope")
    mock_create_run.return_value = SimpleNamespace(id="run:ask-scope")
    mock_build_multimodal_evidence.return_value = {
        "results": [],
        "context_text": "",
    }
    mock_generate_answer_for_thread.return_value = "可以结合项目记忆继续整理。"

    await ask_project(
        "project:demo",
        "需要优先看什么？",
        mode="text",
        source_ids=["source:selected"],
        note_ids=[],
        memory_ids=["memory:demo"],
        agent="retrieval",
    )

    mock_build_multimodal_evidence.assert_awaited_once_with(
        "需要优先看什么？",
        source_ids=["source:selected"],
        note_ids=None,
        include_sources=True,
        include_notes=False,
        limit=8,
        minimum_score=0.2,
    )
    context_text = mock_generate_answer_for_thread.await_args.kwargs["context_text"]
    assert "Selected Project Memories" in context_text
    assert "用户更关注证据链完整性" in context_text
    mock_save_thread_state.assert_awaited_once()
    mock_mark_run_running.assert_awaited_once()
    mock_record_evidence_read.assert_awaited_once()
    mock_record_answer_step.assert_awaited_once()
    mock_mark_run_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_ask_project_rejects_blank_question():
    with pytest.raises(InvalidInputError):
        await ask_project("project:demo", "   ")


@pytest.mark.asyncio
@patch("api.project_evidence_service.build_multimodal_evidence", new_callable=AsyncMock)
@patch("api.project_evidence_service._load_thread_state", new_callable=AsyncMock)
async def test_latest_response_for_thread_prefers_saved_thread_state(
    mock_load_thread_state,
    mock_build_multimodal_evidence,
):
    stored_response = SimpleNamespace(
        answer="使用已保存的线程回答。",
        confidence=0.91,
        evidence_cards=[],
        memory_updates=[],
        run_id="run:thread-state",
        suggested_followups=["继续追问"],
        mode="text",
        thread_id="chat_session:demo",
    )
    mock_load_thread_state.return_value = SimpleNamespace(
        project_id="project:demo",
        latest_response=stored_response,
    )

    response = await _latest_response_for_thread(
        "project:demo",
        messages=[],
        thread_id="chat_session:demo",
    )

    assert response == stored_response
    mock_build_multimodal_evidence.assert_not_awaited()


@pytest.mark.asyncio
@patch(
    "api.project_evidence_service.seekdb_business_store.get_singleton",
    new_callable=AsyncMock,
)
async def test_load_thread_state_ignores_singleton_record_id_metadata(
    mock_get_singleton,
):
    mock_get_singleton.return_value = {
        "id": "project_evidence_thread:chat_session:demo",
        "project_id": "project:demo",
        "thread_id": "chat_session:stale",
        "latest_response": None,
        "source_ids": [],
        "note_ids": [],
        "memory_ids": [],
        "agent": "research",
        "created": "2026-04-19T00:00:00Z",
        "updated": "2026-04-19T00:00:01Z",
    }

    state = await _load_thread_state("chat_session:demo")

    assert state is not None
    assert state.thread_id == "chat_session:demo"
    assert state.project_id == "project:demo"


@pytest.mark.asyncio
@patch("api.project_evidence_service.mark_run_completed", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_answer_step", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_tool_call", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_evidence_read", new_callable=AsyncMock)
@patch("api.project_evidence_service.mark_run_running", new_callable=AsyncMock)
@patch("api.project_evidence_service.create_project_run", new_callable=AsyncMock)
@patch("api.project_evidence_service._save_thread_state", new_callable=AsyncMock)
@patch("api.project_evidence_service._generate_answer_for_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service.build_multimodal_evidence", new_callable=AsyncMock)
@patch("api.project_evidence_service._get_or_create_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service._resolve_project_scope", new_callable=AsyncMock)
async def test_ask_project_returns_text_response(
    mock_resolve_project_scope,
    mock_get_or_create_thread,
    mock_build_multimodal_evidence,
    mock_generate_answer_for_thread,
    mock_save_thread_state,
    mock_create_run,
    mock_mark_run_running,
    mock_record_evidence_read,
    mock_record_tool_call,
    mock_record_answer_step,
    mock_mark_run_completed,
):
    mock_resolve_project_scope.return_value = (
        SimpleNamespace(id="project:demo"),
        SimpleNamespace(id="project:demo"),
        ["source:alpha"],
        [],
    )
    mock_get_or_create_thread.return_value = SimpleNamespace(id="chat_session:demo")
    mock_create_run.return_value = SimpleNamespace(id="run:ask001")
    mock_build_multimodal_evidence.return_value = {
        "results": [
            {
                "source_id": "source:alpha",
                "parent_id": "source:alpha",
                "filename": "spec.pdf",
                "page": 2,
                "match": "系统强调证据优先回答。",
                "citation_text": "引用：spec.pdf（第2页） | 内部引用：[source:alpha]",
                "internal_ref": "source:alpha",
                "score": 0.86,
            }
        ],
        "context_text": "系统强调证据优先回答。",
    }
    mock_generate_answer_for_thread.return_value = (
        "项目的核心特点是证据优先。引用：[1]（spec.pdf，第2页）；内部引用：[source:alpha]"
    )

    response = await ask_project("project:demo", "这个项目的主要特点是什么？")

    assert response.mode == "text"
    assert response.thread_id == "chat_session:demo"
    assert response.run_id == "run:ask001"
    assert response.evidence_cards[0].source_id == "source:alpha"
    assert response.evidence_cards[0].page_no == 2
    mock_save_thread_state.assert_awaited_once()
    mock_mark_run_running.assert_awaited_once()
    assert mock_record_tool_call.await_count == 2
    mock_record_evidence_read.assert_awaited_once()
    mock_record_answer_step.assert_awaited_once()
    mock_mark_run_completed.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.project_evidence_service.mark_run_completed", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_answer_step", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_tool_call", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_evidence_read", new_callable=AsyncMock)
@patch("api.project_evidence_service.mark_run_running", new_callable=AsyncMock)
@patch("api.project_evidence_service.create_project_run", new_callable=AsyncMock)
@patch("api.project_evidence_service._save_thread_state", new_callable=AsyncMock)
@patch("api.project_evidence_service._generate_answer_for_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service.build_multimodal_evidence", new_callable=AsyncMock)
@patch("api.project_evidence_service._get_or_create_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service._resolve_project_scope", new_callable=AsyncMock)
async def test_ask_project_returns_visual_response(
    mock_resolve_project_scope,
    mock_get_or_create_thread,
    mock_build_multimodal_evidence,
    mock_generate_answer_for_thread,
    mock_save_thread_state,
    mock_create_run,
    mock_mark_run_running,
    mock_record_evidence_read,
    mock_record_tool_call,
    mock_record_answer_step,
    mock_mark_run_completed,
):
    mock_resolve_project_scope.return_value = (
        SimpleNamespace(id="project:demo"),
        SimpleNamespace(id="project:demo"),
        ["source:vision"],
        [],
    )
    mock_get_or_create_thread.return_value = SimpleNamespace(id="chat_session:vision")
    mock_create_run.return_value = SimpleNamespace(id="run:ask002")
    mock_build_multimodal_evidence.return_value = {
        "results": [
            {
                "source_id": "source:vision",
                "parent_id": "source:vision",
                "filename": "deck.pdf",
                "page": 7,
                "match": "页面图表展示系统结构与数据流。",
                "citation_text": "引用：deck.pdf（第7页） | 内部引用：[source:vision]",
                "internal_ref": "source:vision",
                "score": 0.91,
                "has_visual_summary": True,
                "page_image_path": "/tmp/deck-page-7.png",
            }
        ],
        "context_text": "视觉证据：已包含页面图像摘要（来自 PDF 页图分析）",
    }
    mock_generate_answer_for_thread.return_value = (
        "这页图表主要展示了系统结构与数据流关系。"
        "引用：[1]（deck.pdf，第7页）；内部引用：[source:vision]"
    )

    response = await ask_project("project:demo", "这张图表说明了什么？")

    assert response.mode == "visual"
    assert response.thread_id == "chat_session:vision"
    assert response.evidence_cards[0].relevance_reason is not None
    assert response.evidence_cards[0].image_thumb == "/tmp/deck-page-7.png"
    assert "图表" in response.answer
    mock_save_thread_state.assert_awaited_once()
    mock_mark_run_running.assert_awaited_once()
    assert mock_record_tool_call.await_count == 2
    mock_record_evidence_read.assert_awaited_once()
    mock_record_answer_step.assert_awaited_once()
    mock_mark_run_completed.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.project_evidence_service.mark_run_completed", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_answer_step", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_tool_call", new_callable=AsyncMock)
@patch("api.project_evidence_service.record_evidence_read", new_callable=AsyncMock)
@patch("api.project_evidence_service.mark_run_running", new_callable=AsyncMock)
@patch("api.project_evidence_service.create_project_run", new_callable=AsyncMock)
@patch("api.project_evidence_service._save_thread_state", new_callable=AsyncMock)
@patch("api.project_evidence_service._generate_answer_for_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service.build_multimodal_evidence", new_callable=AsyncMock)
@patch("api.project_evidence_service._get_or_create_thread", new_callable=AsyncMock)
@patch("api.project_evidence_service._resolve_project_scope", new_callable=AsyncMock)
async def test_ask_project_marks_uncertainty_when_evidence_is_missing(
    mock_resolve_project_scope,
    mock_get_or_create_thread,
    mock_build_multimodal_evidence,
    mock_generate_answer_for_thread,
    mock_save_thread_state,
    mock_create_run,
    mock_mark_run_running,
    mock_record_evidence_read,
    mock_record_tool_call,
    mock_record_answer_step,
    mock_mark_run_completed,
):
    mock_resolve_project_scope.return_value = (
        SimpleNamespace(id="project:demo"),
        SimpleNamespace(id="project:demo"),
        ["source:alpha"],
        [],
    )
    mock_get_or_create_thread.return_value = SimpleNamespace(id="chat_session:empty")
    mock_create_run.return_value = SimpleNamespace(id="run:ask003")
    mock_build_multimodal_evidence.return_value = {
        "results": [],
        "context_text": "",
    }
    mock_generate_answer_for_thread.return_value = "暂时无法确认。"

    response = await ask_project("project:demo", "目前证据足够支持这个结论吗？")

    assert response.confidence == 0.22
    assert response.evidence_cards == []
    assert "证据" in response.answer or "资料" in response.answer
    mock_save_thread_state.assert_awaited_once()
    mock_mark_run_running.assert_awaited_once()
    assert mock_record_tool_call.await_count == 2
    mock_record_evidence_read.assert_awaited_once()
    mock_record_answer_step.assert_awaited_once()
    mock_mark_run_completed.assert_awaited_once()
