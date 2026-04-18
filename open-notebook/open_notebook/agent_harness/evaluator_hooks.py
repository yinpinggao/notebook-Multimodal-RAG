from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.domain.evidence import AskResponse
from open_notebook.domain.memory import MemoryRecord

EvalMetricName = Literal[
    "evidence_faithfulness",
    "compare_consistency",
    "memory_source_coverage",
]
EvalStatus = Literal["passed", "failed", "unavailable"]


class EvalMetricResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: EvalMetricName
    label: str
    status: EvalStatus
    score: float | None = None
    threshold: float | None = None
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


def _round_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 2)


def evaluate_evidence_faithfulness(
    response: AskResponse | None,
) -> EvalMetricResult:
    if not response:
        return EvalMetricResult(
            metric="evidence_faithfulness",
            label="Evidence Faithfulness",
            status="unavailable",
            summary="当前项目还没有可评测的问答结果。",
            details={},
        )

    evidence_cards = response.evidence_cards or []
    cited_cards = [
        card
        for card in evidence_cards
        if card.source_name and card.citation_text and card.internal_ref
    ]
    score = _round_ratio(len(cited_cards), len(evidence_cards))
    status: EvalStatus = "passed" if evidence_cards and score >= 0.8 else "failed"
    if not evidence_cards:
        status = "failed"

    return EvalMetricResult(
        metric="evidence_faithfulness",
        label="Evidence Faithfulness",
        status=status,
        score=score,
        threshold=0.8,
        summary=(
            "回答已经附上足够证据。"
            if status == "passed"
            else "回答的证据卡片不足，或引用字段还不完整。"
        ),
        details={
            "answer_length": len(response.answer),
            "evidence_card_count": len(evidence_cards),
            "cited_card_count": len(cited_cards),
            "thread_id": response.thread_id,
            "run_id": response.run_id,
        },
    )


def evaluate_compare_consistency(
    compare: ProjectCompareRecord | None,
) -> EvalMetricResult:
    if not compare or not compare.result:
        return EvalMetricResult(
            metric="compare_consistency",
            label="Compare Consistency",
            status="unavailable",
            summary="当前项目还没有完成态的对比结果。",
            details={},
        )

    items = [
        *compare.result.similarities,
        *compare.result.differences,
        *compare.result.conflicts,
        *compare.result.missing_items,
        *compare.result.human_review_required,
    ]
    sourced_items = [item for item in items if item.source_refs]
    score = _round_ratio(len(sourced_items), len(items))
    status: EvalStatus = (
        "passed"
        if compare.status == "completed" and items and score >= 0.7
        else "failed"
    )

    return EvalMetricResult(
        metric="compare_consistency",
        label="Compare Consistency",
        status=status,
        score=score,
        threshold=0.7,
        summary=(
            "对比结果已经带上较完整的结构化证据。"
            if status == "passed"
            else "对比结果还不够稳定，或差异项缺少来源锚点。"
        ),
        details={
            "compare_id": compare.id,
            "compare_mode": compare.compare_mode,
            "status": compare.status,
            "finding_count": len(items),
            "sourced_finding_count": len(sourced_items),
        },
    )


def evaluate_memory_source_coverage(
    memories: list[MemoryRecord],
) -> EvalMetricResult:
    if not memories:
        return EvalMetricResult(
            metric="memory_source_coverage",
            label="Memory Source Coverage",
            status="unavailable",
            summary="当前项目还没有长期记忆记录。",
            details={},
        )

    covered = [memory for memory in memories if memory.source_refs]
    score = _round_ratio(len(covered), len(memories))
    status: EvalStatus = "passed" if score >= 1.0 else "failed"

    return EvalMetricResult(
        metric="memory_source_coverage",
        label="Memory Source Coverage",
        status=status,
        score=score,
        threshold=1.0,
        summary=(
            "长期记忆都带上了 source refs。"
            if status == "passed"
            else "仍有长期记忆没有 source refs，回溯链不完整。"
        ),
        details={
            "memory_count": len(memories),
            "covered_memory_count": len(covered),
        },
    )


__all__ = [
    "EvalMetricResult",
    "evaluate_compare_consistency",
    "evaluate_evidence_faithfulness",
    "evaluate_memory_source_coverage",
]
