from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import NAMESPACE_URL, uuid5

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.notebook import Notebook
from open_notebook.domain.projects import ProjectTimelineEvent
from open_notebook.seekdb import seekdb_business_store

from .source_profile_service import build_and_store_source_profile


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceProfileSummary(_Model):
    source_id: str
    title: str
    topic_count: int = 0
    keyword_count: int = 0
    risk_count: int = 0
    requirement_count: int = 0


class ProjectOverviewSnapshot(_Model):
    project_id: str
    status: str = "completed"
    command_id: Optional[str] = None
    error_message: Optional[str] = None
    generated_at: Optional[str] = None
    source_profiles: list[SourceProfileSummary] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)
    people_orgs: list[str] = Field(default_factory=list)
    timeline_events: list[ProjectTimelineEvent] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    recommended_questions: list[str] = Field(default_factory=list)


def project_overview_record_id(project_id: str) -> str:
    return f"project_overview:{project_id}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dedupe(values: list[str], *, limit: Optional[int] = None) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value).strip().split())
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
        if limit and len(deduped) >= limit:
            break
    return deduped


def _top_counts(values: list[str], *, limit: int) -> list[str]:
    counter = Counter(" ".join(str(value).strip().split()) for value in values if str(value).strip())
    return [item for item, _ in counter.most_common(limit)]


def _event_id(project_id: str, title: str) -> str:
    digest = uuid5(NAMESPACE_URL, f"{project_id}:{title}")
    return f"timeline:{digest.hex}"


def _aggregate_timeline_events(
    *,
    project_id: str,
    project_created_at: str,
    source_profiles: list,
) -> list[ProjectTimelineEvent]:
    events: list[ProjectTimelineEvent] = [
        ProjectTimelineEvent(
            id=_event_id(project_id, "Project created"),
            title="创建项目空间",
            description="项目工作台已经建立，可以开始整理资料、抽取画像并沉淀证据。",
            occurred_at=project_created_at,
            source_refs=[],
        )
    ]
    seen_titles = {"创建项目空间"}

    for profile in source_profiles:
        for signal in profile.timeline_events:
            title = signal.value[:96].strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            events.append(
                ProjectTimelineEvent(
                    id=_event_id(project_id, title),
                    title=title[:48],
                    description=signal.evidence_excerpt or title,
                    occurred_at=signal.occurred_at,
                    source_refs=[signal.source_ref] if signal.source_ref else [profile.source_id],
                )
            )
            if len(events) >= 6:
                return events
    return events


def _recommended_questions(
    *,
    topics: list[str],
    risks: list[str],
    requirements: list[str],
) -> list[str]:
    if not topics and not risks and not requirements:
        return [
            "应该先检查哪份资料，才能更快建立可信的项目画像？",
            "当前还缺哪些证据，导致我们不能稳定回答？",
            "这个项目里最需要优先盯住的风险是什么？",
        ]

    first_topic = topics[0] if topics else "当前项目"
    questions = [
        f"围绕“{first_topic}”，目前最扎实的证据是什么？",
        "接下来应该优先补看哪些资料，才能缩小最大的证据缺口？",
    ]

    if risks:
        questions.append(f"这个风险最需要怎么验证或补证：{risks[0]}？")
    elif requirements:
        questions.append(f"这个要求还缺哪类明确证据：{requirements[0]}？")
    else:
        questions.append("如果现在产出项目综述，最需要人工复核的结论会是什么？")

    return questions[:3]


def _strip_singleton_metadata(data: dict) -> dict:
    return {
        key: value
        for key, value in data.items()
        if key not in {"id", "created", "updated"}
    }


async def load_project_overview_snapshot(project_id: str) -> ProjectOverviewSnapshot | None:
    data = await seekdb_business_store.get_singleton(project_overview_record_id(project_id))
    if not data:
        return None
    return ProjectOverviewSnapshot.model_validate(_strip_singleton_metadata(data))


async def save_project_overview_snapshot(
    snapshot: ProjectOverviewSnapshot,
) -> ProjectOverviewSnapshot:
    saved = await seekdb_business_store.upsert_singleton(
        project_overview_record_id(snapshot.project_id),
        snapshot.model_dump(mode="json"),
    )
    return ProjectOverviewSnapshot.model_validate(_strip_singleton_metadata(saved))


async def mark_project_overview_status(
    project_id: str,
    status: str,
    *,
    command_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> ProjectOverviewSnapshot:
    current = await load_project_overview_snapshot(project_id)
    payload = current.model_dump(mode="json") if current else {"project_id": project_id}
    payload["project_id"] = project_id
    payload["status"] = status
    payload["error_message"] = error_message
    if command_id is not None:
        payload["command_id"] = command_id
    if status == "completed":
        payload["generated_at"] = _utc_now()
    return await save_project_overview_snapshot(ProjectOverviewSnapshot.model_validate(payload))


async def build_and_store_project_overview(
    project_id: str,
    *,
    command_id: Optional[str] = None,
) -> ProjectOverviewSnapshot:
    notebook = await Notebook.get(project_id)
    sources = await notebook.get_sources()
    source_profiles = []

    for source in sources:
        if not source.id:
            continue
        try:
            source_profiles.append(await build_and_store_source_profile(str(source.id)))
        except Exception as exc:
            logger.warning(
                f"Skipping source profile rebuild for {source.id} while building overview {project_id}: {exc}"
            )

    topics = _top_counts(
        [item for profile in source_profiles for item in profile.topics],
        limit=6,
    )
    keywords = _top_counts(
        [item for profile in source_profiles for item in profile.keywords],
        limit=10,
    )
    terms = _top_counts(
        [item for profile in source_profiles for item in profile.terms],
        limit=8,
    )
    people_orgs = _top_counts(
        [item for profile in source_profiles for item in profile.people_orgs],
        limit=8,
    )
    metrics = _dedupe(
        [item for profile in source_profiles for item in profile.metrics],
        limit=8,
    )
    risks = _dedupe(
        [item for profile in source_profiles for item in profile.risks],
        limit=6,
    )
    requirements = _dedupe(
        [item for profile in source_profiles for item in profile.requirements],
        limit=6,
    )
    timeline_events = _aggregate_timeline_events(
        project_id=project_id,
        project_created_at=str(notebook.created) if notebook.created else None or _utc_now(),
        source_profiles=source_profiles,
    )

    snapshot = ProjectOverviewSnapshot(
        project_id=project_id,
        status="completed",
        command_id=command_id,
        generated_at=_utc_now(),
        source_profiles=[
            SourceProfileSummary(
                source_id=profile.source_id,
                title=profile.title,
                topic_count=len(profile.topics),
                keyword_count=len(profile.keywords),
                risk_count=len(profile.risks),
                requirement_count=len(profile.requirements),
            )
            for profile in source_profiles
        ],
        topics=topics,
        keywords=keywords,
        terms=terms,
        people_orgs=people_orgs,
        timeline_events=timeline_events,
        metrics=metrics,
        risks=risks,
        requirements=requirements,
        recommended_questions=_recommended_questions(
            topics=topics,
            risks=risks,
            requirements=requirements,
        ),
    )
    return await save_project_overview_snapshot(snapshot)


__all__ = [
    "ProjectOverviewSnapshot",
    "build_and_store_project_overview",
    "load_project_overview_snapshot",
    "mark_project_overview_status",
    "project_overview_record_id",
]
