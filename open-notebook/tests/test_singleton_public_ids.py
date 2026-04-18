from __future__ import annotations

import pytest

from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.domain.evidence import CompareSummary
from open_notebook.domain.memory import SourceReference
from open_notebook.memory_center import powermem_adapter
from open_notebook.memory_center.powermem_adapter import (
    StoredMemoryRecord,
    load_stored_project_memory,
    save_project_memory,
)
from open_notebook.project_os import artifact_service, compare_service
from open_notebook.project_os.artifact_service import (
    ArtifactSourceSnapshot,
    StoredArtifactRecord,
    load_stored_project_artifact,
    save_project_artifact,
)
from open_notebook.project_os.compare_service import (
    load_project_compare,
    save_project_compare,
)


def _singleton_row(record_id: str, payload: dict) -> dict:
    return {
        **payload,
        "id": record_id,
        "created": "2026-04-19T12:00:00Z",
        "updated": "2026-04-19T12:00:01Z",
    }


@pytest.mark.asyncio
async def test_compare_singleton_roundtrip_preserves_public_id(
    monkeypatch: pytest.MonkeyPatch,
):
    record = ProjectCompareRecord(
        id="cmp:demo",
        project_id="project:demo",
        compare_mode="general",
        source_a_id="source:a",
        source_b_id="source:b",
        source_a_title="A",
        source_b_title="B",
        status="completed",
        created_at="2026-04-19T12:00:00Z",
        updated_at="2026-04-19T12:00:01Z",
        result=CompareSummary(summary="done"),
    )

    async def fake_upsert_singleton(record_id: str, data: dict) -> dict:
        return _singleton_row(record_id, data)

    async def fake_get_singleton(record_id: str) -> dict:
        return _singleton_row(record_id, record.model_dump(mode="json"))

    monkeypatch.setattr(
        compare_service.seekdb_business_store,
        "upsert_singleton",
        fake_upsert_singleton,
    )
    monkeypatch.setattr(
        compare_service.seekdb_business_store,
        "get_singleton",
        fake_get_singleton,
    )

    saved = await save_project_compare(record)
    loaded = await load_project_compare("cmp:demo")

    assert saved.id == "cmp:demo"
    assert loaded is not None
    assert loaded.id == "cmp:demo"


@pytest.mark.asyncio
async def test_memory_singleton_roundtrip_preserves_public_id(
    monkeypatch: pytest.MonkeyPatch,
):
    record = StoredMemoryRecord(
        id="memory:demo",
        project_id="project:demo",
        scope="project",
        type="fact",
        text="Demo memory",
        confidence=0.9,
        source_refs=[
            SourceReference(
                source_id="source:a",
                source_name="A",
                internal_ref="source:a#p1",
                citation_text="A p1",
            )
        ],
        status="accepted",
        created_at="2026-04-19T12:00:00Z",
        updated_at="2026-04-19T12:00:01Z",
    )

    async def fake_upsert_singleton(record_id: str, data: dict) -> dict:
        return _singleton_row(record_id, data)

    async def fake_get_singleton(record_id: str) -> dict:
        return _singleton_row(record_id, record.model_dump(mode="json"))

    monkeypatch.setattr(
        powermem_adapter.seekdb_business_store,
        "upsert_singleton",
        fake_upsert_singleton,
    )
    monkeypatch.setattr(
        powermem_adapter.seekdb_business_store,
        "get_singleton",
        fake_get_singleton,
    )

    saved = await save_project_memory(record)
    loaded = await load_stored_project_memory("memory:demo")

    assert saved.id == "memory:demo"
    assert loaded is not None
    assert loaded.id == "memory:demo"


@pytest.mark.asyncio
async def test_artifact_singleton_roundtrip_preserves_public_id(
    monkeypatch: pytest.MonkeyPatch,
):
    record = StoredArtifactRecord(
        id="artifact:demo",
        project_id="project:demo",
        artifact_type="diff_report",
        title="Demo Diff",
        content_md="# Demo",
        source_refs=["source:a#p1"],
        created_by_run_id="run:demo",
        created_at="2026-04-19T12:00:00Z",
        updated_at="2026-04-19T12:00:01Z",
        status="ready",
        origin_kind="compare",
        origin_id="cmp:demo",
        source_snapshot=ArtifactSourceSnapshot(
            origin_kind="compare",
            origin_id="cmp:demo",
            label="Demo compare",
            summary="Demo summary",
        ),
    )

    async def fake_upsert_singleton(record_id: str, data: dict) -> dict:
        return _singleton_row(record_id, data)

    async def fake_get_singleton(record_id: str) -> dict:
        return _singleton_row(record_id, record.model_dump(mode="json"))

    monkeypatch.setattr(
        artifact_service.seekdb_business_store,
        "upsert_singleton",
        fake_upsert_singleton,
    )
    monkeypatch.setattr(
        artifact_service.seekdb_business_store,
        "get_singleton",
        fake_get_singleton,
    )

    saved = await save_project_artifact(record)
    loaded = await load_stored_project_artifact("artifact:demo")

    assert saved.id == "artifact:demo"
    assert loaded is not None
    assert loaded.id == "artifact:demo"
