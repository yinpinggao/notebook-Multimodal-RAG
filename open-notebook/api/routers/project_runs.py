from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger

from api import project_run_service
from api.schemas import AgentRun
from open_notebook.exceptions import NotFoundError

router = APIRouter()


@router.get(
    "/projects/{project_id}/runs",
    response_model=list[AgentRun],
)
async def list_project_runs(project_id: str):
    try:
        return await project_run_service.list_runs(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error listing runs for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing project runs: {e}",
        ) from e


@router.get(
    "/projects/{project_id}/runs/{run_id}",
    response_model=AgentRun,
)
async def get_project_run(project_id: str, run_id: str):
    try:
        return await project_run_service.get_run(project_id, run_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching run {run_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project run: {e}",
        ) from e
