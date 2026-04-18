import time

from pydantic import Field

from open_notebook.agents.defense_coach_agent import generate_defense_artifact
from open_notebook.agents.synthesis_agent import generate_synthesis_artifact
from open_notebook.jobs import CommandInput, CommandOutput, command
from open_notebook.project_os.artifact_service import (
    load_stored_project_artifact_for_project,
    mark_project_artifact_status,
)

DEFENSE_ARTIFACT_TYPES = {"defense_outline", "judge_questions"}


class ProjectArtifactInput(CommandInput):
    project_id: str
    artifact_id: str


class ProjectArtifactOutput(CommandOutput):
    success: bool
    project_id: str
    artifact_id: str
    artifact_type: str
    source_ref_count: int = 0
    content_length: int = 0
    section_count: int = Field(default=0)


@command("generate_artifact", app="open_notebook", retry=None)
async def generate_artifact_command(
    input_data: ProjectArtifactInput,
) -> ProjectArtifactOutput:
    start_time = time.time()
    command_id = (
        input_data.execution_context.command_id
        if input_data.execution_context
        else None
    )

    await mark_project_artifact_status(
        input_data.artifact_id,
        "running",
        command_id=command_id,
        error_message=None,
    )

    try:
        stored_record = await load_stored_project_artifact_for_project(
            input_data.project_id,
            input_data.artifact_id,
        )
        if stored_record.artifact_type in DEFENSE_ARTIFACT_TYPES:
            content_md = await generate_defense_artifact(
                stored_record.artifact_type,
                title=stored_record.title,
                snapshot=stored_record.source_snapshot,
            )
        else:
            content_md = await generate_synthesis_artifact(
                stored_record.artifact_type,
                title=stored_record.title,
                snapshot=stored_record.source_snapshot,
            )

        await mark_project_artifact_status(
            input_data.artifact_id,
            "ready",
            command_id=command_id,
            error_message=None,
            content_md=content_md,
            source_refs=stored_record.source_snapshot.source_refs,
        )

        return ProjectArtifactOutput(
            success=True,
            project_id=input_data.project_id,
            artifact_id=input_data.artifact_id,
            artifact_type=stored_record.artifact_type,
            source_ref_count=len(stored_record.source_snapshot.source_refs),
            content_length=len(content_md),
            section_count=content_md.count("\n## "),
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        await mark_project_artifact_status(
            input_data.artifact_id,
            "failed",
            command_id=command_id,
            error_message=str(exc),
        )
        raise


__all__ = ["generate_artifact_command"]
