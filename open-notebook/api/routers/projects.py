from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from api.models import NotebookCreate
from api.schemas import ProjectOverviewResponse, ProjectSummary
from open_notebook.exceptions import InvalidInputError, NotFoundError

from api import project_overview_service, project_workspace_service

router = APIRouter()


class ProjectDeleteResponse(BaseModel):
    message: str
    project_id: str
    deleted_notes: int
    deleted_sources: int
    unlinked_sources: int


class ProjectOverviewRebuildResponse(BaseModel):
    project_id: str
    status: str
    message: str
    command_id: Optional[str] = None


@router.get("/projects", response_model=list[ProjectSummary])
async def get_projects(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
):
    try:
        return await project_workspace_service.list_projects(
            archived=archived,
            order_by=order_by,
        )
    except Exception as e:
        logger.error(f"Error fetching projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching projects: {e}",
        ) from e


@router.post("/projects", response_model=ProjectSummary)
async def create_project(project: NotebookCreate):
    try:
        return await project_workspace_service.create_project(
            name=project.name,
            description=project.description,
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating project: {e}",
        ) from e


@router.delete("/projects/{project_id}", response_model=ProjectDeleteResponse)
async def delete_project(
    project_id: str,
    delete_exclusive_sources: bool = Query(
        False,
        description="Whether to delete sources linked only to this project",
    ),
):
    try:
        result = await project_workspace_service.delete_project(
            project_id,
            delete_exclusive_sources=delete_exclusive_sources,
        )
        return ProjectDeleteResponse(
            message="Project deleted successfully",
            project_id=str(result["project_id"]),
            deleted_notes=int(result["deleted_notes"]),
            deleted_sources=int(result["deleted_sources"]),
            unlinked_sources=int(result["unlinked_sources"]),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting project: {e}",
        ) from e


@router.get("/projects/{project_id}/overview", response_model=ProjectOverviewResponse)
async def get_project_overview(project_id: str):
    try:
        return await project_overview_service.get_project_overview(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching project overview for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project overview: {e}",
        ) from e


@router.post(
    "/projects/{project_id}/overview/rebuild",
    response_model=ProjectOverviewRebuildResponse,
)
async def rebuild_project_overview(project_id: str):
    try:
        result = await project_overview_service.queue_project_overview_rebuild(project_id)
        return ProjectOverviewRebuildResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error queueing overview rebuild for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error queueing project overview rebuild: {e}",
        ) from e
