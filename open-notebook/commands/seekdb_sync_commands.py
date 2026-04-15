import time
from typing import Literal, Optional

from loguru import logger

from commands.embedding_commands import (
    EmbedInsightInput,
    EmbedNoteInput,
    EmbedSourceInput,
    embed_insight_command,
    embed_note_command,
    embed_source_command,
)
from open_notebook.jobs import CommandInput, CommandOutput, command, submit_command
from open_notebook.seekdb import ai_config_store, ai_sync_service, seekdb_business_store


class SeekDBSyncOutput(CommandOutput):
    success: bool
    processing_time: float
    error_message: Optional[str] = None


class SyncCredentialInput(CommandInput):
    credential_id: str


class SyncModelInput(CommandInput):
    model_id: str


class SyncDefaultsInput(CommandInput):
    pass


class SyncSourceChunksInput(CommandInput):
    source_id: str


class SyncSourcePagesInput(CommandInput):
    source_id: str


class SyncNoteIndexInput(CommandInput):
    note_id: str


class SyncInsightIndexInput(CommandInput):
    insight_id: str


class ResyncScopeInput(CommandInput):
    notebook_id: Optional[str] = None


class DeleteSeekDBEntityInput(CommandInput):
    entity_type: Literal["source", "note", "insight"]
    entity_id: str


class BackfillSeekDBInput(CommandInput):
    pass


@command("sync_seekdb_credential", app="open_notebook")
async def sync_seekdb_credential(
    input_data: SyncCredentialInput,
) -> SeekDBSyncOutput:
    start = time.time()
    try:
        await ai_sync_service.sync_credential_from_surreal(input_data.credential_id)
        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(f"Failed to sync credential {input_data.credential_id}: {e}")
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command("sync_seekdb_model", app="open_notebook")
async def sync_seekdb_model(input_data: SyncModelInput) -> SeekDBSyncOutput:
    start = time.time()
    try:
        await ai_sync_service.sync_model_from_surreal(input_data.model_id)
        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(f"Failed to sync model {input_data.model_id}: {e}")
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command("sync_seekdb_defaults", app="open_notebook")
async def sync_seekdb_defaults(input_data: SyncDefaultsInput) -> SeekDBSyncOutput:
    start = time.time()
    try:
        await ai_sync_service.sync_defaults_from_surreal()
        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(f"Failed to sync default models: {e}")
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command("sync_seekdb_source_chunks", app="open_notebook")
async def sync_seekdb_source_chunks(
    input_data: SyncSourceChunksInput,
) -> SeekDBSyncOutput:
    start = time.time()
    output = await embed_source_command(EmbedSourceInput(source_id=input_data.source_id))
    return SeekDBSyncOutput(
        success=output.success,
        processing_time=time.time() - start,
        error_message=output.error_message,
    )


@command("sync_seekdb_source_pages", app="open_notebook")
async def sync_seekdb_source_pages(
    input_data: SyncSourcePagesInput,
) -> SeekDBSyncOutput:
    start = time.time()
    output = await embed_source_command(EmbedSourceInput(source_id=input_data.source_id))
    return SeekDBSyncOutput(
        success=output.success,
        processing_time=time.time() - start,
        error_message=output.error_message,
    )


@command("sync_seekdb_note_index", app="open_notebook")
async def sync_seekdb_note_index(input_data: SyncNoteIndexInput) -> SeekDBSyncOutput:
    start = time.time()
    output = await embed_note_command(EmbedNoteInput(note_id=input_data.note_id))
    return SeekDBSyncOutput(
        success=output.success,
        processing_time=time.time() - start,
        error_message=output.error_message,
    )


@command("sync_seekdb_insight_index", app="open_notebook")
async def sync_seekdb_insight_index(
    input_data: SyncInsightIndexInput,
) -> SeekDBSyncOutput:
    start = time.time()
    output = await embed_insight_command(
        EmbedInsightInput(insight_id=input_data.insight_id)
    )
    return SeekDBSyncOutput(
        success=output.success,
        processing_time=time.time() - start,
        error_message=output.error_message,
    )


@command("resync_seekdb_source_scope", app="open_notebook")
async def resync_seekdb_source_scope(
    input_data: ResyncScopeInput,
) -> SeekDBSyncOutput:
    start = time.time()
    try:
        if input_data.notebook_id:
            source_ids = await seekdb_business_store.list_relation_sources(
                "reference", input_data.notebook_id
            )
        else:
            source_rows = await seekdb_business_store.list_entities("source")
            source_ids = [str(item["id"]) for item in source_rows]

        for source_id in source_ids:
            submit_command(
                "open_notebook",
                "sync_seekdb_source_pages",
                {"source_id": source_id},
            )

        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(f"Failed to resync source scope: {e}")
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command("resync_seekdb_note_scope", app="open_notebook")
async def resync_seekdb_note_scope(
    input_data: ResyncScopeInput,
) -> SeekDBSyncOutput:
    start = time.time()
    try:
        if input_data.notebook_id:
            note_ids = await seekdb_business_store.list_relation_sources(
                "artifact", input_data.notebook_id
            )
        else:
            note_rows = await seekdb_business_store.list_entities("note")
            note_ids = [str(item["id"]) for item in note_rows]

        for note_id in note_ids:
            submit_command(
                "open_notebook",
                "sync_seekdb_note_index",
                {"note_id": note_id},
            )

        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(f"Failed to resync note scope: {e}")
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command("delete_seekdb_entity", app="open_notebook")
async def delete_seekdb_entity(
    input_data: DeleteSeekDBEntityInput,
) -> SeekDBSyncOutput:
    start = time.time()
    try:
        await ai_sync_service.delete_entity_index(
            input_data.entity_type, input_data.entity_id
        )
        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(
            f"Failed to delete SeekDB entity {input_data.entity_type}/{input_data.entity_id}: {e}"
        )
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command("backfill_seekdb_indexes", app="open_notebook")
async def backfill_seekdb_indexes(input_data: BackfillSeekDBInput) -> SeekDBSyncOutput:
    start = time.time()
    try:
        credential_rows = await ai_config_store.list_credentials()
        for row in credential_rows:
            submit_command(
                "open_notebook",
                "sync_seekdb_credential",
                {"credential_id": str(row["id"])},
            )

        model_rows = await ai_config_store.list_models()
        for row in model_rows:
            submit_command(
                "open_notebook",
                "sync_seekdb_model",
                {"model_id": str(row["id"])},
            )

        submit_command("open_notebook", "sync_seekdb_defaults", {})

        source_rows = await seekdb_business_store.list_entities("source")
        for row in source_rows:
            if not row.get("full_text"):
                continue
            submit_command(
                "open_notebook",
                "sync_seekdb_source_pages",
                {"source_id": str(row["id"])},
            )

        note_rows = await seekdb_business_store.list_entities("note")
        for row in note_rows:
            if not row.get("content"):
                continue
            submit_command(
                "open_notebook",
                "sync_seekdb_note_index",
                {"note_id": str(row["id"])},
            )

        insight_rows = await seekdb_business_store.list_entities("source_insight")
        for row in insight_rows:
            if not row.get("content"):
                continue
            submit_command(
                "open_notebook",
                "sync_seekdb_insight_index",
                {"insight_id": str(row["id"])},
            )

        return SeekDBSyncOutput(success=True, processing_time=time.time() - start)
    except Exception as e:
        logger.error(f"Failed to backfill SeekDB indexes: {e}")
        return SeekDBSyncOutput(
            success=False,
            processing_time=time.time() - start,
            error_message=str(e),
        )
