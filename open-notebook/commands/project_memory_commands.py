import time

from pydantic import Field

from open_notebook.agent_harness import (
    mark_run_completed,
    mark_run_failed,
    mark_run_running,
    record_memory_write,
)
from open_notebook.jobs import CommandInput, CommandOutput, command
from open_notebook.memory_center.memory_writer import rebuild_project_memories
from open_notebook.memory_center.powermem_adapter import mark_project_memory_status


class ProjectRefreshMemoryInput(CommandInput):
    project_id: str
    run_id: str | None = None


class ProjectRefreshMemoryOutput(CommandOutput):
    success: bool
    project_id: str
    memory_count: int = 0
    status_breakdown: dict[str, int] = Field(default_factory=dict)


@command("refresh_memory", app="open_notebook", retry=None)
async def refresh_project_memory_command(
    input_data: ProjectRefreshMemoryInput,
) -> ProjectRefreshMemoryOutput:
    start_time = time.time()
    command_id = (
        input_data.execution_context.command_id
        if input_data.execution_context
        else None
    )

    await mark_project_memory_status(
        input_data.project_id,
        "running",
        command_id=command_id,
        error_message=None,
    )
    if input_data.run_id:
        await mark_run_running(input_data.run_id)

    try:
        records = await rebuild_project_memories(
            input_data.project_id,
            command_id=command_id,
        )
        breakdown: dict[str, int] = {}
        for record in records:
            breakdown[record.status] = breakdown.get(record.status, 0) + 1
        if input_data.run_id:
            evidence_refs = [
                ref.internal_ref
                for record in records
                for ref in record.source_refs
            ]
            memory_ids = [record.id for record in records]
            await record_memory_write(
                input_data.run_id,
                title="写入项目记忆",
                agent_name="memory_center",
                output_json={
                    "memory_count": len(records),
                    "status_breakdown": breakdown,
                },
                evidence_refs=evidence_refs,
                memory_refs=memory_ids,
            )
            await mark_run_completed(
                input_data.run_id,
                output_json={
                    "memory_count": len(records),
                    "status_breakdown": breakdown,
                },
                tool_calls=["rebuild_project_memories"],
                evidence_reads=evidence_refs,
                memory_writes=memory_ids,
                outputs=memory_ids,
            )
        return ProjectRefreshMemoryOutput(
            success=True,
            project_id=input_data.project_id,
            memory_count=len(records),
            status_breakdown=breakdown,
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        await mark_project_memory_status(
            input_data.project_id,
            "failed",
            command_id=command_id,
            error_message=str(exc),
        )
        if input_data.run_id:
            await mark_run_failed(input_data.run_id, str(exc))
        raise


__all__ = ["refresh_project_memory_command"]
