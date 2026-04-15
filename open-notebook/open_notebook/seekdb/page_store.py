import json
from datetime import datetime
from typing import Any, Optional

from .client import seekdb_client


def _now(value: Optional[Any] = None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if value:
        return str(value)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _snippet(text: str, keyword: str, width: int = 220) -> str:
    if not text:
        return ""
    lowered = text.lower()
    keyword_lower = keyword.lower()
    idx = lowered.find(keyword_lower)
    if idx < 0:
        return text[:width]

    start = max(0, idx - width // 3)
    end = min(len(text), idx + len(keyword) + (width // 2))
    snippet = text[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    return snippet


class AIPageStore:
    async def count_source_pages(self, source_id: str) -> int:
        row = await seekdb_client.fetch_one(
            "SELECT COUNT(*) AS count FROM ai_source_pages WHERE source_id = %s",
            (source_id,),
        )
        return int((row or {}).get("count") or 0)

    async def delete_source_pages(self, source_id: str) -> None:
        await seekdb_client.execute(
            "DELETE FROM ai_source_pages WHERE source_id = %s",
            (source_id,),
        )

    async def list_source_pages(self, source_id: str) -> list[dict[str, Any]]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT page_id, source_id, filename, page_no, raw_text, page_summary,
                   combined_text, notebook_ids_json, updated_at, sync_version,
                   embedding_json, page_image_path, image_count, has_visual_summary
            FROM ai_source_pages
            WHERE source_id = %s
            ORDER BY page_no ASC
            """,
            (source_id,),
        )
        normalized: list[dict[str, Any]] = []
        for row in rows:
            row = dict(row)
            row["notebook_ids"] = _json_loads(row.get("notebook_ids_json"), [])
            row["embedding"] = _json_loads(row.get("embedding_json"), [])
            normalized.append(row)
        return normalized

    async def upsert_source_pages(
        self,
        source_id: str,
        pages: list[dict[str, Any]],
        notebook_ids: list[str],
        updated_at: Optional[Any] = None,
        sync_version: int = 0,
    ) -> int:
        await self.delete_source_pages(source_id)
        if not pages:
            return 0

        updated = _now(updated_at)
        params = []
        for page in pages:
            params.append(
                (
                    page["page_id"],
                    source_id,
                    page.get("filename"),
                    page.get("page_no"),
                    page.get("raw_text"),
                    page.get("page_summary"),
                    page.get("combined_text") or "",
                    _json_dumps(notebook_ids),
                    updated,
                    sync_version,
                    _json_dumps(page.get("embedding") or []),
                    page.get("page_image_path"),
                    int(page.get("image_count") or 0),
                    bool(page.get("has_visual_summary")),
                )
            )

        await seekdb_client.executemany(
            """
            INSERT INTO ai_source_pages (
                page_id, source_id, filename, page_no, raw_text, page_summary,
                combined_text, notebook_ids_json, updated_at, sync_version,
                embedding_json, page_image_path, image_count, has_visual_summary
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params,
        )
        return len(params)

    async def text_candidates(
        self,
        keyword: str,
        source_ids: Optional[list[str]] = None,
        limit: int = 120,
    ) -> list[dict[str, Any]]:
        pattern = f"%{keyword.lower()}%"
        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            query = f"""
                SELECT page_id, source_id, filename, page_no, page_summary, combined_text,
                       updated_at, notebook_ids_json, page_image_path, has_visual_summary
                FROM ai_source_pages
                WHERE source_id IN ({placeholders})
                  AND (
                    LOWER(COALESCE(combined_text, '')) LIKE %s
                    OR LOWER(COALESCE(page_summary, '')) LIKE %s
                    OR LOWER(COALESCE(filename, '')) LIKE %s
                  )
                LIMIT %s
            """
            params: tuple[Any, ...] = (
                *source_ids,
                pattern,
                pattern,
                pattern,
                limit,
            )
        else:
            query = """
                SELECT page_id, source_id, filename, page_no, page_summary, combined_text,
                       updated_at, notebook_ids_json, page_image_path, has_visual_summary
                FROM ai_source_pages
                WHERE LOWER(COALESCE(combined_text, '')) LIKE %s
                   OR LOWER(COALESCE(page_summary, '')) LIKE %s
                   OR LOWER(COALESCE(filename, '')) LIKE %s
                LIMIT %s
            """
            params = (pattern, pattern, pattern, limit)

        rows = await seekdb_client.fetch_all(query, params)
        candidates: list[dict[str, Any]] = []
        for row in rows:
            combined_text = row.get("combined_text") or ""
            summary = row.get("page_summary") or ""
            filename = row.get("filename") or ""
            source_id = str(row.get("source_id") or "")
            page_no = int(row.get("page_no") or 0)
            score = (
                combined_text.lower().count(keyword.lower())
                + summary.lower().count(keyword.lower()) * 2
                + filename.lower().count(keyword.lower())
            )
            candidates.append(
                {
                    "id": row.get("page_id"),
                    "parent_id": source_id,
                    "source_id": source_id,
                    "title": filename or "Untitled PDF",
                    "match": _snippet(summary or combined_text, keyword),
                    "score": float(score or 1),
                    "filename": filename,
                    "page": page_no,
                    "page_id": row.get("page_id"),
                    "entity_type": "source",
                    "type": "source",
                    "source_kind": "page",
                    "internal_ref": source_id,
                    "citation_text": (
                        f"引用：{filename}（第{page_no}页） | 内部引用：[{source_id}]"
                        if filename and page_no
                        else f"内部引用：[{source_id}]"
                    ),
                    "updated": row.get("updated_at"),
                    "updated_at": row.get("updated_at"),
                    "page_image_path": row.get("page_image_path"),
                    "has_visual_summary": bool(row.get("has_visual_summary")),
                }
            )
        return candidates

    async def vector_candidates(
        self,
        source_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            query = f"""
                SELECT page_id, source_id, filename, page_no, page_summary, combined_text,
                       updated_at, notebook_ids_json, embedding_json, page_image_path,
                       has_visual_summary
                FROM ai_source_pages
                WHERE source_id IN ({placeholders})
                  AND embedding_json IS NOT NULL
                  AND embedding_json != ''
            """
            params: tuple[Any, ...] = tuple(source_ids)
        else:
            query = """
                SELECT page_id, source_id, filename, page_no, page_summary, combined_text,
                       updated_at, notebook_ids_json, embedding_json, page_image_path,
                       has_visual_summary
                FROM ai_source_pages
                WHERE embedding_json IS NOT NULL
                  AND embedding_json != ''
            """
            params = ()

        rows = await seekdb_client.fetch_all(query, params or None)
        candidates: list[dict[str, Any]] = []
        for row in rows:
            source_id = str(row.get("source_id") or "")
            page_no = int(row.get("page_no") or 0)
            filename = row.get("filename") or ""
            candidates.append(
                {
                    "id": row.get("page_id"),
                    "parent_id": source_id,
                    "source_id": source_id,
                    "title": filename or "Untitled PDF",
                    "match": (row.get("page_summary") or row.get("combined_text") or "")[
                        :260
                    ],
                    "embedding": _json_loads(row.get("embedding_json"), []),
                    "filename": filename,
                    "page": page_no,
                    "page_id": row.get("page_id"),
                    "entity_type": "source",
                    "type": "source",
                    "source_kind": "page",
                    "internal_ref": source_id,
                    "citation_text": (
                        f"引用：{filename}（第{page_no}页） | 内部引用：[{source_id}]"
                        if filename and page_no
                        else f"内部引用：[{source_id}]"
                    ),
                    "updated": row.get("updated_at"),
                    "updated_at": row.get("updated_at"),
                    "page_image_path": row.get("page_image_path"),
                    "has_visual_summary": bool(row.get("has_visual_summary")),
                }
            )
        return candidates


ai_page_store = AIPageStore()
