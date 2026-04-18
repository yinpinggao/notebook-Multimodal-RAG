"""Project compare contract models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.evidence import CompareSummary


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


ProjectCompareMode = Literal["general", "requirements", "risks", "timeline"]
ProjectCompareStatus = Literal["queued", "running", "completed", "failed"]


class ProjectCompareRecord(_ContractModel):
    id: str = Field(..., description="Stable compare record identifier")
    project_id: str = Field(..., description="Owning project identifier")
    compare_mode: ProjectCompareMode = Field(
        default="general",
        description="Selected compare mode",
    )
    source_a_id: str = Field(..., description="Left-side source identifier")
    source_b_id: str = Field(..., description="Right-side source identifier")
    source_a_title: str = Field(..., description="Left-side source title")
    source_b_title: str = Field(..., description="Right-side source title")
    status: ProjectCompareStatus = Field(
        default="queued",
        description="Current compare lifecycle status",
    )
    command_id: Optional[str] = Field(
        default=None,
        description="Associated async command identifier when queued",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Last error message when compare generation fails",
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    result: Optional[CompareSummary] = Field(
        default=None,
        description="Structured compare result once available",
    )


class ProjectCompareCreateResponse(_ContractModel):
    compare_id: str = Field(..., description="Stable compare record identifier")
    status: ProjectCompareStatus = Field(..., description="Queued compare status")
    command_id: Optional[str] = Field(
        default=None,
        description="Associated async command identifier when queued",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Associated run identifier for trace inspection",
    )


class ProjectCompareExportResponse(_ContractModel):
    compare_id: str = Field(..., description="Stable compare record identifier")
    format: Literal["markdown"] = Field(
        default="markdown",
        description="Export format",
    )
    content: str = Field(..., description="Exported compare report content")


__all__ = [
    "ProjectCompareMode",
    "ProjectCompareStatus",
    "ProjectCompareRecord",
    "ProjectCompareCreateResponse",
    "ProjectCompareExportResponse",
]
