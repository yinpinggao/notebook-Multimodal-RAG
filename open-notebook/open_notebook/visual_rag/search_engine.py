"""Canonical Visual RAG search over unified visual assets."""

from __future__ import annotations

import asyncio
from typing import Optional

from open_notebook.seekdb import ai_retrieval_service
from open_notebook.storage.visual_assets import visual_asset_store
from open_notebook.vrag.search_engine import VRAGSearchResult
from open_notebook.vrag.utils import image_to_base64


def visual_asset_file_url(asset_id: str) -> str:
    return f"/api/visual-assets/{asset_id}/file"


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

        visual_task = visual_asset_store.search_assets(
            query,
            source_ids=source_ids,
            top_k=image_top_k,
        )
        text_task = ai_retrieval_service.text_search(
            keyword=query,
            source_ids=source_ids,
            results=text_top_k,
            note=False,
        )
        visual_rows, text_rows = await asyncio.gather(visual_task, text_task)

        results: list[VRAGSearchResult] = []
        for row in visual_rows:
            image_path = row.get("file_path")
            image_base64 = None
            if include_image_base64 and image_path:
                try:
                    image_base64 = await asyncio.to_thread(image_to_base64, image_path)
                except Exception:
                    image_base64 = None

            results.append(
                VRAGSearchResult(
                    chunk_id=str(row.get("id") or ""),
                    asset_id=str(row.get("id") or ""),
                    file_url=visual_asset_file_url(str(row.get("id") or "")),
                    score=float(row.get("score") or 0.0),
                    result_type="image",
                    image_path=image_path,
                    image_base64=image_base64,
                    text=row.get("match"),
                    page_no=row.get("page_no"),
                    source_id=row.get("source_id"),
                    bbox=row.get("bbox") or None,
                    summary=row.get("summary") or row.get("match"),
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
