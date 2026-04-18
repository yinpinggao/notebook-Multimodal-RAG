from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from api.command_service import CommandService
from open_notebook.jobs import registry

router = APIRouter()


class CommandExecutionRequest(BaseModel):
    command: str = Field(
        ..., description="Command function name (e.g., 'process_text')"
    )
    app: str = Field(..., description="Application name (e.g., 'open_notebook')")
    input: Dict[str, Any] = Field(..., description="Arguments to pass to the command")


class CommandJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class CommandJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: Optional[int] = None
    app_name: Optional[str] = None
    command_name: Optional[str] = None


@router.post("/commands/jobs", response_model=CommandJobResponse)
async def execute_command(request: CommandExecutionRequest):
    """
    Submit a command for background processing.
    Returns immediately with job ID for status tracking.

    Example request:
    {
        "command": "process_text",
        "app": "open_notebook",
        "input": {
            "text": "Hello world",
            "operation": "uppercase"
        }
    }
    """
    try:
        # Submit command using app name (not module name)
        job_id = await CommandService.submit_command_job(
            module_name=request.app,  # This should be "open_notebook"
            command_name=request.command,
            command_args=request.input,
        )

        return CommandJobResponse(
            job_id=job_id,
            status="submitted",
            message=f"Command '{request.command}' submitted successfully",
        )

    except Exception as e:
        logger.error(f"Error submitting command: {str(e)}")
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=str(e)) from e
        raise HTTPException(status_code=500, detail="Failed to submit command") from e


@router.post("/commands/jobs/{job_id}/retry", response_model=CommandJobResponse)
async def retry_command_job(job_id: str):
    try:
        retried_job_id = await CommandService.retry_command_job(job_id)
        return CommandJobResponse(
            job_id=retried_job_id,
            status="submitted",
            message=f"Command job '{job_id}' retried successfully",
        )
    except Exception as e:
        logger.error(f"Error retrying command job {job_id}: {str(e)}")
        if isinstance(e, ValueError):
            status_code = 404 if "not found" in str(e).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(e)) from e
        raise HTTPException(
            status_code=500, detail=f"Failed to retry command job: {str(e)}"
        ) from e


@router.get("/commands/jobs/{job_id}", response_model=CommandJobStatusResponse)
async def get_command_job_status(job_id: str):
    """Get the status of a specific command job"""
    try:
        status_data = await CommandService.get_command_status(job_id)
        return CommandJobStatusResponse(**status_data)

    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status") from e


@router.get("/commands/jobs", response_model=List[Dict[str, Any]])
async def list_command_jobs(
    command_filter: Optional[str] = Query(None, description="Filter by command name"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of jobs to return"),
):
    """List command jobs with optional filtering"""
    try:
        jobs = await CommandService.list_command_jobs(
            command_filter=command_filter, status_filter=status_filter, limit=limit
        )
        return jobs

    except Exception as e:
        logger.error(f"Error listing command jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list command jobs") from e


@router.delete("/commands/jobs/{job_id}")
async def cancel_command_job(job_id: str):
    """Cancel a running command job"""
    try:
        success = await CommandService.cancel_command_job(job_id)
        return {"job_id": job_id, "cancelled": success}

    except Exception as e:
        logger.error(f"Error cancelling command job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel command job") from e


@router.get("/commands/registry/debug")
async def debug_registry():
    """Debug endpoint to see what commands are registered"""
    try:
        # Get all registered commands
        all_items = registry.get_all_commands()

        # Create JSON-serializable data
        command_items = []
        for item in all_items:
            try:
                command_items.append(
                    {
                        "app_id": item.app_id,
                        "name": item.name,
                        "full_id": f"{item.app_id}.{item.name}",
                    }
                )
            except Exception as item_error:
                logger.error(f"Error processing item: {item_error}")

        # Get the basic command structure
        try:
            commands_dict: dict[str, list[str]] = {}
            for item in all_items:
                if item.app_id not in commands_dict:
                    commands_dict[item.app_id] = []
                commands_dict[item.app_id].append(item.name)
        except Exception:
            commands_dict = {}

        return {
            "total_commands": len(all_items),
            "commands_by_app": commands_dict,
            "command_items": command_items,
        }

    except Exception as e:
        logger.error(f"Error debugging registry: {str(e)}")
        return {
            "error": str(e),
            "total_commands": 0,
            "commands_by_app": {},
            "command_items": [],
        }
