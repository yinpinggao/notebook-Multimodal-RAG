from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillSpec:
    name: str
    run_type: str
    description: str
    direct_routable: bool = True


_SKILLS: dict[str, SkillSpec] = {
    "ask": SkillSpec(
        name="answer_with_evidence",
        run_type="ask",
        description="Answer a project question with evidence cards and grounded citations.",
    ),
    "overview_rebuild": SkillSpec(
        name="build_project_overview",
        run_type="overview_rebuild",
        description="Build a project overview snapshot from current sources.",
    ),
    "compare": SkillSpec(
        name="compare_sources",
        run_type="compare",
        description="Compare two project sources and write a structured diff.",
    ),
    "artifact": SkillSpec(
        name="generate_artifact",
        run_type="artifact",
        description="Generate a project artifact from overview, compare, or thread evidence.",
    ),
    "memory_rebuild": SkillSpec(
        name="write_project_memory",
        run_type="memory_rebuild",
        description="Rebuild project long-term memory with governance rules.",
    ),
}


def get_skill_for_run_type(run_type: str) -> SkillSpec:
    try:
        return _SKILLS[run_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported run type for skill registry: {run_type}") from exc


def list_registered_skills() -> list[SkillSpec]:
    return list(_SKILLS.values())


__all__ = ["SkillSpec", "get_skill_for_run_type", "list_registered_skills"]
