from __future__ import annotations

ACTIVE_RUN_STATUSES = {"queued", "running", "waiting_review"}
SUPPORTED_RUN_TYPES = {
    "ask",
    "compare",
    "artifact",
    "memory_rebuild",
    "overview_rebuild",
    "ingest",
    "unknown",
}


def compact_text(value: str | None, *, limit: int = 280) -> str:
    normalized = " ".join(str(value or "").strip().split())
    return normalized[:limit]


def dedupe_strings(values: list[str], *, limit: int = 32) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = compact_text(value, limit=512)
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def normalize_trace_refs(values: list[str], *, limit: int = 24) -> list[str]:
    return dedupe_strings(values, limit=limit)


def ensure_supported_run_type(run_type: str) -> str:
    if run_type not in SUPPORTED_RUN_TYPES:
        raise ValueError(f"Unsupported run type: {run_type}")
    return run_type


__all__ = [
    "ACTIVE_RUN_STATUSES",
    "compact_text",
    "dedupe_strings",
    "ensure_supported_run_type",
    "normalize_trace_refs",
]
