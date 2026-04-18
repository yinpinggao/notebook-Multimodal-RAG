from __future__ import annotations

from typing import Any

from open_notebook.domain.evidence import EvidenceCard

from .citation_service import build_citation_text, build_internal_ref, extract_page_no


def _row_score(row: dict[str, Any]) -> float | None:
    raw_score = (
        row.get("final_score")
        or row.get("relevance")
        or row.get("similarity")
        or row.get("score")
    )
    if raw_score is None:
        return None

    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None

    if score < 0:
        return 0.0
    if score <= 1:
        return score
    return min(score / 5.0, 1.0)


def _excerpt(row: dict[str, Any]) -> str:
    matches = row.get("matches")
    if isinstance(matches, list):
        normalized = [str(item).strip() for item in matches if str(item).strip()]
        if normalized:
            return " ".join(normalized)[:320]

    for key in ("match", "summary", "text", "raw_text"):
        value = row.get(key)
        if value:
            return str(value).strip()[:320]

    return "当前检索结果没有返回可直接展示的摘录。"


def _relevance_reason(row: dict[str, Any], mode: str) -> str:
    if mode in {"visual", "mixed"} and row.get("has_visual_summary"):
        return "该页包含页图摘要，能直接支持图表、版面或截图相关判断。"
    if extract_page_no(row):
        return "这条证据定位到了具体页码，适合回看原文或原页。"
    if str(row.get("entity_type") or "") == "note":
        return "这是项目里的相关笔记记录，可补充当前判断。"
    return "这段内容与当前问题的关键词和语义最相关。"


def build_evidence_cards(
    *,
    project_id: str,
    thread_id: str | None,
    rows: list[dict[str, Any]],
    mode: str,
    limit: int = 5,
) -> list[EvidenceCard]:
    cards: list[EvidenceCard] = []

    for index, row in enumerate(rows[:limit], start=1):
        source_id = str(row.get("source_id") or row.get("parent_id") or row.get("id") or "")
        if not source_id:
            continue

        page_no = extract_page_no(row)
        source_name = str(
            row.get("filename")
            or row.get("title")
            or row.get("source_name")
            or "未命名资料"
        )
        internal_ref = build_internal_ref(row)
        citation_text = build_citation_text(row)

        cards.append(
            EvidenceCard(
                id=f"evidence:{project_id}:{thread_id or 'ad-hoc'}:{index}",
                project_id=project_id,
                thread_id=thread_id,
                source_name=source_name,
                source_id=source_id,
                page_no=page_no,
                excerpt=_excerpt(row),
                citation_text=citation_text or f"内部引用：[{internal_ref}]",
                internal_ref=internal_ref or source_id,
                relevance_reason=_relevance_reason(row, mode),
                image_thumb=str(row.get("page_image_path")).strip()
                if row.get("page_image_path")
                else None,
                score=_row_score(row),
            )
        )

    return cards
