import time

from pydantic import Field

from open_notebook.agent_harness import (
    mark_run_completed,
    mark_run_failed,
    mark_run_running,
    record_step,
    record_tool_call,
)
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
    run_id: str | None = None


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
    if input_data.run_id:
        await mark_run_running(input_data.run_id)

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
        evidence_refs = []
        if result:
            evidence_refs = [
                *(ref for item in result.similarities for ref in item.source_refs),
                *(ref for item in result.differences for ref in item.source_refs),
                *(ref for item in result.conflicts for ref in item.source_refs),
                *(ref for item in result.missing_items for ref in item.source_refs),
                *(ref for item in result.human_review_required for ref in item.source_refs),
            ]
        counts = {
            "similarity_count": len(result.similarities) if result else 0,
            "difference_count": len(result.differences) if result else 0,
            "conflict_count": len(result.conflicts) if result else 0,
            "missing_count": len(result.missing_items) if result else 0,
            "review_count": len(result.human_review_required) if result else 0,
        }
        if input_data.run_id:
            await record_tool_call(
                input_data.run_id,
                title="生成结构化对比",
                tool_name="compare_project_sources",
                agent_name="compare_agent",
                input_json={
                    "source_a_id": input_data.source_a_id,
                    "source_b_id": input_data.source_b_id,
                    "compare_mode": input_data.compare_mode,
                },
                output_json=counts,
                evidence_refs=evidence_refs,
                output_refs=[input_data.compare_id],
            )
            await record_step(
                input_data.run_id,
                title="写入对比结果",
                step_type="compare",
                status="completed",
                agent_name="compare_agent",
                output_json={
                    "compare_id": input_data.compare_id,
                    **counts,
                },
                evidence_refs=evidence_refs,
                output_refs=[input_data.compare_id],
            )
            await mark_run_completed(
                input_data.run_id,
                output_json={
                    "compare_id": input_data.compare_id,
                    **counts,
                },
                tool_calls=["compare_project_sources"],
                evidence_reads=evidence_refs,
                outputs=[input_data.compare_id],
            )
        return ProjectCompareOutput(
            success=True,
            project_id=input_data.project_id,
            compare_id=input_data.compare_id,
            similarity_count=counts["similarity_count"],
            difference_count=counts["difference_count"],
            conflict_count=counts["conflict_count"],
            missing_count=counts["missing_count"],
            review_count=counts["review_count"],
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        await mark_project_compare_status(
            input_data.compare_id,
            "failed",
            command_id=command_id,
            error_message=str(exc),
        )
        if input_data.run_id:
            await record_step(
                input_data.run_id,
                title="对比任务失败",
                step_type="compare",
                status="failed",
                agent_name="compare_agent",
                error=str(exc),
            )
            await mark_run_failed(input_data.run_id, str(exc))
        raise


__all__ = ["compare_sources_command"]
