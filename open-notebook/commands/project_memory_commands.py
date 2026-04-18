import time

from pydantic import Field

from open_notebook.jobs import CommandInput, CommandOutput, command
from open_notebook.memory_center.memory_writer import rebuild_project_memories
from open_notebook.memory_center.powermem_adapter import mark_project_memory_status


class ProjectRefreshMemoryInput(CommandInput):
    project_id: str


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

    try:
        records = await rebuild_project_memories(
            input_data.project_id,
            command_id=command_id,
        )
        breakdown: dict[str, int] = {}
        for record in records:
            breakdown[record.status] = breakdown.get(record.status, 0) + 1
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
        raise


__all__ = ["refresh_project_memory_command"]
