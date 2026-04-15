import sys
from pathlib import Path

from loguru import logger

from .commands import run_registered_command_job
from .queue import _build_redis_settings, arq_is_available

try:  # pragma: no cover - optional dependency in local dev
    from arq.worker import run_worker
except Exception:  # pragma: no cover - optional dependency in local dev
    run_worker = None


async def worker_startup(ctx) -> None:
    del ctx
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    import commands  # noqa: F401

    logger.info("Open Notebook worker loaded command registry")


class WorkerSettings:
    functions = [run_registered_command_job]
    on_startup = worker_startup
    max_tries = 1
    job_timeout = 60 * 60
    redis_settings = None


def main() -> None:
    if not arq_is_available() or run_worker is None:
        raise RuntimeError(
            "Worker requires the optional 'arq' package to be installed."
        )
    WorkerSettings.redis_settings = _build_redis_settings()
    run_worker(WorkerSettings)
