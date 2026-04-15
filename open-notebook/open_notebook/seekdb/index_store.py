import json
import math
from datetime import datetime
from typing import Any, Iterable, Optional

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


def _snippet(text: str, keyword: str, width: int = 180) -> str:
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


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    left = list(a)
    right = list(b)
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(x * y for x, y in zip(left, right))
    left_norm = math.sqrt(sum(x * x for x in left))
    right_norm = math.sqrt(sum(y * y for y in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class AIIndexStore:
    async def count_source_chunks(self, source_id: str) -> int:
        row = await seekdb_client.fetch_one(
            "SELECT COUNT(*) AS count FROM ai_source_chunks WHERE source_id = %s",
            (source_id,),
        )
        return int((row or {}).get("count") or 0)

    async def count_note_indexes(self) -> int:
        row = await seekdb_client.fetch_one("SELECT COUNT(*) AS count FROM ai_note_index")
        return int((row or {}).get("count") or 0)

    async def count_insight_indexes(self) -> int:
        row = await seekdb_client.fetch_one("SELECT COUNT(*) AS count FROM ai_insight_index")
        return int((row or {}).get("count") or 0)

    async def count_indexed_sources(self) -> int:
        row = await seekdb_client.fetch_one(
            "SELECT COUNT(DISTINCT source_id) AS count FROM ai_source_chunks"
        )
        return int((row or {}).get("count") or 0)

    async def delete_source_chunks(self, source_id: str) -> None:
        await seekdb_client.execute(
            "DELETE FROM ai_source_chunks WHERE source_id = %s", (source_id,)
        )

    async def upsert_source_chunks(
        self,
        source_id: str,
        title: Optional[str],
        chunks: list[str],
        embeddings: list[list[float]],
        notebook_ids: list[str],
        updated_at: Optional[Any] = None,
        sync_version: int = 0,
        chunk_metadata: Optional[list[dict[str, Any]]] = None,
    ) -> int:
        await self.delete_source_chunks(source_id)
        if not chunks:
            return 0

        params = []
        updated = _now(updated_at)
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            metadata = (
                chunk_metadata[idx]
                if chunk_metadata and idx < len(chunk_metadata)
                else {}
            )
            params.append(
                (
                    f"ai_source_chunk:{source_id}:{idx}",
                    source_id,
                    metadata.get("page_id"),
                    metadata.get("page_no"),
                    metadata.get("filename"),
                    _json_dumps(notebook_ids),
                    title,
                    chunk,
                    idx,
                    metadata.get("chunk_kind"),
                    updated,
                    sync_version,
                    _json_dumps(embedding),
                )
            )

        await seekdb_client.executemany(
            """
            INSERT INTO ai_source_chunks (
                id, source_id, page_id, page_no, filename, notebook_ids_json,
                title, content, order_no, chunk_kind, updated_at, sync_version,
                embedding_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params,
        )
        return len(params)

    async def upsert_note_index(
        self,
        note_id: str,
        title: Optional[str],
        content: str,
        embedding: Optional[list[float]],
        notebook_ids: list[str],
        updated_at: Optional[Any] = None,
        sync_version: int = 0,
    ) -> None:
        await seekdb_client.execute(
            """
            INSERT INTO ai_note_index (
                id, note_id, notebook_ids_json, title, content, updated_at,
                sync_version, embedding_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                note_id = VALUES(note_id),
                notebook_ids_json = VALUES(notebook_ids_json),
                title = VALUES(title),
                content = VALUES(content),
                updated_at = VALUES(updated_at),
                sync_version = VALUES(sync_version),
                embedding_json = VALUES(embedding_json)
            """,
            (
                note_id,
                note_id,
                _json_dumps(notebook_ids),
                title,
                content,
                _now(updated_at),
                sync_version,
                _json_dumps(embedding or []),
            ),
        )

    async def delete_note_index(self, note_id: str) -> None:
        await seekdb_client.execute("DELETE FROM ai_note_index WHERE id = %s", (note_id,))

    async def upsert_insight_index(
        self,
        insight_id: str,
        source_id: str,
        source_title: Optional[str],
        insight_type: str,
        content: str,
        embedding: Optional[list[float]],
        notebook_ids: list[str],
        updated_at: Optional[Any] = None,
        sync_version: int = 0,
    ) -> None:
        await seekdb_client.execute(
            """
            INSERT INTO ai_insight_index (
                id, insight_id, source_id, notebook_ids_json, source_title,
                insight_type, content, updated_at, sync_version, embedding_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                insight_id = VALUES(insight_id),
                source_id = VALUES(source_id),
                notebook_ids_json = VALUES(notebook_ids_json),
                source_title = VALUES(source_title),
                insight_type = VALUES(insight_type),
                content = VALUES(content),
                updated_at = VALUES(updated_at),
                sync_version = VALUES(sync_version),
                embedding_json = VALUES(embedding_json)
            """,
            (
                insight_id,
                insight_id,
                source_id,
                _json_dumps(notebook_ids),
                source_title,
                insight_type,
                content,
                _now(updated_at),
                sync_version,
                _json_dumps(embedding or []),
            ),
        )

    async def delete_insight_index(self, insight_id: str) -> None:
        await seekdb_client.execute(
            "DELETE FROM ai_insight_index WHERE id = %s", (insight_id,)
        )

    async def text_candidates(
        self,
        keyword: str,
        include_sources: bool,
        include_notes: bool,
        limit_per_table: int = 200,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        pattern = f"%{keyword.lower()}%"

        if include_sources:
            chunk_rows = await seekdb_client.fetch_all(
                """
                SELECT id, source_id, title, content, notebook_ids_json, updated_at
                FROM ai_source_chunks
                WHERE LOWER(content) LIKE %s OR LOWER(COALESCE(title, '')) LIKE %s
                LIMIT %s
                """,
                (pattern, pattern, limit_per_table),
            )
            for row in chunk_rows:
                content = row.get("content") or ""
                title = row.get("title") or ""
                score = content.lower().count(keyword.lower()) + title.lower().count(
                    keyword.lower()
                )
                results.append(
                    {
                        "id": row.get("source_id"),
                        "parent_id": row.get("source_id"),
                        "title": title or "Untitled Source",
                        "match": _snippet(content or title, keyword),
                        "score": float(score or 1),
                        "entity_type": "source",
                        "updated_at": row.get("updated_at"),
                    }
                )

            insight_rows = await seekdb_client.fetch_all(
                """
                SELECT id, source_id, source_title, insight_type, content, updated_at
                FROM ai_insight_index
                WHERE LOWER(content) LIKE %s
                   OR LOWER(COALESCE(source_title, '')) LIKE %s
                   OR LOWER(insight_type) LIKE %s
                LIMIT %s
                """,
                (pattern, pattern, pattern, limit_per_table),
            )
            for row in insight_rows:
                content = row.get("content") or ""
                score = content.lower().count(keyword.lower()) or 1
                results.append(
                    {
                        "id": row.get("id"),
                        "parent_id": row.get("id"),
                        "title": f"{row.get('insight_type')} - {row.get('source_title') or ''}".strip(
                            " -"
                        ),
                        "match": _snippet(content, keyword),
                        "score": float(score),
                        "entity_type": "source_insight",
                        "updated_at": row.get("updated_at"),
                    }
                )

        if include_notes:
            note_rows = await seekdb_client.fetch_all(
                """
                SELECT id, note_id, title, content, updated_at
                FROM ai_note_index
                WHERE LOWER(content) LIKE %s OR LOWER(COALESCE(title, '')) LIKE %s
                LIMIT %s
                """,
                (pattern, pattern, limit_per_table),
            )
            for row in note_rows:
                content = row.get("content") or ""
                title = row.get("title") or ""
                score = content.lower().count(keyword.lower()) + title.lower().count(
                    keyword.lower()
                )
                results.append(
                    {
                        "id": row.get("note_id"),
                        "parent_id": row.get("note_id"),
                        "title": title or "Untitled Note",
                        "match": _snippet(content or title, keyword),
                        "score": float(score or 1),
                        "entity_type": "note",
                        "updated_at": row.get("updated_at"),
                    }
                )

        return results

    async def vector_candidates(
        self, include_sources: bool, include_notes: bool
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        if include_sources:
            chunk_rows = await seekdb_client.fetch_all(
                """
                SELECT id, source_id, title, content, updated_at, embedding_json
                FROM ai_source_chunks
                WHERE embedding_json IS NOT NULL AND embedding_json != ''
                """
            )
            for row in chunk_rows:
                results.append(
                    {
                        "id": row.get("source_id"),
                        "parent_id": row.get("source_id"),
                        "title": row.get("title") or "Untitled Source",
                        "match": (row.get("content") or "")[:240],
                        "embedding": _json_loads(row.get("embedding_json"), []),
                        "entity_type": "source",
                        "updated_at": row.get("updated_at"),
                    }
                )

            insight_rows = await seekdb_client.fetch_all(
                """
                SELECT id, source_id, source_title, insight_type, content, updated_at, embedding_json
                FROM ai_insight_index
                WHERE embedding_json IS NOT NULL AND embedding_json != ''
                """
            )
            for row in insight_rows:
                results.append(
                    {
                        "id": row.get("id"),
                        "parent_id": row.get("id"),
                        "title": f"{row.get('insight_type')} - {row.get('source_title') or ''}".strip(
                            " -"
                        ),
                        "match": (row.get("content") or "")[:240],
                        "embedding": _json_loads(row.get("embedding_json"), []),
                        "entity_type": "source_insight",
                        "updated_at": row.get("updated_at"),
                    }
                )

        if include_notes:
            note_rows = await seekdb_client.fetch_all(
                """
                SELECT id, note_id, title, content, updated_at, embedding_json
                FROM ai_note_index
                WHERE embedding_json IS NOT NULL AND embedding_json != ''
                """
            )
            for row in note_rows:
                results.append(
                    {
                        "id": row.get("note_id"),
                        "parent_id": row.get("note_id"),
                        "title": row.get("title") or "Untitled Note",
                        "match": (row.get("content") or "")[:240],
                        "embedding": _json_loads(row.get("embedding_json"), []),
                        "entity_type": "note",
                        "updated_at": row.get("updated_at"),
                    }
                )

        return results


ai_index_store = AIIndexStore()
