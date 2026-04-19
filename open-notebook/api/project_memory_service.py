from __future__ import annotations

from typing import Optional
from uuid import uuid4

from open_notebook.agent_harness import (
    create_project_run,
    mark_run_failed,
    record_step,
)
from open_notebook.domain.memory import MemoryRecord, SourceReference
from open_notebook.exceptions import InvalidInputError
from open_notebook.jobs import async_submit_command
from open_notebook.memory_center import (
    delete_project_memory,
    list_project_memories,
    mark_project_memory_status,
    update_project_memory,
)
from open_notebook.memory_center.memory_policy import (
    clamp_confidence,
    decay_policy_for_type,
    normalize_memory_text,
)
from open_notebook.memory_center.powermem_adapter import save_project_memory_record

from . import project_workspace_service


async def list_memory_records(project_id: str) -> list[MemoryRecord]:
    await project_workspace_service.get_project(project_id)
    return await list_project_memories(project_id, include_deprecated=True)


async def update_memory_record(
    project_id: str,
    memory_id: str,
    *,
    text: Optional[str] = None,
    status: Optional[str] = None,
) -> MemoryRecord:
    await project_workspace_service.get_project(project_id)

    normalized_text = " ".join(str(text or "").strip().split()) if text is not None else None
    if normalized_text == "":
        raise InvalidInputError("Memory text cannot be empty")

    return await update_project_memory(
        project_id,
        memory_id,
        text=normalized_text,
        status=status,
    )


async def create_memory_record(
    project_id: str,
    *,
    text: str,
    memory_type: str,
    status: str = "draft",
    scope: str = "project",
    source_refs: Optional[list[SourceReference]] = None,
) -> MemoryRecord:
    await project_workspace_service.get_project(project_id)

    normalized_text = normalize_memory_text(text)
    if not normalized_text:
        raise InvalidInputError("Memory text cannot be empty")
    if scope != "project":
        raise InvalidInputError("Only project-scoped memory is supported")

    references = source_refs or []
    confidence = clamp_confidence(0.82 if references else 0.58)
    record = MemoryRecord(
        id=f"memory:{uuid4().hex[:12]}",
        scope="project",
        type=memory_type,
        text=normalized_text,
        confidence=confidence,
        freshness=None,
        source_refs=references,
        status=status,
        decay_policy=decay_policy_for_type(memory_type),
        conflict_group=None,
    )
    return await save_project_memory_record(
        project_id,
        record,
        origin="manual",
    )


async def delete_memory_record(project_id: str, memory_id: str) -> dict[str, str]:
    await project_workspace_service.get_project(project_id)
    await delete_project_memory(project_id, memory_id)
    return {
        "project_id": project_id,
        "memory_id": memory_id,
        "status": "deleted",
    }


async def queue_project_memory_rebuild(project_id: str) -> dict[str, str | None]:
    await project_workspace_service.get_project(project_id)

    import commands.project_memory_commands  # noqa: F401
    run = await create_project_run(
        project_id,
        run_type="memory_rebuild",
        input_json={"project_id": project_id},
    )

    try:
        command_id = await async_submit_command(
            "open_notebook",
            "refresh_memory",
            {
                "project_id": project_id,
                "run_id": run.id,
            },
        )
    except Exception as exc:
        await mark_project_memory_status(
            project_id,
            "failed",
            command_id=None,
            error_message=str(exc),
        )
        await mark_run_failed(run.id, str(exc))
        raise

    await mark_project_memory_status(
        project_id,
        "queued",
        command_id=command_id,
        error_message=None,
    )
    await record_step(
        run.id,
        title="记忆重建任务已入队",
        step_type="system",
        status="completed",
        agent_name="project_harness",
        output_json={"command_id": command_id},
    )
    return {
        "project_id": project_id,
        "status": "queued",
        "message": "Project memory rebuild queued.",
        "command_id": command_id,
        "run_id": run.id,
    }


__all__ = [
    "create_memory_record",
    "delete_memory_record",
    "list_memory_records",
    "queue_project_memory_rebuild",
    "update_memory_record",
]
