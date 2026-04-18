from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from commands.eval_commands import ProjectEvalInput, run_project_eval_command
from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.domain.evidence import (
    AskResponse,
    CompareItem,
    CompareSummary,
    EvidenceCard,
)
from open_notebook.domain.memory import MemoryRecord, SourceReference


@pytest.mark.asyncio
@patch("commands.eval_commands.project_memory_service.list_memory_records", new_callable=AsyncMock)
@patch("commands.eval_commands.project_compare_service.list_project_compares", new_callable=AsyncMock)
@patch("commands.eval_commands.project_evidence_service.get_project_thread", new_callable=AsyncMock)
@patch("commands.eval_commands.project_evidence_service.list_project_threads", new_callable=AsyncMock)
@patch("commands.eval_commands.project_workspace_service.get_project", new_callable=AsyncMock)
async def test_run_project_eval_command_uses_latest_thread_and_completed_compare(
    mock_get_project,
    mock_list_project_threads,
    mock_get_project_thread,
    mock_list_project_compares,
    mock_list_memory_records,
):
    mock_get_project.return_value = SimpleNamespace(id="project:demo")
    mock_list_project_threads.return_value = [SimpleNamespace(id="thread:latest")]
    mock_get_project_thread.return_value = SimpleNamespace(
        id="thread:latest",
        latest_response=AskResponse(
            answer="结论成立。",
            confidence=0.86,
            evidence_cards=[
                EvidenceCard(
                    source_name="评分标准",
                    source_id="source:1",
                    page_no=1,
                    excerpt="证据片段",
                    citation_text="评分标准，第 1 页",
                    internal_ref="source:1#p1",
                )
            ],
            memory_updates=[],
            run_id="run:ask:1",
            suggested_followups=[],
            mode="mixed",
            thread_id="thread:latest",
        ),
    )
    mock_list_project_compares.return_value = [
        ProjectCompareRecord(
            id="compare:latest",
            project_id="project:demo",
            compare_mode="requirements",
            source_a_id="source:1",
            source_b_id="source:2",
            source_a_title="评分标准",
            source_b_title="方案说明",
            status="completed",
            command_id="command:compare:1",
            error_message=None,
            created_at="2026-04-19T08:00:00Z",
            updated_at="2026-04-19T08:01:00Z",
            result=CompareSummary(
                summary="结构一致。",
                similarities=[],
                differences=[
                    CompareItem(
                        title="交付节奏不同",
                        detail="方案说明补充了阶段拆解。",
                        source_refs=["source:2#p2"],
                    )
                ],
                conflicts=[],
                missing_items=[],
                human_review_required=[],
            ),
        )
    ]
    mock_list_memory_records.return_value = [
        MemoryRecord(
            id="memory:1",
            scope="project",
            type="fact",
            text="评委看重证据链。",
            confidence=0.91,
            freshness="2026-04-19T08:02:00Z",
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
        )
    ]

    output = await run_project_eval_command(ProjectEvalInput(project_id="project:demo"))

    assert output.success is True
    assert output.project_id == "project:demo"
    assert output.thread_id == "thread:latest"
    assert output.compare_id == "compare:latest"
    assert output.passed_metrics == 3
    assert output.available_metrics == 3
    assert output.summary == "当前项目的最小评测全部通过。"
