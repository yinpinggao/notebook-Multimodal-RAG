"""Agent wrappers for project workflows."""

from .compare_agent import compare_project_sources
from .defense_coach_agent import generate_defense_artifact
from .synthesis_agent import generate_synthesis_artifact

__all__ = [
    "compare_project_sources",
    "generate_defense_artifact",
    "generate_synthesis_artifact",
]
