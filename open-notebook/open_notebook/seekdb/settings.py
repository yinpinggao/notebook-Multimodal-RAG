import os

DEFAULT_AI_CONFIG_BACKEND = "seekdb"
DEFAULT_SEARCH_BACKEND = "seekdb"
DEFAULT_SEEKDB_POOL_SIZE = 5
DEFAULT_SEEKDB_TIMEOUT_SECONDS = 10
DEFAULT_MULTIMODAL_INDEXING = "best_effort"
DEFAULT_PAGE_IMAGE_CACHE_DIR = "./data/page-cache"
DEFAULT_VLM_MAX_PAGES_PER_SOURCE = 50
DEFAULT_VLM_MIN_TEXT_CHARS = 300


def _normalized_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().lower()


def get_ai_config_backend() -> str:
    return _normalized_env(
        "OPEN_NOTEBOOK_AI_CONFIG_BACKEND",
        os.getenv("AI_CONFIG_BACKEND", DEFAULT_AI_CONFIG_BACKEND),
    )


def get_search_backend() -> str:
    return _normalized_env(
        "OPEN_NOTEBOOK_SEARCH_BACKEND",
        os.getenv("SEARCH_BACKEND", DEFAULT_SEARCH_BACKEND),
    )


def use_seekdb_for_ai_config() -> bool:
    return get_ai_config_backend() == "seekdb"


def use_seekdb_for_search() -> bool:
    return get_search_backend() == "seekdb"


def get_seekdb_dsn() -> str:
    return os.getenv("OPEN_NOTEBOOK_SEEKDB_DSN", "").strip()


def get_seekdb_pool_size() -> int:
    raw = os.getenv(
        "OPEN_NOTEBOOK_SEEKDB_POOL_SIZE", str(DEFAULT_SEEKDB_POOL_SIZE)
    ).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_SEEKDB_POOL_SIZE


def get_seekdb_timeout_seconds() -> int:
    raw = os.getenv(
        "OPEN_NOTEBOOK_SEEKDB_TIMEOUT_SECONDS",
        str(DEFAULT_SEEKDB_TIMEOUT_SECONDS),
    ).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_SEEKDB_TIMEOUT_SECONDS


def seekdb_is_configured() -> bool:
    return bool(get_seekdb_dsn())


def get_page_image_cache_dir() -> str:
    return os.getenv(
        "OPEN_NOTEBOOK_PAGE_IMAGE_CACHE_DIR", DEFAULT_PAGE_IMAGE_CACHE_DIR
    ).strip() or DEFAULT_PAGE_IMAGE_CACHE_DIR


def get_multimodal_indexing_mode() -> str:
    mode = _normalized_env(
        "OPEN_NOTEBOOK_MULTIMODAL_INDEXING",
        DEFAULT_MULTIMODAL_INDEXING,
    )
    if mode not in {"off", "best_effort", "required"}:
        return DEFAULT_MULTIMODAL_INDEXING
    return mode


def multimodal_indexing_enabled() -> bool:
    return get_multimodal_indexing_mode() != "off"


def require_multimodal_indexing() -> bool:
    return get_multimodal_indexing_mode() == "required"


def get_vlm_max_pages_per_source() -> int:
    raw = os.getenv(
        "OPEN_NOTEBOOK_VLM_MAX_PAGES_PER_SOURCE",
        str(DEFAULT_VLM_MAX_PAGES_PER_SOURCE),
    ).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_VLM_MAX_PAGES_PER_SOURCE


def get_vlm_min_text_chars() -> int:
    raw = os.getenv(
        "OPEN_NOTEBOOK_VLM_MIN_TEXT_CHARS",
        str(DEFAULT_VLM_MIN_TEXT_CHARS),
    ).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_VLM_MIN_TEXT_CHARS
