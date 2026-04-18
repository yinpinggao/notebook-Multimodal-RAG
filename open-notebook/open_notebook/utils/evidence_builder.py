from typing import Any, Optional

from open_notebook.domain.notebook import Note, Source
from open_notebook.seekdb import ai_retrieval_service, use_seekdb_for_search

VISUAL_QUERY_TERMS = (
    "图片",
    "图像",
    "图表",
    "架构图",
    "插图",
    "配图",
    "截图",
    "照片",
    "figure",
    "fig.",
    "diagram",
    "chart",
    "image",
    "images",
    "picture",
    "visual",
    "vision",
)


def _collect_ids(items: Any) -> list[str]:
    if not items:
        return []
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
        elif isinstance(item, str):
            ids.append(item)
    return ids


def extract_scope_ids_from_context(context: Any) -> tuple[list[str], list[str]]:
    if not isinstance(context, dict):
        return [], []
    source_ids = _collect_ids(context.get("sources"))
    note_ids = _collect_ids(context.get("notes"))
    return source_ids, note_ids


def _is_visual_query(query: str) -> bool:
    lowered = (query or "").lower()
    return any(term in query or term in lowered for term in VISUAL_QUERY_TERMS)


def _format_result_block(index: int, row: dict[str, Any]) -> str:
    filename = row.get("filename") or "未知文件"
    page = row.get("page")
    internal_ref = row.get("internal_ref") or row.get("parent_id") or row.get("id")
    if page:
        header = (
            f"[{index}] 文件：{filename}；页码：{page}；内部引用：{internal_ref}"
        )
    else:
        header = f"[{index}] 文件：{filename}；页码：未知；内部引用：{internal_ref}"
    title = row.get("title") or "Untitled"
    snippets = row.get("matches") or []
    snippet_text = "\n".join(f"- {snippet}" for snippet in snippets if snippet)
    if not snippet_text and row.get("match"):
        snippet_text = f"- {row['match']}"
    citation = row.get("citation_text") or f"内部引用：[{internal_ref}]"
    visual_line = ""
    if row.get("has_visual_summary"):
        visual_line = "视觉证据：已包含页面图像摘要（来自 PDF 页图分析）"
    return "\n".join(
        [
            header,
            f"标题：{title}",
            f"类型：{row.get('source_kind') or row.get('entity_type') or 'unknown'}",
            visual_line,
            f"证据：\n{snippet_text}".strip(),
            citation,
        ]
    ).strip()


def _trim_fallback_text(value: Any, *, limit: int = 1200) -> str:
    normalized = " ".join(str(value or "").strip().split())
    return normalized[:limit] if normalized else "当前资料暂无可展示摘要。"


def _fallback_source_row(context: dict[str, Any]) -> dict[str, Any]:
    source_id = str(context.get("id") or "")
    title = str(context.get("title") or "未命名资料")
    return {
        "source_id": source_id,
        "parent_id": source_id,
        "id": source_id,
        "title": title,
        "filename": title,
        "match": _trim_fallback_text(context.get("full_text")),
        "citation_text": f"引用：{title} | 内部引用：[{source_id}]",
        "internal_ref": source_id,
        "source_kind": "source",
        "entity_type": "source",
    }


def _fallback_note_row(context: dict[str, Any]) -> dict[str, Any]:
    note_id = str(context.get("id") or "")
    title = str(context.get("title") or "未命名笔记")
    return {
        "source_id": note_id,
        "parent_id": note_id,
        "id": note_id,
        "title": title,
        "filename": title,
        "match": _trim_fallback_text(context.get("content")),
        "citation_text": f"引用：{title} | 内部引用：[{note_id}]",
        "internal_ref": note_id,
        "source_kind": "note",
        "entity_type": "note",
    }


async def build_multimodal_evidence(
    query: str,
    *,
    source_ids: Optional[list[str]] = None,
    note_ids: Optional[list[str]] = None,
    include_sources: bool = True,
    include_notes: bool = True,
    limit: int = 6,
    minimum_score: float = 0.2,
    fallback_source_id: Optional[str] = None,
) -> dict[str, Any]:
    source_ids = [str(item) for item in (source_ids or []) if item]
    note_ids = [str(item) for item in (note_ids or []) if item]

    if use_seekdb_for_search():
        results = await ai_retrieval_service.hybrid_multimodal_search(
            query,
            limit,
            source=include_sources,
            note=include_notes,
            minimum_score=minimum_score,
            source_ids=source_ids or None,
            note_ids=note_ids or None,
        )
    else:
        from open_notebook.domain.notebook import vector_search

        results = await vector_search(
            query,
            limit,
            source=include_sources,
            note=include_notes,
            minimum_score=minimum_score,
            source_ids=source_ids or None,
            note_ids=note_ids or None,
        )
        normalized_results = []
        for row in results:
            internal_ref = row.get("parent_id") or row.get("id")
            normalized_results.append(
                {
                    **row,
                    "internal_ref": internal_ref,
                    "citation_text": f"内部引用：[{internal_ref}]"
                    if internal_ref
                    else "",
                    "source_kind": row.get("source_kind")
                    or row.get("entity_type")
                    or row.get("type")
                    or "document",
                }
            )
        results = normalized_results

    if not results and fallback_source_id:
        source = await Source.get(fallback_source_id)
        if source:
            results = [_fallback_source_row(await source.get_context(context_size="long"))]

    if not results:
        fallback_results: list[dict[str, Any]] = []
        for source_id in source_ids[:3]:
            source = await Source.get(source_id)
            if source:
                fallback_results.append(
                    _fallback_source_row(await source.get_context(context_size="long"))
                )
        for note_id in note_ids[:3]:
            note = await Note.get(note_id)
            if note:
                fallback_results.append(
                    _fallback_note_row(note.get_context(context_size="long"))
                )
        if fallback_results:
            results = fallback_results

    if results and _is_visual_query(query):
        visual_rows = [row for row in results if row.get("has_visual_summary")]
        non_visual_rows = [row for row in results if not row.get("has_visual_summary")]
        results = visual_rows + non_visual_rows

    context_text = "\n\n".join(
        _format_result_block(index, row)
        for index, row in enumerate(results, start=1)
    )

    indicators = {
        "sources": [],
        "insights": [],
        "notes": [],
    }
    for row in results:
        entity_type = row.get("entity_type")
        if entity_type == "note":
            indicators["notes"].append(str(row.get("parent_id") or row.get("id")))
        elif entity_type == "source_insight":
            indicators["insights"].append(str(row.get("parent_id") or row.get("id")))
        else:
            indicators["sources"].append(str(row.get("parent_id") or row.get("id")))

    for key in indicators:
        deduped: list[str] = []
        for value in indicators[key]:
            if value and value not in deduped:
                deduped.append(value)
        indicators[key] = deduped

    return {
        "results": results,
        "context_text": context_text,
        "context_indicators": indicators,
    }
