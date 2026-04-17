import asyncio
import time
from pathlib import Path
from typing import Any, Optional

import fitz
from loguru import logger

from open_notebook.domain.notebook import Source
from open_notebook.jobs import CommandInput, CommandOutput, async_submit_command, command
from open_notebook.seekdb import seekdb_business_store
from open_notebook.storage.visual_assets import visual_asset_store
from open_notebook.visual_rag.indexer import VisualAssetIndexer
from open_notebook.vrag.utils import VISUAL_INDEX_VERSION


class IndexVisualSourceInput(CommandInput):
    source_id: str
    regenerate: bool = False
    generate_summaries: bool = True
    dpi: Optional[int] = None


class IndexVisualSourceOutput(CommandOutput):
    success: bool
    source_id: str
    indexing_result: dict[str, Any]
    processing_time: float
    error_message: Optional[str] = None


class BackfillVisualIndexesInput(CommandInput):
    limit: int = 200
    generate_summaries: bool = False
    dpi: Optional[int] = None


class BackfillVisualIndexesOutput(CommandOutput):
    success: bool
    scanned: int
    queued: int
    skipped: int
    command_ids: list[str]
    processing_time: float
    error_message: Optional[str] = None


def _source_pdf_path(source: Source) -> Optional[Path]:
    file_path = source.asset.file_path if source.asset else None
    if not file_path:
        return None
    path = Path(file_path)
    if path.suffix.lower() != ".pdf" or not path.exists():
        return None
    return path


def _pdf_page_count(pdf_path: Path) -> int:
    with fitz.open(str(pdf_path)) as doc:
        return int(doc.page_count or 0)


async def _source_needs_visual_rebuild(source_id: str, pdf_path: Path) -> bool:
    assets = await visual_asset_store.list_assets_by_source(source_id)
    if not assets:
        return True

    page_render_pages = {
        int(asset.get("page_no") or 0)
        for asset in assets
        if asset.get("asset_type") == "page_render"
        and int((asset.get("metadata") or {}).get("index_version") or 0) >= VISUAL_INDEX_VERSION
    }
    page_count = await asyncio.to_thread(_pdf_page_count, pdf_path)
    return len(page_render_pages) < page_count


@command(
    "index_visual_source",
    app="open_notebook",
    retry={
        "max_attempts": 3,
        "wait_strategy": "exponential_jitter",
        "wait_min": 2,
        "wait_max": 60,
        "stop_on": [ValueError, FileNotFoundError],
        "retry_log_level": "debug",
    },
)
async def index_visual_source_command(
    input_data: IndexVisualSourceInput,
) -> IndexVisualSourceOutput:
    start = time.time()
    command_id = (
        str(input_data.execution_context.command_id)
        if input_data.execution_context
        else None
    )
    await visual_asset_store.mark_source_index_status(
        input_data.source_id,
        status="running",
        command_id=command_id,
    )
    try:
        indexer = VisualAssetIndexer()
        result = await indexer.index_source(
            input_data.source_id,
            regenerate=input_data.regenerate,
            generate_summaries=input_data.generate_summaries,
            dpi=input_data.dpi,
            command_id=command_id,
        )
        status = "failed" if result.get("errors") and not result.get("indexed") else "completed"
        await visual_asset_store.mark_source_index_status(
            input_data.source_id,
            status=status,
            command_id=command_id,
        )
        return IndexVisualSourceOutput(
            success=status == "completed",
            source_id=input_data.source_id,
            indexing_result=result,
            processing_time=time.time() - start,
            error_message=None if status == "completed" else "Visual indexing failed",
        )
    except Exception as e:
        logger.warning(f"Visual indexing failed for {input_data.source_id}: {e}")
        await visual_asset_store.mark_source_index_status(
            input_data.source_id,
            status="failed",
            command_id=command_id,
        )
        return IndexVisualSourceOutput(
            success=False,
            source_id=input_data.source_id,
            indexing_result={"total": 0, "indexed": 0, "skipped": 0, "errors": 1},
            processing_time=time.time() - start,
            error_message=str(e),
        )


@command(
    "backfill_visual_indexes",
    app="open_notebook",
    retry={
        "max_attempts": 2,
        "wait_strategy": "exponential_jitter",
        "wait_min": 2,
        "wait_max": 30,
        "retry_log_level": "debug",
    },
)
async def backfill_visual_indexes_command(
    input_data: BackfillVisualIndexesInput,
) -> BackfillVisualIndexesOutput:
    start = time.time()
    command_ids: list[str] = []
    scanned = 0
    queued = 0
    skipped = 0

    try:
        rows = await seekdb_business_store.list_entities("source")
        for row in rows:
            if scanned >= input_data.limit:
                break
            source = Source(**row)
            pdf_path = _source_pdf_path(source)
            if pdf_path is None or source.id is None:
                continue

            scanned += 1

            source_id = str(source.id)
            summary = await visual_asset_store.source_index_summary(source_id)
            if summary.get("visual_index_status") in {"queued", "running"}:
                skipped += 1
                continue

            if not await _source_needs_visual_rebuild(source_id, pdf_path):
                skipped += 1
                continue

            command_id = await async_submit_command(
                "open_notebook",
                "index_visual_source",
                {
                    "source_id": source_id,
                    "regenerate": True,
                    "generate_summaries": input_data.generate_summaries,
                    "dpi": input_data.dpi,
                },
            )
            command_ids.append(command_id)
            queued += 1

        return BackfillVisualIndexesOutput(
            success=True,
            scanned=scanned,
            queued=queued,
            skipped=skipped,
            command_ids=command_ids,
            processing_time=time.time() - start,
            error_message=None,
        )
    except Exception as e:
        logger.warning(f"Visual index backfill failed: {e}")
        return BackfillVisualIndexesOutput(
            success=False,
            scanned=scanned,
            queued=queued,
            skipped=skipped,
            command_ids=command_ids,
            processing_time=time.time() - start,
            error_message=str(e),
        )
