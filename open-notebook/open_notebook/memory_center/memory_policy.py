from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.memory import MemoryRecord, SourceReference

MemoryScope = Literal["project", "user"]
MemoryType = Literal["fact", "term", "decision", "risk", "preference", "question"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemoryCandidate(_Model):
    id: str
    scope: MemoryScope = "project"
    type: MemoryType
    text: str
    confidence: float = Field(..., ge=0, le=1)
    freshness: Optional[str] = None
    source_refs: list[SourceReference] = Field(default_factory=list)
    user_confirmed: bool = False
    conflict_group: Optional[str] = None


def normalize_memory_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def clamp_confidence(value: float) -> float:
    return round(min(max(float(value), 0.0), 1.0), 2)


def decay_policy_for_type(memory_type: MemoryType) -> Literal["strong", "normal", "weak"]:
    if memory_type in {"decision", "preference"}:
        return "strong"
    if memory_type in {"term", "fact"}:
        return "weak"
    return "normal"


def decide_memory_status(candidate: MemoryCandidate) -> Literal[
    "draft",
    "accepted",
    "frozen",
    "deprecated",
]:
    if candidate.user_confirmed and candidate.type in {"preference", "decision"}:
        return "accepted"

    return "draft"


def apply_memory_policy(candidate: MemoryCandidate) -> MemoryRecord:
    normalized_text = normalize_memory_text(candidate.text)
    return MemoryRecord(
        id=candidate.id,
        scope=candidate.scope,
        type=candidate.type,
        text=normalized_text,
        confidence=clamp_confidence(candidate.confidence),
        freshness=candidate.freshness,
        source_refs=candidate.source_refs,
        status=decide_memory_status(candidate),
        decay_policy=decay_policy_for_type(candidate.type),
        conflict_group=candidate.conflict_group,
    )


__all__ = [
    "MemoryCandidate",
    "apply_memory_policy",
    "clamp_confidence",
    "decay_policy_for_type",
    "normalize_memory_text",
]
