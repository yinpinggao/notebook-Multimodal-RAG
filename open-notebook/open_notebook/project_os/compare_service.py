from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, cast
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.compare import ProjectCompareMode, ProjectCompareRecord
from open_notebook.domain.evidence import CompareItem, CompareSummary
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.evidence.structured_extractor import (
    SourceProfile,
    extract_source_profile,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError
from open_notebook.seekdb import seekdb_business_store

from .source_profile_service import build_and_store_source_profile, load_source_profile

CATEGORY_LABELS = {
    "topic": "主题",
    "keyword": "关键词",
    "term": "术语",
    "people_org": "人物/机构",
    "metric": "指标",
    "risk": "风险",
    "requirement": "要求",
    "timeline_event": "时间线",
}

CATEGORY_FIELDS = {
    "topic": "topics",
    "keyword": "keywords",
    "term": "terms",
    "people_org": "people_orgs",
    "metric": "metrics",
    "risk": "risks",
    "requirement": "requirements",
}

MODE_CATEGORIES: dict[ProjectCompareMode, tuple[str, ...]] = {
    "general": (
        "topic",
        "keyword",
        "term",
        "people_org",
        "metric",
        "risk",
        "requirement",
        "timeline_event",
    ),
    "requirements": ("requirement", "metric", "timeline_event"),
    "risks": ("risk", "requirement", "metric"),
    "timeline": ("timeline_event", "metric", "topic"),
}

MODE_LABELS: dict[ProjectCompareMode, str] = {
    "general": "综合对比",
    "requirements": "要求对比",
    "risks": "风险对比",
    "timeline": "时间线对比",
}
VALID_COMPARE_MODES = tuple(MODE_CATEGORIES.keys())

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9%]+|[\u4e00-\u9fff]{2,}")
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
NEGATION_MARKERS = (
    " not ",
    " without ",
    " no ",
    "禁止",
    "不得",
    "不应",
    "不能",
    "未",
    "缺少",
)


@dataclass
class _Signal:
    category: str
    value: str
    refs: list[str] = field(default_factory=list)
    tokens: set[str] = field(default_factory=set)
    numbers: tuple[str, ...] = ()


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCompareIndex(_Model):
    project_id: str
    compare_ids: list[str] = Field(default_factory=list)


def project_compare_record_id(compare_id: str) -> str:
    return f"project_compare:{compare_id}"


def project_compare_index_record_id(project_id: str) -> str:
    return f"project_compare_index:{project_id}"


def create_compare_id() -> str:
    return f"cmp_{uuid4().hex[:12]}"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _strip_singleton_metadata(data: dict) -> dict:
    return {
        key: value
        for key, value in data.items()
        if key not in {"id", "created", "updated"}
    }


def _normalize_text(value: str) -> str:
    collapsed = " ".join(str(value or "").strip().split())
    lowered = collapsed.casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", lowered)


async def _load_project_compare_index(project_id: str) -> ProjectCompareIndex:
    data = await seekdb_business_store.get_singleton(
        project_compare_index_record_id(project_id)
    )
    if not data:
        return ProjectCompareIndex(project_id=project_id)
    return ProjectCompareIndex.model_validate(_strip_singleton_metadata(data))


async def _save_project_compare_index(
    index: ProjectCompareIndex,
) -> ProjectCompareIndex:
    saved = await seekdb_business_store.upsert_singleton(
        project_compare_index_record_id(index.project_id),
        index.model_dump(mode="json"),
    )
    return ProjectCompareIndex.model_validate(_strip_singleton_metadata(saved))


async def _register_project_compare(project_id: str, compare_id: str) -> None:
    index = await _load_project_compare_index(project_id)
    compare_ids = [compare_id, *index.compare_ids]
    deduped_ids: list[str] = []
    for item in compare_ids:
        if item and item not in deduped_ids:
            deduped_ids.append(item)
    index.compare_ids = deduped_ids
    await _save_project_compare_index(index)


def _clean_display(value: str, *, limit: int = 160) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _signal_tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_PATTERN.findall(value)
        if token and not token.isdigit()
    }


def _extract_numbers(value: str) -> tuple[str, ...]:
    return tuple(NUMBER_PATTERN.findall(value))


def _merge_refs(*ref_groups: Iterable[str], limit: int = 6) -> list[str]:
    merged: list[str] = []
    for refs in ref_groups:
        for ref in refs:
            normalized = " ".join(str(ref or "").strip().split())
            if not normalized or normalized in merged:
                continue
            merged.append(normalized)
            if len(merged) >= limit:
                return merged
    return merged


def _default_refs(profile: SourceProfile) -> list[str]:
    return _merge_refs(profile.source_refs or [profile.source_id])


def normalize_compare_mode(compare_mode: str) -> ProjectCompareMode:
    if compare_mode not in MODE_CATEGORIES:
        raise InvalidInputError(
            f"Unsupported compare mode: {compare_mode}. "
            f"Expected one of: {', '.join(VALID_COMPARE_MODES)}"
        )
    return cast(ProjectCompareMode, compare_mode)


def _record_signal(
    grouped: dict[tuple[str, str], _Signal],
    *,
    category: str,
    value: str,
    refs: Iterable[str],
) -> None:
    display = _clean_display(value)
    normalized = _normalize_text(display)
    if not display or not normalized:
        return

    key = (category, normalized)
    if key not in grouped:
        grouped[key] = _Signal(
            category=category,
            value=display,
            refs=_merge_refs(refs),
            tokens=_signal_tokens(display),
            numbers=_extract_numbers(display),
        )
        return

    grouped[key].refs = _merge_refs(grouped[key].refs, refs)


def _profile_signals(
    profile: SourceProfile,
    *,
    categories: tuple[str, ...],
) -> dict[tuple[str, str], _Signal]:
    grouped: dict[tuple[str, str], _Signal] = {}
    default_refs = _default_refs(profile)

    for fact in profile.facts:
        if fact.category not in categories:
            continue
        _record_signal(
            grouped,
            category=fact.category,
            value=fact.value,
            refs=fact.source_refs or default_refs,
        )

    for category, field_name in CATEGORY_FIELDS.items():
        if category not in categories:
            continue
        for value in getattr(profile, field_name):
            _record_signal(
                grouped,
                category=category,
                value=value,
                refs=default_refs,
            )

    if "timeline_event" in categories:
        for event in profile.timeline_events:
            event_value = (
                f"{event.occurred_at} {event.value}".strip()
                if event.occurred_at
                else event.value
            )
            _record_signal(
                grouped,
                category="timeline_event",
                value=event_value,
                refs=[event.source_ref] if event.source_ref else default_refs,
            )

    return grouped


def _build_similarity_items(
    left_signals: dict[tuple[str, str], _Signal],
    right_signals: dict[tuple[str, str], _Signal],
    *,
    limit: int = 8,
) -> list[CompareItem]:
    items: list[CompareItem] = []
    for key in sorted(left_signals.keys() & right_signals.keys()):
        left = left_signals[key]
        right = right_signals[key]
        items.append(
            CompareItem(
                title=f"共同{CATEGORY_LABELS.get(left.category, left.category)}",
                detail=f"两份资料都提到“{left.value}”。",
                source_refs=_merge_refs(left.refs, right.refs),
            )
        )
        if len(items) >= limit:
            break
    return items


def _build_difference_items(
    left_signals: dict[tuple[str, str], _Signal],
    right_signals: dict[tuple[str, str], _Signal],
    *,
    left_title: str,
    right_title: str,
    limit: int = 10,
) -> list[CompareItem]:
    items: list[CompareItem] = []

    for key in sorted(left_signals.keys() - right_signals.keys()):
        signal = left_signals[key]
        items.append(
            CompareItem(
                title=f"{left_title}独有的{CATEGORY_LABELS.get(signal.category, signal.category)}",
                detail=signal.value,
                source_refs=signal.refs,
            )
        )
        if len(items) >= limit:
            return items

    for key in sorted(right_signals.keys() - left_signals.keys()):
        signal = right_signals[key]
        items.append(
            CompareItem(
                title=f"{right_title}独有的{CATEGORY_LABELS.get(signal.category, signal.category)}",
                detail=signal.value,
                source_refs=signal.refs,
            )
        )
        if len(items) >= limit:
            return items

    return items


def _signals_conflict(left: _Signal, right: _Signal) -> bool:
    if left.category != right.category:
        return False

    shared_tokens = left.tokens & right.tokens
    if not shared_tokens:
        return False

    if left.numbers and right.numbers and left.numbers != right.numbers:
        return True

    left_text = f" {left.value.casefold()} "
    right_text = f" {right.value.casefold()} "
    left_negative = any(marker in left_text for marker in NEGATION_MARKERS)
    right_negative = any(marker in right_text for marker in NEGATION_MARKERS)
    return left_negative != right_negative


def _sorted_signals(signals: dict[tuple[str, str], _Signal]) -> list[_Signal]:
    return [
        signals[key]
        for key in sorted(signals, key=lambda item: (item[0], signals[item].value))
    ]


def _build_conflict_items(
    left_signals: dict[tuple[str, str], _Signal],
    right_signals: dict[tuple[str, str], _Signal],
    *,
    left_title: str,
    right_title: str,
    limit: int = 5,
) -> list[CompareItem]:
    items: list[CompareItem] = []
    seen: set[tuple[str, str, str]] = set()

    left_candidates = [
        signal
        for signal in _sorted_signals(left_signals)
        if signal.category in {"metric", "timeline_event", "requirement", "risk"}
    ]
    right_candidates = [
        signal
        for signal in _sorted_signals(right_signals)
        if signal.category in {"metric", "timeline_event", "requirement", "risk"}
    ]

    for left in left_candidates:
        for right in right_candidates:
            if not _signals_conflict(left, right):
                continue
            pair_key = (
                left.category,
                _normalize_text(left.value),
                _normalize_text(right.value),
            )
            if pair_key in seen:
                continue
            seen.add(pair_key)
            items.append(
                CompareItem(
                    title=f"{CATEGORY_LABELS.get(left.category, left.category)}表述不一致",
                    detail=(
                        f"{left_title} 提到“{left.value}”，"
                        f"{right_title} 提到“{right.value}”。"
                    ),
                    source_refs=_merge_refs(left.refs, right.refs),
                )
            )
            if len(items) >= limit:
                return items

    return items


def _build_missing_items(
    left_signals: dict[tuple[str, str], _Signal],
    right_signals: dict[tuple[str, str], _Signal],
    *,
    left_title: str,
    right_title: str,
    limit: int = 6,
) -> list[CompareItem]:
    items: list[CompareItem] = []
    priority_categories = {"requirement", "metric", "timeline_event", "risk"}

    for key in sorted(left_signals.keys() - right_signals.keys()):
        signal = left_signals[key]
        if signal.category not in priority_categories:
            continue
        items.append(
            CompareItem(
                title=f"{right_title}中未见对应{CATEGORY_LABELS.get(signal.category, signal.category)}",
                detail=f"{left_title} 提到：{signal.value}",
                source_refs=signal.refs,
            )
        )
        if len(items) >= limit:
            return items

    for key in sorted(right_signals.keys() - left_signals.keys()):
        signal = right_signals[key]
        if signal.category not in priority_categories:
            continue
        items.append(
            CompareItem(
                title=f"{left_title}中未见对应{CATEGORY_LABELS.get(signal.category, signal.category)}",
                detail=f"{right_title} 提到：{signal.value}",
                source_refs=signal.refs,
            )
        )
        if len(items) >= limit:
            return items

    return items


def _build_human_review_items(
    left_profile: SourceProfile,
    right_profile: SourceProfile,
    *,
    left_title: str,
    right_title: str,
    similarities: list[CompareItem],
    conflicts: list[CompareItem],
) -> list[CompareItem]:
    items: list[CompareItem] = []

    if len(left_profile.facts) < 3:
        items.append(
            CompareItem(
                title=f"{left_title}结构化事实偏少",
                detail="当前结论更多依赖摘要或标题信号，建议回看原文后再确认关键结论。",
                source_refs=_default_refs(left_profile),
            )
        )

    if len(right_profile.facts) < 3:
        items.append(
            CompareItem(
                title=f"{right_title}结构化事实偏少",
                detail="当前结论更多依赖摘要或标题信号，建议回看原文后再确认关键结论。",
                source_refs=_default_refs(right_profile),
            )
        )

    if not similarities:
        items.append(
            CompareItem(
                title="共同点较少，可能存在术语差异",
                detail="两份资料可能使用不同表述描述同一问题，建议人工复核是否属于同一主题。",
                source_refs=_merge_refs(
                    _default_refs(left_profile),
                    _default_refs(right_profile),
                ),
            )
        )

    if conflicts:
        items.append(
            CompareItem(
                title="存在冲突项需要逐条回源",
                detail="建议对冲突项逐条打开原始资料，确认时间、数字或约束条件的最新版本。",
                source_refs=_merge_refs(*(item.source_refs for item in conflicts)),
            )
        )

    return items[:5]


def compare_source_profiles(
    left_profile: SourceProfile,
    right_profile: SourceProfile,
    *,
    left_title: str,
    right_title: str,
    compare_mode: ProjectCompareMode = "general",
) -> CompareSummary:
    compare_mode = normalize_compare_mode(compare_mode)
    categories = MODE_CATEGORIES[compare_mode]
    left_signals = _profile_signals(left_profile, categories=categories)
    right_signals = _profile_signals(right_profile, categories=categories)

    similarities = _build_similarity_items(left_signals, right_signals)
    differences = _build_difference_items(
        left_signals,
        right_signals,
        left_title=left_title,
        right_title=right_title,
    )
    conflicts = _build_conflict_items(
        left_signals,
        right_signals,
        left_title=left_title,
        right_title=right_title,
    )
    missing_items = _build_missing_items(
        left_signals,
        right_signals,
        left_title=left_title,
        right_title=right_title,
    )
    human_review_required = _build_human_review_items(
        left_profile,
        right_profile,
        left_title=left_title,
        right_title=right_title,
        similarities=similarities,
        conflicts=conflicts,
    )

    comparison_basis = (
        "结构化事实"
        if left_profile.facts or right_profile.facts
        else "摘要与标题线索"
    )
    summary = (
        f"已按“{MODE_LABELS[compare_mode]}”对比《{left_title}》与《{right_title}》，"
        f"识别出 {len(similarities)} 个共同点、{len(differences)} 个差异点、"
        f"{len(conflicts)} 个冲突点，并补充了 {len(missing_items)} 个缺失项提示。"
        f"本轮结果优先基于{comparison_basis}生成。"
    )
    if human_review_required:
        summary += " 其中仍有需要人工复核的内容。"

    return CompareSummary(
        summary=summary,
        similarities=similarities,
        differences=differences,
        conflicts=conflicts,
        missing_items=missing_items,
        human_review_required=human_review_required,
    )


async def load_project_compare(compare_id: str) -> ProjectCompareRecord | None:
    data = await seekdb_business_store.get_singleton(project_compare_record_id(compare_id))
    if not data:
        return None
    return ProjectCompareRecord.model_validate(_strip_singleton_metadata(data))


async def load_project_compare_for_project(
    project_id: str,
    compare_id: str,
) -> ProjectCompareRecord:
    record = await load_project_compare(compare_id)
    if not record or record.project_id != project_id:
        raise NotFoundError("Compare record not found")
    return record


async def list_project_compares(
    project_id: str,
    *,
    limit: int = 30,
) -> list[ProjectCompareRecord]:
    index = await _load_project_compare_index(project_id)
    records: list[ProjectCompareRecord] = []
    for compare_id in index.compare_ids:
        record = await load_project_compare(compare_id)
        if not record or record.project_id != project_id:
            continue
        records.append(record)

    records.sort(key=lambda item: item.updated_at, reverse=True)
    return records[:limit]


async def save_project_compare(record: ProjectCompareRecord) -> ProjectCompareRecord:
    saved = await seekdb_business_store.upsert_singleton(
        project_compare_record_id(record.id),
        record.model_dump(mode="json"),
    )
    return ProjectCompareRecord.model_validate(_strip_singleton_metadata(saved))


async def mark_project_compare_status(
    compare_id: str,
    status: str,
    *,
    command_id: str | None = None,
    error_message: str | None = None,
) -> ProjectCompareRecord:
    current = await load_project_compare(compare_id)
    if not current:
        raise NotFoundError("Compare record not found")

    payload = current.model_dump(mode="json")
    payload["status"] = status
    payload["error_message"] = error_message
    payload["updated_at"] = _utc_now()
    if command_id is not None:
        payload["command_id"] = command_id

    return await save_project_compare(ProjectCompareRecord.model_validate(payload))


async def _resolve_project_sources(
    project_id: str,
    source_a_id: str,
    source_b_id: str,
) -> tuple[Source, Source]:
    if source_a_id == source_b_id:
        raise InvalidInputError("Please choose two different sources to compare")

    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Project not found")

    sources = await notebook.get_sources()
    source_map = {str(source.id): source for source in sources if source.id}

    left = source_map.get(source_a_id)
    right = source_map.get(source_b_id)
    if not left or not right:
        raise NotFoundError("Source not found")

    return left, right


async def initialize_project_compare(
    project_id: str,
    *,
    source_a_id: str,
    source_b_id: str,
    compare_mode: ProjectCompareMode = "general",
) -> ProjectCompareRecord:
    compare_mode = normalize_compare_mode(compare_mode)
    left_source, right_source = await _resolve_project_sources(
        project_id,
        source_a_id,
        source_b_id,
    )
    compare_id = create_compare_id()
    now = _utc_now()
    record = ProjectCompareRecord(
        id=compare_id,
        project_id=project_id,
        compare_mode=compare_mode,
        source_a_id=source_a_id,
        source_b_id=source_b_id,
        source_a_title=str(left_source.title or source_a_id),
        source_b_title=str(right_source.title or source_b_id),
        status="queued",
        created_at=now,
        updated_at=now,
        result=None,
    )
    saved = await save_project_compare(record)
    await _register_project_compare(project_id, saved.id)
    return saved


async def _fallback_source_profile(source_id: str) -> SourceProfile:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    return extract_source_profile(
        source_id=source_id,
        title=str(source.title or source_id),
        full_text=str(source.full_text or ""),
        source_updated_at=str(source.updated) if source.updated else None,
        existing_topics=list(source.topics or []),
        insight_texts=[],
        page_summaries=[],
        visual_summaries=[],
    )


async def _load_or_build_profile(source_id: str) -> SourceProfile:
    profile = await load_source_profile(source_id)
    if profile:
        return profile

    try:
        return await build_and_store_source_profile(source_id)
    except Exception as exc:
        logger.warning(
            f"Falling back to raw source compare profile for {source_id}: {exc}"
        )
        return await _fallback_source_profile(source_id)


async def build_and_store_project_compare(
    project_id: str,
    *,
    compare_id: str,
    source_a_id: str,
    source_b_id: str,
    compare_mode: ProjectCompareMode = "general",
    command_id: str | None = None,
) -> ProjectCompareRecord:
    compare_mode = normalize_compare_mode(compare_mode)
    current = await load_project_compare_for_project(project_id, compare_id)
    await _resolve_project_sources(project_id, source_a_id, source_b_id)

    left_profile, right_profile = await asyncio.gather(
        _load_or_build_profile(source_a_id),
        _load_or_build_profile(source_b_id),
    )

    result = compare_source_profiles(
        left_profile,
        right_profile,
        left_title=current.source_a_title,
        right_title=current.source_b_title,
        compare_mode=compare_mode,
    )

    record = ProjectCompareRecord(
        **{
            **current.model_dump(mode="json"),
            "compare_mode": compare_mode,
            "status": "completed",
            "command_id": command_id if command_id is not None else current.command_id,
            "error_message": None,
            "updated_at": _utc_now(),
            "result": result.model_dump(mode="json"),
        }
    )
    return await save_project_compare(record)


def _render_items(items: list[CompareItem]) -> list[str]:
    if not items:
        return ["暂无。", ""]

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. **{item.title}**")
        lines.append(f"   - {item.detail}")
        if item.source_refs:
            lines.append(f"   - source refs: {', '.join(item.source_refs)}")
    lines.append("")
    return lines


def render_project_compare_markdown(record: ProjectCompareRecord) -> str:
    lines = [
        f"# 对比报告：{record.source_a_title} vs {record.source_b_title}",
        "",
        f"- compare_id: `{record.id}`",
        f"- project_id: `{record.project_id}`",
        f"- compare_mode: `{record.compare_mode}`",
        f"- status: `{record.status}`",
        f"- updated_at: `{record.updated_at}`",
        "",
    ]

    if not record.result:
        lines.extend(
            [
                "## 状态",
                "",
                "当前对比结果尚未生成完成。",
                "",
            ]
        )
        return "\n".join(lines)

    sections = [
        ("摘要", [CompareItem(title="概览", detail=record.result.summary, source_refs=[])]),
        ("相同点", record.result.similarities),
        ("差异点", record.result.differences),
        ("冲突点", record.result.conflicts),
        ("缺失点", record.result.missing_items),
        ("需人工确认", record.result.human_review_required),
    ]

    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        lines.extend(_render_items(items))

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "build_and_store_project_compare",
    "compare_source_profiles",
    "create_compare_id",
    "initialize_project_compare",
    "list_project_compares",
    "load_project_compare",
    "load_project_compare_for_project",
    "mark_project_compare_status",
    "normalize_compare_mode",
    "project_compare_index_record_id",
    "project_compare_record_id",
    "render_project_compare_markdown",
    "save_project_compare",
]
