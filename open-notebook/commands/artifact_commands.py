import time

from pydantic import Field

from open_notebook.agent_harness import (
    mark_run_completed,
    mark_run_failed,
    mark_run_running,
    record_evidence_read,
    record_tool_call,
)
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
    run_id: str | None = None


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
    if input_data.run_id:
        await mark_run_running(input_data.run_id)

    try:
        stored_record = await load_stored_project_artifact_for_project(
            input_data.project_id,
            input_data.artifact_id,
        )
        source_refs = stored_record.source_snapshot.source_refs
        if input_data.run_id:
            await record_evidence_read(
                input_data.run_id,
                title="读取产物来源证据",
                agent_name="artifact_service",
                output_json={
                    "artifact_type": stored_record.artifact_type,
                    "source_ref_count": len(source_refs),
                    "origin_kind": stored_record.origin_kind,
                },
                evidence_refs=source_refs,
            )
        if stored_record.artifact_type in DEFENSE_ARTIFACT_TYPES:
            content_md = await generate_defense_artifact(
                stored_record.artifact_type,
                title=stored_record.title,
                snapshot=stored_record.source_snapshot,
            )
            generator_tool = "generate_defense_artifact"
        else:
            content_md = await generate_synthesis_artifact(
                stored_record.artifact_type,
                title=stored_record.title,
                snapshot=stored_record.source_snapshot,
            )
            generator_tool = "generate_synthesis_artifact"
        section_count = content_md.count("\n## ")

        await mark_project_artifact_status(
            input_data.artifact_id,
            "ready",
            command_id=command_id,
            error_message=None,
            content_md=content_md,
            source_refs=source_refs,
        )
        if input_data.run_id:
            await record_tool_call(
                input_data.run_id,
                title="生成 Markdown 产物",
                tool_name=generator_tool,
                agent_name="artifact_agent",
                input_json={
                    "artifact_type": stored_record.artifact_type,
                    "artifact_id": input_data.artifact_id,
                },
                output_json={
                    "content_length": len(content_md),
                    "section_count": section_count,
                },
                evidence_refs=source_refs,
                output_refs=[input_data.artifact_id],
            )
            await mark_run_completed(
                input_data.run_id,
                output_json={
                    "artifact_id": input_data.artifact_id,
                    "artifact_type": stored_record.artifact_type,
                    "content_length": len(content_md),
                    "section_count": section_count,
                },
                tool_calls=[generator_tool],
                evidence_reads=source_refs,
                outputs=[input_data.artifact_id],
            )

        return ProjectArtifactOutput(
            success=True,
            project_id=input_data.project_id,
            artifact_id=input_data.artifact_id,
            artifact_type=stored_record.artifact_type,
            source_ref_count=len(source_refs),
            content_length=len(content_md),
            section_count=section_count,
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        await mark_project_artifact_status(
            input_data.artifact_id,
            "failed",
            command_id=command_id,
            error_message=str(exc),
        )
        if input_data.run_id:
            await mark_run_failed(input_data.run_id, str(exc))
        raise


__all__ = ["generate_artifact_command"]
