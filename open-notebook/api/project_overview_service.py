from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from api.schemas import (
    ProjectOverviewResponse,
    ProjectTimelineEvent,
    RecentArtifactSummary,
    RecentRunSummary,
)
from open_notebook.agent_harness import list_recent_run_summaries
from open_notebook.domain.notebook import Source
from open_notebook.jobs import async_submit_command
from open_notebook.project_os import artifact_service as project_os_artifact_service
from open_notebook.project_os import overview_service as project_os_overview_service
from open_notebook.storage.visual_assets import visual_asset_store

from . import project_workspace_service

DEFAULT_TOPICS = ["研究目标", "资料结构", "证据线索"]


def _dedupe_strings(values: list[str | None], *, limit: int | None = None) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value).strip().split()) if value else ""
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
        if limit and len(deduped) >= limit:
            break
    return deduped


def _build_risks(
    *,
    source_count: int,
    embedded_source_count: int,
    visual_ready_count: int,
    processing_source_count: int,
) -> list[str]:
    risks: list[str] = []

    if source_count == 0:
        risks.append(
            "尚未导入资料，项目画像和证据问答还没有可依赖的基础材料。"
        )
    if processing_source_count > 0:
        risks.append(
            f"{processing_source_count} 份资料仍在处理中，当前总览可能还不完整。"
        )
    if source_count > 0 and embedded_source_count == 0:
        risks.append(
            "文本检索索引还没有准备好，主题归纳和问答召回会受到影响。"
        )
    if source_count > 0 and visual_ready_count == 0:
        risks.append(
            "视觉资料还没有建立索引，图表、版面和截图相关问题暂时不够稳。"
        )
    if not risks:
        risks.append(
            "当前资料状态比较稳定，可以先从证据问答或项目综述开始。"
        )

    return risks


def _fallback_timeline_events(
    *,
    project_id: str,
    project_created_at: str,
    project_updated_at: str,
    sources: list[dict[str, Any]],
    processing_source_count: int,
) -> list[ProjectTimelineEvent]:
    timeline = [
        ProjectTimelineEvent(
            id=f"timeline:{project_id}:created",
            title="创建项目空间",
            description="项目工作台已经建立，可以开始整理资料、抽取画像并沉淀证据。",
            occurred_at=project_created_at,
            source_refs=[],
        )
    ]

    latest_source = sorted(
        sources,
        key=lambda source: str(source.get("updated", "")),
        reverse=True,
    )[:1]

    if latest_source:
        source = latest_source[0]
        source_id = str(source.get("id") or "")
        timeline.insert(
            0,
            ProjectTimelineEvent(
                id=f"timeline:{project_id}:source:{source_id}",
                title="最近整理资料",
                description=(
                    f"{source.get('title') or '未命名资料'} 最近被更新，可继续补充主题和证据。"
                ),
                occurred_at=str(source.get("updated") or project_updated_at),
                source_refs=[source_id] if source_id else [],
            ),
        )

    if processing_source_count > 0:
        timeline.insert(
            0,
            ProjectTimelineEvent(
                id=f"timeline:{project_id}:processing",
                title="总览重建中",
                description=(
                    f"{processing_source_count} 份资料仍在处理或建索引，稍后适合重新查看项目画像。"
                ),
                occurred_at=project_updated_at,
                source_refs=[],
            ),
        )

    return timeline[:4]


def _build_recommended_questions(
    topics: list[str],
    *,
    has_sources: bool,
    risks: list[str],
) -> list[str]:
    if not has_sources:
        return [
            "这个项目最值得先导入哪几类资料？",
            "项目总览应该先回答哪些关键问题？",
            "第一轮证据问答适合从什么任务开始？",
        ]

    first_topic = topics[0] if topics else "核心主题"
    questions = [
        f"围绕“{first_topic}”目前最扎实的证据是什么？",
        "下一步最值得优先补看的资料是哪几份？",
    ]

    if risks:
        questions.append(f"针对这个风险，最需要补强或人工复核的地方是什么：{risks[0]}？")
    else:
        questions.append("如果现在生成项目综述，最需要人工复核的部分会在哪里？")

    return questions[:3]


async def _source_runtime_rows(project_id: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows = await project_workspace_service.seekdb_business_store.source_list_rows(
        notebook_id=project_id,
        limit=100,
        offset=0,
        sort_by="updated",
        sort_order="DESC",
    )

    processing_source_count = 0
    embedded_source_count = 0
    visual_ready_count = 0
    
    async def _enrich_source_row(row: dict[str, Any]) -> dict[str, Any]:
        source = Source.model_validate(row)
        source_status = None
        index_stats = {"chunk_count": 0}
        try:
            source_status = await source.get_status()
        except Exception as exc:
            logger.warning(f"Failed to read source status for {source.id}: {exc}")

        try:
            index_stats = await source.get_index_stats()
        except Exception as exc:
            logger.warning(f"Failed to read index stats for {source.id}: {exc}")

        try:
            visual_summary = await visual_asset_store.source_index_summary(str(source.id))
        except Exception as exc:
            logger.warning(f"Failed to read visual index summary for {source.id}: {exc}")
            visual_summary = {
                "visual_index_status": None,
                "visual_asset_count": 0,
            }

        embedded = int(index_stats.get("chunk_count") or 0) > 0
        visual_ready = visual_summary.get("visual_index_status") == "completed"

        return {
            **row,
            "status": source_status,
            "embedded": embedded,
            "embedded_chunks": int(index_stats.get("chunk_count") or 0),
            "visual_index_status": visual_summary.get("visual_index_status"),
            "visual_asset_count": visual_summary.get("visual_asset_count"),
            "_derived_processing": source_status in {"new", "queued", "running"},
            "_derived_embedded": embedded,
            "_derived_visual_ready": visual_ready,
        }

    enriched_rows = await asyncio.gather(*[_enrich_source_row(row) for row in rows])

    for row in enriched_rows:
        if row.pop("_derived_processing", False):
            processing_source_count += 1
        if row.pop("_derived_embedded", False):
            embedded_source_count += 1
        if row.pop("_derived_visual_ready", False):
            visual_ready_count += 1

    return enriched_rows, {
        "processing_source_count": processing_source_count,
        "embedded_source_count": embedded_source_count,
        "visual_ready_count": visual_ready_count,
    }


async def _recent_artifact_summaries(
    project_id: str,
    *,
    limit: int = 5,
) -> list[RecentArtifactSummary]:
    artifacts = await project_os_artifact_service.list_project_artifacts(
        project_id,
        limit=limit + 5,
    )
    summaries = [
        RecentArtifactSummary(
            id=artifact.id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            created_at=artifact.created_at,
            created_by_run_id=artifact.created_by_run_id,
        )
        for artifact in artifacts
        if artifact.status not in {"archived", "failed"}
    ]
    return summaries[:limit]


async def _recent_run_summaries(
    project_id: str,
    *,
    limit: int = 5,
) -> list[RecentRunSummary]:
    return await list_recent_run_summaries(project_id, limit=limit)


async def get_project_overview(project_id: str) -> ProjectOverviewResponse:
    project = await project_workspace_service.get_project(project_id)
    (sources, live_metrics), snapshot, recent_artifacts, recent_runs = await asyncio.gather(
        _source_runtime_rows(project_id),
        project_os_overview_service.load_project_overview_snapshot(project_id),
        _recent_artifact_summaries(project_id),
        _recent_run_summaries(project_id),
    )

    raw_topics = [
        topic
        for source in sources
        for topic in (source.get("topics") or [])
        if isinstance(topic, str)
    ]
    fallback_topics = _dedupe_strings(raw_topics, limit=6) or DEFAULT_TOPICS
    fallback_keywords = _dedupe_strings(
        [
            *fallback_topics,
            "文本检索" if live_metrics["embedded_source_count"] > 0 else None,
            "视觉证据" if live_metrics["visual_ready_count"] > 0 else None,
        ],
        limit=8,
    )
    fallback_risks = _build_risks(
        source_count=project.source_count,
        embedded_source_count=live_metrics["embedded_source_count"],
        visual_ready_count=live_metrics["visual_ready_count"],
        processing_source_count=live_metrics["processing_source_count"],
    )

    topics = snapshot.topics if snapshot and snapshot.topics else fallback_topics
    keywords = snapshot.keywords if snapshot and snapshot.keywords else fallback_keywords
    risks = snapshot.risks if snapshot and snapshot.risks else fallback_risks
    timeline_events = (
        snapshot.timeline_events
        if snapshot and snapshot.timeline_events
        else _fallback_timeline_events(
            project_id=project.id,
            project_created_at=project.created_at,
            project_updated_at=project.updated_at,
            sources=sources,
            processing_source_count=live_metrics["processing_source_count"],
        )
    )
    recommended_questions = (
        snapshot.recommended_questions
        if snapshot and snapshot.recommended_questions
        else _build_recommended_questions(
            topics,
            has_sources=project.source_count > 0,
            risks=risks,
        )
    )

    return ProjectOverviewResponse(
        project=project,
        source_count=project.source_count,
        artifact_count=project.artifact_count,
        memory_count=project.memory_count,
        topics=topics,
        keywords=keywords,
        risks=risks,
        timeline_events=timeline_events,
        recommended_questions=recommended_questions,
        recent_runs=recent_runs,
        recent_artifacts=recent_artifacts,
    )


async def queue_project_overview_rebuild(project_id: str) -> dict[str, str | None]:
    await project_workspace_service.get_project(project_id)

    import commands.project_commands  # noqa: F401

    command_id = await async_submit_command(
        "open_notebook",
        "build_overview",
        {"project_id": project_id},
    )
    await project_os_overview_service.mark_project_overview_status(
        project_id,
        "queued",
        command_id=command_id,
        error_message=None,
    )

    return {
        "project_id": project_id,
        "status": "queued",
        "message": "Project overview rebuild queued.",
        "command_id": command_id,
    }
