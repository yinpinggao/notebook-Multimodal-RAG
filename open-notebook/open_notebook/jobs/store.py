import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from loguru import logger

from open_notebook.seekdb import seekdb_business_store, seekdb_client


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


@dataclass
class JobStatus:
    job_id: str
    status: str
    result: Optional[dict[str, Any]]
    error_message: Optional[str]
    created: Optional[str]
    updated: Optional[str]
    progress: Optional[dict[str, Any]]


@dataclass
class JobRecord(JobStatus):
    app_name: str
    command_name: str
    args: dict[str, Any]
    retry_count: int
    started_at: Optional[str]
    completed_at: Optional[str]


_running_tasks: dict[str, asyncio.Task[Any]] = {}


class JobStore:
    def now(self) -> str:
        return _now()

    async def create_job(
        self,
        app_name: str,
        command_name: str,
        args: dict[str, Any],
        *,
        job_id: Optional[str] = None,
    ) -> str:
        await seekdb_business_store.ensure_schema()
        job_id = job_id or f"command:{uuid4().hex}"
        now = _now()
        await seekdb_client.execute(
            """
            INSERT INTO jobs (
                id, app_name, command_name, status, args_json,
                result_json, error_message, progress_json, retry_count,
                created, updated, started_at, completed_at
            ) VALUES (%s, %s, %s, %s, %s, NULL, NULL, NULL, 0, %s, %s, NULL, NULL)
            """,
            (job_id, app_name, command_name, "queued", _json_dumps(args), now, now),
        )
        return job_id

    async def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        progress: Optional[dict[str, Any]] = None,
        retry_count: Optional[int] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> None:
        assignments = ["updated = %s"]
        params: list[Any] = [_now()]
        if status is not None:
            assignments.append("status = %s")
            params.append(status)
        if result is not None:
            assignments.append("result_json = %s")
            params.append(_json_dumps(result))
        if error_message is not None:
            assignments.append("error_message = %s")
            params.append(error_message)
        if progress is not None:
            assignments.append("progress_json = %s")
            params.append(_json_dumps(progress))
        if retry_count is not None:
            assignments.append("retry_count = %s")
            params.append(retry_count)
        if started_at is not None:
            assignments.append("started_at = %s")
            params.append(started_at)
        if completed_at is not None:
            assignments.append("completed_at = %s")
            params.append(completed_at)
        params.append(job_id)
        await seekdb_client.execute(
            f"UPDATE jobs SET {', '.join(assignments)} WHERE id = %s",
            tuple(params),
        )

    async def get_job(self, job_id: str) -> Optional[JobStatus]:
        row = await seekdb_client.fetch_one("SELECT * FROM jobs WHERE id = %s", (job_id,))
        if not row:
            return None
        return JobStatus(
            job_id=str(row.get("id") or job_id),
            status=str(row.get("status") or "unknown"),
            result=_json_loads(row.get("result_json"), None),
            error_message=row.get("error_message"),
            created=str(row.get("created")) if row.get("created") else None,
            updated=str(row.get("updated")) if row.get("updated") else None,
            progress=_json_loads(row.get("progress_json"), None),
        )

    async def get_job_record(self, job_id: str) -> Optional[JobRecord]:
        row = await seekdb_client.fetch_one("SELECT * FROM jobs WHERE id = %s", (job_id,))
        if not row:
            return None
        return JobRecord(
            job_id=str(row.get("id") or job_id),
            app_name=str(row.get("app_name") or ""),
            command_name=str(row.get("command_name") or ""),
            status=str(row.get("status") or "unknown"),
            args=_json_loads(row.get("args_json"), {}),
            result=_json_loads(row.get("result_json"), None),
            error_message=row.get("error_message"),
            created=str(row.get("created")) if row.get("created") else None,
            updated=str(row.get("updated")) if row.get("updated") else None,
            progress=_json_loads(row.get("progress_json"), None),
            retry_count=int(row.get("retry_count") or 0),
            started_at=str(row.get("started_at")) if row.get("started_at") else None,
            completed_at=str(row.get("completed_at"))
            if row.get("completed_at")
            else None,
        )

    async def list_jobs(
        self,
        *,
        command_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if command_filter:
            clauses.append("command_name = %s")
            params.append(command_filter)
        if status_filter:
            clauses.append("status = %s")
            params.append(status_filter)
        query = "SELECT * FROM jobs"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created DESC LIMIT %s"
        params.append(limit)
        rows = await seekdb_client.fetch_all(query, tuple(params))
        return [
            {
                "job_id": row.get("id"),
                "app_name": row.get("app_name"),
                "command_name": row.get("command_name"),
                "status": row.get("status"),
                "args": _json_loads(row.get("args_json"), {}),
                "result": _json_loads(row.get("result_json"), None),
                "error_message": row.get("error_message"),
                "created": str(row.get("created")) if row.get("created") else None,
                "updated": str(row.get("updated")) if row.get("updated") else None,
                "started_at": str(row.get("started_at"))
                if row.get("started_at")
                else None,
                "completed_at": str(row.get("completed_at"))
                if row.get("completed_at")
                else None,
                "retry_count": int(row.get("retry_count") or 0),
                "progress": _json_loads(row.get("progress_json"), None),
            }
            for row in rows
        ]

    async def cancel_job(self, job_id: str) -> bool:
        task = _running_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        await self.update_job(
            job_id,
            status="cancelled",
            completed_at=_now(),
            error_message="Cancelled by user",
        )
        return True

    async def run_in_background(
        self,
        job_id: str,
        runner: Callable[[str], Awaitable[dict[str, Any]]],
    ) -> None:
        async def _run() -> None:
            await self.update_job(job_id, status="running", started_at=_now())
            try:
                result = await runner(job_id)
                await self.update_job(
                    job_id,
                    status="completed",
                    result=result,
                    completed_at=_now(),
                    error_message=None,
                )
            except asyncio.CancelledError:
                await self.update_job(
                    job_id,
                    status="cancelled",
                    completed_at=_now(),
                    error_message="Cancelled by user",
                )
                raise
            except Exception as exc:
                logger.exception(exc)
                await self.update_job(
                    job_id,
                    status="failed",
                    completed_at=_now(),
                    error_message=str(exc),
                )
            finally:
                _running_tasks.pop(job_id, None)

        task = asyncio.create_task(_run())
        _running_tasks[job_id] = task


job_store = JobStore()
