import json
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any, Optional

from open_notebook.utils.embedding import generate_embedding

from .client import seekdb_client
from .index_store import cosine_similarity
from .page_store import ai_page_store

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


def _json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


class AIRetrievalService:
    def _is_visual_query(self, keyword: str) -> bool:
        lowered = (keyword or "").lower()
        return any(term in keyword or term in lowered for term in VISUAL_QUERY_TERMS)

    def _query_boost(
        self, keyword: str, row: dict[str, Any], *, for_vector: bool = False
    ) -> float:
        if not self._is_visual_query(keyword):
            return 0.0

        boost = 0.0
        source_kind = str(row.get("source_kind") or "")
        has_visual_summary = bool(row.get("has_visual_summary"))

        if source_kind == "page":
            boost += 0.35 if for_vector else 1.5
        if has_visual_summary:
            boost += 0.75 if for_vector else 3.0
        if row.get("page"):
            boost += 0.05 if for_vector else 0.25
        if source_kind in {"note", "insight"}:
            boost -= 0.20 if for_vector else 0.50

        return boost

    def _within_scope(
        self,
        row: dict[str, Any],
        source_ids: Optional[set[str]],
        note_ids: Optional[set[str]],
    ) -> bool:
        parent_id = str(row.get("parent_id") or "")
        source_id = str(row.get("source_id") or parent_id)
        if source_ids is not None and row.get("entity_type") in {
            "source",
            "source_insight",
            "source_page",
            "source_chunk",
        }:
            if source_id not in source_ids and parent_id not in source_ids:
                return False
        if note_ids is not None and row.get("entity_type") == "note":
            return parent_id in note_ids
        return True

    def _base_result(
        self,
        *,
        row_id: str,
        parent_id: str,
        title: str,
        entity_type: str,
        source_kind: str,
        match: str = "",
        filename: Optional[str] = None,
        page: Optional[int] = None,
        page_id: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> dict[str, Any]:
        internal_ref = parent_id or row_id
        citation_text = ""
        if filename and page:
            citation_text = f"引用：{filename}（第{page}页） | 内部引用：[{internal_ref}]"
        elif internal_ref:
            citation_text = f"内部引用：[{internal_ref}]"

        return {
            "id": row_id,
            "parent_id": parent_id,
            "title": title,
            "match": match,
            "entity_type": entity_type,
            "type": entity_type,
            "source_kind": source_kind,
            "filename": filename,
            "page": page,
            "page_id": page_id,
            "updated": updated_at,
            "internal_ref": internal_ref,
            "citation_text": citation_text,
        }

    async def _chunk_text_candidates(
        self,
        keyword: str,
        source_ids: Optional[list[str]],
        limit_per_table: int,
    ) -> list[dict[str, Any]]:
        pattern = f"%{keyword.lower()}%"
        params: list[Any] = []
        where_clause = """
            (LOWER(content) LIKE %s OR LOWER(COALESCE(title, '')) LIKE %s)
        """
        params.extend([pattern, pattern])

        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            where_clause += f" AND source_id IN ({placeholders})"
            params.extend(source_ids)

        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, source_id, page_id, page_no, filename, title, content, updated_at
            FROM ai_source_chunks
            WHERE {where_clause}
            LIMIT %s
            """,
            (*params, limit_per_table),
        )
        candidates: list[dict[str, Any]] = []
        lowered_keyword = keyword.lower()
        for row in rows:
            title = str(row.get("title") or row.get("filename") or "Untitled Source")
            content = str(row.get("content") or "")
            score = content.lower().count(lowered_keyword) + title.lower().count(
                lowered_keyword
            )
            candidates.append(
                {
                    **self._base_result(
                        row_id=str(row.get("id") or ""),
                        parent_id=str(row.get("source_id") or ""),
                        title=title,
                        entity_type="source",
                        source_kind="chunk",
                        match=content[:240],
                        filename=row.get("filename"),
                        page=int(row.get("page_no") or 0) or None,
                        page_id=row.get("page_id"),
                        updated_at=row.get("updated_at"),
                    ),
                    "source_id": str(row.get("source_id") or ""),
                    "score": float(score or 1),
                }
            )
        return candidates

    async def _chunk_vector_candidates(
        self,
        source_ids: Optional[list[str]],
    ) -> list[dict[str, Any]]:
        params: list[Any] = []
        where_clause = "embedding_json IS NOT NULL AND embedding_json != ''"
        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            where_clause += f" AND source_id IN ({placeholders})"
            params.extend(source_ids)

        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, source_id, page_id, page_no, filename, title, content,
                   updated_at, embedding_json
            FROM ai_source_chunks
            WHERE {where_clause}
            """,
            tuple(params) if params else None,
        )

        candidates: list[dict[str, Any]] = []
        for row in rows:
            candidates.append(
                {
                    **self._base_result(
                        row_id=str(row.get("id") or ""),
                        parent_id=str(row.get("source_id") or ""),
                        title=str(
                            row.get("title") or row.get("filename") or "Untitled Source"
                        ),
                        entity_type="source",
                        source_kind="chunk",
                        match=(row.get("content") or "")[:260],
                        filename=row.get("filename"),
                        page=int(row.get("page_no") or 0) or None,
                        page_id=row.get("page_id"),
                        updated_at=row.get("updated_at"),
                    ),
                    "source_id": str(row.get("source_id") or ""),
                    "embedding": _json_loads(row.get("embedding_json"), []),
                }
            )
        return candidates

    async def _note_text_candidates(
        self,
        keyword: str,
        note_ids: Optional[list[str]],
        limit_per_table: int,
    ) -> list[dict[str, Any]]:
        pattern = f"%{keyword.lower()}%"
        params: list[Any] = [pattern, pattern]
        where_clause = "LOWER(content) LIKE %s OR LOWER(COALESCE(title, '')) LIKE %s"
        if note_ids:
            placeholders = ", ".join(["%s"] * len(note_ids))
            where_clause += f" AND note_id IN ({placeholders})"
            params.extend(note_ids)

        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, note_id, title, content, updated_at
            FROM ai_note_index
            WHERE {where_clause}
            LIMIT %s
            """,
            (*params, limit_per_table),
        )
        lowered_keyword = keyword.lower()
        return [
            {
                **self._base_result(
                    row_id=str(row.get("note_id") or row.get("id") or ""),
                    parent_id=str(row.get("note_id") or row.get("id") or ""),
                    title=str(row.get("title") or "Untitled Note"),
                    entity_type="note",
                    source_kind="note",
                    match=(row.get("content") or "")[:240],
                    updated_at=row.get("updated_at"),
                ),
                "score": float(
                    (str(row.get("content") or "").lower().count(lowered_keyword))
                    + (str(row.get("title") or "").lower().count(lowered_keyword))
                    or 1
                ),
            }
            for row in rows
        ]

    async def _note_vector_candidates(
        self,
        note_ids: Optional[list[str]],
    ) -> list[dict[str, Any]]:
        params: list[Any] = []
        where_clause = "embedding_json IS NOT NULL AND embedding_json != ''"
        if note_ids:
            placeholders = ", ".join(["%s"] * len(note_ids))
            where_clause += f" AND note_id IN ({placeholders})"
            params.extend(note_ids)
        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, note_id, title, content, updated_at, embedding_json
            FROM ai_note_index
            WHERE {where_clause}
            """,
            tuple(params) if params else None,
        )
        return [
            {
                **self._base_result(
                    row_id=str(row.get("note_id") or row.get("id") or ""),
                    parent_id=str(row.get("note_id") or row.get("id") or ""),
                    title=str(row.get("title") or "Untitled Note"),
                    entity_type="note",
                    source_kind="note",
                    match=(row.get("content") or "")[:240],
                    updated_at=row.get("updated_at"),
                ),
                "embedding": _json_loads(row.get("embedding_json"), []),
            }
            for row in rows
        ]

    async def _insight_text_candidates(
        self,
        keyword: str,
        source_ids: Optional[list[str]],
        limit_per_table: int,
    ) -> list[dict[str, Any]]:
        pattern = f"%{keyword.lower()}%"
        params: list[Any] = [pattern, pattern, pattern]
        where_clause = """
            LOWER(content) LIKE %s
            OR LOWER(COALESCE(source_title, '')) LIKE %s
            OR LOWER(COALESCE(insight_type, '')) LIKE %s
        """
        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            where_clause += f" AND source_id IN ({placeholders})"
            params.extend(source_ids)
        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, insight_id, source_id, source_title, insight_type, content, updated_at
            FROM ai_insight_index
            WHERE {where_clause}
            LIMIT %s
            """,
            (*params, limit_per_table),
        )
        lowered_keyword = keyword.lower()
        candidates: list[dict[str, Any]] = []
        for row in rows:
            title = f"{row.get('insight_type')} - {row.get('source_title') or ''}".strip(
                " -"
            )
            candidates.append(
                {
                    **self._base_result(
                        row_id=str(row.get("insight_id") or row.get("id") or ""),
                        parent_id=str(row.get("insight_id") or row.get("id") or ""),
                        title=title or "Source Insight",
                        entity_type="source_insight",
                        source_kind="insight",
                        match=(row.get("content") or "")[:240],
                        updated_at=row.get("updated_at"),
                    ),
                    "source_id": str(row.get("source_id") or ""),
                    "score": float(
                        str(row.get("content") or "").lower().count(lowered_keyword) or 1
                    ),
                }
            )
        return candidates

    async def _insight_vector_candidates(
        self,
        source_ids: Optional[list[str]],
    ) -> list[dict[str, Any]]:
        params: list[Any] = []
        where_clause = "embedding_json IS NOT NULL AND embedding_json != ''"
        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            where_clause += f" AND source_id IN ({placeholders})"
            params.extend(source_ids)
        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, insight_id, source_id, source_title, insight_type, content,
                   updated_at, embedding_json
            FROM ai_insight_index
            WHERE {where_clause}
            """,
            tuple(params) if params else None,
        )
        candidates: list[dict[str, Any]] = []
        for row in rows:
            title = f"{row.get('insight_type')} - {row.get('source_title') or ''}".strip(
                " -"
            )
            candidates.append(
                {
                    **self._base_result(
                        row_id=str(row.get("insight_id") or row.get("id") or ""),
                        parent_id=str(row.get("insight_id") or row.get("id") or ""),
                        title=title or "Source Insight",
                        entity_type="source_insight",
                        source_kind="insight",
                        match=(row.get("content") or "")[:240],
                        updated_at=row.get("updated_at"),
                    ),
                    "source_id": str(row.get("source_id") or ""),
                    "embedding": _json_loads(row.get("embedding_json"), []),
                }
            )
        return candidates

    def _collapse_results(
        self,
        rows: list[dict[str, Any]],
        score_field: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        matches_map: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
        page_presence: set[tuple[str, int]] = set()

        for row in rows:
            if row.get("source_kind") == "page" and row.get("parent_id") and row.get("page"):
                page_presence.add((str(row["parent_id"]), int(row["page"])))

        for row in rows:
            if row.get("source_kind") == "chunk" and row.get("parent_id") and row.get("page"):
                page_key = (str(row["parent_id"]), int(row["page"]))
                if page_key in page_presence:
                    page_rows = [
                        item
                        for item in rows
                        if item.get("source_kind") == "page"
                        and str(item.get("parent_id")) == page_key[0]
                        and int(item.get("page") or 0) == page_key[1]
                    ]
                    if page_rows:
                        overlap = SequenceMatcher(
                            None,
                            str(row.get("match") or "")[:300],
                            str(page_rows[0].get("match") or "")[:300],
                        ).ratio()
                        if overlap > 0.7:
                            continue

            row_id = str(row.get("id") or "")
            parent_id = str(row.get("parent_id") or row_id)
            title = str(row.get("title") or "")
            source_kind = str(row.get("source_kind") or "")
            key = (row_id, parent_id, title, source_kind)
            score = float(row.get(score_field) or 0.0)

            current = grouped.get(key)
            if current is None or score > float(current.get(score_field) or 0.0):
                grouped[key] = {
                    **row,
                    score_field: score,
                    "matches": [],
                }

            match = str(row.get("match") or "").strip()
            if match and match not in matches_map[key]:
                matches_map[key].append(match)

        final_rows = []
        for key, value in grouped.items():
            value["matches"] = matches_map[key][:3]
            final_rows.append(value)

        def sort_key(item: dict[str, Any]) -> tuple[float, int]:
            source_kind = str(item.get("source_kind") or "")
            page_bonus = 1 if source_kind == "page" else 0
            return (float(item.get(score_field) or 0.0), page_bonus)

        final_rows.sort(key=sort_key, reverse=True)
        return final_rows[:limit]

    async def hybrid_multimodal_search(
        self,
        keyword: str,
        results: int,
        source: bool = True,
        note: bool = True,
        minimum_score: float = 0.2,
        source_ids: Optional[list[str]] = None,
        note_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        text_rows = await self.text_search(
            keyword,
            results * 2,
            source=source,
            note=note,
            source_ids=source_ids,
            note_ids=note_ids,
        )
        vector_rows = await self.vector_search(
            keyword,
            results * 2,
            source=source,
            note=note,
            minimum_score=minimum_score,
            source_ids=source_ids,
            note_ids=note_ids,
        )

        merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for row in text_rows:
            key = (
                row["id"],
                row["parent_id"],
                row["title"],
                str(row.get("source_kind") or ""),
            )
            merged[key] = {
                **row,
                "score": float(row.get("relevance") or 0.0),
            }

        for row in vector_rows:
            key = (
                row["id"],
                row["parent_id"],
                row["title"],
                str(row.get("source_kind") or ""),
            )
            existing = merged.get(key)
            if existing is None:
                merged[key] = {
                    **row,
                    "score": float(row.get("similarity") or 0.0),
                }
                continue
            existing["score"] = max(
                float(existing.get("score") or 0.0),
                float(row.get("similarity") or 0.0),
            )
            for match in row.get("matches") or []:
                if match not in existing.setdefault("matches", []):
                    existing["matches"].append(match)

        final_rows = list(merged.values())
        final_rows.sort(
            key=lambda item: (
                float(item.get("score") or 0.0),
                1 if item.get("source_kind") == "page" else 0,
            ),
            reverse=True,
        )
        return final_rows[:results]

    async def text_search(
        self,
        keyword: str,
        results: int,
        source: bool = True,
        note: bool = True,
        source_ids: Optional[list[str]] = None,
        note_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if source:
            candidates.extend(
                await ai_page_store.text_candidates(keyword, source_ids, results * 4)
            )
            candidates.extend(
                await self._chunk_text_candidates(keyword, source_ids, results * 4)
            )
            candidates.extend(
                await self._insight_text_candidates(keyword, source_ids, results * 2)
            )
        if note:
            candidates.extend(await self._note_text_candidates(keyword, note_ids, results * 2))

        filtered = [
            row
            for row in candidates
            if self._within_scope(
                row,
                set(source_ids) if source_ids else None,
                set(note_ids) if note_ids else None,
            )
        ]
        normalized = []
        for row in filtered:
            normalized.append(
                {
                    **row,
                    "relevance": float(row.get("score") or 0.0)
                    + self._query_boost(keyword, row),
                }
            )
        return self._collapse_results(normalized, "relevance", results)

    async def vector_search(
        self,
        keyword: str,
        results: int,
        source: bool = True,
        note: bool = True,
        minimum_score: float = 0.2,
        source_ids: Optional[list[str]] = None,
        note_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        query_embedding = await generate_embedding(
            keyword,
            task_type="retrieval_query",
        )
        candidates: list[dict[str, Any]] = []
        if source:
            candidates.extend(await ai_page_store.vector_candidates(source_ids))
            candidates.extend(await self._chunk_vector_candidates(source_ids))
            candidates.extend(await self._insight_vector_candidates(source_ids))
        if note:
            candidates.extend(await self._note_vector_candidates(note_ids))

        filtered = [
            row
            for row in candidates
            if self._within_scope(
                row,
                set(source_ids) if source_ids else None,
                set(note_ids) if note_ids else None,
            )
        ]
        normalized = []
        for row in filtered:
            similarity = cosine_similarity(row.get("embedding") or [], query_embedding)
            if similarity < minimum_score:
                continue
            normalized.append(
                {
                    **row,
                    "similarity": similarity
                    + self._query_boost(keyword, row, for_vector=True),
                }
            )
        return self._collapse_results(normalized, "similarity", results)

    async def source_page_stats(self, source_id: str) -> dict[str, int]:
        page_row = await seekdb_client.fetch_one(
            "SELECT COUNT(*) AS count FROM ai_source_pages WHERE source_id = %s",
            (source_id,),
        )
        chunk_row = await seekdb_client.fetch_one(
            "SELECT COUNT(*) AS count FROM ai_source_chunks WHERE source_id = %s",
            (source_id,),
        )
        return {
            "page_count": int((page_row or {}).get("count") or 0),
            "chunk_count": int((chunk_row or {}).get("count") or 0),
        }


    async def get_image_chunks_by_ids(
        self, ids: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch image chunks by their IDs.

        Args:
            ids: List of image chunk IDs to fetch.

        Returns:
            List of image chunk records with fields:
            id, source_id, page_no, image_path, image_summary, bbox_regions, embedding_json.
        """
        if not ids:
            return []
        placeholders = ", ".join(["%s"] * len(ids))
        return await seekdb_client.fetch_all(
            f"""
            SELECT id, source_id, page_no, image_path, image_summary, bbox_regions, embedding_json
            FROM ai_image_chunks
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )


# --------------------------------------------------------------------------
    # VRAG Search Helpers (sync wrappers for VRAG search_engine.py)
    # --------------------------------------------------------------------------

    def search_images_sync(
        self, query: str, source_ids: Optional[list[str]], top_k: int
    ) -> list[dict[str, Any]]:
        """Sync wrapper for image search — called by VRAG search_engine.

        Uses text_search for keyword-based image lookup. Image chunks have
        image_summary + description fields that get matched.
        """
        import asyncio

        async def _run():
            results = await self.text_search(
                keyword=query,
                results=top_k * 2,  # Over-fetch for RRF fusion
                source_ids=source_ids,
                note=False,
            )
            # Filter to only image chunks
            return [
                r
                for r in results
                if r.get("entity_type") == "image"
                or r.get("source_kind") == "image"
            ]

        return asyncio.get_event_loop().run_until_complete(_run())[:top_k]

    def search_text_chunks_sync(
        self, query: str, source_ids: Optional[list[str]], top_k: int
    ) -> list[dict[str, Any]]:
        """Sync wrapper for text chunk search — called by VRAG search_engine."""
        import asyncio

        async def _run():
            results = await self.text_search(
                keyword=query,
                results=top_k * 2,
                source_ids=source_ids,
                note=False,
            )
            # Filter to only chunk results
            return [
                r
                for r in results
                if r.get("entity_type") == "chunk"
                or r.get("source_kind") == "chunk"
            ]

        return asyncio.get_event_loop().run_until_complete(_run())[:top_k]

    def get_text_chunks_sync(self, ids: list[str]) -> list[dict[str, Any]]:
        """Fetch text chunks by IDs — called by VRAG search_engine."""
        import asyncio

        async def _run():
            if not ids:
                return []
            placeholders = ", ".join(["%s"] * len(ids))
            return await seekdb_client.fetch_all(
                f"""
                SELECT id, source_id, page_no, page_id, filename, content, title
                FROM ai_source_chunks
                WHERE id IN ({placeholders})
                """,
                tuple(ids),
            )

        return asyncio.get_event_loop().run_until_complete(_run())

    async def get_text_chunks_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        """Fetch text chunks by IDs — async version for VRAG search_engine.

        Args:
            ids: List of chunk IDs to fetch.

        Returns:
            List of chunk dicts with id, source_id, page_no, content fields.
        """
        if not ids:
            return []
        placeholders = ", ".join(["%s"] * len(ids))
        return await seekdb_client.fetch_all(
            f"""
            SELECT id, source_id, page_no, page_id, filename, content, title
            FROM ai_source_chunks
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )

    def get_image_chunks_sync(
        self, ids: list[str], include_base64: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch image chunks by IDs — called by VRAG search_engine."""
        import asyncio

        async def _run():
            if not ids:
                return []
            placeholders = ", ".join(["%s"] * len(ids))
            return await seekdb_client.fetch_all(
                f"""
                SELECT id, source_id, page_no, image_path, image_summary, bbox_regions
                FROM ai_image_chunks
                WHERE id IN ({placeholders})
                """,
                tuple(ids),
            )

        return asyncio.get_event_loop().run_until_complete(_run())


ai_retrieval_service = AIRetrievalService()
