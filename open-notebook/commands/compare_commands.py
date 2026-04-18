import time

from pydantic import Field

from open_notebook.agents.compare_agent import compare_project_sources
from open_notebook.domain.compare import ProjectCompareMode
from open_notebook.jobs import CommandInput, CommandOutput, command
from open_notebook.project_os.compare_service import mark_project_compare_status


class ProjectCompareInput(CommandInput):
    project_id: str
    compare_id: str
    source_a_id: str
    source_b_id: str
    compare_mode: ProjectCompareMode = "general"


class ProjectCompareOutput(CommandOutput):
    success: bool
    project_id: str
    compare_id: str
    similarity_count: int = 0
    difference_count: int = 0
    conflict_count: int = 0
    missing_count: int = 0
    review_count: int = Field(default=0)


@command("compare_sources", app="open_notebook", retry=None)
async def compare_sources_command(
    input_data: ProjectCompareInput,
) -> ProjectCompareOutput:
    start_time = time.time()
    command_id = (
        input_data.execution_context.command_id
        if input_data.execution_context
        else None
    )

    await mark_project_compare_status(
        input_data.compare_id,
        "running",
        command_id=command_id,
        error_message=None,
    )

    try:
        record = await compare_project_sources(
            input_data.project_id,
            compare_id=input_data.compare_id,
            source_a_id=input_data.source_a_id,
            source_b_id=input_data.source_b_id,
            compare_mode=input_data.compare_mode,
            command_id=command_id,
        )
        result = record.result
        return ProjectCompareOutput(
            success=True,
            project_id=input_data.project_id,
            compare_id=input_data.compare_id,
            similarity_count=len(result.similarities) if result else 0,
            difference_count=len(result.differences) if result else 0,
            conflict_count=len(result.conflicts) if result else 0,
            missing_count=len(result.missing_items) if result else 0,
            review_count=len(result.human_review_required) if result else 0,
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        await mark_project_compare_status(
            input_data.compare_id,
            "failed",
            command_id=command_id,
            error_message=str(exc),
        )
        raise


__all__ = ["compare_sources_command"]
