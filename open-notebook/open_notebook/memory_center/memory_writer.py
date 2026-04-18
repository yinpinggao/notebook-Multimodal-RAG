from __future__ import annotations

from open_notebook.agents.memory_curator_agent import collect_project_memory_candidates
from open_notebook.domain.memory import MemoryRecord
from open_notebook.memory_center.memory_policy import apply_memory_policy
from open_notebook.memory_center.memory_resolver import merge_memory_record
from open_notebook.memory_center.powermem_adapter import (
    list_project_memories,
    mark_project_memory_status,
    save_project_memory_record,
)


async def rebuild_project_memories(
    project_id: str,
    *,
    command_id: str | None = None,
) -> list[MemoryRecord]:
    candidates = await collect_project_memory_candidates(project_id)
    existing_records = {
        record.id: record
        for record in await list_project_memories(project_id, include_deprecated=True)
    }

    stored_records: list[MemoryRecord] = []
    active_memory_ids: set[str] = set()
    for candidate in candidates:
        governed_record = apply_memory_policy(candidate)
        resolved_record = merge_memory_record(
            existing_records.get(governed_record.id),
            governed_record,
        )
        active_memory_ids.add(resolved_record.id)
        stored_records.append(
            await save_project_memory_record(
                project_id,
                resolved_record,
                origin="rebuild",
            )
        )

    for existing_record in existing_records.values():
        if existing_record.id in active_memory_ids:
            continue
        if existing_record.status != "draft":
            continue

        deprecated_record = MemoryRecord.model_validate(
            {
                **existing_record.model_dump(mode="json"),
                "status": "deprecated",
            }
        )
        stored_records.append(
            await save_project_memory_record(
                project_id,
                deprecated_record,
                origin="rebuild",
            )
        )

    await mark_project_memory_status(
        project_id,
        "completed",
        command_id=command_id,
        error_message=None,
    )
    return stored_records


__all__ = ["rebuild_project_memories"]
