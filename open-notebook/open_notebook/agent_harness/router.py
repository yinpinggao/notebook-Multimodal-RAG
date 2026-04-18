from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from open_notebook.agent_harness.skill_registry import get_skill_for_run_type


@dataclass(frozen=True)
class RouteDecision:
    selected_skill: str
    planning_mode: str
    reason: str


def route_project_task(run_type: str, input_json: dict[str, Any] | None = None) -> RouteDecision:
    skill = get_skill_for_run_type(run_type)
    if run_type == "ask":
        return RouteDecision(
            selected_skill=skill.name,
            planning_mode="direct",
            reason="Simple ask requests can route directly to the evidence skill.",
        )

    return RouteDecision(
        selected_skill=skill.name,
        planning_mode="targeted",
        reason="This task maps to a dedicated project skill.",
    )


__all__ = ["RouteDecision", "route_project_task"]
