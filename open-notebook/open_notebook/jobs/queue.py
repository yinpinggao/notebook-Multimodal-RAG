import asyncio
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlparse

from loguru import logger

from .settings import get_redis_url, use_in_memory_jobs
from .store import job_store

try:  # pragma: no cover - optional dependency in local dev
    from arq import create_pool
    from arq.connections import RedisSettings
    from arq.jobs import Job as ArqJob
except Exception:  # pragma: no cover - optional dependency in local dev
    create_pool = None
    RedisSettings = None
    ArqJob = None


def arq_is_available() -> bool:
    return create_pool is not None and RedisSettings is not None and ArqJob is not None


def _build_redis_settings():
    if not arq_is_available():
        raise RuntimeError(
            "ARQ support requires the optional 'arq' package to be installed."
        )

    redis_url = get_redis_url()
    if not redis_url:
        raise RuntimeError(
            "OPEN_NOTEBOOK_REDIS_URL is required when OPEN_NOTEBOOK_JOB_BACKEND=arq."
        )

    if hasattr(RedisSettings, "from_dsn"):
        return RedisSettings.from_dsn(redis_url)

    parsed = urlparse(redis_url)
    database = parsed.path.lstrip("/") or "0"
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        username=parsed.username or None,
        password=parsed.password or None,
        database=int(database),
        ssl=parsed.scheme == "rediss",
    )


class JobQueue:
    def __init__(self) -> None:
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}

    async def enqueue(
        self,
        job_id: str,
        inline_runner: Optional[Callable[[str], Awaitable[dict[str, Any]]]] = None,
    ) -> None:
        if not use_in_memory_jobs():
            if not arq_is_available():
                raise RuntimeError(
                    "OPEN_NOTEBOOK_JOB_BACKEND=arq but the 'arq' package is not installed."
                )
            await self._enqueue_arq(job_id)
            return

        if inline_runner is None:
            raise RuntimeError("Inline runner is required for in-memory job execution.")
        logger.warning(
            f"Running job {job_id} in in-memory mode. Configure "
            "OPEN_NOTEBOOK_REDIS_URL and install 'arq' to enable the external worker backend."
        )
        await self._enqueue_in_memory(job_id, inline_runner)

    async def cancel(self, job_id: str) -> bool:
        if not use_in_memory_jobs() and arq_is_available():
            try:
                redis = await create_pool(_build_redis_settings())
                try:
                    await ArqJob(job_id, redis).abort(timeout=5)
                finally:
                    await redis.close()
            except Exception as e:
                logger.warning(f"Failed to abort ARQ job {job_id}: {e}")

        task = self._running_tasks.get(job_id)
        if task and not task.done():
            task.cancel()

        await job_store.update_job(
            job_id,
            status="cancelled",
            completed_at=job_store.now(),
            error_message="Cancelled by user",
        )
        return True

    async def _enqueue_in_memory(
        self,
        job_id: str,
        inline_runner: Callable[[str], Awaitable[dict[str, Any]]],
    ) -> None:
        async def _run() -> None:
            try:
                await inline_runner(job_id)
            finally:
                self._running_tasks.pop(job_id, None)

        task = asyncio.create_task(_run())
        self._running_tasks[job_id] = task

    async def _enqueue_arq(self, job_id: str) -> None:
        redis = await create_pool(_build_redis_settings())
        try:
            await redis.enqueue_job(
                "run_registered_command_job",
                job_id,
                _job_id=job_id,
            )
        finally:
            await redis.close()


job_queue = JobQueue()
