"""Best-effort migration from legacy VRAG/Page visual stores."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from open_notebook.storage.visual_assets import safe_source_dir, visual_asset_store
from open_notebook.storage.visual_rag import visual_rag_session_store
from open_notebook.seekdb import seekdb_client


def _json_loads(value: Optional[str], default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _copy_visual_file(
    source_id: str,
    original_path: Optional[str],
    filename: str,
) -> Optional[str]:
    if not original_path:
        return None
    src = Path(original_path)
    if not src.exists() or not src.is_file():
        return original_path

    dest_dir = safe_source_dir(source_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = src.suffix or ".png"
    dest = dest_dir / f"{filename}{suffix}"
    if dest.resolve() == src.resolve():
        return str(dest)
    try:
        shutil.copy2(src, dest)
        return str(dest)
    except Exception as e:
        logger.debug(f"Could not copy visual asset {src} -> {dest}: {e}")
        return original_path


async def migrate_legacy_page_assets() -> int:
    rows = await seekdb_client.fetch_all(
        """
        SELECT page_id, source_id, filename, page_no, raw_text, page_summary,
               combined_text, page_image_path, embedding_json, updated_at
        FROM ai_source_pages
        WHERE page_image_path IS NOT NULL
           OR page_summary IS NOT NULL
           OR combined_text IS NOT NULL
        """
    )
    migrated = 0
    for row in rows:
        source_id = str(row.get("source_id") or "")
        page_no = int(row.get("page_no") or 0)
        if not source_id or not page_no:
            continue
        copied_path = _copy_visual_file(
            source_id,
            row.get("page_image_path"),
            f"page-{page_no}",
        )
        await visual_asset_store.upsert_asset(
            {
                "id": f"visual_asset:page:{source_id}:{page_no}",
                "source_id": source_id,
                "page_id": row.get("page_id"),
                "legacy_id": row.get("page_id"),
                "asset_type": "pdf_page",
                "media_type": "image/png" if copied_path else None,
                "page_no": page_no,
                "file_path": copied_path,
                "summary": row.get("page_summary"),
                "raw_text": row.get("combined_text") or row.get("raw_text"),
                "embedding": _json_loads(row.get("embedding_json"), []),
                "metadata": {
                    "legacy_table": "ai_source_pages",
                    "filename": row.get("filename"),
                },
                "updated_at": row.get("updated_at"),
            }
        )
        migrated += 1
    return migrated


async def migrate_legacy_image_chunks() -> int:
    rows = await seekdb_client.fetch_all(
        """
        SELECT id, source_id, page_no, image_path, image_summary, bbox_regions,
               embedding_json, chunk_kind, updated_at
        FROM ai_image_chunks
        """
    )
    migrated = 0
    for row in rows:
        source_id = str(row.get("source_id") or "")
        legacy_id = str(row.get("id") or "")
        if not source_id or not legacy_id:
            continue
        copied_path = _copy_visual_file(
            source_id,
            row.get("image_path"),
            legacy_id.replace(":", "_").replace("/", "_"),
        )
        await visual_asset_store.upsert_asset(
            {
                "id": f"visual_asset:image:{legacy_id}",
                "source_id": source_id,
                "legacy_id": legacy_id,
                "asset_type": row.get("chunk_kind") or "document_image",
                "media_type": "image/png" if copied_path else None,
                "page_no": row.get("page_no"),
                "file_path": copied_path,
                "summary": row.get("image_summary"),
                "bbox": _json_loads(row.get("bbox_regions"), []),
                "embedding": _json_loads(row.get("embedding_json"), []),
                "metadata": {"legacy_table": "ai_image_chunks"},
                "updated_at": row.get("updated_at"),
            }
        )
        migrated += 1
    return migrated


async def _load_legacy_state(session_id: str, state_type: str) -> Any:
    state_id = f"{session_id}_{state_type}"
    row = await seekdb_client.fetch_one(
        "SELECT state_data FROM ai_vrag_state WHERE id = %s",
        (state_id,),
    )
    return _json_loads((row or {}).get("state_data"), None)


async def migrate_legacy_vrag_sessions() -> int:
    rows = await seekdb_client.fetch_all(
        """
        SELECT session_id, notebook_id, created_at, updated_at, metadata
        FROM ai_vrag_sessions
        """
    )
    migrated = 0
    for row in rows:
        session_id = str(row.get("session_id") or "")
        notebook_id = str(row.get("notebook_id") or "")
        if not session_id or not notebook_id:
            continue
        metadata = _json_loads(row.get("metadata"), {})
        await visual_rag_session_store.save_session(
            session_id,
            notebook_id,
            {
                **metadata,
                "migrated_from": "ai_vrag_sessions",
            },
        )
        memory_graph = await _load_legacy_state(session_id, "memory_graph")
        evidence = await _load_legacy_state(session_id, "evidence")
        messages = await _load_legacy_state(session_id, "messages")
        if memory_graph is not None:
            await visual_rag_session_store.save_state(
                session_id,
                "memory_graph",
                memory_graph,
            )
        if evidence is not None:
            await visual_rag_session_store.save_state(session_id, "evidence", evidence)
        if messages is not None:
            await visual_rag_session_store.save_state(session_id, "messages", messages)
        migrated += 1
    return migrated


async def run_visual_rag_legacy_migration() -> dict[str, int]:
    """Run idempotent, non-destructive visual data migration."""
    try:
        await seekdb_client.ensure_schema()
        page_assets = await _run_migration_step(
            "ai_source_pages -> ai_visual_assets",
            migrate_legacy_page_assets,
        )
        image_assets = await _run_migration_step(
            "ai_image_chunks -> ai_visual_assets",
            migrate_legacy_image_chunks,
        )
        sessions = await _run_migration_step(
            "ai_vrag_sessions -> ai_visual_rag_sessions",
            migrate_legacy_vrag_sessions,
        )
        result = {
            "page_assets": page_assets,
            "image_assets": image_assets,
            "sessions": sessions,
        }
        logger.info(f"Visual RAG legacy migration complete: {result}")
        return result
    except Exception as e:
        logger.warning(f"Visual RAG legacy migration skipped: {e}")
        return {"page_assets": 0, "image_assets": 0, "sessions": 0}


async def _run_migration_step(name: str, migration_fn) -> int:
    try:
        return await migration_fn()
    except Exception as e:
        logger.warning(f"Visual RAG legacy migration step skipped ({name}): {e}")
        return 0
