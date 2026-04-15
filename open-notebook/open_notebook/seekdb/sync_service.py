from typing import Any, Optional
from uuid import uuid4

from loguru import logger

from .client import seekdb_client
from .business_store import seekdb_business_store
from .config_store import ai_config_store
from .index_store import ai_index_store
from .page_store import ai_page_store


class AISyncService:
    async def get_source_notebook_ids(self, source_id: str) -> list[str]:
        return await seekdb_business_store.get_source_notebook_ids(source_id)

    async def get_note_notebook_ids(self, note_id: str) -> list[str]:
        return await seekdb_business_store.get_note_notebook_ids(note_id)

    async def get_or_create_sync_state(
        self, entity_type: str, entity_id: str
    ) -> dict[str, Any]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT * FROM ai_sync_state
            WHERE entity_type = %s AND entity_id = %s
            LIMIT 1
            """,
            (entity_type, entity_id),
        )
        if rows:
            return rows[0]

        sync_id = f"ai_sync_state:{uuid4().hex}"
        await seekdb_client.execute(
            """
            INSERT INTO ai_sync_state (
                id, entity_type, entity_id, sync_version, last_status, last_error, last_synced_at
            ) VALUES (%s, %s, %s, 0, 'pending', NULL, NULL)
            """,
            (sync_id, entity_type, entity_id),
        )
        return {
            "id": sync_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "sync_version": 0,
            "last_status": "pending",
        }

    async def next_sync_version(self, entity_type: str, entity_id: str) -> int:
        current = await self.get_or_create_sync_state(entity_type, entity_id)
        return int(current.get("sync_version") or 0) + 1

    async def mark_sync_status(
        self,
        entity_type: str,
        entity_id: str,
        sync_version: int,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        state = await self.get_or_create_sync_state(entity_type, entity_id)
        state_id = state.get("id")
        if not state_id:
            logger.warning(
                f"Could not resolve ai_sync_state id for {entity_type}/{entity_id}"
            )
            return

        await seekdb_client.execute(
            """
            UPDATE ai_sync_state
            SET sync_version = %s,
                last_status = %s,
                last_error = %s,
                last_synced_at = NOW()
            WHERE id = %s
            """,
            (sync_version, status, error, state_id),
        )

    async def delete_entity_index(self, entity_type: str, entity_id: str) -> None:
        if entity_type == "source":
            from .pdf_indexer import cleanup_page_cache

            await ai_index_store.delete_source_chunks(entity_id)
            await ai_page_store.delete_source_pages(entity_id)
            cleanup_page_cache(entity_id)
        elif entity_type == "note":
            await ai_index_store.delete_note_index(entity_id)
        elif entity_type == "insight":
            await ai_index_store.delete_insight_index(entity_id)

    async def sync_credential_from_surreal(self, credential_id: str) -> None:
        row = await ai_config_store.get_credential(credential_id)
        if not row:
            return
        row["id"] = str(row.get("id") or credential_id)
        await ai_config_store.upsert_credential(row)

    async def sync_model_from_surreal(self, model_id: str) -> None:
        row = await ai_config_store.get_model(model_id)
        if not row:
            return
        row["id"] = str(row.get("id") or model_id)
        if row.get("credential") is not None:
            row["credential"] = str(row.get("credential"))
        await ai_config_store.upsert_model(row)

    async def sync_defaults_from_surreal(self) -> None:
        row = await ai_config_store.get_default_models()
        await ai_config_store.upsert_default_models(row or {})


ai_sync_service = AISyncService()
