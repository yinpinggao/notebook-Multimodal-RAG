from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from api import project_artifact_service
from api.schemas import ArtifactRecord, ProjectArtifactCreateResponse
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter()


class ProjectArtifactRequest(BaseModel):
    artifact_type: Literal[
        "project_summary",
        "diff_report",
        "defense_outline",
        "judge_questions",
        "qa_cards",
    ] = Field(..., description="Artifact type")
    origin_kind: Literal["overview", "compare", "thread"] = Field(
        ...,
        description="Origin kind used to generate the artifact",
    )
    origin_id: Optional[str] = Field(
        default=None,
        description="Origin identifier for compare or thread sources",
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional custom artifact title",
    )


@router.post(
    "/projects/{project_id}/artifacts",
    response_model=ProjectArtifactCreateResponse,
)
async def create_project_artifact(project_id: str, request: ProjectArtifactRequest):
    try:
        return await project_artifact_service.queue_project_artifact(
            project_id,
            artifact_type=request.artifact_type,
            origin_kind=request.origin_kind,
            origin_id=request.origin_id,
            title=request.title,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error queueing artifact for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error queueing project artifact: {e}",
        ) from e


@router.get(
    "/projects/{project_id}/artifacts",
    response_model=list[ArtifactRecord],
)
async def list_project_artifacts(project_id: str):
    try:
        return await project_artifact_service.list_project_artifacts(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error listing artifacts for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing project artifacts: {e}",
        ) from e


@router.get(
    "/projects/{project_id}/artifacts/{artifact_id}",
    response_model=ArtifactRecord,
)
async def get_project_artifact(project_id: str, artifact_id: str):
    try:
        return await project_artifact_service.get_project_artifact(
            project_id,
            artifact_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching artifact {artifact_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project artifact: {e}",
        ) from e


@router.post(
    "/projects/{project_id}/artifacts/{artifact_id}/regenerate",
    response_model=ProjectArtifactCreateResponse,
)
async def regenerate_project_artifact(project_id: str, artifact_id: str):
    try:
        return await project_artifact_service.regenerate_project_artifact(
            project_id,
            artifact_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error regenerating artifact {artifact_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating project artifact: {e}",
        ) from e
