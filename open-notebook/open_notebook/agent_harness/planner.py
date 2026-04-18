from __future__ import annotations

from typing import Any

from open_notebook.agent_harness.router import RouteDecision, route_project_task


def plan_project_task(run_type: str, input_json: dict[str, Any] | None = None) -> RouteDecision:
    return route_project_task(run_type, input_json=input_json)


__all__ = ["plan_project_task"]
