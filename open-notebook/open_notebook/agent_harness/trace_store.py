from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.domain.projects import RecentRunSummary
from open_notebook.domain.runs import AgentRun, AgentStep
from open_notebook.exceptions import NotFoundError
from open_notebook.seekdb import seekdb_business_store


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectRunIndex(_Model):
    project_id: str
    run_ids: list[str] = Field(default_factory=list)


def create_run_id() -> str:
    return f"run:{uuid4().hex[:12]}"


def create_step_id() -> str:
    return f"step:{uuid4().hex[:12]}"


def project_run_record_id(run_id: str) -> str:
    return f"project_run:{run_id}"


def project_run_index_record_id(project_id: str) -> str:
    return f"project_run_index:{project_id}"


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _strip_singleton_metadata(data: dict, *, public_id: str | None = None) -> dict:
    payload = {
        key: value for key, value in data.items() if key not in {"created", "updated"}
    }
    if public_id is None:
        payload.pop("id", None)
    else:
        payload["id"] = public_id
    return payload


def _dedupe_ids(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
    return deduped


def _run_activity_at(run: AgentRun) -> str:
    return run.completed_at or run.started_at or run.created_at


async def _load_project_run_index(project_id: str) -> ProjectRunIndex:
    data = await seekdb_business_store.get_singleton(
        project_run_index_record_id(project_id)
    )
    if not data:
        return ProjectRunIndex(project_id=project_id)
    return ProjectRunIndex.model_validate(_strip_singleton_metadata(data))


async def _save_project_run_index(index: ProjectRunIndex) -> ProjectRunIndex:
    saved = await seekdb_business_store.upsert_singleton(
        project_run_index_record_id(index.project_id),
        index.model_dump(mode="json"),
    )
    return ProjectRunIndex.model_validate(_strip_singleton_metadata(saved))


async def _register_project_run(project_id: str, run_id: str) -> None:
    index = await _load_project_run_index(project_id)
    index.run_ids = _dedupe_ids([run_id, *index.run_ids])
    await _save_project_run_index(index)


async def save_agent_run(run: AgentRun) -> AgentRun:
    saved = await seekdb_business_store.upsert_singleton(
        project_run_record_id(run.id),
        run.model_dump(mode="json"),
    )
    return AgentRun.model_validate(_strip_singleton_metadata(saved, public_id=run.id))


async def load_agent_run(run_id: str) -> AgentRun | None:
    data = await seekdb_business_store.get_singleton(project_run_record_id(run_id))
    if not data:
        return None
    return AgentRun.model_validate(_strip_singleton_metadata(data, public_id=run_id))


async def load_agent_run_for_project(project_id: str, run_id: str) -> AgentRun:
    run = await load_agent_run(run_id)
    if not run or run.project_id != project_id:
        raise NotFoundError("Run not found")
    return run


async def create_agent_run(
    project_id: str,
    *,
    run_type: str,
    input_summary: str | None = None,
    selected_skill: str | None = None,
    input_json: dict | None = None,
    status: str = "queued",
) -> AgentRun:
    now = utc_now()
    run = AgentRun(
        id=create_run_id(),
        project_id=project_id,
        status=status,
        run_type=run_type,
        input_summary=input_summary,
        selected_skill=selected_skill,
        input_json=input_json,
        output_json=None,
        created_at=now,
        started_at=now if status == "running" else None,
        completed_at=None,
        tool_calls=[],
        evidence_reads=[],
        memory_writes=[],
        outputs=[],
        steps=[],
        failure_reason=None,
    )
    saved = await save_agent_run(run)
    await _register_project_run(project_id, saved.id)
    return saved


async def update_agent_run(run_id: str, **changes) -> AgentRun:
    current = await load_agent_run(run_id)
    if not current:
        raise NotFoundError("Run not found")

    payload = current.model_dump(mode="json")
    payload.update(changes)
    return await save_agent_run(AgentRun.model_validate(payload))


async def append_agent_step(run_id: str, step: AgentStep) -> AgentRun:
    current = await load_agent_run(run_id)
    if not current:
        raise NotFoundError("Run not found")

    steps = [*current.steps, step]
    return await update_agent_run(run_id, steps=steps)


async def list_project_runs(
    project_id: str,
    *,
    limit: int = 50,
) -> list[AgentRun]:
    index = await _load_project_run_index(project_id)
    runs: list[AgentRun] = []
    for run_id in index.run_ids:
        run = await load_agent_run(run_id)
        if not run or run.project_id != project_id:
            continue
        runs.append(run)

    runs.sort(key=_run_activity_at, reverse=True)
    return runs[:limit]


async def list_recent_run_summaries(
    project_id: str,
    *,
    limit: int = 5,
) -> list[RecentRunSummary]:
    runs = await list_project_runs(project_id, limit=limit)
    return [
        RecentRunSummary(
            id=run.id,
            run_type=run.run_type,
            status=run.status,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]


async def get_project_last_run_at(project_id: str) -> str | None:
    runs = await list_project_runs(project_id, limit=1)
    if not runs:
        return None
    return _run_activity_at(runs[0])


__all__ = [
    "append_agent_step",
    "create_agent_run",
    "create_run_id",
    "create_step_id",
    "get_project_last_run_at",
    "list_project_runs",
    "list_recent_run_summaries",
    "load_agent_run",
    "load_agent_run_for_project",
    "save_agent_run",
    "update_agent_run",
    "utc_now",
]
