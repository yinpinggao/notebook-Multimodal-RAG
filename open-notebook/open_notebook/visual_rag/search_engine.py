"""Canonical Visual RAG search over unified visual assets."""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from open_notebook.seekdb import ai_retrieval_service
from open_notebook.storage.visual_assets import visual_asset_store
from open_notebook.vrag.search_engine import VRAGSearchResult
from open_notebook.vrag.utils import image_to_base64


def visual_asset_file_url(asset_id: str) -> str:
    return f"/api/visual-assets/{asset_id}/file"


VISUAL_QUERY_SYNONYMS: dict[str, list[str]] = {
    "图表": ["figure", "fig", "table", "chart", "diagram"],
    "图示": ["figure", "fig", "diagram"],
    "图片": ["image", "figure", "illustration"],
    "图像": ["image", "figure", "illustration"],
    "表格": ["table"],
    "插图": ["figure", "illustration", "image"],
    "figure": ["fig", "diagram", "chart"],
    "figures": ["figure", "fig"],
    "fig": ["figure"],
    "table": ["figure", "chart"],
    "tables": ["table"],
    "chart": ["figure", "graph", "plot"],
    "charts": ["chart", "graph"],
    "diagram": ["figure", "schema"],
    "diagrams": ["diagram", "figure"],
    "graph": ["chart", "plot", "figure"],
    "graphs": ["graph", "chart"],
}

VISUAL_FALLBACK_QUERIES = ["figure", "fig", "table", "chart", "diagram", "image"]
PAGE_RENDER_ASSET_TYPES = {"page_render", "pdf_page"}
DETAIL_QUERY_MARKERS = (
    "figure",
    "fig",
    "table",
    "chart",
    "diagram",
    "graph",
    "plot",
    "局部",
    "细节",
    "放大",
    "裁剪",
    "框选",
    "bbox",
    "crop",
    "panel",
)
VISUAL_INVENTORY_MARKERS = (
    "什么图片",
    "哪些图片",
    "什么图",
    "哪些图",
    "看见什么",
    "看到什么",
    "能看见什么",
    "能看到什么",
    "可以看见什么",
    "可以看到什么",
    "有哪些图片",
    "有什么图片",
    "有哪些图",
    "有什么图",
    "what can you see",
    "what do you see",
    "what images",
    "which images",
    "what figures",
    "which figures",
    "what charts",
    "which charts",
)
ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "those",
    "to",
    "what",
    "which",
    "with",
}


def _singularize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _expand_search_queries(query: str) -> list[str]:
    normalized = " ".join((query or "").strip().lower().split())
    if not normalized:
        return []

    queries: list[str] = [normalized]
    tokens = [
        token
        for token in re.split(r"[^\w\u4e00-\u9fff]+", normalized)
        if token and token not in ENGLISH_STOPWORDS and (len(token) > 2 or token in {"fig", "图", "表"})
    ]

    for token in tokens:
        queries.append(token)
        singular = _singularize_token(token)
        if singular != token:
            queries.append(singular)

    query_space = " ".join(tokens)
    for key, synonyms in VISUAL_QUERY_SYNONYMS.items():
        if key in normalized or key in query_space:
            queries.extend(synonyms)

    if any("\u4e00" <= char <= "\u9fff" for char in normalized):
        queries.extend(VISUAL_FALLBACK_QUERIES)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in queries:
        cleaned = item.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)

    return deduped[:8]


def _merge_ranked_rows(rows_by_query: list[list[dict]]) -> list[dict]:
    merged: dict[str, dict] = {}

    for rows in rows_by_query:
        for row in rows:
            row_id = str(
                row.get("id")
                or row.get("chunk_id")
                or f"{row.get('source_id') or row.get('parent_id')}:{row.get('page') or row.get('page_no')}:{row.get('match') or row.get('title') or ''}"
            )
            if not row_id:
                continue

            if row_id not in merged:
                merged[row_id] = dict(row)
                continue

            current = merged[row_id]
            current["score"] = float(current.get("score") or 0.0) + float(row.get("score") or 0.0)

            if len(str(row.get("match") or "")) > len(str(current.get("match") or "")):
                current["match"] = row.get("match")
            if not current.get("summary") and row.get("summary"):
                current["summary"] = row.get("summary")
            if not current.get("text") and row.get("text"):
                current["text"] = row.get("text")

    return sorted(
        merged.values(),
        key=lambda item: float(item.get("score") or item.get("relevance") or 0.0),
        reverse=True,
    )


def _normalize_query_text(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def _is_visual_inventory_query(query: str) -> bool:
    normalized = _normalize_query_text(query)
    if not normalized:
        return False
    return any(marker in normalized for marker in VISUAL_INVENTORY_MARKERS)


def _query_requests_detail_assets(query: str) -> bool:
    normalized = _normalize_query_text(query)
    if not normalized:
        return False
    if any(marker in normalized for marker in DETAIL_QUERY_MARKERS):
        return True
    return bool(
        re.search(
            r"\b(fig(?:ure)?|table|chart|diagram|graph|plot)\s*[\divx]+\b",
            normalized,
        )
    )


def _row_metadata(row: dict) -> dict:
    metadata = row.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _is_native_image_row(row: dict) -> bool:
    if row.get("asset_type") == "native_image":
        return True
    return bool(_row_metadata(row).get("is_native_image"))


def _is_page_render_row(row: dict) -> bool:
    asset_type = str(row.get("asset_type") or "")
    if asset_type in PAGE_RENDER_ASSET_TYPES:
        return True
    return not _is_native_image_row(row)


def _visual_row_page_key(row: dict) -> tuple[str, int]:
    return (
        str(row.get("source_id") or ""),
        int(row.get("page_no") or -1),
    )


def _visual_row_effective_score(
    row: dict,
    *,
    inventory_query: bool,
    detail_query: bool,
) -> float:
    score = float(row.get("score") or row.get("relevance") or 0.0)
    metadata = _row_metadata(row)
    is_page_render = _is_page_render_row(row)
    is_native = _is_native_image_row(row)
    area_ratio = float(metadata.get("area_ratio") or 0.0)
    haystack = " ".join(
        str(row.get(key) or "") for key in ("summary", "match", "raw_text")
    ).lower()

    if is_page_render:
        score += 1.2 if inventory_query else 0.25
    elif inventory_query:
        score -= 0.2

    if is_native and area_ratio:
        if area_ratio < 0.01:
            score -= 0.5
        elif area_ratio < 0.02:
            score -= 0.2

    if detail_query and is_native and any(
        marker in haystack for marker in ("figure", "fig", "table", "chart", "diagram", "graph", "plot", "图", "表")
    ):
        score += 0.35

    return score


def _rerank_visual_rows(rows: list[dict], query: str, image_top_k: int) -> list[dict]:
    if not rows:
        return []

    inventory_query = _is_visual_inventory_query(query)
    detail_query = _query_requests_detail_assets(query)
    candidates = [dict(row) for row in rows]

    page_render_rows = [row for row in candidates if _is_page_render_row(row)]
    if inventory_query and page_render_rows:
        candidates = page_render_rows

    for row in candidates:
        row["effective_score"] = _visual_row_effective_score(
            row,
            inventory_query=inventory_query,
            detail_query=detail_query,
        )

    candidates.sort(
        key=lambda row: (
            float(row.get("effective_score") or 0.0),
            1 if _is_page_render_row(row) else 0,
            -int(row.get("page_no") or 0),
        ),
        reverse=True,
    )

    selected: list[dict] = []
    selected_ids: set[str] = set()
    seen_pages: set[tuple[str, int]] = set()

    for row in candidates:
        row_id = str(row.get("id") or "")
        if row_id in selected_ids:
            continue
        page_key = _visual_row_page_key(row)
        if page_key in seen_pages:
            continue
        selected.append(row)
        selected_ids.add(row_id)
        seen_pages.add(page_key)
        if len(selected) >= image_top_k:
            return selected

    for row in candidates:
        row_id = str(row.get("id") or "")
        if row_id in selected_ids:
            continue
        selected.append(row)
        selected_ids.add(row_id)
        if len(selected) >= image_top_k:
            break

    return selected[:image_top_k]


class VisualAssetSearchEngine:
    """Search engine used by Visual RAG tools.

    It searches the canonical `ai_visual_assets` table for visual evidence and
    the existing text index for textual context, then returns the result shape
    expected by `VRAGTools`.
    """

    def __init__(self, default_top_k: int = 5):
        self.default_top_k = default_top_k

    async def search_hybrid(
        self,
        query: str,
        query_image_path: Optional[str] = None,
        source_ids: Optional[list[str]] = None,
        image_top_k: Optional[int] = None,
        text_top_k: Optional[int] = None,
        include_image_base64: bool = False,
    ) -> list[VRAGSearchResult]:
        image_top_k = image_top_k or self.default_top_k
        text_top_k = text_top_k or self.default_top_k
        search_queries = _expand_search_queries(query) or [query]
        visual_candidate_top_k = max(image_top_k * 6, 24)
        text_candidate_top_k = max(text_top_k * 2, text_top_k)

        visual_tasks = [
            visual_asset_store.search_assets(
                search_query,
                source_ids=source_ids,
                top_k=visual_candidate_top_k,
            )
            for search_query in search_queries
        ]
        text_tasks = [
            ai_retrieval_service.text_search(
                keyword=search_query,
                source_ids=source_ids,
                results=text_candidate_top_k,
                note=False,
            )
            for search_query in search_queries
        ]
        visual_rows_by_query, text_rows_by_query = await asyncio.gather(
            asyncio.gather(*visual_tasks),
            asyncio.gather(*text_tasks),
        )
        visual_rows = _rerank_visual_rows(
            _merge_ranked_rows(visual_rows_by_query),
            query,
            image_top_k,
        )
        text_rows = _merge_ranked_rows(text_rows_by_query)[:text_top_k]

        results: list[VRAGSearchResult] = []
        for row in visual_rows:
            asset_id = str(row.get("id") or "")
            image_path = row.get("file_path")
            is_native_image = _is_native_image_row(row)
            image_base64 = None
            if include_image_base64 and image_path:
                try:
                    image_base64 = await asyncio.to_thread(image_to_base64, image_path)
                except Exception:
                    image_base64 = None

            results.append(
                VRAGSearchResult(
                    chunk_id=asset_id,
                    asset_id=asset_id,
                    file_url=visual_asset_file_url(asset_id) if asset_id and image_path else None,
                    score=float(row.get("effective_score") or row.get("score") or 0.0),
                    result_type="image",
                    image_path=image_path,
                    image_base64=image_base64,
                    text=row.get("match"),
                    page_no=row.get("page_no"),
                    source_id=row.get("source_id"),
                    bbox=row.get("bbox") or None,
                    summary=row.get("summary") or row.get("match"),
                    asset_type=row.get("asset_type"),
                    is_native_image=is_native_image,
                )
            )

        for row in text_rows[:text_top_k]:
            results.append(
                VRAGSearchResult(
                    chunk_id=str(row.get("id") or ""),
                    score=float(row.get("relevance") or row.get("score") or 0.0),
                    result_type="text",
                    text=(row.get("match") or "\n".join(row.get("matches") or [])),
                    page_no=row.get("page"),
                    source_id=row.get("source_id") or row.get("parent_id"),
                    summary=row.get("title"),
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[: image_top_k + text_top_k]
