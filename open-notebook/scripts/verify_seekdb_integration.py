#!/usr/bin/env python3
import argparse
import asyncio
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

from dotenv import load_dotenv
from loguru import logger
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
seekdb_env = ROOT / ".env.seekdb"
if seekdb_env.exists():
    load_dotenv(seekdb_env, override=True)

from commands import embedding_commands as embedding_module
from commands import seekdb_sync_commands as sync_commands
from open_notebook.ai.models import DefaultModels, Model
from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.credential import Credential
from open_notebook.domain.notebook import (
    Note,
    Notebook,
    Source,
    text_search,
    vector_search,
)
from open_notebook.seekdb import (
    ai_config_store,
    ai_index_store,
    seekdb_client,
)
from open_notebook.seekdb import pdf_indexer as pdf_indexer_module
from open_notebook.seekdb import retrieval_service as retrieval_module


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def deterministic_embedding(text: str, dimensions: int = 12) -> list[float]:
    values: list[float] = []
    normalized = text.strip() or "empty"
    for index in range(dimensions):
        digest = hashlib.sha256(f"{index}:{normalized}".encode("utf-8")).digest()
        raw = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
        values.append((raw * 2.0) - 1.0)
    return values


async def fake_generate_embedding(
    text: str, content_type: Any = None, command_id: str | None = None
) -> list[float]:
    return deterministic_embedding(text)


async def fake_generate_embeddings(
    texts: list[str], command_id: str | None = None
) -> list[list[float]]:
    return [deterministic_embedding(text) for text in texts]


@dataclass
class ValidationContext:
    notebook_id: str
    source_id: str
    note_id: str
    insight_id: str
    credential_id: str
    model_id: str
    previous_default_embedding_model: str | None


class MonkeyPatchScope:
    def __init__(self) -> None:
        self._restore: list[tuple[Any, str, Any]] = []

    def set(self, obj: Any, attr: str, value: Any) -> None:
        self._restore.append((obj, attr, getattr(obj, attr)))
        setattr(obj, attr, value)

    def close(self) -> None:
        while self._restore:
            obj, attr, value = self._restore.pop()
            setattr(obj, attr, value)


async def dispatch_sync_command(name: str, args: dict[str, Any]) -> None:
    handlers: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {
        "sync_seekdb_credential": lambda payload: sync_commands.sync_seekdb_credential(
            sync_commands.SyncCredentialInput(**payload)
        ),
        "sync_seekdb_model": lambda payload: sync_commands.sync_seekdb_model(
            sync_commands.SyncModelInput(**payload)
        ),
        "sync_seekdb_defaults": lambda payload: sync_commands.sync_seekdb_defaults(
            sync_commands.SyncDefaultsInput(**payload)
        ),
        "sync_seekdb_source_chunks": lambda payload: sync_commands.sync_seekdb_source_chunks(
            sync_commands.SyncSourceChunksInput(**payload)
        ),
        "sync_seekdb_source_pages": lambda payload: sync_commands.sync_seekdb_source_pages(
            sync_commands.SyncSourcePagesInput(**payload)
        ),
        "sync_seekdb_note_index": lambda payload: sync_commands.sync_seekdb_note_index(
            sync_commands.SyncNoteIndexInput(**payload)
        ),
        "sync_seekdb_insight_index": lambda payload: sync_commands.sync_seekdb_insight_index(
            sync_commands.SyncInsightIndexInput(**payload)
        ),
    }
    handler = handlers.get(name)
    if handler is None:
        raise RuntimeError(f"Unsupported local backfill dispatch: {name}")
    await handler(args)


async def prepare_databases() -> None:
    require_env("SURREAL_URL")
    require_env("SURREAL_USER")
    require_env("SURREAL_PASSWORD")
    require_env("SURREAL_NAMESPACE")
    require_env("SURREAL_DATABASE")
    require_env("OPEN_NOTEBOOK_ENCRYPTION_KEY")
    require_env("OPEN_NOTEBOOK_SEEKDB_DSN")

    migration_manager = AsyncMigrationManager()
    await migration_manager.run_migration_up()

    deadline = time.monotonic() + 240
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            await seekdb_client.ensure_schema()
            if await seekdb_client.ping():
                return
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(5)

    raise RuntimeError(f"SeekDB was not ready within timeout: {last_error}")


async def create_surreal_seed(prefix: str) -> ValidationContext:
    os.environ["OPEN_NOTEBOOK_AI_CONFIG_BACKEND"] = "surreal"
    os.environ["OPEN_NOTEBOOK_SEARCH_BACKEND"] = "surreal"

    notebook = Notebook(
        name=f"{prefix} notebook",
        description="SeekDB dual-database validation notebook",
    )
    await notebook.save()

    source = Source(
        title=f"{prefix} source",
        full_text=(
            "Solar inverter efficiency improves when thermal losses are reduced. "
            "This validation source documents a chart about inverter temperature "
            "and conversion efficiency."
        ),
    )
    await source.save()
    await source.add_to_notebook(notebook.id or "")

    note = Note(
        title=f"{prefix} note",
        content=(
            "Maintenance note: inspect the wind turbine gearbox vibration before "
            "the next scheduled service window."
        ),
    )
    await note.save()
    await note.add_to_notebook(notebook.id or "")

    insight_rows = await repo_query(
        """
        CREATE source_insight CONTENT {
            "source": $source_id,
            "insight_type": $insight_type,
            "content": $content
        }
        """,
        {
            "source_id": ensure_record_id(source.id or ""),
            "insight_type": "summary",
            "content": (
                "The source links higher inverter temperature with lower conversion "
                "efficiency and recommends better cooling."
            ),
        },
    )
    insight_id = str(insight_rows[0]["id"])

    credential = Credential(
        name=f"{prefix} credential",
        provider="openai",
        modalities=["llm", "embedding"],
        api_key=SecretStr("sk-test-seekdb-validation"),
        base_url="https://api.openai.example.invalid/v1",
    )
    await credential.save()

    model = Model(
        name=f"{prefix}-embedding-model",
        provider="openai",
        type="embedding",
        credential=credential.id,
    )
    await model.save()

    defaults = await DefaultModels.get_instance()
    previous_default_embedding_model = defaults.default_embedding_model
    defaults.default_embedding_model = model.id
    await defaults.update()

    return ValidationContext(
        notebook_id=notebook.id or "",
        source_id=source.id or "",
        note_id=note.id or "",
        insight_id=insight_id,
        credential_id=credential.id or "",
        model_id=model.id or "",
        previous_default_embedding_model=previous_default_embedding_model,
    )


async def run_backfill_with_local_dispatch() -> None:
    os.environ["OPEN_NOTEBOOK_SEARCH_BACKEND"] = "seekdb"
    tasks: list[asyncio.Task[Any]] = []

    def local_submit_command(app_name: str, command_name: str, args: dict[str, Any]):
        del app_name
        task = asyncio.create_task(dispatch_sync_command(command_name, args))
        tasks.append(task)
        return f"local:{command_name}:{len(tasks)}"

    sync_commands.submit_command = local_submit_command  # type: ignore[assignment]
    result = await sync_commands.backfill_seekdb_indexes(
        sync_commands.BackfillSeekDBInput()
    )
    if not result.success:
        raise RuntimeError(result.error_message or "Backfill command failed")

    if tasks:
        await asyncio.gather(*tasks)


async def validate_seekdb_reads(ctx: ValidationContext) -> dict[str, Any]:
    os.environ["OPEN_NOTEBOOK_AI_CONFIG_BACKEND"] = "seekdb"
    os.environ["OPEN_NOTEBOOK_SEARCH_BACKEND"] = "seekdb"

    credential = await Credential.get(ctx.credential_id)
    model = await Model.get(ctx.model_id)
    defaults = await DefaultModels.get_instance()

    seek_credential = await ai_config_store.get_credential(ctx.credential_id)
    seek_model = await ai_config_store.get_model(ctx.model_id)
    seek_defaults = await ai_config_store.get_default_models()

    source_chunks = await ai_index_store.count_source_chunks(ctx.source_id)
    note_rows = await ai_index_store.count_note_indexes()
    insight_rows = await ai_index_store.count_insight_indexes()

    text_rows = await text_search("inverter efficiency", 5, source=True, note=False)
    vector_rows = await vector_search(
        "gearbox vibration service", 5, source=False, note=True
    )

    if not credential.id or credential.id != ctx.credential_id:
        raise RuntimeError("Credential could not be read back from SeekDB")
    if not model.id or model.id != ctx.model_id:
        raise RuntimeError("Model could not be read back from SeekDB")
    if defaults.default_embedding_model != ctx.model_id:
        raise RuntimeError("Default embedding model was not synced to SeekDB")
    if not seek_credential or not seek_model or not seek_defaults:
        raise RuntimeError("SeekDB config rows are missing")
    if source_chunks <= 0:
        raise RuntimeError("Source chunks were not backfilled into SeekDB")
    if note_rows <= 0:
        raise RuntimeError("Note index was not backfilled into SeekDB")
    if insight_rows <= 0:
        raise RuntimeError("Insight index was not backfilled into SeekDB")
    if not any(row.get("parent_id") == ctx.source_id for row in text_rows):
        raise RuntimeError("SeekDB text search did not return the seeded source")
    if not any(row.get("parent_id") == ctx.note_id for row in vector_rows):
        raise RuntimeError("SeekDB vector search did not return the seeded note")

    return {
        "source_chunks": source_chunks,
        "note_rows": note_rows,
        "insight_rows": insight_rows,
        "text_hits": len(text_rows),
        "vector_hits": len(vector_rows),
    }


async def cleanup(ctx: ValidationContext) -> None:
    os.environ["OPEN_NOTEBOOK_AI_CONFIG_BACKEND"] = "seekdb"
    os.environ["OPEN_NOTEBOOK_SEARCH_BACKEND"] = "seekdb"

    await ai_index_store.delete_insight_index(ctx.insight_id)
    await ai_index_store.delete_note_index(ctx.note_id)
    await ai_index_store.delete_source_chunks(ctx.source_id)
    await ai_config_store.delete_model(ctx.model_id)
    await ai_config_store.delete_credential(ctx.credential_id)

    defaults = await DefaultModels.get_instance()
    if defaults.default_embedding_model == ctx.model_id:
        defaults.default_embedding_model = ctx.previous_default_embedding_model
        await defaults.update()

    await repo_query("DELETE $id", {"id": ensure_record_id(ctx.insight_id)})
    await repo_query(
        "DELETE artifact WHERE in = $note_id",
        {"note_id": ensure_record_id(ctx.note_id)},
    )
    await repo_query(
        "DELETE reference WHERE in = $source_id",
        {"source_id": ensure_record_id(ctx.source_id)},
    )
    await repo_query("DELETE $id", {"id": ensure_record_id(ctx.model_id)})
    await repo_query("DELETE $id", {"id": ensure_record_id(ctx.credential_id)})
    await repo_query("DELETE $id", {"id": ensure_record_id(ctx.note_id)})
    await repo_query("DELETE $id", {"id": ensure_record_id(ctx.source_id)})
    await repo_query("DELETE $id", {"id": ensure_record_id(ctx.notebook_id)})
    await repo_query(
        "DELETE ai_sync_state WHERE entity_id INSIDE $ids",
        {"ids": [ctx.source_id, ctx.note_id, ctx.insight_id]},
    )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate SurrealDB + SeekDB dual database integration."
    )
    parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep the seeded validation records for manual inspection.",
    )
    args = parser.parse_args()

    patch_scope = MonkeyPatchScope()
    context: ValidationContext | None = None

    try:
        await prepare_databases()

        patch_scope.set(embedding_module, "generate_embedding", fake_generate_embedding)
        patch_scope.set(embedding_module, "generate_embeddings", fake_generate_embeddings)
        patch_scope.set(pdf_indexer_module, "generate_embedding", fake_generate_embedding)
        patch_scope.set(pdf_indexer_module, "generate_embeddings", fake_generate_embeddings)
        patch_scope.set(retrieval_module, "generate_embedding", fake_generate_embedding)
        patch_scope.set(
            sync_commands,
            "submit_command",
            sync_commands.submit_command,
        )

        import open_notebook.domain.notebook as notebook_module

        patch_scope.set(
            notebook_module, "submit_command", lambda *args, **kwargs: "local:no-op"
        )

        prefix = f"seekdb-verify-{uuid4().hex[:8]}"
        context = await create_surreal_seed(prefix)
        await run_backfill_with_local_dispatch()
        summary = await validate_seekdb_reads(context)

        logger.success("SeekDB dual-database validation succeeded")
        logger.info(f"Notebook: {context.notebook_id}")
        logger.info(f"Source: {context.source_id}")
        logger.info(f"Note: {context.note_id}")
        logger.info(f"Insight: {context.insight_id}")
        logger.info(f"Credential: {context.credential_id}")
        logger.info(f"Model: {context.model_id}")
        logger.info(f"Summary: {summary}")

    finally:
        patch_scope.close()
        if context and not args.keep_data:
            try:
                await cleanup(context)
                logger.info("Validation seed data cleaned up")
            except Exception as cleanup_error:
                logger.warning(f"Cleanup failed: {cleanup_error}")


if __name__ == "__main__":
    asyncio.run(main())
