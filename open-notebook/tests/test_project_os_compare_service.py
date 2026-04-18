from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.evidence.structured_extractor import SourceProfile, StructuredFact
from open_notebook.project_os.compare_service import (
    _load_or_build_profile,
    compare_source_profiles,
    render_project_compare_markdown,
)


def _profile(
    *,
    source_id: str,
    title: str,
    topics: list[str],
    requirements: list[str],
    metrics: list[str],
) -> SourceProfile:
    facts = [
        StructuredFact(
            id=f"fact:{source_id}:topic",
            category="topic",
            value=topics[0],
            source_id=source_id,
            source_refs=[f"{source_id}#p1"],
            confidence=0.8,
        ),
        StructuredFact(
            id=f"fact:{source_id}:requirement",
            category="requirement",
            value=requirements[0],
            source_id=source_id,
            source_refs=[f"{source_id}#p2"],
            confidence=0.8,
        ),
        StructuredFact(
            id=f"fact:{source_id}:metric",
            category="metric",
            value=metrics[0],
            source_id=source_id,
            source_refs=[f"{source_id}#p3"],
            confidence=0.8,
        ),
    ]
    return SourceProfile(
        source_id=source_id,
        title=title,
        generated_at="2026-04-18T12:00:00Z",
        source_refs=[f"{source_id}#p1"],
        topics=topics,
        keywords=[],
        terms=[],
        people_orgs=[],
        timeline_events=[],
        metrics=metrics,
        risks=[],
        requirements=requirements,
        facts=facts,
        text_sample=f"{title} text sample",
    )


def test_compare_source_profiles_builds_structured_sections():
    left = _profile(
        source_id="source:left",
        title="方案 A",
        topics=["风控系统"],
        requirements=["系统必须支持审计日志"],
        metrics=["响应时间 5 秒"],
    )
    right = _profile(
        source_id="source:right",
        title="方案 B",
        topics=["风控系统"],
        requirements=["系统必须支持多租户"],
        metrics=["响应时间 8 秒"],
    )

    summary = compare_source_profiles(
        left,
        right,
        left_title="方案 A",
        right_title="方案 B",
        compare_mode="general",
    )

    assert "综合对比" in summary.summary
    assert any(item.title == "共同主题" for item in summary.similarities)
    assert any(item.title == "方案 A独有的要求" for item in summary.differences)
    assert any("表述不一致" in item.title for item in summary.conflicts)
    assert any("中未见对应要求" in item.title for item in summary.missing_items)
    assert any("逐条回源" in item.title for item in summary.human_review_required)


def test_render_project_compare_markdown_contains_main_sections():
    left = _profile(
        source_id="source:left",
        title="方案 A",
        topics=["风控系统"],
        requirements=["系统必须支持审计日志"],
        metrics=["响应时间 5 秒"],
    )
    right = _profile(
        source_id="source:right",
        title="方案 B",
        topics=["风控系统"],
        requirements=["系统必须支持多租户"],
        metrics=["响应时间 8 秒"],
    )
    result = compare_source_profiles(
        left,
        right,
        left_title="方案 A",
        right_title="方案 B",
    )

    record = ProjectCompareRecord(
        id="cmp_demo",
        project_id="project:demo",
        compare_mode="general",
        source_a_id="source:left",
        source_b_id="source:right",
        source_a_title="方案 A",
        source_b_title="方案 B",
        status="completed",
        created_at="2026-04-18T12:00:00Z",
        updated_at="2026-04-18T12:00:30Z",
        result=result,
    )

    markdown = render_project_compare_markdown(record)

    assert "# 对比报告：方案 A vs 方案 B" in markdown
    assert "## 差异点" in markdown
    assert "## 冲突点" in markdown


@pytest.mark.asyncio
@patch(
    "open_notebook.project_os.compare_service.build_and_store_source_profile",
    new_callable=AsyncMock,
)
@patch(
    "open_notebook.project_os.compare_service.load_source_profile",
    new_callable=AsyncMock,
)
@patch("open_notebook.project_os.compare_service.Source.get", new_callable=AsyncMock)
async def test_load_or_build_profile_falls_back_to_raw_source_extract(
    mock_get_source,
    mock_load_profile,
    mock_build_profile,
):
    mock_load_profile.return_value = None
    mock_build_profile.side_effect = RuntimeError("extract failed")
    mock_get_source.return_value = SimpleNamespace(
        id="source:left",
        title="方案 A",
        full_text="风控系统需要审计日志，并要求 5 秒内响应。",
        updated="2026-04-18T12:00:00Z",
        topics=["风控系统"],
    )

    profile = await _load_or_build_profile("source:left")

    assert profile.source_id == "source:left"
    assert profile.title == "方案 A"
    assert "风控系统" in profile.topics
    assert profile.text_sample
