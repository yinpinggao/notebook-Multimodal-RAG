from fastapi import APIRouter, HTTPException
from loguru import logger

from api.command_service import CommandService
from api.models import (
    RebuildProgress,
    RebuildRequest,
    RebuildResponse,
    RebuildStats,
    RebuildStatusResponse,
)
from open_notebook.jobs import get_command_status
from open_notebook.seekdb import ai_index_store, seekdb_business_store, use_seekdb_for_search

router = APIRouter()


def _extract_count(query_result) -> int:
    if not query_result:
        return 0
    first = query_result[0]
    if isinstance(first, dict):
        return int(first.get("count", 0) or 0)
    if isinstance(first, int):
        return first
    return 0


@router.post("/rebuild", response_model=RebuildResponse)
async def start_rebuild(request: RebuildRequest):
    """
    Start a background job to rebuild embeddings.

    - **mode**: "existing" (re-embed items with embeddings) or "all" (embed everything)
    - **include_sources**: Include sources in rebuild (default: true)
    - **include_notes**: Include notes in rebuild (default: true)
    - **include_insights**: Include insights in rebuild (default: true)

    Returns command ID to track progress and estimated item count.
    """
    try:
        logger.info(f"Starting rebuild request: mode={request.mode}")

        # Import commands to ensure they're registered
        import commands.embedding_commands  # noqa: F401

        # Estimate total items (quick count query)
        # This is a rough estimate before the command runs
        total_estimate = 0

        if request.include_sources:
            source_count = 0
            if use_seekdb_for_search() and request.mode == "existing":
                source_count = await ai_index_store.count_indexed_sources()
            elif request.mode == "existing":
                # Count sources with embeddings
                result = await seekdb_business_store.list_entities("source_embedding")
                source_count = len(
                    {str(item.get("source")) for item in result if item.get("source")}
                )
            else:
                result = await seekdb_business_store.list_entities("source")
                source_count = len(
                    [
                        item
                        for item in result
                        if item.get("full_text") and str(item.get("full_text")).strip()
                    ]
                )

            total_estimate += source_count

        if request.include_notes:
            note_count = 0
            if use_seekdb_for_search() and request.mode == "existing":
                note_count = await ai_index_store.count_note_indexes()
            elif request.mode == "existing":
                result = await seekdb_business_store.list_entities("note")
                note_count = len(
                    [
                        item
                        for item in result
                        if item.get("content") and str(item.get("content")).strip()
                    ]
                )
            else:
                result = await seekdb_business_store.list_entities("note")
                note_count = len(
                    [
                        item
                        for item in result
                        if item.get("content") and str(item.get("content")).strip()
                    ]
                )

            total_estimate += note_count

        if request.include_insights:
            insight_count = 0
            if use_seekdb_for_search() and request.mode == "existing":
                insight_count = await ai_index_store.count_insight_indexes()
            elif request.mode == "existing":
                result = await seekdb_business_store.list_entities("source_insight")
                insight_count = len(
                    [
                        item
                        for item in result
                        if item.get("content") and str(item.get("content")).strip()
                    ]
                )
            else:
                result = await seekdb_business_store.list_entities("source_insight")
                insight_count = len(result)

            total_estimate += insight_count

        logger.info(f"Estimated {total_estimate} items to process")

        # Submit command
        command_id = await CommandService.submit_command_job(
            "open_notebook",
            "rebuild_embeddings",
            {
                "mode": request.mode,
                "include_sources": request.include_sources,
                "include_notes": request.include_notes,
                "include_insights": request.include_insights,
            },
        )

        logger.info(f"Submitted rebuild command: {command_id}")

        return RebuildResponse(
            command_id=command_id,
            total_items=total_estimate,
            message=f"Rebuild operation started. Estimated {total_estimate} items to process.",
        )

    except Exception as e:
        logger.error(f"Failed to start rebuild: {e}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, detail=f"Failed to start rebuild operation: {str(e)}"
        )


@router.get("/rebuild/{command_id}/status", response_model=RebuildStatusResponse)
async def get_rebuild_status(command_id: str):
    """
    Get the status of a rebuild operation.

    Returns:
    - **status**: queued, running, completed, failed
    - **progress**: processed count, total count, percentage
    - **stats**: breakdown by type (sources, notes, insights, failed)
    - **timestamps**: started_at, completed_at
    """
    try:
        status = await get_command_status(command_id)

        if not status:
            raise HTTPException(status_code=404, detail="Rebuild command not found")

        # Build response based on status
        response = RebuildStatusResponse(
            command_id=command_id,
            status=status.status,
        )

        # Extract metadata from command result
        if status.result and isinstance(status.result, dict):
            result = status.result

            # Build progress info
            if "total_items" in result and "jobs_submitted" in result:
                total = result["total_items"]
                submitted = result["jobs_submitted"]
                response.progress = RebuildProgress(
                    processed=submitted,
                    total=total,
                    percentage=round((submitted / total * 100) if total > 0 else 0, 2),
                )

            # Build stats
            response.stats = RebuildStats(
                sources=result.get("sources_submitted", 0),
                notes=result.get("notes_submitted", 0),
                insights=result.get("insights_submitted", 0),
                failed=result.get("failed_submissions", 0),
            )

        # Add timestamps
        if hasattr(status, "created") and status.created:
            response.started_at = str(status.created)
        if hasattr(status, "updated") and status.updated:
            response.completed_at = str(status.updated)

        # Add error message if failed
        if (
            status.status == "failed"
            and status.result
            and isinstance(status.result, dict)
        ):
            response.error_message = status.result.get("error_message", "Unknown error")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rebuild status: {e}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get rebuild status: {str(e)}"
        )
