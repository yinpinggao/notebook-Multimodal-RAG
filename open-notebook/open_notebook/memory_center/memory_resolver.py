from __future__ import annotations

from collections import defaultdict

from open_notebook.domain.memory import MemoryRecord, SourceReference
from open_notebook.memory_center.memory_policy import normalize_memory_text


def _merge_source_refs(
    existing_refs: list[SourceReference],
    candidate_refs: list[SourceReference],
) -> list[SourceReference]:
    merged: list[SourceReference] = []
    seen: set[tuple[str, str]] = set()

    for ref in [*existing_refs, *candidate_refs]:
        key = (ref.source_id, ref.internal_ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)

    return merged


def merge_memory_record(
    existing: MemoryRecord | None,
    candidate: MemoryRecord,
) -> MemoryRecord:
    if not existing:
        return candidate

    if existing.status == "frozen":
        return existing

    payload = candidate.model_dump(mode="json")
    payload["source_refs"] = candidate.source_refs

    if existing.status in {"accepted", "deprecated"}:
        payload["status"] = existing.status
        payload["text"] = existing.text
        payload["source_refs"] = _merge_source_refs(
            existing.source_refs,
            candidate.source_refs,
        )
    if existing.decay_policy:
        payload["decay_policy"] = existing.decay_policy
    if existing.conflict_group:
        payload["conflict_group"] = existing.conflict_group

    return MemoryRecord.model_validate(payload)


def build_conflict_groups(records: list[MemoryRecord]) -> dict[str, list[MemoryRecord]]:
    groups: dict[str, list[MemoryRecord]] = defaultdict(list)
    for record in records:
        if not record.conflict_group:
            continue
        groups[record.conflict_group].append(record)

    return {
        key: value
        for key, value in groups.items()
        if len(value) > 1
    }


def stable_memory_id(scope: str, memory_type: str, text: str) -> str:
    normalized = normalize_memory_text(text).casefold().replace(" ", "_")
    return f"mem:{scope}:{memory_type}:{normalized[:48]}"


__all__ = [
    "build_conflict_groups",
    "merge_memory_record",
    "stable_memory_id",
]
