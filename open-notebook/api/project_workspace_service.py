from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from api.schemas import ProjectSummary
from open_notebook.agent_harness import list_project_runs
from open_notebook.domain.artifacts import ArtifactRecord
from open_notebook.domain.runs import AgentRun
from open_notebook.memory_center import count_project_memories
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import NotFoundError
from open_notebook.project_os import artifact_service as project_os_artifact_service
from open_notebook.project_os.demo_service import ensure_demo_project
from open_notebook.seekdb import seekdb_business_store


@dataclass(frozen=True)
class ProjectRuntimeSummary:
    artifact_count: int
    memory_count: int
    last_run_at: Optional[str]
    phase: str
    latest_output_title: Optional[str]
    latest_run_status: Optional[str]


RUNS_PHASE_STATUSES = {"failed", "waiting_review", "cancelled"}
RUN_TYPE_PHASES = {
    "ask": "ask",
    "compare": "compare",
    "artifact": "outputs",
    "memory_rebuild": "memory",
    "overview_rebuild": "collect",
    "ingest": "collect",
    "unknown": "collect",
}


def _run_activity_at(run: AgentRun) -> str:
    return run.completed_at or run.started_at or run.created_at


def _latest_active_artifact(
    artifacts: list[ArtifactRecord],
) -> ArtifactRecord | None:
    for artifact in artifacts:
        if artifact.status not in {"archived", "failed"}:
            return artifact
    return None


def derive_project_phase(
    *,
    source_count: int,
    memory_count: int,
    latest_run: AgentRun | None,
    latest_artifact: ArtifactRecord | None,
) -> str:
    if latest_run and latest_run.status in RUNS_PHASE_STATUSES:
        return "runs"

    if latest_run:
        return RUN_TYPE_PHASES.get(latest_run.run_type, "collect")

    if latest_artifact:
        return "outputs"

    if memory_count > 0:
        return "memory"

    if source_count > 0:
        return "ask"

    return "collect"


def _row_to_project_summary(
    row: dict,
    *,
    artifact_count: int = 0,
    memory_count: int = 0,
    last_run_at: Optional[str] = None,
    phase: str = "collect",
    latest_output_title: Optional[str] = None,
    latest_run_status: Optional[str] = None,
) -> ProjectSummary:
    archived = bool(row.get("archived", False))
    return ProjectSummary(
        id=str(row.get("id", "")),
        name=row.get("name", ""),
        description=row.get("description") or "",
        status="archived" if archived else "active",
        created_at=str(row.get("created", "")),
        updated_at=str(row.get("updated", "")),
        source_count=int(row.get("source_count") or 0),
        artifact_count=artifact_count,
        memory_count=memory_count,
        last_run_at=last_run_at,
        phase=phase,
        latest_output_title=latest_output_title,
        latest_run_status=latest_run_status,
    )


def _notebook_to_project_summary(
    notebook: Notebook,
    *,
    artifact_count: int = 0,
    memory_count: int = 0,
    last_run_at: Optional[str] = None,
    phase: str = "collect",
    latest_output_title: Optional[str] = None,
    latest_run_status: Optional[str] = None,
) -> ProjectSummary:
    return ProjectSummary(
        id=str(notebook.id or ""),
        name=notebook.name,
        description=notebook.description or "",
        status="archived" if notebook.archived else "active",
        created_at=str(notebook.created or ""),
        updated_at=str(notebook.updated or ""),
        source_count=0,
        artifact_count=artifact_count,
        memory_count=memory_count,
        last_run_at=last_run_at,
        phase=phase,
        latest_output_title=latest_output_title,
        latest_run_status=latest_run_status,
    )


async def _artifacts_for_project(project_id: str) -> list[ArtifactRecord]:
    if not project_id:
        return []
    return await project_os_artifact_service.list_project_artifacts(project_id, limit=1000)


async def _memory_count_for_project(project_id: str) -> int:
    if not project_id:
        return 0
    return await count_project_memories(project_id)


async def _latest_run_for_project(project_id: str) -> AgentRun | None:
    if not project_id:
        return None
    runs = await list_project_runs(project_id, limit=1)
    return runs[0] if runs else None


async def _project_runtime_summary(
    project_id: str,
    *,
    source_count: int,
) -> ProjectRuntimeSummary:
    artifacts, memory_count, latest_run = await asyncio.gather(
        _artifacts_for_project(project_id),
        _memory_count_for_project(project_id),
        _latest_run_for_project(project_id),
    )
    active_artifacts = [
        artifact for artifact in artifacts if artifact.status not in {"archived", "failed"}
    ]
    latest_artifact = _latest_active_artifact(artifacts)

    return ProjectRuntimeSummary(
        artifact_count=len(active_artifacts),
        memory_count=memory_count,
        last_run_at=_run_activity_at(latest_run) if latest_run else None,
        phase=derive_project_phase(
            source_count=source_count,
            memory_count=memory_count,
            latest_run=latest_run,
            latest_artifact=latest_artifact,
        ),
        latest_output_title=latest_artifact.title if latest_artifact else None,
        latest_run_status=latest_run.status if latest_run else None,
    )


async def list_projects(
    archived: Optional[bool] = None,
    order_by: str = "updated desc",
) -> list[ProjectSummary]:
    rows = await seekdb_business_store.notebook_rows(order_by=order_by)

    if archived is not None:
        rows = [row for row in rows if bool(row.get("archived", False)) == archived]

    runtime_summaries = await asyncio.gather(
        *[
            _project_runtime_summary(
                str(row.get("id", "")),
                source_count=int(row.get("source_count") or 0),
            )
            for row in rows
        ]
    )
    return [
        _row_to_project_summary(
            row,
            artifact_count=runtime_summary.artifact_count,
            memory_count=runtime_summary.memory_count,
            last_run_at=runtime_summary.last_run_at,
            phase=runtime_summary.phase,
            latest_output_title=runtime_summary.latest_output_title,
            latest_run_status=runtime_summary.latest_run_status,
        )
        for row, runtime_summary in zip(
            rows,
            runtime_summaries,
            strict=False,
        )
    ]


async def get_project(project_id: str) -> ProjectSummary:
    row = await seekdb_business_store.notebook_row(project_id)
    if not row:
        raise NotFoundError("Project not found")

    runtime_summary = await _project_runtime_summary(
        project_id,
        source_count=int(row.get("source_count") or 0),
    )
    return _row_to_project_summary(
        row,
        artifact_count=runtime_summary.artifact_count,
        memory_count=runtime_summary.memory_count,
        last_run_at=runtime_summary.last_run_at,
        phase=runtime_summary.phase,
        latest_output_title=runtime_summary.latest_output_title,
        latest_run_status=runtime_summary.latest_run_status,
    )


async def create_project(name: str, description: str = "") -> ProjectSummary:
    notebook = Notebook(
        name=name,
        description=description,
    )
    await notebook.save()

    if notebook.id:
        row = await seekdb_business_store.notebook_row(str(notebook.id))
        if row:
            return _row_to_project_summary(row)

    return _notebook_to_project_summary(notebook)


async def create_demo_project() -> ProjectSummary:
    project_id = await ensure_demo_project()
    return await get_project(project_id)


async def delete_project(
    project_id: str,
    delete_exclusive_sources: bool = False,
) -> dict[str, int | str]:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Project not found")

    result = await notebook.delete(delete_exclusive_sources=delete_exclusive_sources)

    return {
        "project_id": project_id,
        **result,
    }
