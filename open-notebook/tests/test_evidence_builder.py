from __future__ import annotations

import pytest

from open_notebook.utils import evidence_builder


class _FakeSource:
    def __init__(self, source_id: str, title: str, full_text: str):
        self.source_id = source_id
        self.title = title
        self.full_text = full_text

    async def get_context(self, context_size: str = "short"):
        assert context_size == "long"
        return {
            "id": self.source_id,
            "title": self.title,
            "full_text": self.full_text,
            "insights": [],
        }


class _FakeNote:
    def __init__(self, note_id: str, title: str, content: str):
        self.note_id = note_id
        self.title = title
        self.content = content

    def get_context(self, context_size: str = "short"):
        assert context_size == "long"
        return {
            "id": self.note_id,
            "title": self.title,
            "content": self.content,
        }


@pytest.mark.asyncio
async def test_build_multimodal_evidence_uses_source_fallback_rows(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_search(*args, **kwargs):
        return []

    async def fake_source_get(source_id: str):
        return _FakeSource(source_id, "竞赛评分标准", "评分标准包括可运行性、证据链和闭环。")

    monkeypatch.setattr(
        evidence_builder.ai_retrieval_service,
        "hybrid_multimodal_search",
        fake_search,
    )
    monkeypatch.setattr(evidence_builder, "use_seekdb_for_search", lambda: True)
    monkeypatch.setattr(evidence_builder.Source, "get", staticmethod(fake_source_get))

    result = await evidence_builder.build_multimodal_evidence(
        "竞赛评分标准最关注哪几项？",
        source_ids=["source:demo"],
        include_sources=True,
        include_notes=False,
        minimum_score=0.2,
    )

    assert len(result["results"]) == 1
    assert result["results"][0]["source_id"] == "source:demo"
    assert "评分标准包括可运行性" in result["context_text"]


@pytest.mark.asyncio
async def test_build_multimodal_evidence_uses_note_fallback_rows(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_search(*args, **kwargs):
        return []

    async def fake_note_get(note_id: str):
        return _FakeNote(note_id, "演示脚本", "三分钟闭环包括 overview、evidence、compare。")

    monkeypatch.setattr(
        evidence_builder.ai_retrieval_service,
        "hybrid_multimodal_search",
        fake_search,
    )
    monkeypatch.setattr(evidence_builder, "use_seekdb_for_search", lambda: True)
    monkeypatch.setattr(evidence_builder.Note, "get", staticmethod(fake_note_get))

    result = await evidence_builder.build_multimodal_evidence(
        "三分钟演示闭环包含哪些页面？",
        note_ids=["note:demo"],
        include_sources=False,
        include_notes=True,
        minimum_score=0.2,
    )

    assert len(result["results"]) == 1
    assert result["results"][0]["entity_type"] == "note"
    assert "overview、evidence、compare" in result["context_text"]
