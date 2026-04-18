"""Evidence and compare contract models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class EvidenceCard(_ContractModel):
    id: Optional[str] = Field(
        default=None,
        description="Stable evidence card identifier when persisted",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Owning project identifier when the card belongs to a project",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread identifier when the card belongs to a conversation",
    )
    source_name: str = Field(..., description="Display name of the source")
    source_id: str = Field(..., description="Stable source identifier")
    page_no: Optional[int] = Field(
        ...,
        ge=1,
        description="1-based page number when the evidence is page anchored",
    )
    excerpt: str = Field(..., description="Concise excerpt used to support the answer")
    citation_text: str = Field(
        ...,
        description="User-facing citation string rendered in the answer UI",
    )
    internal_ref: str = Field(
        ...,
        description="Internal stable reference used for source jumps and traceability",
    )
    relevance_reason: Optional[str] = Field(
        default=None,
        description="Short explanation of why this evidence is relevant",
    )
    image_thumb: Optional[str] = Field(
        default=None,
        validation_alias="image_thumb_url",
        description="Optional thumbnail URL for visual evidence",
    )
    score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Retriever or reranker confidence for this evidence card",
    )


class MemoryUpdatePreview(_ContractModel):
    text: str = Field(..., description="Candidate memory text")
    type: str = Field(..., description="Candidate memory category")
    source_refs: list[str] = Field(
        default_factory=list,
        description="Evidence anchors supporting the candidate memory",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Confidence before memory governance is applied",
    )


class AskResponse(_ContractModel):
    answer: str = Field(..., description="Final answer text")
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence score for the final answer",
    )
    evidence_cards: list[EvidenceCard] = Field(
        default_factory=list,
        description="Evidence cards shown alongside the answer",
    )
    memory_updates: list[MemoryUpdatePreview] = Field(
        default_factory=list,
        description="Candidate memory updates emitted by the run",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Associated run identifier when tracing is enabled",
    )
    suggested_followups: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions",
    )
    mode: Literal["text", "visual", "mixed", "compare", "synthesis"] = Field(
        default="text",
        description="Selected answer mode for the request",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation thread identifier when the answer belongs to a thread",
    )


class CompareItem(_ContractModel):
    title: str = Field(..., description="Short label for the compare finding")
    detail: str = Field(..., description="Expanded description of the finding")
    source_refs: list[str] = Field(
        default_factory=list,
        description="Source references supporting the finding",
    )


class CompareSummary(_ContractModel):
    summary: str = Field(..., description="Top-level compare summary")
    similarities: list[CompareItem] = Field(
        default_factory=list,
        description="Shared characteristics across the compared sources",
    )
    differences: list[CompareItem] = Field(
        default_factory=list,
        description="Meaningful differences across the compared sources",
    )
    conflicts: list[CompareItem] = Field(
        default_factory=list,
        description="Conflicting statements or incompatible facts",
    )
    missing_items: list[CompareItem] = Field(
        default_factory=list,
        description="Items that appear to be missing from one side of the comparison",
    )
    human_review_required: list[CompareItem] = Field(
        default_factory=list,
        description="Findings that still require manual confirmation",
    )


__all__ = [
    "EvidenceCard",
    "MemoryUpdatePreview",
    "AskResponse",
    "CompareItem",
    "CompareSummary",
]
