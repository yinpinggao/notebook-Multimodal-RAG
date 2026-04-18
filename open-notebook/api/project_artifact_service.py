from __future__ import annotations

from uuid import uuid4

from api.schemas import ArtifactRecord, ProjectArtifactCreateResponse
from open_notebook.domain.artifacts import ArtifactOriginKind, ArtifactType
from open_notebook.exceptions import InvalidInputError
from open_notebook.jobs import async_submit_command
from open_notebook.project_os import (
    artifact_service as project_os_artifact_service,
)
from open_notebook.project_os import (
    overview_service as project_os_overview_service,
)
from open_notebook.project_os.artifact_service import (
    ArtifactSourceBullet,
    ArtifactSourceQAPair,
    ArtifactSourceSnapshot,
)

from . import (
    project_compare_service,
    project_evidence_service,
    project_overview_service,
    project_workspace_service,
)


def _dedupe_refs(values: list[str], *, limit: int = 12) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def _artifact_run_id() -> str:
    return f"run:{uuid4().hex[:12]}"


async def _build_overview_source_snapshot(project_id: str) -> ArtifactSourceSnapshot:
    overview = await project_overview_service.get_project_overview(project_id)
    snapshot = await project_os_overview_service.load_project_overview_snapshot(project_id)
    source_refs = _dedupe_refs(
        [
            *(profile.source_id for profile in (snapshot.source_profiles if snapshot else [])),
            *(
                ref
                for event in overview.timeline_events
                for ref in (event.source_refs or [])
            ),
        ]
    )

    bullets = [
        *[
            ArtifactSourceBullet(title="主题", detail=topic, source_refs=source_refs)
            for topic in overview.topics[:4]
        ],
        *[
            ArtifactSourceBullet(title="风险", detail=risk, source_refs=source_refs)
            for risk in overview.risks[:3]
        ],
    ]

    summary = (
        f"{overview.project.name} 当前聚焦于 {', '.join(overview.topics[:3]) or '项目主线'}，"
        f"资料规模为 {overview.source_count} 份。"
    )

    return ArtifactSourceSnapshot(
        origin_kind="overview",
        origin_id=None,
        label=overview.project.name,
        summary=summary,
        bullets=bullets,
        qa_pairs=[],
        open_questions=overview.recommended_questions[:5],
        source_refs=source_refs,
    )


async def _build_compare_source_snapshot(
    project_id: str,
    compare_id: str,
) -> ArtifactSourceSnapshot:
    compare = await project_compare_service.get_project_compare(project_id, compare_id)
    if compare.status != "completed" or not compare.result:
        raise InvalidInputError("Compare result is not ready yet")

    source_refs = _dedupe_refs(
        [
            *(ref for item in compare.result.similarities for ref in item.source_refs),
            *(ref for item in compare.result.differences for ref in item.source_refs),
            *(ref for item in compare.result.conflicts for ref in item.source_refs),
            *(ref for item in compare.result.missing_items for ref in item.source_refs),
            *(ref for item in compare.result.human_review_required for ref in item.source_refs),
        ]
    )
    bullets = [
        ArtifactSourceBullet(
            title=item.title,
            detail=item.detail,
            source_refs=item.source_refs,
        )
        for item in [
            *compare.result.differences,
            *compare.result.conflicts,
            *compare.result.missing_items,
        ][:8]
    ]

    return ArtifactSourceSnapshot(
        origin_kind="compare",
        origin_id=compare_id,
        label=f"{compare.source_a_title} vs {compare.source_b_title}",
        summary=compare.result.summary,
        bullets=bullets,
        qa_pairs=[],
        open_questions=[item.detail for item in compare.result.human_review_required[:5]],
        source_refs=source_refs,
    )


async def _build_thread_source_snapshot(
    project_id: str,
    thread_id: str,
) -> ArtifactSourceSnapshot:
    thread = await project_evidence_service.get_project_thread(project_id, thread_id)
    latest_response = thread.latest_response
    if not latest_response:
        raise InvalidInputError("Thread does not have a reusable answer yet")

    last_question = thread.last_question or "这轮问答最重要的结论是什么？"
    source_refs = _dedupe_refs(
        [card.internal_ref for card in latest_response.evidence_cards[:8]]
    )
    bullets = [
        ArtifactSourceBullet(
            title=card.source_name,
            detail=card.excerpt,
            source_refs=[card.internal_ref],
        )
        for card in latest_response.evidence_cards[:6]
    ]
    qa_pairs = [
        ArtifactSourceQAPair(
            question=last_question,
            answer=latest_response.answer,
            source_refs=source_refs,
        )
    ]

    for followup in latest_response.suggested_followups[:4]:
        qa_pairs.append(
            ArtifactSourceQAPair(
                question=followup,
                answer="可基于当前证据继续追问或展开。",
                source_refs=source_refs,
            )
        )

    return ArtifactSourceSnapshot(
        origin_kind="thread",
        origin_id=thread_id,
        label=thread.title,
        summary=latest_response.answer,
        bullets=bullets,
        qa_pairs=qa_pairs,
        open_questions=latest_response.suggested_followups[:5],
        source_refs=source_refs,
    )


async def _resolve_source_snapshot(
    project_id: str,
    origin_kind: ArtifactOriginKind,
    origin_id: str | None,
) -> ArtifactSourceSnapshot:
    if origin_kind == "overview":
        return await _build_overview_source_snapshot(project_id)
    if origin_kind == "compare":
        if not origin_id:
            raise InvalidInputError("compare origin requires origin_id")
        return await _build_compare_source_snapshot(project_id, origin_id)
    if origin_kind == "thread":
        if not origin_id:
            raise InvalidInputError("thread origin requires origin_id")
        return await _build_thread_source_snapshot(project_id, origin_id)
    raise InvalidInputError(f"Unsupported artifact origin: {origin_kind}")


async def queue_project_artifact(
    project_id: str,
    *,
    artifact_type: ArtifactType,
    origin_kind: ArtifactOriginKind,
    origin_id: str | None = None,
    title: str | None = None,
) -> ProjectArtifactCreateResponse:
    await project_workspace_service.get_project(project_id)
    source_snapshot = await _resolve_source_snapshot(project_id, origin_kind, origin_id)
    created_by_run_id = _artifact_run_id()

    artifact = await project_os_artifact_service.initialize_project_artifact(
        project_id,
        artifact_type=artifact_type,
        origin_kind=origin_kind,
        origin_id=origin_id,
        source_snapshot=source_snapshot,
        created_by_run_id=created_by_run_id,
        title=title,
        thread_id=origin_id if origin_kind == "thread" else None,
    )

    try:
        command_id = await async_submit_command(
            "open_notebook",
            "generate_artifact",
            {
                "project_id": project_id,
                "artifact_id": artifact.id,
            },
        )
    except Exception as exc:
        await project_os_artifact_service.mark_project_artifact_status(
            artifact.id,
            "failed",
            error_message=str(exc),
        )
        raise

    queued_artifact = await project_os_artifact_service.mark_project_artifact_status(
        artifact.id,
        "queued",
        command_id=command_id,
        error_message=None,
    )
    return ProjectArtifactCreateResponse(
        artifact_id=queued_artifact.id,
        status=queued_artifact.status,
        command_id=queued_artifact.command_id,
        created_by_run_id=queued_artifact.created_by_run_id,
    )


async def list_project_artifacts(project_id: str) -> list[ArtifactRecord]:
    await project_workspace_service.get_project(project_id)
    return await project_os_artifact_service.list_project_artifacts(project_id)


async def get_project_artifact(project_id: str, artifact_id: str) -> ArtifactRecord:
    await project_workspace_service.get_project(project_id)
    return await project_os_artifact_service.load_project_artifact_for_project(
        project_id,
        artifact_id,
    )


async def regenerate_project_artifact(
    project_id: str,
    artifact_id: str,
) -> ProjectArtifactCreateResponse:
    await project_workspace_service.get_project(project_id)
    artifact = await project_os_artifact_service.load_project_artifact_for_project(
        project_id,
        artifact_id,
    )
    if not artifact.origin_kind:
        raise InvalidInputError("Artifact does not have a regeneratable origin")

    source_snapshot = await _resolve_source_snapshot(
        project_id,
        artifact.origin_kind,
        artifact.origin_id,
    )
    created_by_run_id = _artifact_run_id()

    await project_os_artifact_service.update_project_artifact_source_snapshot(
        artifact_id,
        source_snapshot,
    )
    await project_os_artifact_service.mark_project_artifact_status(
        artifact_id,
        "queued",
        command_id=None,
        error_message=None,
        content_md="",
        source_refs=source_snapshot.source_refs,
        created_by_run_id=created_by_run_id,
        title=artifact.title,
    )

    try:
        command_id = await async_submit_command(
            "open_notebook",
            "generate_artifact",
            {
                "project_id": project_id,
                "artifact_id": artifact_id,
            },
        )
    except Exception as exc:
        await project_os_artifact_service.mark_project_artifact_status(
            artifact_id,
            "failed",
            error_message=str(exc),
            created_by_run_id=created_by_run_id,
        )
        raise

    queued_artifact = await project_os_artifact_service.mark_project_artifact_status(
        artifact_id,
        "queued",
        command_id=command_id,
        error_message=None,
        created_by_run_id=created_by_run_id,
    )
    return ProjectArtifactCreateResponse(
        artifact_id=queued_artifact.id,
        status=queued_artifact.status,
        command_id=queued_artifact.command_id,
        created_by_run_id=queued_artifact.created_by_run_id,
    )
