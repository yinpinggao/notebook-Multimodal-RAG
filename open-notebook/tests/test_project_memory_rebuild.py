from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.memory import MemoryRecord, SourceReference
from open_notebook.memory_center.memory_resolver import merge_memory_record
from open_notebook.memory_center.memory_writer import rebuild_project_memories


def _source_ref(source_id: str, internal_ref: str) -> SourceReference:
    return SourceReference(
        source_id=source_id,
        source_name=source_id,
        page_no=1,
        internal_ref=internal_ref,
        citation_text=internal_ref,
    )


def _memory_record(
    memory_id: str,
    *,
    text: str,
    status: str = "draft",
    source_refs: list[SourceReference] | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        scope="project",
        type="fact",
        text=text,
        confidence=0.8,
        freshness="2026-04-18T12:00:00Z",
        source_refs=source_refs or [_source_ref("source:1", "source:1#p1")],
        status=status,
        decay_policy="weak",
    )


def test_merge_memory_record_preserves_manual_text_for_accepted_memory():
    existing = _memory_record(
        "mem:demo",
        text="人工修订后的记忆文本",
        status="accepted",
        source_refs=[_source_ref("source:1", "source:1#p1")],
    )
    candidate = _memory_record(
        "mem:demo",
        text="机器重新抽取的候选文本",
        status="draft",
        source_refs=[_source_ref("source:2", "source:2#p4")],
    )

    merged = merge_memory_record(existing, candidate)

    assert merged.status == "accepted"
    assert merged.text == "人工修订后的记忆文本"
    assert [ref.internal_ref for ref in merged.source_refs] == [
        "source:1#p1",
        "source:2#p4",
    ]


@pytest.mark.asyncio
@patch("open_notebook.memory_center.memory_writer.mark_project_memory_status", new_callable=AsyncMock)
@patch("open_notebook.memory_center.memory_writer.save_project_memory_record", new_callable=AsyncMock)
@patch("open_notebook.memory_center.memory_writer.list_project_memories", new_callable=AsyncMock)
@patch("open_notebook.memory_center.memory_writer.collect_project_memory_candidates", new_callable=AsyncMock)
async def test_rebuild_project_memories_deprecates_stale_draft(
    mock_collect_candidates,
    mock_list_memories,
    mock_save_memory,
    mock_mark_status,
):
    stale_record = _memory_record(
        "mem:stale",
        text="旧候选记忆",
        status="draft",
    )
    mock_collect_candidates.return_value = []
    mock_list_memories.return_value = [stale_record]

    async def _save_side_effect(
        project_id: str,
        record: MemoryRecord,
        *,
        origin: str = "rebuild",
    ) -> MemoryRecord:
        return record

    mock_save_memory.side_effect = _save_side_effect

    stored_records = await rebuild_project_memories(
        "project:demo",
        command_id="command:memory:1",
    )

    assert len(stored_records) == 1
    assert stored_records[0].id == "mem:stale"
    assert stored_records[0].status == "deprecated"

    _, saved_record = mock_save_memory.await_args.args
    assert saved_record.status == "deprecated"
    assert mock_save_memory.await_args.kwargs == {"origin": "rebuild"}
    mock_mark_status.assert_awaited_once_with(
        "project:demo",
        "completed",
        command_id="command:memory:1",
        error_message=None,
    )
