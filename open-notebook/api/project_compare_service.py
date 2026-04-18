from __future__ import annotations

from api.schemas import (
    ProjectCompareCreateResponse,
    ProjectCompareExportResponse,
    ProjectCompareRecord,
)
from open_notebook.agent_harness import (
    create_project_run,
    mark_run_failed,
    record_step,
)
from open_notebook.domain.compare import ProjectCompareMode
from open_notebook.exceptions import InvalidInputError
from open_notebook.jobs import async_submit_command
from open_notebook.project_os import compare_service as project_os_compare_service

from . import project_workspace_service


async def queue_project_compare(
    project_id: str,
    *,
    source_a_id: str,
    source_b_id: str,
    compare_mode: ProjectCompareMode = "general",
) -> ProjectCompareCreateResponse:
    await project_workspace_service.get_project(project_id)

    record = await project_os_compare_service.initialize_project_compare(
        project_id,
        source_a_id=source_a_id,
        source_b_id=source_b_id,
        compare_mode=compare_mode,
    )
    run = await create_project_run(
        project_id,
        run_type="compare",
        input_json={
            "compare_id": record.id,
            "source_a_id": source_a_id,
            "source_b_id": source_b_id,
            "source_a_title": record.source_a_title,
            "source_b_title": record.source_b_title,
            "compare_mode": compare_mode,
        },
    )

    try:
        command_id = await async_submit_command(
            "open_notebook",
            "compare_sources",
            {
                "project_id": project_id,
                "compare_id": record.id,
                "source_a_id": source_a_id,
                "source_b_id": source_b_id,
                "compare_mode": compare_mode,
                "run_id": run.id,
            },
        )
    except Exception as exc:
        await project_os_compare_service.mark_project_compare_status(
            record.id,
            "failed",
            error_message=str(exc),
        )
        await mark_run_failed(run.id, str(exc))
        raise

    queued_record = await project_os_compare_service.mark_project_compare_status(
        record.id,
        "queued",
        command_id=command_id,
        error_message=None,
    )
    await record_step(
        run.id,
        title="对比任务已入队",
        step_type="system",
        status="completed",
        agent_name="project_harness",
        output_json={
            "compare_id": queued_record.id,
            "command_id": command_id,
        },
        output_refs=[queued_record.id],
    )
    return ProjectCompareCreateResponse(
        compare_id=queued_record.id,
        status=queued_record.status,
        command_id=queued_record.command_id,
        run_id=run.id,
    )


async def get_project_compare(
    project_id: str,
    compare_id: str,
) -> ProjectCompareRecord:
    await project_workspace_service.get_project(project_id)
    return await project_os_compare_service.load_project_compare_for_project(
        project_id,
        compare_id,
    )


async def list_project_compares(project_id: str) -> list[ProjectCompareRecord]:
    await project_workspace_service.get_project(project_id)
    return await project_os_compare_service.list_project_compares(project_id)


async def export_project_compare(
    project_id: str,
    compare_id: str,
) -> ProjectCompareExportResponse:
    record = await get_project_compare(project_id, compare_id)
    if record.status != "completed" or not record.result:
        raise InvalidInputError("Compare result is not ready yet")

    return ProjectCompareExportResponse(
        compare_id=record.id,
        format="markdown",
        content=project_os_compare_service.render_project_compare_markdown(record),
    )
