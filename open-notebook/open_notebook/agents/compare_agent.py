from __future__ import annotations

from open_notebook.domain.compare import ProjectCompareMode, ProjectCompareRecord
from open_notebook.project_os.compare_service import build_and_store_project_compare


async def compare_project_sources(
    project_id: str,
    *,
    compare_id: str,
    source_a_id: str,
    source_b_id: str,
    compare_mode: ProjectCompareMode = "general",
    command_id: str | None = None,
) -> ProjectCompareRecord:
    return await build_and_store_project_compare(
        project_id,
        compare_id=compare_id,
        source_a_id=source_a_id,
        source_b_id=source_b_id,
        compare_mode=compare_mode,
        command_id=command_id,
    )


__all__ = ["compare_project_sources"]
