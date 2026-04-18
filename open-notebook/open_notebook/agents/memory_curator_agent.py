from __future__ import annotations

from collections import defaultdict

from open_notebook.domain.memory import SourceReference
from open_notebook.domain.notebook import Notebook
from open_notebook.evidence.structured_extractor import SourceProfile
from open_notebook.exceptions import NotFoundError
from open_notebook.memory_center.memory_policy import MemoryCandidate, clamp_confidence
from open_notebook.memory_center.memory_resolver import stable_memory_id
from open_notebook.project_os.overview_service import (
    build_and_store_project_overview,
    load_project_overview_snapshot,
)
from open_notebook.project_os.source_profile_service import (
    build_and_store_source_profile,
    load_source_profile,
)


def _parse_page_no(internal_ref: str) -> int | None:
    _, _, page_fragment = str(internal_ref or "").partition("#p")
    if not page_fragment:
        return None
    try:
        page_no = int(page_fragment)
    except (TypeError, ValueError):
        return None
    return page_no if page_no >= 1 else None


def _build_source_reference(source_id: str, ref: str, source_name: str | None) -> SourceReference:
    page_no = _parse_page_no(ref)
    if source_name and page_no:
        citation_text = f"引用：{source_name}（第{page_no}页）"
    elif source_name:
        citation_text = f"引用：{source_name}"
    else:
        citation_text = ref

    return SourceReference(
        source_id=source_id,
        source_name=source_name,
        page_no=page_no,
        internal_ref=ref,
        citation_text=citation_text,
    )


def _dedupe_source_refs(refs: list[SourceReference], *, limit: int = 6) -> list[SourceReference]:
    deduped: list[SourceReference] = []
    seen: set[str] = set()
    for ref in refs:
        key = f"{ref.source_id}:{ref.internal_ref}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
        if len(deduped) >= limit:
            break
    return deduped


def _register_refs(
    lookup: dict[tuple[str, str], list[SourceReference]],
    *,
    category: str,
    value: str,
    refs: list[SourceReference],
) -> None:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        return
    lookup[(category, normalized.casefold())].extend(refs)


def _default_refs(profile: SourceProfile) -> list[str]:
    return list(profile.source_refs or [profile.source_id])


def _build_reference_lookup(
    profiles: list[SourceProfile],
) -> dict[tuple[str, str], list[SourceReference]]:
    lookup: dict[tuple[str, str], list[SourceReference]] = defaultdict(list)

    for profile in profiles:
        default_refs = [
            _build_source_reference(profile.source_id, ref, profile.title)
            for ref in _default_refs(profile)
        ]

        for fact in profile.facts:
            refs = [
                _build_source_reference(
                    profile.source_id,
                    ref,
                    profile.title,
                )
                for ref in (fact.source_refs or _default_refs(profile))
            ]
            _register_refs(
                lookup,
                category=fact.category,
                value=fact.value,
                refs=refs or default_refs,
            )

        for topic in profile.topics:
            _register_refs(lookup, category="topic", value=topic, refs=default_refs)
        for term in profile.terms:
            _register_refs(lookup, category="term", value=term, refs=default_refs)
        for risk in profile.risks:
            _register_refs(lookup, category="risk", value=risk, refs=default_refs)
        for requirement in profile.requirements:
            _register_refs(
                lookup,
                category="requirement",
                value=requirement,
                refs=default_refs,
            )

    return lookup


def _candidate_confidence(
    memory_type: str,
    refs: list[SourceReference],
) -> float:
    source_count = len({ref.source_id for ref in refs})
    ref_count = len(refs)
    base_by_type = {
        "term": 0.8,
        "fact": 0.78,
        "risk": 0.68,
        "question": 0.6,
    }
    base = base_by_type.get(memory_type, 0.72)
    if source_count >= 2:
        base += 0.08
    if ref_count >= 2:
        base += 0.04
    return clamp_confidence(base)


def _candidate_text(memory_type: str, value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if memory_type == "fact" and not normalized.startswith("项目核心主题："):
        return normalized
    return normalized


def _build_candidates_for_values(
    *,
    category: str,
    memory_type: str,
    values: list[str],
    lookup: dict[tuple[str, str], list[SourceReference]],
    transform_text=None,
) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized:
            continue
        refs = _dedupe_source_refs(lookup.get((category, normalized.casefold()), []))
        if not refs:
            continue
        text = transform_text(normalized) if transform_text else _candidate_text(memory_type, normalized)
        candidates.append(
            MemoryCandidate(
                id=stable_memory_id("project", memory_type, text),
                scope="project",
                type=memory_type,
                text=text,
                confidence=_candidate_confidence(memory_type, refs),
                source_refs=refs,
            )
        )
    return candidates


async def collect_project_memory_candidates(project_id: str) -> list[MemoryCandidate]:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Project not found")

    snapshot = await load_project_overview_snapshot(project_id)
    if not snapshot or snapshot.status != "completed":
        snapshot = await build_and_store_project_overview(project_id)

    profiles: list[SourceProfile] = []
    for source in await notebook.get_sources():
        if not source.id:
            continue
        source_id = str(source.id)
        profile = await load_source_profile(source_id)
        if not profile:
            profile = await build_and_store_source_profile(source_id)
        profiles.append(profile)

    lookup = _build_reference_lookup(profiles)
    candidates: list[MemoryCandidate] = []
    candidates.extend(
        _build_candidates_for_values(
            category="term",
            memory_type="term",
            values=snapshot.terms[:8],
            lookup=lookup,
        )
    )
    candidates.extend(
        _build_candidates_for_values(
            category="requirement",
            memory_type="fact",
            values=snapshot.requirements[:8],
            lookup=lookup,
        )
    )
    candidates.extend(
        _build_candidates_for_values(
            category="risk",
            memory_type="risk",
            values=snapshot.risks[:6],
            lookup=lookup,
        )
    )

    deduped: list[MemoryCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.id in seen:
            continue
        seen.add(candidate.id)
        deduped.append(candidate)

    return deduped


__all__ = ["collect_project_memory_candidates"]
