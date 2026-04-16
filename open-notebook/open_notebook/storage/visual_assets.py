"""Async persistence for unified visual assets.

The visual asset table is the canonical store for page-render images, native
document images, crops, summaries, and optional multimodal embeddings.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from open_notebook.config import DATA_FOLDER, VISUAL_ASSETS_FOLDER
from open_notebook.seekdb import seekdb_client


def _now(value: Optional[Any] = None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if value:
        return str(value)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if value in (None, ""):
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


def safe_source_dir(source_id: str) -> Path:
    sanitized = (
        str(source_id)
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    return Path(VISUAL_ASSETS_FOLDER) / sanitized


class VisualAssetStore:
    """Repository for canonical visual assets."""

    async def upsert_asset(self, asset: dict[str, Any]) -> dict[str, Any]:
        now = _now(asset.get("updated_at"))
        created = _now(asset.get("created_at")) if asset.get("created_at") else now
        await seekdb_client.execute(
            """
            INSERT INTO ai_visual_assets (
                id, source_id, page_id, legacy_id, asset_type, media_type, page_no,
                file_path, summary, raw_text, bbox_json, embedding_json,
                metadata_json, index_status, index_command_id, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                source_id = VALUES(source_id),
                page_id = VALUES(page_id),
                legacy_id = VALUES(legacy_id),
                asset_type = VALUES(asset_type),
                media_type = VALUES(media_type),
                page_no = VALUES(page_no),
                file_path = VALUES(file_path),
                summary = VALUES(summary),
                raw_text = VALUES(raw_text),
                bbox_json = VALUES(bbox_json),
                embedding_json = VALUES(embedding_json),
                metadata_json = VALUES(metadata_json),
                index_status = VALUES(index_status),
                index_command_id = VALUES(index_command_id),
                updated_at = VALUES(updated_at)
            """,
            (
                asset["id"],
                asset["source_id"],
                asset.get("page_id"),
                asset.get("legacy_id"),
                asset.get("asset_type") or "image",
                asset.get("media_type"),
                asset.get("page_no"),
                asset.get("file_path"),
                asset.get("summary"),
                asset.get("raw_text"),
                _json_dumps(asset.get("bbox") or asset.get("bbox_json") or []),
                _json_dumps(asset.get("embedding") or asset.get("embedding_json") or []),
                _json_dumps(asset.get("metadata") or {}),
                asset.get("index_status") or "completed",
                asset.get("index_command_id"),
                created,
                now,
            ),
        )
        return await self.get_asset(asset["id"]) or {}

    async def get_asset(self, asset_id: str) -> Optional[dict[str, Any]]:
        row = await seekdb_client.fetch_one(
            """
            SELECT id, source_id, page_id, legacy_id, asset_type, media_type, page_no,
                   file_path, summary, raw_text, bbox_json, embedding_json,
                   metadata_json, index_status, index_command_id, created_at, updated_at
            FROM ai_visual_assets
            WHERE id = %s
            """,
            (asset_id,),
        )
        return self._decode(row) if row else None

    async def list_assets_by_source(self, source_id: str) -> list[dict[str, Any]]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT id, source_id, page_id, legacy_id, asset_type, media_type, page_no,
                   file_path, summary, raw_text, bbox_json, embedding_json,
                   metadata_json, index_status, index_command_id, created_at, updated_at
            FROM ai_visual_assets
            WHERE source_id = %s
            ORDER BY page_no ASC, id ASC
            """,
            (source_id,),
        )
        return [self._decode(row) for row in rows]

    async def delete_source_assets(self, source_id: str) -> int:
        deleted = await seekdb_client.execute(
            "DELETE FROM ai_visual_assets WHERE source_id = %s",
            (source_id,),
        )
        asset_dir = safe_source_dir(source_id)
        if asset_dir.exists():
            shutil.rmtree(asset_dir, ignore_errors=True)
        return deleted

    async def count_assets_by_source(self, source_id: str) -> int:
        row = await seekdb_client.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM ai_visual_assets
            WHERE source_id = %s AND asset_type != 'index_status'
            """,
            (source_id,),
        )
        return int((row or {}).get("count") or 0)

    async def source_index_summary(self, source_id: str) -> dict[str, Any]:
        row = await seekdb_client.fetch_one(
            """
            SELECT
                COUNT(*) AS asset_count,
                MAX(updated_at) AS last_indexed_at,
                MAX(index_command_id) AS index_command_id,
                SUM(CASE WHEN index_status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
                SUM(CASE WHEN index_status IN ('queued', 'running') THEN 1 ELSE 0 END) AS active_count
            FROM ai_visual_assets
            WHERE source_id = %s
              AND asset_type != 'index_status'
            """,
            (source_id,),
        )
        marker = await seekdb_client.fetch_one(
            """
            SELECT index_status, index_command_id, updated_at
            FROM ai_visual_assets
            WHERE source_id = %s AND asset_type = 'index_status'
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (source_id,),
        )
        asset_count = int((row or {}).get("asset_count") or 0)
        active_count = int((row or {}).get("active_count") or 0)
        failed_count = int((row or {}).get("failed_count") or 0)
        marker_status = (marker or {}).get("index_status")
        if marker_status in {"queued", "running"}:
            status = str(marker_status)
        elif marker_status == "failed" and not asset_count:
            status = "failed"
        elif active_count:
            status = "running"
        elif failed_count:
            status = "failed"
        elif asset_count:
            status = "completed"
        else:
            status = "not_indexed"
        marker_updated_at = (marker or {}).get("updated_at")
        asset_updated_at = (row or {}).get("last_indexed_at")
        last_indexed_at = (
            marker_updated_at
            if marker_status in {"queued", "running"}
            else asset_updated_at or marker_updated_at
        )
        return {
            "visual_asset_count": asset_count,
            "visual_index_status": status,
            "visual_last_indexed_at": str(last_indexed_at or "") or None,
            "visual_index_command_id": (marker or {}).get("index_command_id")
            or (row or {}).get("index_command_id"),
        }

    async def mark_source_index_status(
        self,
        source_id: str,
        *,
        status: str,
        command_id: Optional[str] = None,
    ) -> None:
        now = _now()
        marker_id = f"visual_asset:index_status:{source_id}"
        await self.upsert_asset(
            {
                "id": marker_id,
                "source_id": source_id,
                "asset_type": "index_status",
                "summary": "",
                "index_status": status,
                "index_command_id": command_id,
                "updated_at": now,
                "created_at": now,
            }
        )

    async def search_assets(
        self,
        keyword: str,
        *,
        source_ids: Optional[list[str]] = None,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        if not keyword:
            return []

        pattern = f"%{keyword.lower()}%"
        params: list[Any] = [pattern, pattern]
        where_clause = """
            asset_type != 'index_status'
            AND (
                LOWER(COALESCE(summary, '')) LIKE %s
                OR LOWER(COALESCE(raw_text, '')) LIKE %s
            )
        """
        if source_ids:
            placeholders = ", ".join(["%s"] * len(source_ids))
            where_clause += f" AND source_id IN ({placeholders})"
            params.extend(source_ids)

        rows = await seekdb_client.fetch_all(
            f"""
            SELECT id, source_id, page_id, legacy_id, asset_type, media_type, page_no,
                   file_path, summary, raw_text, bbox_json, embedding_json,
                   metadata_json, index_status, index_command_id, created_at, updated_at
            FROM ai_visual_assets
            WHERE {where_clause}
            LIMIT %s
            """,
            (*params, top_k * 4),
        )

        keyword_lower = keyword.lower()
        results = []
        for row in rows:
            summary = str(row.get("summary") or "")
            raw_text = str(row.get("raw_text") or "")
            score = (
                summary.lower().count(keyword_lower) * 2
                + raw_text.lower().count(keyword_lower)
            )
            decoded = self._decode(row)
            decoded["score"] = float(score or 0.5)
            decoded["match"] = _snippet(summary or raw_text, keyword)
            results.append(decoded)

        results.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
        return results[:top_k]

    def resolve_file_path(self, asset: dict[str, Any]) -> Optional[str]:
        file_path = asset.get("file_path")
        if not file_path:
            return None

        resolved = os.path.realpath(str(file_path))
        allowed_roots = [
            os.path.realpath(VISUAL_ASSETS_FOLDER),
            os.path.realpath(DATA_FOLDER),
        ]
        if not any(
            resolved == root or resolved.startswith(f"{root}{os.sep}")
            for root in allowed_roots
        ):
            return None
        if not os.path.exists(resolved):
            return None
        return resolved

    def _decode(self, row: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(row)
        decoded["bbox"] = _json_loads(decoded.pop("bbox_json", None), [])
        decoded["embedding"] = _json_loads(decoded.pop("embedding_json", None), [])
        decoded["metadata"] = _json_loads(decoded.pop("metadata_json", None), {})
        return decoded


visual_asset_store = VisualAssetStore()
