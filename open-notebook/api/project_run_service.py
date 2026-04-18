from __future__ import annotations

from api.schemas import AgentRun
from open_notebook.agent_harness import (
    list_project_runs,
    load_agent_run_for_project,
)

from . import project_workspace_service


async def list_runs(project_id: str) -> list[AgentRun]:
    await project_workspace_service.get_project(project_id)
    return await list_project_runs(project_id)


async def get_run(project_id: str, run_id: str) -> AgentRun:
    await project_workspace_service.get_project(project_id)
    return await load_agent_run_for_project(project_id, run_id)


__all__ = ["get_run", "list_runs"]
