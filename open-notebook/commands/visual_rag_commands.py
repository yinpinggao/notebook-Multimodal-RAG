import time
from typing import Any, Optional

from loguru import logger

from open_notebook.jobs import CommandInput, CommandOutput, command
from open_notebook.storage.visual_assets import visual_asset_store
from open_notebook.visual_rag.indexer import VisualAssetIndexer


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
