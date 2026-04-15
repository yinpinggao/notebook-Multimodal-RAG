import os

DEFAULT_JOB_BACKEND = "arq"


def get_job_backend() -> str:
    raw = os.getenv("OPEN_NOTEBOOK_JOB_BACKEND", DEFAULT_JOB_BACKEND).strip().lower()
    if raw in {"arq", "in_memory"}:
        return raw
    return DEFAULT_JOB_BACKEND


def get_redis_url() -> str:
    return os.getenv("OPEN_NOTEBOOK_REDIS_URL", "").strip()


def redis_is_configured() -> bool:
    return bool(get_redis_url())


def use_in_memory_jobs() -> bool:
    backend = get_job_backend()
    if backend == "in_memory":
        return True
    return backend != "arq" or not redis_is_configured()
