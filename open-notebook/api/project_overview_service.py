from __future__ import annotations

from typing import Any

from api.schemas import ProjectOverviewResponse, ProjectTimelineEvent

from . import project_workspace_service

DEFAULT_TOPICS = ["研究目标", "资料结构", "证据线索"]


def _dedupe_strings(values: list[str | None]) -> list[str]:
    deduped: list[str] = []

    for value in values:
        normalized = value.strip() if isinstance(value, str) else None
        if normalized and normalized not in deduped:
            deduped.append(normalized)

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
        risks.append("尚未导入资料，项目画像和证据回答还没有可依赖的基础材料。")

    if processing_source_count > 0:
        risks.append(
            f"{processing_source_count} 份资料仍在处理中，当前结论可能还不完整。"
        )

    if source_count > 0 and embedded_source_count == 0:
        risks.append("文本检索索引还没有准备好，主题归纳和问答召回会受到影响。")

    if source_count > 0 and visual_ready_count == 0:
        risks.append("视觉资料还没有建立索引，图表、版面和截图相关问题暂时不够稳。")

    if not risks:
        risks.append("当前资料状态比较稳定，可以先从证据问答或项目综述开始。")

    return risks


def _build_timeline_events(
    *,
    project_id: str,
    project_created_at: str,
    project_updated_at: str,
    sources: list[dict[str, Any]],
    processing_source_count: int,
) -> list[ProjectTimelineEvent]:
    latest_source = sorted(
        sources,
        key=lambda source: str(source.get("updated", "")),
        reverse=True,
    )[:1]

    timeline: list[ProjectTimelineEvent] = [
        ProjectTimelineEvent(
            id=f"timeline:{project_id}:created",
            title="创建项目空间",
            description="项目工作台已经建立，可以开始整理资料和沉淀证据。",
            occurred_at=project_created_at,
            source_refs=[],
        )
    ]

    if latest_source:
        source = latest_source[0]
        source_id = str(source.get("id", ""))
        timeline.insert(
            0,
            ProjectTimelineEvent(
                id=f"timeline:{project_id}:source:{source_id}",
                title="最近整理资料",
                description=(
                    f"{source.get('title') or '未命名资料'} 最近被更新，可继续补充主题和证据。"
                ),
                occurred_at=str(source.get("updated", "")),
                source_refs=[source_id] if source_id else [],
            ),
        )

    if processing_source_count > 0:
        timeline.insert(
            0,
            ProjectTimelineEvent(
                id=f"timeline:{project_id}:processing",
                title="资料处理中",
                description=(
                    f"{processing_source_count} 份资料仍在建立索引，稍后适合重新生成项目画像。"
                ),
                occurred_at=project_updated_at,
                source_refs=[],
            ),
        )

    return timeline[:4]


def _build_recommended_questions(topics: list[str], has_sources: bool) -> list[str]:
    if not has_sources:
        return [
            "这个项目最值得先导入哪几类资料？",
            "项目总览应该先回答哪些关键问题？",
            "第一轮证据问答适合从什么任务开始？",
        ]

    first_topic = topics[0] if topics else "核心主题"
    second_topic = topics[1] if len(topics) > 1 else "项目目标"

    return [
        f"围绕“{first_topic}”目前最扎实的证据是什么？",
        f"从“{second_topic}”出发，还缺哪些资料才能形成完整判断？",
        "如果现在生成项目综述，最需要人工复核的部分会在哪里？",
    ]


async def get_project_overview(project_id: str) -> ProjectOverviewResponse:
    project = await project_workspace_service.get_project(project_id)
    sources = await project_workspace_service.seekdb_business_store.source_list_rows(
        notebook_id=project_id,
        limit=100,
        offset=0,
        sort_by="updated",
        sort_order="DESC",
    )

    can_assess_processing = any("status" in source for source in sources)
    can_assess_text_index = any("embedded" in source for source in sources)
    can_assess_visual_index = any("visual_index_status" in source for source in sources)

    processing_source_count = sum(
        1
        for source in sources
        if str(source.get("status") or "") in {"new", "queued", "running"}
    )
    embedded_source_count = sum(1 for source in sources if bool(source.get("embedded")))
    visual_ready_count = sum(
        1
        for source in sources
        if str(source.get("visual_index_status") or "") == "completed"
    )

    raw_topics = [
        topic
        for source in sources
        for topic in (source.get("topics") or [])
        if isinstance(topic, str)
    ]
    topics = _dedupe_strings(raw_topics)[:6]
    effective_topics = topics or DEFAULT_TOPICS
    keywords = _dedupe_strings(
        [
            *effective_topics,
            "文本检索" if can_assess_text_index and embedded_source_count > 0 else None,
            "视觉证据" if can_assess_visual_index and visual_ready_count > 0 else None,
            "项目画像" if project.source_count > 0 else None,
        ]
    )[:8]
    risks = _build_risks(
        source_count=project.source_count,
        embedded_source_count=embedded_source_count,
        visual_ready_count=visual_ready_count,
        processing_source_count=processing_source_count,
    )

    if not can_assess_processing:
        risks = [risk for risk in risks if "处理中" not in risk]
    if not can_assess_text_index:
        risks = [risk for risk in risks if "文本检索索引" not in risk]
    if not can_assess_visual_index:
        risks = [risk for risk in risks if "视觉资料" not in risk]
    if (
        project.source_count > 0
        and not can_assess_processing
        and not can_assess_text_index
        and not can_assess_visual_index
    ):
        risks = []

    return ProjectOverviewResponse(
        project=project,
        source_count=project.source_count,
        artifact_count=project.artifact_count,
        memory_count=project.memory_count,
        topics=effective_topics,
        keywords=keywords,
        risks=risks,
        timeline_events=_build_timeline_events(
            project_id=project.id,
            project_created_at=project.created_at,
            project_updated_at=project.updated_at,
            sources=sources,
            processing_source_count=processing_source_count,
        ),
        recommended_questions=_build_recommended_questions(
            effective_topics,
            project.source_count > 0,
        ),
        recent_runs=[],
        recent_artifacts=[],
    )


async def queue_project_overview_rebuild(project_id: str) -> dict[str, str | None]:
    await project_workspace_service.get_project(project_id)

    return {
        "project_id": project_id,
        "status": "queued",
        "message": "Project overview rebuild queued.",
        "command_id": None,
    }
