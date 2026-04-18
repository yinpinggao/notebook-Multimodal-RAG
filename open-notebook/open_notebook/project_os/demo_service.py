from __future__ import annotations

import asyncio
from pathlib import Path

from open_notebook.agent_harness import (
    create_project_run,
    mark_run_completed,
    mark_run_running,
    record_memory_write,
    record_tool_call,
)
from open_notebook.agents.synthesis_agent import generate_synthesis_artifact
from open_notebook.domain.base import ObjectModel
from open_notebook.domain.compare import ProjectCompareRecord
from open_notebook.domain.memory import MemoryRecord
from open_notebook.domain.notebook import Note, Notebook, Source
from open_notebook.exceptions import NotFoundError
from open_notebook.memory_center import list_project_memories
from open_notebook.memory_center.memory_writer import rebuild_project_memories
from open_notebook.project_os.artifact_service import (
    ArtifactSourceBullet,
    ArtifactSourceSnapshot,
    initialize_project_artifact,
    list_project_artifacts,
    mark_project_artifact_status,
)
from open_notebook.project_os.compare_service import (
    build_and_store_project_compare,
    initialize_project_compare,
    list_project_compares,
)
from open_notebook.project_os.overview_service import build_and_store_project_overview
from open_notebook.seekdb import ai_index_store, seekdb_business_store
from open_notebook.utils.chunking import chunk_text

DEMO_PROJECT_NAME = "智研舱 Demo 项目"
DEMO_PROJECT_DESCRIPTION = (
    "用于 3 分钟比赛演示的预置项目空间，覆盖项目画像、证据问答、对比、记忆和输出。"
)
DEMO_BUNDLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "zhiyancang_demo"

DEMO_SOURCE_SPECS = (
    ("competition_brief.md", "竞赛评分标准"),
    ("solution_plan.md", "方案说明"),
)
DEMO_NOTE_SPECS = (
    ("evidence_brief.md", "证据问答速览"),
    ("judge_focus.md", "评委追问清单"),
)
_DEMO_PROJECT_LOCK = asyncio.Lock()


async def _read_demo_file(filename: str) -> str:
    path = DEMO_BUNDLE_DIR / filename
    return (await asyncio.to_thread(path.read_text, encoding="utf-8")).strip()


async def _save_object_without_hooks(obj: ObjectModel) -> None:
    await ObjectModel.save(obj)


async def _index_demo_source(
    source: Source,
    *,
    project_id: str,
    filename: str,
) -> None:
    source_id = str(source.id or "")
    content = source.full_text or ""
    if not source_id or not content.strip():
        return

    chunks = chunk_text(content, file_path=filename)
    await ai_index_store.upsert_source_chunks(
        source_id,
        source.title,
        chunks,
        [[] for _ in chunks],
        [project_id],
        updated_at=source.updated,
    )


async def _create_demo_source(project_id: str, filename: str, title: str) -> Source:
    source = Source(
        title=title,
        full_text=await _read_demo_file(filename),
    )
    await _save_object_without_hooks(source)
    await source.relate("reference", project_id)
    await _index_demo_source(source, project_id=project_id, filename=filename)
    return source


async def _create_demo_note(project_id: str, filename: str, title: str) -> Note:
    note = Note(
        title=title,
        note_type="human",
        content=await _read_demo_file(filename),
    )
    await _save_object_without_hooks(note)
    await note.relate("artifact", project_id)
    await _upsert_demo_note_index(note, project_id)
    return note


async def _upsert_demo_note_index(note: Note, project_id: str) -> None:
    await ai_index_store.upsert_note_index(
        str(note.id or ""),
        note.title,
        note.content or "",
        embedding=None,
        notebook_ids=[project_id],
        updated_at=note.updated,
    )


async def _sync_demo_source(
    source: Source,
    *,
    project_id: str,
    filename: str,
    title: str,
) -> Source:
    content = await _read_demo_file(filename)
    changed = False
    if source.title != title:
        source.title = title
        changed = True
    if (source.full_text or "").strip() != content:
        source.full_text = content
        changed = True

    if changed:
        await _save_object_without_hooks(source)

    await _index_demo_source(source, project_id=project_id, filename=filename)
    return source


async def _sync_demo_note(
    note: Note,
    *,
    project_id: str,
    filename: str,
    title: str,
) -> Note:
    content = await _read_demo_file(filename)
    changed = False
    if note.title != title:
        note.title = title
        changed = True
    if note.note_type != "human":
        note.note_type = "human"
        changed = True
    if (note.content or "").strip() != content:
        note.content = content
        changed = True

    if changed:
        await _save_object_without_hooks(note)

    await _upsert_demo_note_index(note, project_id)
    return note


async def _ensure_demo_sources(project_id: str) -> list[Source]:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Demo project not found")

    existing_sources = {
        " ".join(str(source.title or "").strip().split()): source
        for source in await notebook.get_sources()
    }
    ensured_sources: list[Source] = []
    for filename, title in DEMO_SOURCE_SPECS:
        source = existing_sources.get(title)
        if source:
            ensured_sources.append(
                await _sync_demo_source(
                    source,
                    project_id=project_id,
                    filename=filename,
                    title=title,
                )
            )
            continue
        ensured_sources.append(await _create_demo_source(project_id, filename, title))
    return ensured_sources


async def _ensure_demo_notes(project_id: str) -> None:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Demo project not found")

    existing_notes = {
        " ".join(str(note.title or "").strip().split()): note
        for note in await notebook.get_notes()
    }
    for filename, title in DEMO_NOTE_SPECS:
        note = existing_notes.get(title)
        if note:
            await _sync_demo_note(
                note,
                project_id=project_id,
                filename=filename,
                title=title,
            )
            continue
        await _create_demo_note(project_id, filename, title)


def _compare_counts(compare: ProjectCompareRecord) -> dict[str, int]:
    result = compare.result
    if not result:
        return {
            "similarity_count": 0,
            "difference_count": 0,
            "conflict_count": 0,
            "missing_count": 0,
            "review_count": 0,
        }

    return {
        "similarity_count": len(result.similarities),
        "difference_count": len(result.differences),
        "conflict_count": len(result.conflicts),
        "missing_count": len(result.missing_items),
        "review_count": len(result.human_review_required),
    }


def _compare_refs(compare: ProjectCompareRecord) -> list[str]:
    result = compare.result
    if not result:
        return []

    refs: list[str] = []
    for item in (
        list(result.similarities)
        + list(result.differences)
        + list(result.conflicts)
        + list(result.missing_items)
        + list(result.human_review_required)
    ):
        for ref in item.source_refs:
            if ref and ref not in refs:
                refs.append(ref)
    return refs


def _compare_snapshot(compare: ProjectCompareRecord) -> ArtifactSourceSnapshot:
    result = compare.result
    if not result:
        raise NotFoundError("Demo compare result not found")

    bullets = [
        ArtifactSourceBullet(
            title=item.title,
            detail=item.detail,
            source_refs=item.source_refs,
        )
        for item in [
            *result.differences,
            *result.conflicts,
            *result.missing_items,
        ][:8]
    ]
    open_questions = [item.detail for item in result.human_review_required[:5]]
    source_refs = _compare_refs(compare)

    return ArtifactSourceSnapshot(
        origin_kind="compare",
        origin_id=compare.id,
        label=f"{compare.source_a_title} vs {compare.source_b_title}",
        summary=result.summary,
        bullets=bullets,
        qa_pairs=[],
        open_questions=open_questions,
        source_refs=source_refs,
    )


async def _record_demo_compare_run(
    project_id: str,
    compare: ProjectCompareRecord,
) -> None:
    counts = _compare_counts(compare)
    refs = _compare_refs(compare)
    run = await create_project_run(
        project_id,
        run_type="compare",
        input_summary=f"{compare.source_a_title} vs {compare.source_b_title}",
        input_json={
            "compare_id": compare.id,
            "compare_mode": compare.compare_mode,
            "source_a_id": compare.source_a_id,
            "source_b_id": compare.source_b_id,
        },
    )
    await mark_run_running(run.id)
    await record_tool_call(
        run.id,
        title="生成示例对比结果",
        tool_name="build_and_store_project_compare",
        agent_name="demo_seed",
        input_json={
            "compare_id": compare.id,
            "compare_mode": compare.compare_mode,
        },
        output_json=counts,
        evidence_refs=refs,
        output_refs=[compare.id],
    )
    await mark_run_completed(
        run.id,
        output_json={
            "compare_id": compare.id,
            **counts,
        },
        tool_calls=["build_and_store_project_compare"],
        evidence_reads=refs,
        outputs=[compare.id],
    )


async def _record_demo_memory_run(
    project_id: str,
    memories: list[MemoryRecord],
) -> None:
    run = await create_project_run(
        project_id,
        run_type="memory_rebuild",
        input_summary="演示项目长期记忆重建",
        input_json={"origin": "demo_seed"},
    )
    await mark_run_running(run.id)
    evidence_refs = [
        ref.internal_ref
        for memory in memories
        for ref in memory.source_refs
        if ref.internal_ref
    ]
    memory_ids = [memory.id for memory in memories]
    status_breakdown: dict[str, int] = {}
    for memory in memories:
        status_breakdown[memory.status] = status_breakdown.get(memory.status, 0) + 1

    await record_memory_write(
        run.id,
        title="写入示例项目记忆",
        agent_name="demo_seed",
        output_json={
            "memory_count": len(memories),
            "status_breakdown": status_breakdown,
        },
        evidence_refs=evidence_refs,
        memory_refs=memory_ids,
    )
    await mark_run_completed(
        run.id,
        output_json={
            "memory_count": len(memories),
            "status_breakdown": status_breakdown,
        },
        tool_calls=["rebuild_project_memories"],
        evidence_reads=evidence_refs,
        memory_writes=memory_ids,
        outputs=memory_ids,
    )


async def _start_demo_artifact_run(
    project_id: str,
    title: str,
    compare_id: str,
) -> str:
    run = await create_project_run(
        project_id,
        run_type="artifact",
        input_summary=title,
        input_json={
            "artifact_type": "diff_report",
            "origin_kind": "compare",
            "origin_id": compare_id,
        },
    )
    await mark_run_running(run.id)
    return run.id


async def _record_demo_artifact_run(
    run_id: str,
    artifact_id: str,
    source_refs: list[str],
    content_length: int,
) -> None:
    await record_tool_call(
        run_id,
        title="生成示例 Markdown 产物",
        tool_name="generate_synthesis_artifact",
        agent_name="demo_seed",
        input_json={
            "artifact_id": artifact_id,
            "artifact_type": "diff_report",
        },
        output_json={
            "content_length": content_length,
            "source_ref_count": len(source_refs),
        },
        evidence_refs=source_refs,
        output_refs=[artifact_id],
    )
    await mark_run_completed(
        run_id,
        output_json={
            "artifact_id": artifact_id,
            "content_length": content_length,
        },
        tool_calls=["generate_synthesis_artifact"],
        evidence_reads=source_refs,
        outputs=[artifact_id],
    )


async def _ensure_demo_compare(
    project_id: str,
    sources: list[Source],
) -> ProjectCompareRecord:
    compares = await list_project_compares(project_id)
    for compare in compares:
        if (
            compare.compare_mode == "requirements"
            and compare.status == "completed"
            and compare.result
        ):
            return compare

    compare = await initialize_project_compare(
        project_id,
        source_a_id=str(sources[0].id or ""),
        source_b_id=str(sources[1].id or ""),
        compare_mode="requirements",
    )
    compare = await build_and_store_project_compare(
        project_id,
        compare_id=compare.id,
        source_a_id=compare.source_a_id,
        source_b_id=compare.source_b_id,
        compare_mode="requirements",
    )
    await _record_demo_compare_run(project_id, compare)
    return compare


async def _ensure_demo_memories(project_id: str) -> list[MemoryRecord]:
    memories = await list_project_memories(project_id, include_deprecated=True)
    if memories:
        return memories

    memories = await rebuild_project_memories(project_id)
    await _record_demo_memory_run(project_id, memories)
    return memories


async def _ensure_demo_artifact(
    project_id: str,
    compare: ProjectCompareRecord,
) -> None:
    artifacts = await list_project_artifacts(project_id, limit=1000)
    for artifact in artifacts:
        if (
            artifact.artifact_type == "diff_report"
            and artifact.origin_kind == "compare"
            and artifact.origin_id == compare.id
            and artifact.status == "ready"
        ):
            return

    snapshot = _compare_snapshot(compare)
    artifact_run_id = await _start_demo_artifact_run(
        project_id,
        "智研舱 Demo 差异报告",
        compare.id,
    )
    artifact = await initialize_project_artifact(
        project_id,
        artifact_type="diff_report",
        origin_kind="compare",
        origin_id=compare.id,
        source_snapshot=snapshot,
        created_by_run_id=artifact_run_id,
        title="智研舱 Demo 差异报告",
    )
    content_md = await generate_synthesis_artifact(
        "diff_report",
        title=artifact.title,
        snapshot=snapshot,
    )
    artifact = await mark_project_artifact_status(
        artifact.id,
        "ready",
        content_md=content_md,
        source_refs=snapshot.source_refs,
        created_by_run_id=artifact_run_id,
        error_message=None,
    )
    await _record_demo_artifact_run(
        artifact_run_id,
        artifact.id,
        snapshot.source_refs,
        len(content_md),
    )


async def ensure_demo_project() -> str:
    async with _DEMO_PROJECT_LOCK:
        rows = await seekdb_business_store.notebook_rows(order_by="updated desc")
        project_id = ""
        for row in rows:
            if (
                row.get("name") == DEMO_PROJECT_NAME
                and row.get("description") == DEMO_PROJECT_DESCRIPTION
            ):
                project_id = str(row.get("id") or "")
                break

        if not project_id:
            notebook = Notebook(
                name=DEMO_PROJECT_NAME,
                description=DEMO_PROJECT_DESCRIPTION,
            )
            await _save_object_without_hooks(notebook)
            project_id = str(notebook.id or "")

        sources = await _ensure_demo_sources(project_id)
        await _ensure_demo_notes(project_id)
        await build_and_store_project_overview(project_id)
        compare = await _ensure_demo_compare(project_id, sources)
        await _ensure_demo_memories(project_id)
        await _ensure_demo_artifact(project_id, compare)
        return project_id


__all__ = [
    "DEMO_BUNDLE_DIR",
    "DEMO_PROJECT_DESCRIPTION",
    "DEMO_PROJECT_NAME",
    "ensure_demo_project",
]
