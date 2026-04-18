"""Memory governance contract models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SourceReference(_ContractModel):
    source_id: str = Field(..., description="Stable source identifier")
    source_name: Optional[str] = Field(
        default=None,
        description="Display name of the source when available",
    )
    page_no: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-based page number for document-backed references",
    )
    internal_ref: str = Field(
        ...,
        description="Internal stable reference used to locate the source evidence",
    )
    citation_text: Optional[str] = Field(
        default=None,
        description="User-facing citation string for this reference",
    )


class MemoryRecord(_ContractModel):
    id: str = Field(..., description="Stable memory record identifier")
    scope: Literal["project", "user"] = Field(
        ...,
        description="Memory scope",
    )
    type: Literal["fact", "term", "decision", "risk", "preference", "question"] = (
        Field(..., description="Memory record type")
    )
    text: str = Field(..., description="Normalized memory text")
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence after memory governance is applied",
    )
    freshness: Optional[str] = Field(
        default=None,
        description="Timestamp or freshness marker for the memory",
    )
    source_refs: list[SourceReference] = Field(
        ...,
        description="Evidence references supporting the memory",
    )
    status: Literal["draft", "accepted", "frozen", "deprecated"] = Field(
        ...,
        description="Current governance status",
    )
    decay_policy: Literal["strong", "normal", "weak"] = Field(
        default="normal",
        description="Retention policy for the memory",
    )
    conflict_group: Optional[str] = Field(
        default=None,
        description="Logical conflict group identifier for competing memories",
    )


__all__ = ["SourceReference", "MemoryRecord"]
