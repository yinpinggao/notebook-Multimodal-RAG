import time
from typing import Any

from pydantic import Field

from api import (
    project_compare_service,
    project_evidence_service,
    project_memory_service,
    project_workspace_service,
)
from open_notebook.agent_harness.evaluator_hooks import (
    EvalMetricResult,
    evaluate_compare_consistency,
    evaluate_evidence_faithfulness,
    evaluate_memory_source_coverage,
)
from open_notebook.jobs import CommandInput, CommandOutput, command


class ProjectEvalInput(CommandInput):
    project_id: str
    thread_id: str | None = None
    compare_id: str | None = None


class ProjectEvalOutput(CommandOutput):
    success: bool
    project_id: str
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    passed_metrics: int = 0
    available_metrics: int = 0
    summary: str = ""
    thread_id: str | None = None
    compare_id: str | None = None


async def _resolve_eval_thread(project_id: str, thread_id: str | None):
    if thread_id:
        return await project_evidence_service.get_project_thread(project_id, thread_id)

    threads = await project_evidence_service.list_project_threads(project_id)
    if not threads:
        return None
    return await project_evidence_service.get_project_thread(project_id, threads[0].id)


async def _resolve_eval_compare(project_id: str, compare_id: str | None):
    if compare_id:
        return await project_compare_service.get_project_compare(project_id, compare_id)

    compares = await project_compare_service.list_project_compares(project_id)
    for compare in compares:
        if compare.status == "completed":
            return compare
    return None


def _summary(metrics: list[EvalMetricResult]) -> tuple[int, int, str]:
    available = [metric for metric in metrics if metric.status != "unavailable"]
    passed = [metric for metric in available if metric.status == "passed"]

    if not available:
        return 0, 0, "当前项目还没有足够的运行结果来完成评测。"

    if len(passed) == len(available):
        return len(passed), len(available), "当前项目的最小评测全部通过。"

    return (
        len(passed),
        len(available),
        f"当前项目通过了 {len(passed)}/{len(available)} 项最小评测。",
    )


@command("run_project_eval", app="open_notebook", retry=None)
async def run_project_eval_command(
    input_data: ProjectEvalInput,
) -> ProjectEvalOutput:
    start_time = time.time()

    await project_workspace_service.get_project(input_data.project_id)
    thread = await _resolve_eval_thread(input_data.project_id, input_data.thread_id)
    compare = await _resolve_eval_compare(input_data.project_id, input_data.compare_id)
    memories = await project_memory_service.list_memory_records(input_data.project_id)

    metrics = [
        evaluate_evidence_faithfulness(
            thread.latest_response if thread else None
        ),
        evaluate_compare_consistency(compare),
        evaluate_memory_source_coverage(memories),
    ]
    passed_metrics, available_metrics, summary = _summary(metrics)

    return ProjectEvalOutput(
        success=True,
        project_id=input_data.project_id,
        metrics=[metric.model_dump(mode="json") for metric in metrics],
        passed_metrics=passed_metrics,
        available_metrics=available_metrics,
        summary=summary,
        thread_id=thread.id if thread else None,
        compare_id=compare.id if compare else None,
        processing_time=time.time() - start_time,
    )


__all__ = ["run_project_eval_command"]
