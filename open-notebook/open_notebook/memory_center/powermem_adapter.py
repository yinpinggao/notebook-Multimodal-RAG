from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.memory import MemoryRecord
from open_notebook.exceptions import NotFoundError
from open_notebook.seekdb import seekdb_business_store, seekdb_client


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoredMemoryRecord(MemoryRecord):
    project_id: str
    created_at: str
    updated_at: str
    origin: Literal["rebuild", "manual"] = "rebuild"


class ProjectMemoryIndex(_Model):
    project_id: str
    memory_ids: list[str] = Field(default_factory=list)


class ProjectMemoryStatus(_Model):
    project_id: str
    status: Literal["idle", "queued", "running", "completed", "failed"] = "idle"
    command_id: Optional[str] = None
    error_message: Optional[str] = None
    generated_at: Optional[str] = None


def project_memory_record_id(memory_id: str) -> str:
    return f"project_memory:{memory_id}"


def project_memory_index_record_id(project_id: str) -> str:
    return f"project_memory_index:{project_id}"


def project_memory_status_record_id(project_id: str) -> str:
    return f"project_memory_status:{project_id}"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _strip_singleton_metadata(data: dict) -> dict:
    return {
        key: value
        for key, value in data.items()
        if key not in {"id", "created", "updated"}
    }


def _dedupe_ids(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
    return deduped


def _to_public_record(record: StoredMemoryRecord) -> MemoryRecord:
    return MemoryRecord.model_validate(
        record.model_dump(mode="json", exclude={"project_id", "created_at", "updated_at", "origin"})
    )


async def _load_project_memory_index(project_id: str) -> ProjectMemoryIndex:
    data = await seekdb_business_store.get_singleton(
        project_memory_index_record_id(project_id)
    )
    if not data:
        return ProjectMemoryIndex(project_id=project_id)
    return ProjectMemoryIndex.model_validate(_strip_singleton_metadata(data))


async def _save_project_memory_index(
    index: ProjectMemoryIndex,
) -> ProjectMemoryIndex:
    saved = await seekdb_business_store.upsert_singleton(
        project_memory_index_record_id(index.project_id),
        index.model_dump(mode="json"),
    )
    return ProjectMemoryIndex.model_validate(_strip_singleton_metadata(saved))


async def _register_project_memory(project_id: str, memory_id: str) -> None:
    index = await _load_project_memory_index(project_id)
    index.memory_ids = _dedupe_ids([memory_id, *index.memory_ids])
    await _save_project_memory_index(index)


async def _unregister_project_memory(project_id: str, memory_id: str) -> None:
    index = await _load_project_memory_index(project_id)
    index.memory_ids = [item for item in index.memory_ids if item != memory_id]
    await _save_project_memory_index(index)


async def save_project_memory(record: StoredMemoryRecord) -> StoredMemoryRecord:
    saved = await seekdb_business_store.upsert_singleton(
        project_memory_record_id(record.id),
        record.model_dump(mode="json"),
    )
    return StoredMemoryRecord.model_validate(_strip_singleton_metadata(saved))


async def load_stored_project_memory(memory_id: str) -> StoredMemoryRecord | None:
    data = await seekdb_business_store.get_singleton(
        project_memory_record_id(memory_id)
    )
    if not data:
        return None
    return StoredMemoryRecord.model_validate(_strip_singleton_metadata(data))


async def load_stored_project_memory_for_project(
    project_id: str,
    memory_id: str,
) -> StoredMemoryRecord:
    record = await load_stored_project_memory(memory_id)
    if not record or record.project_id != project_id:
        raise NotFoundError("Memory record not found")
    return record


def sort_memory_records(records: list[MemoryRecord]) -> list[MemoryRecord]:
    status_order = {"accepted": 0, "frozen": 1, "draft": 2, "deprecated": 3}
    type_order = {
        "fact": 0,
        "term": 1,
        "decision": 2,
        "risk": 3,
        "preference": 4,
        "question": 5,
    }

    return sorted(
        records,
        key=lambda item: (
            status_order.get(item.status, 99),
            type_order.get(item.type, 99),
            -(item.confidence or 0),
            item.text,
        ),
    )


async def list_project_memories(
    project_id: str,
    *,
    include_deprecated: bool = True,
) -> list[MemoryRecord]:
    index = await _load_project_memory_index(project_id)
    records: list[MemoryRecord] = []
    for memory_id in index.memory_ids:
        stored = await load_stored_project_memory(memory_id)
        if not stored or stored.project_id != project_id:
            continue
        public_record = _to_public_record(stored)
        if not include_deprecated and public_record.status == "deprecated":
            continue
        records.append(public_record)

    return sort_memory_records(records)


async def count_project_memories(project_id: str) -> int:
    records = await list_project_memories(project_id, include_deprecated=False)
    return len(records)


async def update_project_memory(
    project_id: str,
    memory_id: str,
    *,
    text: str | None = None,
    status: str | None = None,
    confidence: float | None = None,
    decay_policy: str | None = None,
) -> MemoryRecord:
    current = await load_stored_project_memory_for_project(project_id, memory_id)
    payload = current.model_dump(mode="json")

    if text is not None:
        payload["text"] = " ".join(str(text).strip().split())
    if status is not None:
        payload["status"] = status
    if confidence is not None:
        payload["confidence"] = confidence
    if decay_policy is not None:
        payload["decay_policy"] = decay_policy

    payload["updated_at"] = _utc_now()
    updated = await save_project_memory(StoredMemoryRecord.model_validate(payload))
    return _to_public_record(updated)


async def delete_project_memory(project_id: str, memory_id: str) -> None:
    await load_stored_project_memory_for_project(project_id, memory_id)
    await seekdb_client.execute(
        "DELETE FROM singleton_record WHERE id = %s",
        (project_memory_record_id(memory_id),),
    )
    await _unregister_project_memory(project_id, memory_id)


async def save_project_memory_record(
    project_id: str,
    record: MemoryRecord,
    *,
    origin: Literal["rebuild", "manual"] = "rebuild",
) -> MemoryRecord:
    existing = await load_stored_project_memory(record.id)
    now = _utc_now()
    stored = StoredMemoryRecord(
        **record.model_dump(mode="json"),
        project_id=project_id,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        origin=origin,
    )
    saved = await save_project_memory(stored)
    await _register_project_memory(project_id, record.id)
    return _to_public_record(saved)


async def load_project_memory_status(project_id: str) -> ProjectMemoryStatus:
    data = await seekdb_business_store.get_singleton(
        project_memory_status_record_id(project_id)
    )
    if not data:
        return ProjectMemoryStatus(project_id=project_id)
    return ProjectMemoryStatus.model_validate(_strip_singleton_metadata(data))


async def mark_project_memory_status(
    project_id: str,
    status: str,
    *,
    command_id: str | None = None,
    error_message: str | None = None,
) -> ProjectMemoryStatus:
    current = await load_project_memory_status(project_id)
    payload = current.model_dump(mode="json")
    payload["project_id"] = project_id
    payload["status"] = status
    payload["error_message"] = error_message
    if command_id is not None:
        payload["command_id"] = command_id
    if status == "completed":
        payload["generated_at"] = _utc_now()
    saved = await seekdb_business_store.upsert_singleton(
        project_memory_status_record_id(project_id),
        payload,
    )
    return ProjectMemoryStatus.model_validate(_strip_singleton_metadata(saved))


__all__ = [
    "ProjectMemoryIndex",
    "ProjectMemoryStatus",
    "StoredMemoryRecord",
    "count_project_memories",
    "delete_project_memory",
    "list_project_memories",
    "load_project_memory_status",
    "load_stored_project_memory",
    "load_stored_project_memory_for_project",
    "mark_project_memory_status",
    "project_memory_index_record_id",
    "project_memory_record_id",
    "project_memory_status_record_id",
    "save_project_memory_record",
    "sort_memory_records",
    "update_project_memory",
]
