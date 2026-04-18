from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from api import project_evidence_service
from api.schemas import (
    AskResponse,
    EvidenceThreadDetail,
    EvidenceThreadSummary,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter()


class ProjectAskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    mode: Literal["auto", "text", "visual", "mixed"] = Field(
        default="auto",
        description="Requested answer mode",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Existing thread identifier for continuation",
    )


class ProjectFollowupRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Follow-up question")
    mode: Literal["auto", "text", "visual", "mixed"] = Field(
        default="auto",
        description="Requested answer mode",
    )


@router.post("/projects/{project_id}/ask", response_model=AskResponse)
async def ask_project(project_id: str, request: ProjectAskRequest):
    try:
        return await project_evidence_service.ask_project(
            project_id,
            request.question,
            mode=request.mode,
            thread_id=request.thread_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error asking project evidence for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error asking project evidence: {e}",
        ) from e


@router.get("/projects/{project_id}/threads", response_model=list[EvidenceThreadSummary])
async def get_project_threads(project_id: str):
    try:
        return await project_evidence_service.list_project_threads(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching project threads for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project threads: {e}",
        ) from e


@router.get(
    "/projects/{project_id}/threads/{thread_id}",
    response_model=EvidenceThreadDetail,
)
async def get_project_thread(project_id: str, thread_id: str):
    try:
        return await project_evidence_service.get_project_thread(project_id, thread_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error fetching project thread {thread_id} for {project_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project thread: {e}",
        ) from e


@router.post(
    "/projects/{project_id}/threads/{thread_id}/followup",
    response_model=AskResponse,
)
async def followup_project_thread(
    project_id: str,
    thread_id: str,
    request: ProjectFollowupRequest,
):
    try:
        return await project_evidence_service.followup_project_thread(
            project_id,
            thread_id,
            request.question,
            mode=request.mode,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"Error following up project thread {thread_id} for {project_id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error following up project thread: {e}",
        ) from e
