"""Artifact contract models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ArtifactRecord(_ContractModel):
    id: str = Field(..., description="Stable artifact identifier")
    project_id: str = Field(..., description="Owning project identifier")
    artifact_type: Literal[
        "project_summary",
        "literature_review",
        "diff_report",
        "risk_list",
        "defense_outline",
        "judge_questions",
        "qa_cards",
        "presentation_script",
        "podcast",
    ] = Field(
        ...,
        validation_alias="type",
        description="Artifact type",
    )
    title: str = Field(..., description="Artifact display title")
    content_md: str = Field(
        ...,
        validation_alias="content_markdown",
        description="Persisted markdown content for the artifact",
    )
    source_refs: list[str] = Field(
        default_factory=list,
        description="Source references supporting the artifact",
    )
    created_by_run_id: str = Field(
        ...,
        description="Run identifier that created the artifact",
    )
    created_at: str = Field(..., description="Artifact creation timestamp")
    updated_at: str = Field(..., description="Artifact update timestamp")
    status: Literal["draft", "ready", "archived"] = Field(
        default="draft",
        description="Artifact lifecycle status",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Originating thread identifier when generated from a conversation",
    )


__all__ = ["ArtifactRecord"]
