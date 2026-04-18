from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from api import project_memory_service
from api.schemas import MemoryRecord
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter()


class ProjectMemoryUpdateRequest(BaseModel):
    status: Optional[Literal["draft", "accepted", "frozen", "deprecated"]] = Field(
        default=None,
        description="Updated governance status for the memory record",
    )
    text: Optional[str] = Field(
        default=None,
        description="Optional edited memory text",
    )


class ProjectMemoryDeleteResponse(BaseModel):
    project_id: str
    memory_id: str
    status: Literal["deleted"]


class ProjectMemoryRebuildResponse(BaseModel):
    project_id: str
    status: str
    message: str
    command_id: Optional[str] = None
    run_id: Optional[str] = None


@router.get(
    "/projects/{project_id}/memory",
    response_model=list[MemoryRecord],
)
async def get_project_memory(project_id: str):
    try:
        return await project_memory_service.list_memory_records(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error listing memory for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing project memory: {e}",
        ) from e


@router.patch(
    "/projects/{project_id}/memory/{memory_id}",
    response_model=MemoryRecord,
)
async def patch_project_memory(
    project_id: str,
    memory_id: str,
    request: ProjectMemoryUpdateRequest,
):
    try:
        return await project_memory_service.update_memory_record(
            project_id,
            memory_id,
            text=request.text,
            status=request.status,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error updating memory {memory_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating project memory: {e}",
        ) from e


@router.delete(
    "/projects/{project_id}/memory/{memory_id}",
    response_model=ProjectMemoryDeleteResponse,
)
async def remove_project_memory(project_id: str, memory_id: str):
    try:
        return await project_memory_service.delete_memory_record(project_id, memory_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting project memory: {e}",
        ) from e


@router.post(
    "/projects/{project_id}/memory/rebuild",
    response_model=ProjectMemoryRebuildResponse,
)
async def rebuild_project_memory(project_id: str):
    try:
        return await project_memory_service.queue_project_memory_rebuild(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error queueing memory rebuild for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error queueing project memory rebuild: {e}",
        ) from e
