import time

from pydantic import Field

from open_notebook.jobs import CommandInput, CommandOutput, command
from open_notebook.project_os.overview_service import (
    build_and_store_project_overview,
    mark_project_overview_status,
)


class ProjectBuildOverviewInput(CommandInput):
    project_id: str


class ProjectBuildOverviewOutput(CommandOutput):
    success: bool
    project_id: str
    profile_count: int = 0
    extracted_counts: dict[str, int] = Field(default_factory=dict)


@command("build_overview", app="open_notebook", retry=None)
async def build_project_overview_command(
    input_data: ProjectBuildOverviewInput,
) -> ProjectBuildOverviewOutput:
    start_time = time.time()
    command_id = (
        input_data.execution_context.command_id
        if input_data.execution_context
        else None
    )

    await mark_project_overview_status(
        input_data.project_id,
        "running",
        command_id=command_id,
        error_message=None,
    )

    try:
        snapshot = await build_and_store_project_overview(
            input_data.project_id,
            command_id=command_id,
        )
        return ProjectBuildOverviewOutput(
            success=True,
            project_id=input_data.project_id,
            profile_count=len(snapshot.source_profiles),
            extracted_counts={
                "topics": len(snapshot.topics),
                "keywords": len(snapshot.keywords),
                "risks": len(snapshot.risks),
                "requirements": len(snapshot.requirements),
                "timeline_events": len(snapshot.timeline_events),
            },
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        await mark_project_overview_status(
            input_data.project_id,
            "failed",
            command_id=command_id,
            error_message=str(exc),
        )
        raise


__all__ = ["build_project_overview_command"]
