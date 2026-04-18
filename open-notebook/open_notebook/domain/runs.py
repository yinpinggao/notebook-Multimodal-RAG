"""Run tracing contract models."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AgentStep(_ContractModel):
    id: str = Field(..., description="Stable step identifier")
    run_id: Optional[str] = Field(
        default=None,
        description="Owning run identifier when the step is persisted independently",
    )
    step_index: int = Field(
        ...,
        ge=0,
        validation_alias="index",
        description="0-based step index within the run",
    )
    agent_name: Optional[str] = Field(
        default=None,
        description="Agent or capability name responsible for the step",
    )
    title: str = Field(..., description="User-facing step title")
    type: Literal[
        "plan",
        "tool_call",
        "evidence_read",
        "memory_write",
        "artifact_write",
        "answer",
        "compare",
        "system",
    ] = Field(..., description="Step category")
    status: Literal["queued", "running", "completed", "failed", "skipped"] = Field(
        ...,
        description="Step execution status",
    )
    started_at: Optional[str] = Field(
        default=None,
        description="Step start timestamp",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Step completion timestamp",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Tool name when the step is a tool call",
    )
    input_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured step input payload when trace data is captured",
    )
    output_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured step output payload when trace data is captured",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references read during the step",
    )
    memory_refs: list[str] = Field(
        default_factory=list,
        description="Memory record identifiers touched by the step",
    )
    output_refs: list[str] = Field(
        default_factory=list,
        description="Output identifiers produced by the step",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message when the step fails",
    )


class AgentRun(_ContractModel):
    id: str = Field(..., description="Stable run identifier")
    project_id: str = Field(..., description="Owning project identifier")
    status: Literal[
        "queued",
        "running",
        "waiting_review",
        "completed",
        "failed",
        "cancelled",
    ] = Field(..., description="Run lifecycle status")
    run_type: Literal[
        "ask",
        "compare",
        "artifact",
        "memory_rebuild",
        "overview_rebuild",
        "ingest",
        "unknown",
    ] = Field(
        ...,
        validation_alias="task_type",
        description="High-level run type",
    )
    input_summary: Optional[str] = Field(
        default=None,
        description="User-facing summary of the run input",
    )
    selected_skill: Optional[str] = Field(
        default=None,
        description="Selected skill or capability name",
    )
    input_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured run input payload when trace data is captured",
    )
    output_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured run output payload when trace data is captured",
    )
    created_at: str = Field(..., description="Run creation timestamp")
    started_at: Optional[str] = Field(
        default=None,
        description="Run start timestamp",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Run completion timestamp",
    )
    tool_calls: list[str] = Field(
        default_factory=list,
        description="Tool calls issued during the run",
    )
    evidence_reads: list[str] = Field(
        default_factory=list,
        description="Evidence references read during the run",
    )
    memory_writes: list[str] = Field(
        default_factory=list,
        description="Memory record identifiers written during the run",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="Output identifiers produced by the run",
    )
    steps: list[AgentStep] = Field(
        default_factory=list,
        description="Detailed run steps in execution order",
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Failure reason when the run does not complete successfully",
    )


__all__ = ["AgentStep", "AgentRun"]
