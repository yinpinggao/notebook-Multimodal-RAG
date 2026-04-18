from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field

FactCategory = Literal[
    "topic",
    "keyword",
    "term",
    "people_org",
    "timeline_event",
    "metric",
    "risk",
    "requirement",
]

STOPWORDS_EN = {
    "about",
    "after",
    "also",
    "among",
    "because",
    "been",
    "being",
    "between",
    "could",
    "document",
    "from",
    "have",
    "into",
    "more",
    "most",
    "should",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "through",
    "using",
    "with",
    "without",
}

STOPWORDS_ZH = {
    "我们",
    "你们",
    "他们",
    "以及",
    "或者",
    "其中",
    "这个",
    "这些",
    "那些",
    "有关",
    "进行",
    "一个",
    "一种",
    "为了",
    "可以",
    "需要",
    "主要",
    "当前",
    "相关",
    "通过",
    "如果",
    "然后",
    "已经",
    "没有",
    "由于",
    "因为",
}

RISK_MARKERS = (
    "risk",
    "risks",
    "risky",
    "challenge",
    "challenges",
    "problem",
    "problems",
    "issue",
    "issues",
    "limitation",
    "limitations",
    "concern",
    "concerns",
    "warning",
    "warnings",
    "风险",
    "挑战",
    "问题",
    "隐患",
    "限制",
    "不足",
    "困难",
)

REQUIREMENT_MARKERS = (
    "must",
    "should",
    "shall",
    "required",
    "requirement",
    "requirements",
    "needs to",
    "need to",
    "要求",
    "必须",
    "应当",
    "需",
    "需要",
    "不得",
)

ORG_SUFFIXES = (
    "University",
    "Institute",
    "Laboratory",
    "Lab",
    "College",
    "School",
    "Center",
    "Centre",
    "Inc",
    "Corp",
    "Ltd",
    "Company",
    "大学",
    "学院",
    "研究院",
    "研究所",
    "实验室",
    "公司",
    "中心",
    "协会",
)

DATE_PATTERN = re.compile(
    r"(?P<date>"
    r"\b20\d{2}[-/.](?:0?[1-9]|1[0-2])(?:[-/.](?:0?[1-9]|[12]\d|3[01]))?\b"
    r"|20\d{2}年(?:0?[1-9]|1[0-2])月?(?:[0-3]?\d日?)?"
    r"|(?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])[-/.]20\d{2}"
    r")"
)
METRIC_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:%|ms|s|sec|seconds|minutes|hours|GB|MB|KB|x|times)\b"
    r"|(?:\d+(?:\.\d+)?)\s?(?:个|项|人|页|分|秒|分钟|小时|天|周|月|年|倍|万元|亿元|%)"
)
ACRONYM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_-]{1,}\b")
TITLE_ENTITY_PATTERN = re.compile(
    r"\b(?:[A-Z][A-Za-z]+|[A-Z]{2,}[A-Za-z]*)(?:\s+(?:[A-Z][A-Za-z]+|[A-Z]{2,}[A-Za-z]*)){0,3}\s+"
    r"(?:University|Institute|Laboratory|Lab|College|School|Center|Centre|Inc|Corp|Ltd|Company)\b"
)
ZH_ENTITY_PATTERN = re.compile(
    r"[\u4e00-\u9fff]{2,20}(?:大学|学院|研究院|研究所|实验室|公司|中心|协会)"
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StructuredFact(_Model):
    id: str
    category: FactCategory
    value: str
    source_id: str
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence_excerpt: Optional[str] = None


class TimelineSignal(_Model):
    id: str
    value: str
    occurred_at: Optional[str] = None
    source_ref: Optional[str] = None
    evidence_excerpt: Optional[str] = None


class SourceProfile(_Model):
    source_id: str
    title: str
    generated_at: str
    source_updated_at: Optional[str] = None
    source_refs: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)
    people_orgs: list[str] = Field(default_factory=list)
    timeline_events: list[TimelineSignal] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    facts: list[StructuredFact] = Field(default_factory=list)
    text_sample: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_phrase(value: str, *, max_length: int = 80) -> str:
    cleaned = _normalize_text(value).strip(" -:|,.;()[]{}<>")
    if not cleaned:
        return ""
    return cleaned[:max_length]


def _stable_id(source_id: str, category: str, value: str) -> str:
    digest = uuid5(NAMESPACE_URL, f"{source_id}:{category}:{value}")
    return f"fact:{digest.hex}"


def _dedupe(values: list[str], *, limit: Optional[int] = None) -> list[str]:
    deduped: list[str] = []
    for value in values:
        cleaned = _clean_phrase(value)
        if not cleaned or cleaned in deduped:
            continue
        deduped.append(cleaned)
        if limit and len(deduped) >= limit:
            break
    return deduped


def _split_title_phrases(title: str) -> list[str]:
    cleaned = re.sub(r"\.[A-Za-z0-9]+$", "", title or "")
    phrases: list[str] = []
    for piece in re.split(r"[/|:_\-]+", cleaned):
        normalized = _clean_phrase(piece, max_length=48)
        if normalized:
            phrases.append(normalized)
    if not phrases and cleaned:
        phrases.append(_clean_phrase(cleaned, max_length=48))
    return _dedupe(phrases, limit=4)


def _keyword_counter(text: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    normalized = _normalize_text(text)

    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b", normalized):
        lowered = token.lower()
        if lowered in STOPWORDS_EN:
            continue
        counter[token] += 1

    for token in re.findall(r"[\u4e00-\u9fff]{2,10}", normalized):
        if token in STOPWORDS_ZH:
            continue
        if len(token) > 8 and not re.search(r"(项目|系统|模型|证据|文档|方案|要求|风险)", token):
            continue
        counter[token] += 1

    return counter


def _segments_from_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    for item in items:
        source_ref = item["source_ref"]
        text = item["text"]
        for fragment in re.split(r"[\n\r。！？!?；;.\u2026]+", text):
            normalized = _clean_phrase(fragment, max_length=220)
            if len(normalized) < 4:
                continue
            segments.append({"text": normalized, "source_ref": source_ref})
    return segments


def _match_segments(
    segments: list[dict[str, str]],
    markers: tuple[str, ...],
    *,
    limit: int,
) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    lowered_markers = tuple(marker.lower() for marker in markers)
    for segment in segments:
        lowered = segment["text"].lower()
        if any(marker in lowered for marker in lowered_markers):
            matches.append(segment)
        if len(matches) >= limit:
            break
    return matches


def _extract_people_orgs(segments: list[dict[str, str]]) -> list[str]:
    results: list[str] = []
    for segment in segments:
        text = segment["text"]
        results.extend(match.group(0) for match in TITLE_ENTITY_PATTERN.finditer(text))
        results.extend(match.group(0) for match in ZH_ENTITY_PATTERN.finditer(text))
    return _dedupe(results, limit=8)


def _extract_terms(text: str) -> list[str]:
    terms = [match.group(0) for match in ACRONYM_PATTERN.finditer(text)]
    quoted = re.findall(r"[\"“](.{2,40}?)[\"”]", text)
    return _dedupe([*terms, *quoted], limit=8)


def _extract_timeline_events(
    source_id: str,
    segments: list[dict[str, str]],
) -> list[TimelineSignal]:
    events: list[TimelineSignal] = []
    seen: set[str] = set()
    for segment in segments:
        match = DATE_PATTERN.search(segment["text"])
        if not match:
            continue
        event_text = _clean_phrase(segment["text"], max_length=180)
        if not event_text or event_text in seen:
            continue
        seen.add(event_text)
        events.append(
            TimelineSignal(
                id=_stable_id(source_id, "timeline_event", event_text),
                value=event_text,
                occurred_at=match.group("date"),
                source_ref=segment["source_ref"],
                evidence_excerpt=event_text,
            )
        )
        if len(events) >= 6:
            break
    return events


def _extract_metrics(segments: list[dict[str, str]]) -> list[str]:
    metrics: list[str] = []
    for segment in segments:
        if METRIC_PATTERN.search(segment["text"]):
            metrics.append(segment["text"])
        if len(metrics) >= 8:
            break
    return _dedupe(metrics, limit=8)


def _build_fact(
    *,
    source_id: str,
    category: FactCategory,
    value: str,
    source_refs: list[str],
    confidence: float,
    evidence_excerpt: Optional[str],
) -> StructuredFact:
    normalized_value = _clean_phrase(value, max_length=180)
    return StructuredFact(
        id=_stable_id(source_id, category, normalized_value),
        category=category,
        value=normalized_value,
        source_id=source_id,
        source_refs=_dedupe(source_refs, limit=4),
        confidence=confidence,
        evidence_excerpt=_clean_phrase(evidence_excerpt or normalized_value, max_length=220)
        or None,
    )


def extract_source_profile(
    *,
    source_id: str,
    title: str,
    full_text: str = "",
    source_updated_at: Optional[str] = None,
    existing_topics: Optional[list[str]] = None,
    insight_texts: Optional[list[str]] = None,
    page_summaries: Optional[list[dict[str, str]]] = None,
    visual_summaries: Optional[list[dict[str, str]]] = None,
) -> SourceProfile:
    source_ref = source_id
    text_items: list[dict[str, str]] = []

    if title:
        text_items.append({"text": title, "source_ref": source_ref})

    for topic in existing_topics or []:
        text_items.append({"text": topic, "source_ref": source_ref})

    for insight_text in insight_texts or []:
        if insight_text:
            text_items.append({"text": insight_text, "source_ref": source_ref})

    for page in page_summaries or []:
        text = page.get("text") or ""
        if not text:
            continue
        text_items.append(
            {
                "text": text,
                "source_ref": page.get("source_ref") or source_ref,
            }
        )

    for asset in visual_summaries or []:
        text = asset.get("text") or ""
        if not text:
            continue
        text_items.append(
            {
                "text": text,
                "source_ref": asset.get("source_ref") or source_ref,
            }
        )

    if full_text:
        text_items.append({"text": full_text[:12000], "source_ref": source_ref})

    combined_text = " ".join(item["text"] for item in text_items if item["text"]).strip()
    title_topics = _split_title_phrases(title)
    keyword_counts = _keyword_counter(combined_text)
    keyword_candidates = [item for item, _ in keyword_counts.most_common(24)]
    terms = _extract_terms(combined_text)
    segments = _segments_from_items(text_items)
    people_orgs = _extract_people_orgs(segments)
    timeline_events = _extract_timeline_events(source_id, segments)
    metrics = _extract_metrics(segments)
    risk_segments = _match_segments(segments, RISK_MARKERS, limit=6)
    requirement_segments = _match_segments(segments, REQUIREMENT_MARKERS, limit=6)

    topics = _dedupe(
        [
            *(existing_topics or []),
            *title_topics,
            *keyword_candidates[:8],
        ],
        limit=6,
    )
    keywords = _dedupe(
        [
            *title_topics,
            *terms,
            *keyword_candidates,
        ],
        limit=10,
    )
    risks = _dedupe([segment["text"] for segment in risk_segments], limit=6)
    requirements = _dedupe(
        [segment["text"] for segment in requirement_segments],
        limit=6,
    )

    facts: list[StructuredFact] = []
    for topic in topics:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="topic",
                value=topic,
                source_refs=[source_ref],
                confidence=0.56,
                evidence_excerpt=topic,
            )
        )
    for keyword in keywords:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="keyword",
                value=keyword,
                source_refs=[source_ref],
                confidence=0.52,
                evidence_excerpt=keyword,
            )
        )
    for term in terms:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="term",
                value=term,
                source_refs=[source_ref],
                confidence=0.66,
                evidence_excerpt=term,
            )
        )
    for entity in people_orgs:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="people_org",
                value=entity,
                source_refs=[source_ref],
                confidence=0.6,
                evidence_excerpt=entity,
            )
        )
    for event in timeline_events:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="timeline_event",
                value=event.value,
                source_refs=[event.source_ref or source_ref],
                confidence=0.68,
                evidence_excerpt=event.evidence_excerpt,
            )
        )
    for metric in metrics:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="metric",
                value=metric,
                source_refs=[source_ref],
                confidence=0.7,
                evidence_excerpt=metric,
            )
        )
    for segment in risk_segments:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="risk",
                value=segment["text"],
                source_refs=[segment["source_ref"]],
                confidence=0.74,
                evidence_excerpt=segment["text"],
            )
        )
    for segment in requirement_segments:
        facts.append(
            _build_fact(
                source_id=source_id,
                category="requirement",
                value=segment["text"],
                source_refs=[segment["source_ref"]],
                confidence=0.76,
                evidence_excerpt=segment["text"],
            )
        )

    return SourceProfile(
        source_id=source_id,
        title=_clean_phrase(title or source_id, max_length=160) or source_id,
        generated_at=_utc_now(),
        source_updated_at=source_updated_at,
        source_refs=_dedupe(
            [item["source_ref"] for item in text_items if item["source_ref"]],
            limit=16,
        ),
        topics=topics,
        keywords=keywords,
        terms=terms,
        people_orgs=people_orgs,
        timeline_events=timeline_events,
        metrics=metrics,
        risks=risks,
        requirements=requirements,
        facts=facts,
        text_sample=_clean_phrase(combined_text, max_length=280),
    )


__all__ = [
    "StructuredFact",
    "TimelineSignal",
    "SourceProfile",
    "extract_source_profile",
]
