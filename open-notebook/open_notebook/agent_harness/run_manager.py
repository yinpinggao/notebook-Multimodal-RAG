from __future__ import annotations

from typing import Any

from open_notebook.agent_harness.context_packer import (
    build_input_summary,
    pack_json_payload,
)
from open_notebook.agent_harness.guardrails import (
    compact_text,
    dedupe_strings,
    ensure_supported_run_type,
    normalize_trace_refs,
)
from open_notebook.agent_harness.planner import plan_project_task
from open_notebook.agent_harness.trace_store import (
    append_agent_step,
    create_agent_run,
    create_step_id,
    load_agent_run,
    update_agent_run,
    utc_now,
)
from open_notebook.domain.runs import AgentRun, AgentStep
from open_notebook.exceptions import NotFoundError


async def _merge_run_fields(
    run_id: str,
    *,
    tool_calls: list[str] | None = None,
    evidence_reads: list[str] | None = None,
    memory_writes: list[str] | None = None,
    outputs: list[str] | None = None,
) -> AgentRun:
    current = await load_agent_run(run_id)
    if not current:
        raise NotFoundError("Run not found")

    updates: dict[str, Any] = {}
    if tool_calls:
        updates["tool_calls"] = dedupe_strings([*current.tool_calls, *tool_calls], limit=32)
    if evidence_reads:
        updates["evidence_reads"] = normalize_trace_refs(
            [*current.evidence_reads, *evidence_reads],
            limit=48,
        )
    if memory_writes:
        updates["memory_writes"] = dedupe_strings(
            [*current.memory_writes, *memory_writes],
            limit=48,
        )
    if outputs:
        updates["outputs"] = dedupe_strings([*current.outputs, *outputs], limit=48)

    if not updates:
        return current

    return await update_agent_run(run_id, **updates)


async def create_project_run(
    project_id: str,
    *,
    run_type: str,
    input_json: dict[str, Any] | None = None,
    input_summary: str | None = None,
) -> AgentRun:
    normalized_run_type = ensure_supported_run_type(run_type)
    route = plan_project_task(normalized_run_type, input_json=input_json or {})
    run = await create_agent_run(
        project_id,
        run_type=normalized_run_type,
        input_summary=input_summary or build_input_summary(normalized_run_type, input_json),
        selected_skill=route.selected_skill,
        input_json=pack_json_payload(input_json or {}),
        status="queued",
    )
    await record_step(
        run.id,
        title="选择执行技能",
        step_type="plan",
        status="completed",
        agent_name="project_harness",
        output_json={
            "selected_skill": route.selected_skill,
            "planning_mode": route.planning_mode,
            "reason": route.reason,
        },
    )
    return await load_agent_run(run.id) or run


async def mark_run_running(run_id: str) -> AgentRun:
    current = await load_agent_run(run_id)
    if not current:
        raise NotFoundError("Run not found")

    updates: dict[str, Any] = {"status": "running"}
    if not current.started_at:
        updates["started_at"] = utc_now()
    return await update_agent_run(run_id, **updates)


async def mark_run_completed(
    run_id: str,
    *,
    output_json: dict[str, Any] | None = None,
    tool_calls: list[str] | None = None,
    evidence_reads: list[str] | None = None,
    memory_writes: list[str] | None = None,
    outputs: list[str] | None = None,
) -> AgentRun:
    current = await _merge_run_fields(
        run_id,
        tool_calls=tool_calls,
        evidence_reads=evidence_reads,
        memory_writes=memory_writes,
        outputs=outputs,
    )
    updates: dict[str, Any] = {
        "status": "completed",
        "completed_at": utc_now(),
        "failure_reason": None,
    }
    if not current.started_at:
        updates["started_at"] = current.created_at
    if output_json is not None:
        updates["output_json"] = pack_json_payload(output_json)
    return await update_agent_run(run_id, **updates)


async def mark_run_failed(run_id: str, error_message: str) -> AgentRun:
    current = await load_agent_run(run_id)
    if not current:
        raise NotFoundError("Run not found")

    updates = {
        "status": "failed",
        "completed_at": utc_now(),
        "failure_reason": compact_text(error_message, limit=280),
    }
    if not current.started_at:
        updates["started_at"] = current.created_at
    return await update_agent_run(run_id, **updates)


async def record_step(
    run_id: str,
    *,
    title: str,
    step_type: str,
    status: str = "completed",
    agent_name: str | None = None,
    tool_name: str | None = None,
    input_json: dict[str, Any] | None = None,
    output_json: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
    memory_refs: list[str] | None = None,
    output_refs: list[str] | None = None,
    error: str | None = None,
) -> AgentStep:
    current = await load_agent_run(run_id)
    if not current:
        raise NotFoundError("Run not found")

    timestamp = utc_now()
    step = AgentStep(
        id=create_step_id(),
        run_id=run_id,
        step_index=len(current.steps),
        title=title,
        type=step_type,
        status=status,
        agent_name=agent_name,
        tool_name=tool_name,
        started_at=timestamp if status in {"running", "completed", "failed"} else None,
        completed_at=timestamp if status in {"completed", "failed", "skipped"} else None,
        input_json=pack_json_payload(input_json) if input_json is not None else None,
        output_json=pack_json_payload(output_json) if output_json is not None else None,
        evidence_refs=normalize_trace_refs(evidence_refs or [], limit=24),
        memory_refs=dedupe_strings(memory_refs or [], limit=24),
        output_refs=dedupe_strings(output_refs or [], limit=24),
        error=compact_text(error, limit=280) if error else None,
    )
    await append_agent_step(run_id, step)
    return step


async def record_tool_call(
    run_id: str,
    *,
    title: str,
    tool_name: str,
    agent_name: str | None = None,
    input_json: dict[str, Any] | None = None,
    output_json: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
    output_refs: list[str] | None = None,
    error: str | None = None,
    status: str = "completed",
) -> AgentStep:
    step = await record_step(
        run_id,
        title=title,
        step_type="tool_call",
        status=status,
        agent_name=agent_name,
        tool_name=tool_name,
        input_json=input_json,
        output_json=output_json,
        evidence_refs=evidence_refs,
        output_refs=output_refs,
        error=error,
    )
    await _merge_run_fields(
        run_id,
        tool_calls=[tool_name],
        evidence_reads=evidence_refs,
        outputs=output_refs,
    )
    return step


async def record_evidence_read(
    run_id: str,
    *,
    title: str,
    agent_name: str | None = None,
    input_json: dict[str, Any] | None = None,
    output_json: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
) -> AgentStep:
    step = await record_step(
        run_id,
        title=title,
        step_type="evidence_read",
        status="completed",
        agent_name=agent_name,
        input_json=input_json,
        output_json=output_json,
        evidence_refs=evidence_refs,
    )
    await _merge_run_fields(run_id, evidence_reads=evidence_refs)
    return step


async def record_memory_write(
    run_id: str,
    *,
    title: str,
    agent_name: str | None = None,
    output_json: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
    memory_refs: list[str] | None = None,
) -> AgentStep:
    step = await record_step(
        run_id,
        title=title,
        step_type="memory_write",
        status="completed",
        agent_name=agent_name,
        output_json=output_json,
        evidence_refs=evidence_refs,
        memory_refs=memory_refs,
    )
    await _merge_run_fields(
        run_id,
        evidence_reads=evidence_refs,
        memory_writes=memory_refs,
    )
    return step


async def record_answer_step(
    run_id: str,
    *,
    title: str,
    agent_name: str | None = None,
    output_json: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
    output_refs: list[str] | None = None,
) -> AgentStep:
    step = await record_step(
        run_id,
        title=title,
        step_type="answer",
        status="completed",
        agent_name=agent_name,
        output_json=output_json,
        evidence_refs=evidence_refs,
        output_refs=output_refs,
    )
    await _merge_run_fields(
        run_id,
        evidence_reads=evidence_refs,
        outputs=output_refs,
    )
    return step


__all__ = [
    "create_project_run",
    "mark_run_completed",
    "mark_run_failed",
    "mark_run_running",
    "record_answer_step",
    "record_evidence_read",
    "record_memory_write",
    "record_step",
    "record_tool_call",
]
