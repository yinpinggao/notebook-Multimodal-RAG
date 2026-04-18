from open_notebook.agent_harness.evaluator_hooks import (
    evaluate_compare_consistency,
    evaluate_evidence_faithfulness,
    evaluate_memory_source_coverage,
)
from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.domain.evidence import AskResponse, EvidenceCard
from open_notebook.domain.memory import MemoryRecord, SourceReference


def test_evaluate_evidence_faithfulness_passes_at_threshold():
    response = AskResponse(
        answer="结论成立。",
        confidence=0.82,
        evidence_cards=[
            EvidenceCard(
                source_name="评分标准",
                source_id=f"source:{idx}",
                page_no=1,
                excerpt="证据片段",
                citation_text="评分标准，第 1 页",
                internal_ref=f"source:{idx}#p1",
            )
            for idx in range(4)
        ]
        + [
            EvidenceCard(
                source_name="",
                source_id="source:missing",
                page_no=None,
                excerpt="缺失引用字段",
                citation_text="",
                internal_ref="",
            )
        ],
        memory_updates=[],
        run_id="run:1",
        suggested_followups=[],
        mode="mixed",
        thread_id="thread:1",
    )

    result = evaluate_evidence_faithfulness(response)

    assert result.status == "passed"
    assert result.score == 0.8
    assert result.details["evidence_card_count"] == 5


def test_evaluate_compare_consistency_is_unavailable_without_result():
    compare = ProjectCompareRecord(
        id="compare:1",
        project_id="project:demo",
        compare_mode="requirements",
        source_a_id="source:a",
        source_b_id="source:b",
        source_a_title="评分标准",
        source_b_title="方案说明",
        status="completed",
        command_id=None,
        error_message=None,
        created_at="2026-04-19T08:00:00Z",
        updated_at="2026-04-19T08:01:00Z",
        result=None,
    )

    result = evaluate_compare_consistency(compare)

    assert result.status == "unavailable"
    assert result.score is None


def test_evaluate_memory_source_coverage_fails_when_refs_are_missing():
    memories = [
        MemoryRecord(
            id="memory:1",
            scope="project",
            type="fact",
            text="评委最看重证据链。",
            confidence=0.9,
            freshness="2026-04-19T08:00:00Z",
            source_refs=[
                SourceReference(
                    source_id="source:1",
                    source_name="评分标准",
                    page_no=1,
                    internal_ref="source:1#p1",
                    citation_text="评分标准，第 1 页",
                )
            ],
            status="accepted",
            decay_policy="normal",
            conflict_group=None,
        ),
        MemoryRecord(
            id="memory:2",
            scope="project",
            type="risk",
            text="视觉材料解释还不稳。",
            confidence=0.72,
            freshness="2026-04-19T08:05:00Z",
            source_refs=[],
            status="draft",
            decay_policy="normal",
            conflict_group=None,
        ),
    ]

    result = evaluate_memory_source_coverage(memories)

    assert result.status == "failed"
    assert result.score == 0.5
    assert result.details["covered_memory_count"] == 1
