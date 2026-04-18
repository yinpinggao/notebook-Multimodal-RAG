from __future__ import annotations

from typing import Any

from loguru import logger

from open_notebook.domain.notebook import Source
from open_notebook.evidence.structured_extractor import (
    SourceProfile,
    extract_source_profile,
)
from open_notebook.seekdb import ai_page_store, seekdb_business_store
from open_notebook.storage.visual_assets import visual_asset_store


def source_profile_record_id(source_id: str) -> str:
    return f"source_profile:{source_id}"


def _strip_singleton_metadata(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if key not in {"id", "created", "updated"}
    }


async def load_source_profile(source_id: str) -> SourceProfile | None:
    data = await seekdb_business_store.get_singleton(source_profile_record_id(source_id))
    if not data:
        return None
    return SourceProfile.model_validate(_strip_singleton_metadata(data))


async def save_source_profile(profile: SourceProfile) -> SourceProfile:
    saved = await seekdb_business_store.upsert_singleton(
        source_profile_record_id(profile.source_id),
        profile.model_dump(mode="json"),
    )
    return SourceProfile.model_validate(_strip_singleton_metadata(saved))


def _source_ref(source_id: str, page_no: Any) -> str:
    try:
        if page_no is not None and int(page_no) >= 1:
            return f"{source_id}#p{int(page_no)}"
    except (TypeError, ValueError):
        pass
    return source_id


async def _page_summary_inputs(source_id: str) -> list[dict[str, str]]:
    try:
        pages = await ai_page_store.list_source_pages(source_id)
    except Exception as exc:
        logger.warning(f"Failed to read page summaries for {source_id}: {exc}")
        return []

    summaries: list[dict[str, str]] = []
    for page in pages:
        text = str(
            page.get("page_summary")
            or page.get("combined_text")
            or page.get("raw_text")
            or ""
        ).strip()
        if not text:
            continue
        summaries.append(
            {
                "text": text[:1200],
                "source_ref": _source_ref(source_id, page.get("page_no")),
            }
        )
    return summaries


async def _visual_summary_inputs(source_id: str) -> list[dict[str, str]]:
    try:
        assets = await visual_asset_store.list_assets_by_source(source_id)
    except Exception as exc:
        logger.warning(f"Failed to read visual summaries for {source_id}: {exc}")
        return []

    summaries: list[dict[str, str]] = []
    for asset in assets:
        text = str(asset.get("summary") or asset.get("raw_text") or "").strip()
        if not text:
            continue
        summaries.append(
            {
                "text": text[:1200],
                "source_ref": _source_ref(source_id, asset.get("page_no")),
            }
        )
    return summaries


async def build_source_profile(source_id: str) -> SourceProfile:
    source = await Source.get(source_id)
    insights = await source.get_insights()
    page_summaries = await _page_summary_inputs(source_id)
    visual_summaries = await _visual_summary_inputs(source_id)

    profile = extract_source_profile(
        source_id=source_id,
        title=str(source.title or source_id),
        full_text=str(source.full_text or ""),
        source_updated_at=str(source.updated) if source.updated else None,
        existing_topics=list(source.topics or []),
        insight_texts=[str(insight.content or "") for insight in insights],
        page_summaries=page_summaries,
        visual_summaries=visual_summaries,
    )
    return await save_source_profile(profile)


async def build_and_store_source_profile(source_id: str) -> SourceProfile:
    return await build_source_profile(source_id)


__all__ = [
    "build_and_store_source_profile",
    "build_source_profile",
    "load_source_profile",
    "save_source_profile",
    "source_profile_record_id",
]
