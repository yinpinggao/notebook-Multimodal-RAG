from __future__ import annotations

import pytest

from open_notebook.agent_harness import trace_store
from open_notebook.agent_harness.run_manager import create_project_run
from open_notebook.agent_harness.trace_store import load_agent_run, save_agent_run
from open_notebook.domain.runs import AgentRun


def _singleton_row(record_id: str, payload: dict) -> dict:
    return {
        **payload,
        "id": record_id,
        "created": "2026-04-19T10:00:00Z",
        "updated": "2026-04-19T10:00:01Z",
    }


def _build_run(run_id: str = "run:demo") -> AgentRun:
    return AgentRun(
        id=run_id,
        project_id="project:demo",
        run_type="ask",
        status="queued",
        input_summary="项目证据问答",
        selected_skill="answer_with_evidence",
        input_json={"question": "这个项目的主要结论是什么？"},
        created_at="2026-04-19T10:00:00Z",
        started_at=None,
        completed_at=None,
        tool_calls=[],
        evidence_reads=[],
        memory_writes=[],
        outputs=[],
        steps=[],
        failure_reason=None,
    )


@pytest.mark.asyncio
async def test_save_agent_run_preserves_public_id(monkeypatch: pytest.MonkeyPatch):
    run = _build_run()

    async def fake_upsert_singleton(record_id: str, data: dict) -> dict:
        return _singleton_row(record_id, data)

    monkeypatch.setattr(
        trace_store.seekdb_business_store,
        "upsert_singleton",
        fake_upsert_singleton,
    )

    saved = await save_agent_run(run)

    assert saved.id == "run:demo"
    assert saved.project_id == "project:demo"


@pytest.mark.asyncio
async def test_load_agent_run_restores_public_id(monkeypatch: pytest.MonkeyPatch):
    run = _build_run("run:load")

    async def fake_get_singleton(record_id: str) -> dict:
        return _singleton_row(record_id, run.model_dump(mode="json"))

    monkeypatch.setattr(
        trace_store.seekdb_business_store,
        "get_singleton",
        fake_get_singleton,
    )

    loaded = await load_agent_run("run:load")

    assert loaded is not None
    assert loaded.id == "run:load"
    assert loaded.project_id == "project:demo"


@pytest.mark.asyncio
async def test_create_project_run_handles_singleton_metadata_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
):
    stored_rows: dict[str, dict] = {}

    async def fake_upsert_singleton(record_id: str, data: dict) -> dict:
        current = stored_rows.get(record_id)
        created = current["created"] if current else "2026-04-19T10:00:00Z"
        updated = "2026-04-19T10:00:01Z"
        stored_rows[record_id] = {
            "payload": dict(data),
            "created": created,
            "updated": updated,
        }
        return {
            **data,
            "id": record_id,
            "created": created,
            "updated": updated,
        }

    async def fake_get_singleton(record_id: str) -> dict:
        row = stored_rows.get(record_id)
        if not row:
            return {}
        return {
            **row["payload"],
            "id": record_id,
            "created": row["created"],
            "updated": row["updated"],
        }

    monkeypatch.setattr(
        trace_store.seekdb_business_store,
        "upsert_singleton",
        fake_upsert_singleton,
    )
    monkeypatch.setattr(
        trace_store.seekdb_business_store,
        "get_singleton",
        fake_get_singleton,
    )

    run = await create_project_run(
        "project:demo",
        run_type="ask",
        input_json={"question": "现在有哪些关键证据？"},
    )

    assert run.id.startswith("run:")
    assert run.project_id == "project:demo"
    assert run.selected_skill == "answer_with_evidence"
    assert len(run.steps) == 1
    assert run.steps[0].type == "plan"
