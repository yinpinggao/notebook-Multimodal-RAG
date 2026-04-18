from __future__ import annotations

import asyncio
from typing import Optional

from api.schemas import ProjectSummary
from open_notebook.agent_harness import get_project_last_run_at
from open_notebook.memory_center import count_project_memories
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import NotFoundError
from open_notebook.project_os import artifact_service as project_os_artifact_service
from open_notebook.seekdb import seekdb_business_store


def _row_to_project_summary(
    row: dict,
    *,
    artifact_count: int = 0,
    memory_count: int = 0,
    last_run_at: Optional[str] = None,
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
    )


def _notebook_to_project_summary(
    notebook: Notebook,
    *,
    artifact_count: int = 0,
    memory_count: int = 0,
    last_run_at: Optional[str] = None,
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
    )


async def _artifact_count_for_project(project_id: str) -> int:
    if not project_id:
        return 0
    return await project_os_artifact_service.count_project_artifacts(project_id)


async def _memory_count_for_project(project_id: str) -> int:
    if not project_id:
        return 0
    return await count_project_memories(project_id)


async def _last_run_at_for_project(project_id: str) -> Optional[str]:
    if not project_id:
        return None
    return await get_project_last_run_at(project_id)


async def list_projects(
    archived: Optional[bool] = None,
    order_by: str = "updated desc",
) -> list[ProjectSummary]:
    rows = await seekdb_business_store.notebook_rows(order_by=order_by)

    if archived is not None:
        rows = [row for row in rows if bool(row.get("archived", False)) == archived]

    artifact_counts = await asyncio.gather(
        *[_artifact_count_for_project(str(row.get("id", ""))) for row in rows]
    )
    memory_counts = await asyncio.gather(
        *[_memory_count_for_project(str(row.get("id", ""))) for row in rows]
    )
    last_run_ats = await asyncio.gather(
        *[_last_run_at_for_project(str(row.get("id", ""))) for row in rows]
    )
    return [
        _row_to_project_summary(
            row,
            artifact_count=artifact_count,
            memory_count=memory_count,
            last_run_at=last_run_at,
        )
        for row, artifact_count, memory_count, last_run_at in zip(
            rows,
            artifact_counts,
            memory_counts,
            last_run_ats,
            strict=False,
        )
    ]


async def get_project(project_id: str) -> ProjectSummary:
    row = await seekdb_business_store.notebook_row(project_id)
    if not row:
        raise NotFoundError("Project not found")

    artifact_count, memory_count, last_run_at = await asyncio.gather(
        _artifact_count_for_project(project_id),
        _memory_count_for_project(project_id),
        _last_run_at_for_project(project_id),
    )
    return _row_to_project_summary(
        row,
        artifact_count=artifact_count,
        memory_count=memory_count,
        last_run_at=last_run_at,
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
