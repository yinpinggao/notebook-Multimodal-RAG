from __future__ import annotations

from open_notebook.domain.artifacts import ArtifactType
from open_notebook.exceptions import InvalidInputError
from open_notebook.project_os.artifact_service import ArtifactSourceSnapshot
from open_notebook.project_os.defense_service import (
    build_defense_outline_markdown,
    build_judge_questions_markdown,
)


async def generate_defense_artifact(
    artifact_type: ArtifactType,
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    if artifact_type == "defense_outline":
        return build_defense_outline_markdown(title=title, snapshot=snapshot)
    if artifact_type == "judge_questions":
        return build_judge_questions_markdown(title=title, snapshot=snapshot)

    raise InvalidInputError(f"Unsupported defense artifact type: {artifact_type}")


__all__ = ["generate_defense_artifact"]
