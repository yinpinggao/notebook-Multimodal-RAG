from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

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
from open_notebook.domain.evidence import EvidenceCard
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
from open_notebook.utils.embedding import generate_embedding, generate_embeddings

DEMO_PROJECT_NAME = "智研舱 Demo 项目"
DEMO_PROJECT_DESCRIPTION = (
    "用于 3 分钟比赛演示的预置项目空间，覆盖项目画像、证据问答、对比、记忆和输出。"
)
DEMO_BUNDLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "zhiyancang_demo"

DEMO_SOURCE_SPECS = (
    ("competition_brief.md", "竞赛评分标准"),
    ("solution_plan.md", "方案说明"),
    ("innovation_brief.md", "创新点答辩备忘"),
    ("demo_runbook.md", "演示与兜底手册"),
)
DEMO_NOTE_SPECS = (
    ("evidence_brief.md", "证据问答速览"),
    ("judge_focus.md", "评委追问清单"),
)
_DEMO_PROJECT_LOCK = asyncio.Lock()


@dataclass(frozen=True)
class DemoEvidenceSpec:
    source_title: str
    excerpt: str
    citation_label: str
    relevance_reason: str
    score: float


@dataclass(frozen=True)
class DemoAnswerBundle:
    answer: str
    confidence: float
    evidence_keys: tuple[str, ...]
    suggested_followups: tuple[str, ...]
    mode: Literal["text"] = "text"


DEMO_EVIDENCE_LIBRARY: dict[str, DemoEvidenceSpec] = {
    "coverage_brief": DemoEvidenceSpec(
        source_title="竞赛评分标准",
        excerpt=(
            "任务书第 4 节把评分拆成六项：项目理解与场景贴合、证据可靠性、"
            "对比分析质量、记忆治理、成果输出质量、演示稳定性。"
        ),
        citation_label="第 4 节评分标准",
        relevance_reason="这段内容直接定义了比赛的评分项，是回答覆盖情况的原始依据。",
        score=0.92,
    ),
    "coverage_plan": DemoEvidenceSpec(
        source_title="方案说明",
        excerpt=(
            "方案说明第 5 节逐项标注“项目空间、证据问答、多文档对比、长期记忆、"
            "成果输出、运行轨迹”均已覆盖。"
        ),
        citation_label="第 5 节覆盖情况",
        relevance_reason="这段内容把方案能力和任务书要求一一对应，能直接支撑“已覆盖哪些评分项”的回答。",
        score=0.9,
    ),
    "workspace_brief": DemoEvidenceSpec(
        source_title="竞赛评分标准",
        excerpt=(
            "任务书第 2 节要求系统围绕单个项目持续组织证据、形成记忆、生成成果，"
            "不是只完成一次性的即时问答。"
        ),
        citation_label="第 2 节赛题目标",
        relevance_reason="这段内容说明产品目标是项目级工作流，而不是聊天窗口本身。",
        score=0.89,
    ),
    "workspace_plan": DemoEvidenceSpec(
        source_title="方案说明",
        excerpt=(
            "方案说明第 2 节和第 4.1 节明确写了“以项目为一级入口”，"
            "并把总览、证据、对比、记忆、输出、运行收进同一条主线。"
        ),
        citation_label="第 2 节与第 4.1 节",
        relevance_reason="这段内容给出了为什么主入口是项目空间的直接设计依据。",
        score=0.88,
    ),
    "risk_brief": DemoEvidenceSpec(
        source_title="竞赛评分标准",
        excerpt=(
            "任务书第 6 节重点问五件事：如何证明回答可追溯、"
            "如何处理 compare 冲突、什么内容允许写入长期记忆、"
            "失败任务能否看到状态、为什么以项目空间为主入口。"
        ),
        citation_label="第 6 节评委重点关注问题",
        relevance_reason="这段内容直接定义了评委高概率追问点。",
        score=0.9,
    ),
    "risk_plan": DemoEvidenceSpec(
        source_title="方案说明",
        excerpt=(
            "方案说明第 6 节承认三类边界：compare 仍以两两对比为主、"
            "记忆治理还需要人工确认闭环、演示环境速度受模型和硬件影响。"
        ),
        citation_label="第 6 节当前风险与边界",
        relevance_reason="这段内容说明当前方案仍需人工复核和降级兜底的部分。",
        score=0.86,
    ),
    "memory_brief": DemoEvidenceSpec(
        source_title="竞赛评分标准",
        excerpt=(
            "任务书第 3.4 节要求长期记忆必须可见，每条都必须带 source_refs，"
            "未确认结论不能直接写入长期记忆。"
        ),
        citation_label="第 3.4 节长期记忆",
        relevance_reason="这段内容给出了长期记忆写入边界和可追溯要求。",
        score=0.91,
    ),
    "memory_plan": DemoEvidenceSpec(
        source_title="方案说明",
        excerpt=(
            "方案说明第 4.4 节把记忆状态分成待确认、已接受、已冻结，"
            "并强调只沉淀稳定事实和用户确认内容。"
        ),
        citation_label="第 4.4 节长期记忆",
        relevance_reason="这段内容解释了为什么记忆页需要审核状态和来源。",
        score=0.88,
    ),
    "compare_brief": DemoEvidenceSpec(
        source_title="竞赛评分标准",
        excerpt=(
            "任务书第 3.3 节要求规则文档 vs 方案文档的输出至少包含已覆盖项、"
            "缺失项、风险项、需人工确认项。"
        ),
        citation_label="第 3.3 节多文档对比",
        relevance_reason="这段内容定义了 compare 页必须展示的结构。",
        score=0.9,
    ),
    "compare_plan": DemoEvidenceSpec(
        source_title="方案说明",
        excerpt=(
            "方案说明第 4.3 节和第 7 节把 compare 作为演示第二步，"
            "用于检查规则文档与方案说明之间的覆盖、缺失和风险。"
        ),
        citation_label="第 4.3 节与第 7 节",
        relevance_reason="这段内容说明 compare 结果在演示中的位置和用途。",
        score=0.87,
    ),
    "summary_brief": DemoEvidenceSpec(
        source_title="竞赛评分标准",
        excerpt=(
            "任务书把 demo 验收口径收成五件事：问答带引用、compare 结构化、"
            "memory 带 source_refs、output 可展示、全链路稳定。"
        ),
        citation_label="第 7 节演示验收口径",
        relevance_reason="这段内容给出了演示闭环的最小通过条件。",
        score=0.88,
    ),
    "summary_plan": DemoEvidenceSpec(
        source_title="方案说明",
        excerpt=(
            "方案说明推荐的现场顺序是总览 -> 证据问答 -> compare -> memory -> outputs，"
            "目标是在 3 分钟内完成完整闭环。"
        ),
        citation_label="第 7 节推荐演示顺序",
        relevance_reason="这段内容说明了 demo 的主线流程和演示顺序。",
        score=0.86,
    ),
}


DEMO_ANSWER_LIBRARY: dict[str, DemoAnswerBundle] = {
    "coverage": DemoAnswerBundle(
        answer=(
            "当前方案已经正面覆盖六个评分维度：项目理解与场景贴合、证据可靠性、"
            "对比分析质量、记忆治理、成果输出质量、演示稳定性。"
            "任务书第 4 节给出评分项，方案说明第 5 节又把项目空间、证据问答、"
            "对比、记忆、输出和运行逐项对齐，所以 demo 时可以把这两份材料并排讲。"
        ),
        confidence=0.9,
        evidence_keys=("coverage_brief", "coverage_plan"),
        suggested_followups=(
            "为什么主入口改成项目空间而不是聊天窗口？",
            "评委最可能继续追问哪些风险？",
            "如果只保留一页演示，应该先展示哪三个环节？",
        ),
    ),
    "workspace": DemoAnswerBundle(
        answer=(
            "智研舱不是普通聊天式知识库，因为比赛要处理的是持续演进的项目上下文。"
            "任务书要求系统围绕单个项目持续组织证据、形成记忆、生成成果，"
            "方案说明也明确把项目作为一级入口，所以主叙事必须是项目空间，"
            "聊天只是项目里的一个动作，不是产品本体。"
        ),
        confidence=0.88,
        evidence_keys=("workspace_brief", "workspace_plan"),
        suggested_followups=(
            "这样设计后，证据和输出是怎么串起来的？",
            "为什么长期记忆也要挂在项目里？",
            "如果评委质疑这只是换皮聊天页，该怎么回应？",
        ),
    ),
    "risk": DemoAnswerBundle(
        answer=(
            "评委最可能追问三类风险：第一，回答是不是能回到资料而不是模型臆测；"
            "第二，compare 遇到部分覆盖和冲突描述时怎么处理；"
            "第三，长期记忆和异步任务失败有没有清晰边界。"
            "任务书第 6 节直接列了这些问题，方案说明第 6 节也承认 compare、"
            "记忆治理和演示环境速度仍有边界，所以 demo 时要主动先讲降级路径。"
        ),
        confidence=0.87,
        evidence_keys=("risk_brief", "risk_plan"),
        suggested_followups=(
            "如果现场某步失败，最稳的兜底顺序是什么？",
            "compare 里哪些项还需要人工确认？",
            "长期记忆为什么不能直接写入未确认结论？",
        ),
    ),
    "memory": DemoAnswerBundle(
        answer=(
            "长期记忆的作用是把项目里的稳定事实沉淀下来，供后续问答、对比和输出重复复用。"
            "但它不能什么都收。任务书要求每条记忆都带 source_refs，未确认结论不能直接写入；"
            "方案说明进一步把状态分成待确认、已接受、已冻结，所以记忆中心本质上是治理界面，"
            "不是自动摘要垃圾桶。"
        ),
        confidence=0.89,
        evidence_keys=("memory_brief", "memory_plan"),
        suggested_followups=(
            "现在 demo 里哪几条记忆最适合现场展示？",
            "什么内容应该留在问答里，不该写进长期记忆？",
            "如果一条记忆来源冲突，状态应该怎么处理？",
        ),
    ),
    "compare": DemoAnswerBundle(
        answer=(
            "规则文档和方案说明之间的 compare，核心不是给一段总结，而是拆成覆盖项、缺失项、"
            "风险项和待确认项。任务书把这四类结构写成了必选能力，方案说明也把 compare 放到"
            "演示主线第二步，所以现场要重点展示“哪些要求已经覆盖、哪些地方还要人工补证”。"
        ),
        confidence=0.88,
        evidence_keys=("compare_brief", "compare_plan"),
        suggested_followups=(
            "当前 compare 结果里最值得评委追问的缺失项是什么？",
            "如果 compare 失败，前端应该给出什么状态提示？",
            "哪些差异现在只能做两两对比，不能自动合并？",
        ),
    ),
    "summary": DemoAnswerBundle(
        answer=(
            "这套 demo 的完整主线是：先从项目总览建立场景，再在证据页证明回答可追溯，"
            "然后进入 compare 展示结构化分析，接着到 memory 证明结论可治理，"
            "最后用 outputs 和 runs 交付产物并解释执行轨迹。"
            "任务书第 7 节定义了最小验收口径，方案说明第 7 节给了推荐演示顺序，"
            "所以现场只要沿这条线走，3 分钟内就能形成闭环。"
        ),
        confidence=0.86,
        evidence_keys=("summary_brief", "summary_plan"),
        suggested_followups=(
            "这一条演示链里最先该点开的页面是哪一个？",
            "如果只剩一分钟，哪些页面必须保住？",
            "当前方案覆盖了哪些评分项？",
        ),
    ),
}


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
    chunk_embeddings = (
        await generate_embeddings(chunks, task_type="retrieval_document")
        if chunks
        else []
    )
    chunk_metadata = [
        {
            "filename": filename,
            "chunk_kind": "demo_source_chunk",
        }
        for _ in chunks
    ]
    await ai_index_store.upsert_source_chunks(
        source_id,
        source.title,
        chunks,
        chunk_embeddings,
        [project_id],
        updated_at=source.updated,
        chunk_metadata=chunk_metadata,
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
    note_text = "\n\n".join(
        part for part in [note.title or "", note.content or ""] if part.strip()
    )
    embedding = (
        await generate_embedding(note_text, task_type="retrieval_document")
        if note_text.strip()
        else None
    )
    await ai_index_store.upsert_note_index(
        str(note.id or ""),
        note.title,
        note.content or "",
        embedding=embedding,
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


def _demo_answer_key(question: str) -> str:
    normalized = " ".join(question.strip().split()).lower()
    if any(token in normalized for token in ("覆盖", "评分", "score")):
        return "coverage"
    if any(
        token in normalized
        for token in ("为什么", "聊天", "知识库", "主入口", "项目空间")
    ):
        return "workspace"
    if any(token in normalized for token in ("风险", "评委", "追问", "失败")):
        return "risk"
    if any(token in normalized for token in ("记忆", "memory", "source_refs")):
        return "memory"
    if any(token in normalized for token in ("对比", "compare", "缺什么", "缺失")):
        return "compare"
    return "summary"


def _citation_text(source_title: str, source_id: str, citation_label: str) -> str:
    return f"引用：{source_title} | {citation_label} | 内部引用：[{source_id}]"


def _build_demo_cards(
    *,
    project_id: str,
    thread_id: str,
    evidence_keys: tuple[str, ...],
    sources_by_title: dict[str, Source],
    scoped_source_ids: Optional[list[str]] = None,
) -> list[EvidenceCard]:
    allowed_ids = set(scoped_source_ids or [])
    cards: list[EvidenceCard] = []

    for index, key in enumerate(evidence_keys, start=1):
        spec = DEMO_EVIDENCE_LIBRARY[key]
        source = sources_by_title.get(spec.source_title)
        source_id = str(source.id or "") if source and source.id else ""
        if not source_id:
            continue
        if allowed_ids and source_id not in allowed_ids:
            continue

        cards.append(
            EvidenceCard(
                id=f"evidence:{project_id}:{thread_id}:{index}",
                project_id=project_id,
                thread_id=thread_id,
                source_name=spec.source_title,
                source_id=source_id,
                page_no=None,
                excerpt=spec.excerpt,
                citation_text=_citation_text(
                    spec.source_title,
                    source_id,
                    spec.citation_label,
                ),
                internal_ref=source_id,
                relevance_reason=spec.relevance_reason,
                image_thumb=None,
                score=spec.score,
            )
        )

    return cards


async def is_demo_project(project_id: str) -> bool:
    notebook = await Notebook.get(project_id)
    if not notebook:
        return False

    return (
        notebook.name == DEMO_PROJECT_NAME
        and (notebook.description or "") == DEMO_PROJECT_DESCRIPTION
    )


async def build_demo_ask_response(
    project_id: str,
    question: str,
    *,
    thread_id: str,
    scoped_source_ids: Optional[list[str]] = None,
) -> tuple[DemoAnswerBundle, list[EvidenceCard]]:
    notebook = await Notebook.get(project_id)
    if not notebook:
        raise NotFoundError("Demo project not found")

    sources = await notebook.get_sources()
    if len(sources) < len(DEMO_SOURCE_SPECS):
        sources = await _ensure_demo_sources(project_id)

    sources_by_title = {
        " ".join(str(source.title or "").strip().split()): source for source in sources
    }
    answer_key = _demo_answer_key(question)
    bundle = DEMO_ANSWER_LIBRARY[answer_key]
    cards = _build_demo_cards(
        project_id=project_id,
        thread_id=thread_id,
        evidence_keys=bundle.evidence_keys,
        sources_by_title=sources_by_title,
        scoped_source_ids=scoped_source_ids,
    )

    if cards:
        return bundle, cards

    fallback_bundle = DemoAnswerBundle(
        answer=(
            "当前 demo 预置资料里没有命中你选定范围的证据。"
            "先取消范围限制，或者优先追问评分项、项目空间、compare、记忆和演示风险这些主线问题。"
        ),
        confidence=0.34,
        evidence_keys=(),
        suggested_followups=(
            "当前方案覆盖了哪些评分项？",
            "为什么主入口是项目空间？",
            "评委最可能追问哪些风险？",
        ),
    )
    return fallback_bundle, []


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
    "DEMO_ANSWER_LIBRARY",
    "DEMO_EVIDENCE_LIBRARY",
    "DemoAnswerBundle",
    "DemoEvidenceSpec",
    "build_demo_ask_response",
    "ensure_demo_project",
    "is_demo_project",
]
