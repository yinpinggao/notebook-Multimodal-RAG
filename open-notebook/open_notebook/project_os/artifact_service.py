from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.artifacts import (
    ArtifactOriginKind,
    ArtifactRecord,
    ArtifactType,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError
from open_notebook.seekdb import seekdb_business_store

ARTIFACT_LABELS: dict[ArtifactType, str] = {
    "project_summary": "项目综述",
    "literature_review": "文献综述",
    "diff_report": "差异报告",
    "risk_list": "风险清单",
    "defense_outline": "答辩提纲",
    "judge_questions": "评委问题清单",
    "qa_cards": "问答卡片",
    "presentation_script": "汇报讲稿",
    "podcast": "播客音频",
}

ARTIFACT_TYPES_BY_ORIGIN: dict[ArtifactOriginKind, tuple[ArtifactType, ...]] = {
    "overview": ("project_summary", "defense_outline", "judge_questions"),
    "compare": ("diff_report", "defense_outline", "judge_questions"),
    "thread": ("qa_cards", "defense_outline", "judge_questions"),
}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArtifactSourceBullet(_Model):
    title: str
    detail: str
    source_refs: list[str] = Field(default_factory=list)


class ArtifactSourceQAPair(_Model):
    question: str
    answer: str
    source_refs: list[str] = Field(default_factory=list)


class ArtifactSourceSnapshot(_Model):
    origin_kind: ArtifactOriginKind
    origin_id: Optional[str] = None
    label: str
    summary: str
    bullets: list[ArtifactSourceBullet] = Field(default_factory=list)
    qa_pairs: list[ArtifactSourceQAPair] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class StoredArtifactRecord(ArtifactRecord):
    source_snapshot: ArtifactSourceSnapshot


class ProjectArtifactIndex(_Model):
    project_id: str
    artifact_ids: list[str] = Field(default_factory=list)


def project_artifact_record_id(artifact_id: str) -> str:
    return f"project_artifact:{artifact_id}"


def project_artifact_index_record_id(project_id: str) -> str:
    return f"project_artifact_index:{project_id}"


def create_artifact_id() -> str:
    return f"artifact:{uuid4().hex[:12]}"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _strip_singleton_metadata(data: dict, *, public_id: str | None = None) -> dict:
    payload = {
        key: value for key, value in data.items() if key not in {"created", "updated"}
    }
    if public_id is None:
        payload.pop("id", None)
    else:
        payload["id"] = public_id
    return payload


def _dedupe_strings(values: list[str], *, limit: int | None = None) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
        if limit and len(deduped) >= limit:
            break
    return deduped


def validate_artifact_origin(
    artifact_type: ArtifactType,
    origin_kind: ArtifactOriginKind,
) -> None:
    supported_types = ARTIFACT_TYPES_BY_ORIGIN[origin_kind]
    if artifact_type not in supported_types:
        raise InvalidInputError(
            f"Artifact type {artifact_type} is not supported for {origin_kind} sources"
        )


def artifact_title_for_type(
    artifact_type: ArtifactType,
    *,
    label: str,
) -> str:
    base_label = " ".join(str(label or "").strip().split()) or "当前项目"
    return f"{base_label} {ARTIFACT_LABELS[artifact_type]}"


def artifact_type_label(artifact_type: ArtifactType) -> str:
    return ARTIFACT_LABELS[artifact_type]


def render_source_refs(refs: list[str], *, prefix: str = "source refs") -> str:
    deduped_refs = _dedupe_strings(refs, limit=8)
    if not deduped_refs:
        return ""
    return f"{prefix}: {', '.join(deduped_refs)}"


def artifact_source_summary_lines(
    snapshot: ArtifactSourceSnapshot,
    *,
    limit: int = 6,
) -> list[str]:
    lines: list[str] = []
    for bullet in snapshot.bullets[:limit]:
        lines.append(f"- **{bullet.title}**：{bullet.detail}")
        refs_line = render_source_refs(bullet.source_refs)
        if refs_line:
            lines.append(f"  - {refs_line}")
    if not lines and snapshot.summary:
        lines.append(f"- {snapshot.summary}")
    return lines


def _to_public_record(record: StoredArtifactRecord) -> ArtifactRecord:
    return ArtifactRecord.model_validate(
        record.model_dump(mode="json", exclude={"source_snapshot"})
    )


async def _load_project_artifact_index(project_id: str) -> ProjectArtifactIndex:
    data = await seekdb_business_store.get_singleton(
        project_artifact_index_record_id(project_id)
    )
    if not data:
        return ProjectArtifactIndex(project_id=project_id)
    return ProjectArtifactIndex.model_validate(_strip_singleton_metadata(data))


async def _save_project_artifact_index(
    index: ProjectArtifactIndex,
) -> ProjectArtifactIndex:
    saved = await seekdb_business_store.upsert_singleton(
        project_artifact_index_record_id(index.project_id),
        index.model_dump(mode="json"),
    )
    return ProjectArtifactIndex.model_validate(_strip_singleton_metadata(saved))


async def _register_project_artifact(project_id: str, artifact_id: str) -> None:
    index = await _load_project_artifact_index(project_id)
    artifact_ids = [artifact_id, *index.artifact_ids]
    index.artifact_ids = _dedupe_strings(artifact_ids)
    await _save_project_artifact_index(index)


async def save_project_artifact(
    record: StoredArtifactRecord,
) -> StoredArtifactRecord:
    saved = await seekdb_business_store.upsert_singleton(
        project_artifact_record_id(record.id),
        record.model_dump(mode="json"),
    )
    return StoredArtifactRecord.model_validate(
        _strip_singleton_metadata(saved, public_id=record.id)
    )


async def load_stored_project_artifact(
    artifact_id: str,
) -> StoredArtifactRecord | None:
    data = await seekdb_business_store.get_singleton(
        project_artifact_record_id(artifact_id)
    )
    if not data:
        return None
    return StoredArtifactRecord.model_validate(
        _strip_singleton_metadata(data, public_id=artifact_id)
    )


async def load_stored_project_artifact_for_project(
    project_id: str,
    artifact_id: str,
) -> StoredArtifactRecord:
    record = await load_stored_project_artifact(artifact_id)
    if not record or record.project_id != project_id:
        raise NotFoundError("Artifact not found")
    return record


async def load_project_artifact_for_project(
    project_id: str,
    artifact_id: str,
) -> ArtifactRecord:
    return _to_public_record(
        await load_stored_project_artifact_for_project(project_id, artifact_id)
    )


async def list_project_artifacts(
    project_id: str,
    *,
    limit: int = 50,
) -> list[ArtifactRecord]:
    index = await _load_project_artifact_index(project_id)
    records: list[ArtifactRecord] = []
    for artifact_id in index.artifact_ids:
        stored = await load_stored_project_artifact(artifact_id)
        if not stored or stored.project_id != project_id:
            continue
        records.append(_to_public_record(stored))

    records.sort(key=lambda item: item.updated_at, reverse=True)
    return records[:limit]


async def count_project_artifacts(project_id: str) -> int:
    artifacts = await list_project_artifacts(project_id, limit=1000)
    return len(
        [
            artifact
            for artifact in artifacts
            if artifact.status not in {"archived", "failed"}
        ]
    )


async def initialize_project_artifact(
    project_id: str,
    *,
    artifact_type: ArtifactType,
    origin_kind: ArtifactOriginKind,
    source_snapshot: ArtifactSourceSnapshot,
    created_by_run_id: str,
    origin_id: str | None = None,
    title: str | None = None,
    thread_id: str | None = None,
) -> ArtifactRecord:
    validate_artifact_origin(artifact_type, origin_kind)
    artifact_id = create_artifact_id()
    now = _utc_now()
    stored = StoredArtifactRecord(
        id=artifact_id,
        project_id=project_id,
        artifact_type=artifact_type,
        title=title or artifact_title_for_type(artifact_type, label=source_snapshot.label),
        content_md="",
        source_refs=_dedupe_strings(source_snapshot.source_refs),
        created_by_run_id=created_by_run_id,
        created_at=now,
        updated_at=now,
        status="queued",
        thread_id=thread_id,
        origin_kind=origin_kind,
        origin_id=origin_id,
        command_id=None,
        error_message=None,
        source_snapshot=source_snapshot,
    )
    saved = await save_project_artifact(stored)
    await _register_project_artifact(project_id, saved.id)
    return _to_public_record(saved)


async def update_project_artifact_source_snapshot(
    artifact_id: str,
    source_snapshot: ArtifactSourceSnapshot,
) -> ArtifactRecord:
    current = await load_stored_project_artifact(artifact_id)
    if not current:
        raise NotFoundError("Artifact not found")

    updated = StoredArtifactRecord(
        **{
            **current.model_dump(mode="json"),
            "source_snapshot": source_snapshot.model_dump(mode="json"),
            "source_refs": _dedupe_strings(source_snapshot.source_refs),
            "updated_at": _utc_now(),
        }
    )
    return _to_public_record(await save_project_artifact(updated))


async def mark_project_artifact_status(
    artifact_id: str,
    status: str,
    *,
    command_id: Optional[str] = None,
    error_message: Optional[str] = None,
    content_md: Optional[str] = None,
    source_refs: Optional[list[str]] = None,
    created_by_run_id: Optional[str] = None,
    title: Optional[str] = None,
) -> ArtifactRecord:
    current = await load_stored_project_artifact(artifact_id)
    if not current:
        raise NotFoundError("Artifact not found")

    payload = current.model_dump(mode="json")
    payload["status"] = status
    payload["error_message"] = error_message
    payload["updated_at"] = _utc_now()
    if command_id is not None:
        payload["command_id"] = command_id
    if content_md is not None:
        payload["content_md"] = content_md
    if source_refs is not None:
        payload["source_refs"] = _dedupe_strings(source_refs)
    if created_by_run_id is not None:
        payload["created_by_run_id"] = created_by_run_id
    if title is not None:
        payload["title"] = title

    saved = await save_project_artifact(StoredArtifactRecord.model_validate(payload))
    return _to_public_record(saved)


__all__ = [
    "ARTIFACT_LABELS",
    "ARTIFACT_TYPES_BY_ORIGIN",
    "ArtifactSourceBullet",
    "ArtifactSourceQAPair",
    "ArtifactSourceSnapshot",
    "ProjectArtifactIndex",
    "StoredArtifactRecord",
    "artifact_source_summary_lines",
    "artifact_title_for_type",
    "artifact_type_label",
    "count_project_artifacts",
    "create_artifact_id",
    "initialize_project_artifact",
    "list_project_artifacts",
    "load_project_artifact_for_project",
    "load_stored_project_artifact",
    "load_stored_project_artifact_for_project",
    "mark_project_artifact_status",
    "project_artifact_index_record_id",
    "project_artifact_record_id",
    "render_source_refs",
    "save_project_artifact",
    "update_project_artifact_source_snapshot",
    "validate_artifact_origin",
]
