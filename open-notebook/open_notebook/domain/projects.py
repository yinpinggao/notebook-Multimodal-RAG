"""Project workspace contract models.

These models define the product-facing project schemas used by the
Project Workspace layer. They are intentionally separate from the current
notebook persistence models so the application can adopt project-centric
contracts without forcing an immediate data migration.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProjectSummary(_ContractModel):
    id: str = Field(..., description="Stable project identifier")
    name: str = Field(..., description="Project display name")
    description: str = Field(
        default="",
        description="Short user-facing description of the project",
    )
    status: Literal["active", "archived"] = Field(
        default="active",
        description="Project lifecycle status",
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    source_count: int = Field(default=0, ge=0, description="Number of linked sources")
    artifact_count: int = Field(
        default=0,
        ge=0,
        description="Number of generated artifacts",
    )
    memory_count: int = Field(
        default=0,
        ge=0,
        description="Number of stored project memory records",
    )
    last_run_at: Optional[str] = Field(
        default=None,
        description="Timestamp of the most recent recorded run",
    )


class ProjectTimelineEvent(_ContractModel):
    id: str = Field(..., description="Stable timeline event identifier")
    title: str = Field(..., description="Short timeline event label")
    description: str = Field(
        default="",
        description="Expanded event description",
    )
    occurred_at: Optional[str] = Field(
        default=None,
        description="Timestamp or normalized date string for the event",
    )
    source_refs: list[str] = Field(
        default_factory=list,
        description="Source references supporting this timeline event",
    )


class RecentRunSummary(_ContractModel):
    id: str = Field(..., description="Run identifier")
    status: str = Field(..., description="Current run status")
    run_type: str = Field(
        ...,
        validation_alias="task_type",
        description="Run task type, such as ask or compare",
    )
    created_at: str = Field(..., description="Run creation timestamp")
    completed_at: Optional[str] = Field(
        default=None,
        description="Run completion timestamp when available",
    )


class RecentArtifactSummary(_ContractModel):
    id: str = Field(..., description="Artifact identifier")
    title: str = Field(..., description="Artifact display title")
    artifact_type: str = Field(
        ...,
        validation_alias="type",
        description="Artifact type",
    )
    created_at: str = Field(..., description="Artifact creation timestamp")
    created_by_run_id: Optional[str] = Field(
        default=None,
        description="Run that produced the artifact when available",
    )


class ProjectOverviewResponse(_ContractModel):
    project: ProjectSummary = Field(..., description="Core project summary")
    source_count: int = Field(default=0, ge=0, description="Source count snapshot")
    artifact_count: int = Field(
        default=0,
        ge=0,
        description="Artifact count snapshot",
    )
    memory_count: int = Field(
        default=0,
        ge=0,
        description="Memory count snapshot",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Extracted project themes or topic labels",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="High-signal extracted keywords",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Detected risks or open concerns",
    )
    timeline_events: list[ProjectTimelineEvent] = Field(
        default_factory=list,
        description="Normalized timeline events for the project",
    )
    recommended_questions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions for the user",
    )
    recent_runs: list[RecentRunSummary] = Field(
        default_factory=list,
        description="Recent run summaries shown on the overview page",
    )
    recent_artifacts: list[RecentArtifactSummary] = Field(
        default_factory=list,
        description="Recent artifacts shown on the overview page",
    )


__all__ = [
    "ProjectSummary",
    "ProjectTimelineEvent",
    "RecentRunSummary",
    "RecentArtifactSummary",
    "ProjectOverviewResponse",
]
