from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import AliasChoices, BaseModel, Field

from api import project_compare_service
from api.schemas import (
    ProjectCompareCreateResponse,
    ProjectCompareExportResponse,
    ProjectCompareRecord,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter()


class ProjectCompareRequest(BaseModel):
    source_a_id: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("source_a_id", "left_source_id"),
        description="Left-side source identifier",
    )
    source_b_id: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("source_b_id", "right_source_id"),
        description="Right-side source identifier",
    )
    compare_mode: Literal["general", "requirements", "risks", "timeline"] = Field(
        default="general",
        description="Compare mode",
    )


@router.post(
    "/projects/{project_id}/compare",
    response_model=ProjectCompareCreateResponse,
)
async def create_project_compare(project_id: str, request: ProjectCompareRequest):
    try:
        return await project_compare_service.queue_project_compare(
            project_id,
            source_a_id=request.source_a_id,
            source_b_id=request.source_b_id,
            compare_mode=request.compare_mode,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error queueing compare for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error queueing project compare: {e}",
        ) from e


@router.get(
    "/projects/{project_id}/compare/{compare_id}",
    response_model=ProjectCompareRecord,
)
async def get_project_compare(project_id: str, compare_id: str):
    try:
        return await project_compare_service.get_project_compare(project_id, compare_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching compare {compare_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project compare: {e}",
        ) from e


@router.post(
    "/projects/{project_id}/compare/{compare_id}/export",
    response_model=ProjectCompareExportResponse,
)
async def export_project_compare(project_id: str, compare_id: str):
    try:
        return await project_compare_service.export_project_compare(project_id, compare_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error exporting compare {compare_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting project compare: {e}",
        ) from e
