import json
from datetime import datetime
from typing import Any, Optional

from .client import seekdb_client


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _now() -> str:
    return datetime.utcnow().isoformat()


class AIImageChunkStore:
    """Synchronous persistence helpers for VRAG image chunks."""

    def get_chunk(self, chunk_id: str) -> Optional[dict[str, Any]]:
        return seekdb_client.fetch_one_sync(
            """
            SELECT id, source_id, page_no, image_path, image_summary, bbox_regions,
                   embedding_json, chunk_kind, updated_at, sync_version
            FROM ai_image_chunks
            WHERE id = %s
            """,
            (chunk_id,),
        )

    def list_chunks_by_source(self, source_id: str) -> list[dict[str, Any]]:
        return seekdb_client.fetch_all_sync(
            """
            SELECT id, source_id, page_no, image_path, image_summary, bbox_regions,
                   embedding_json, chunk_kind, updated_at, sync_version
            FROM ai_image_chunks
            WHERE source_id = %s
            ORDER BY page_no ASC, id ASC
            """,
            (source_id,),
        )

    def upsert_chunk(self, chunk_data: dict[str, Any]) -> int:
        return seekdb_client.execute_sync(
            """
            INSERT INTO ai_image_chunks (
                id, source_id, page_no, image_path, image_summary, bbox_regions,
                embedding_json, chunk_kind, updated_at, sync_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                source_id = VALUES(source_id),
                page_no = VALUES(page_no),
                image_path = VALUES(image_path),
                image_summary = VALUES(image_summary),
                bbox_regions = VALUES(bbox_regions),
                embedding_json = VALUES(embedding_json),
                chunk_kind = VALUES(chunk_kind),
                updated_at = VALUES(updated_at),
                sync_version = VALUES(sync_version)
            """,
            (
                chunk_data["id"],
                chunk_data["source_id"],
                chunk_data.get("page_no"),
                chunk_data["image_path"],
                chunk_data.get("image_summary"),
                chunk_data.get("bbox_regions") or _json_dumps([]),
                chunk_data.get("embedding_json"),
                chunk_data.get("chunk_kind"),
                chunk_data.get("updated_at") or _now(),
                int(chunk_data.get("sync_version") or 0),
            ),
        )

    def update_chunk(self, chunk_id: str, update_data: dict[str, Any]) -> int:
        if not update_data:
            return 0

        allowed_fields = {
            "source_id",
            "page_no",
            "image_path",
            "image_summary",
            "bbox_regions",
            "embedding_json",
            "chunk_kind",
            "updated_at",
            "sync_version",
        }
        assignments: list[str] = []
        params: list[Any] = []

        for field, value in update_data.items():
            if field not in allowed_fields:
                continue
            assignments.append(f"{field} = %s")
            params.append(value)

        if not assignments:
            return 0

        params.append(chunk_id)
        return seekdb_client.execute_sync(
            f"UPDATE ai_image_chunks SET {', '.join(assignments)} WHERE id = %s",
            tuple(params),
        )

    def delete_source_chunks(self, source_id: str) -> int:
        return seekdb_client.execute_sync(
            "DELETE FROM ai_image_chunks WHERE source_id = %s",
            (source_id,),
        )


ai_image_chunk_store = AIImageChunkStore()
