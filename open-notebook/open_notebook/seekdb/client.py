import asyncio
from dataclasses import dataclass
from typing import Any, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

from loguru import logger

from open_notebook.exceptions import ConfigurationError, DatabaseOperationError

from .settings import (
    get_seekdb_dsn,
    get_seekdb_timeout_seconds,
    use_seekdb_for_ai_config,
    use_seekdb_for_search,
)

try:
    import pymysql
    from pymysql.cursors import DictCursor
except Exception:  # pragma: no cover - optional dependency
    pymysql = None
    DictCursor = None


@dataclass
class SeekDBConnectionConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"
    connect_timeout: int = 10


def _requires_seekdb() -> bool:
    return use_seekdb_for_ai_config() or use_seekdb_for_search()


def _parse_seekdb_dsn() -> SeekDBConnectionConfig:
    dsn = get_seekdb_dsn()
    if not dsn:
        raise ConfigurationError(
            "OPEN_NOTEBOOK_SEEKDB_DSN is required when SeekDB backends are enabled."
        )

    parsed = urlparse(dsn)
    if not parsed.hostname or not parsed.path:
        raise ConfigurationError(
            "OPEN_NOTEBOOK_SEEKDB_DSN must include host and database name."
        )

    query = parse_qs(parsed.query)
    charset = query.get("charset", ["utf8mb4"])[0]

    return SeekDBConnectionConfig(
        host=parsed.hostname,
        port=parsed.port or 2881,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=parsed.path.lstrip("/"),
        charset=charset,
        connect_timeout=get_seekdb_timeout_seconds(),
    )


class SeekDBClient:
    def __init__(self) -> None:
        self._schema_lock = asyncio.Lock()
        self._schema_initialized = False

    def _require_driver(self) -> None:
        if pymysql is None or DictCursor is None:
            raise ConfigurationError(
                "SeekDB support requires the optional 'pymysql' package to be installed."
            )

    def _connect(self, include_database: bool = True):
        self._require_driver()
        config = _parse_seekdb_dsn()
        kwargs = dict(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            charset=config.charset,
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=config.connect_timeout,
        )
        if include_database:
            kwargs["database"] = config.database
        return pymysql.connect(**kwargs)

    async def _run(self, fn, *args, **kwargs):
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except ConfigurationError:
            raise
        except Exception as e:
            raise DatabaseOperationError(f"SeekDB operation failed: {e}") from e

    def _execute_sync(
        self,
        query: str,
        params: Optional[Iterable[Any]] = None,
        fetch: str = "all",
        many: bool = False,
    ):
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                if many:
                    cursor.executemany(query, list(params or []))
                else:
                    cursor.execute(query, params)

                if fetch == "all":
                    return list(cursor.fetchall())
                if fetch == "one":
                    return cursor.fetchone()
                return cursor.rowcount
        finally:
            conn.close()

    def _ensure_database_sync(self) -> None:
        config = _parse_seekdb_dsn()
        conn = self._connect(include_database=False)
        try:
            with conn.cursor() as cursor:
                database_name = config.database.replace("`", "")
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}`")
        finally:
            conn.close()

    def fetch_all_sync(
        self, query: str, params: Optional[Iterable[Any]] = None
    ) -> list[dict[str, Any]]:
        self._ensure_database_sync()
        return self._execute_sync(query, params, "all")

    def fetch_one_sync(
        self, query: str, params: Optional[Iterable[Any]] = None
    ) -> Optional[dict[str, Any]]:
        self._ensure_database_sync()
        return self._execute_sync(query, params, "one")

    def execute_sync(
        self, query: str, params: Optional[Iterable[Any]] = None
    ) -> int:
        self._ensure_database_sync()
        return self._execute_sync(query, params, "none")

    async def fetch_all(
        self, query: str, params: Optional[Iterable[Any]] = None
    ) -> list[dict[str, Any]]:
        await self.ensure_schema()
        return await self._run(self._execute_sync, query, params, "all")

    async def fetch_one(
        self, query: str, params: Optional[Iterable[Any]] = None
    ) -> Optional[dict[str, Any]]:
        await self.ensure_schema()
        return await self._run(self._execute_sync, query, params, "one")

    async def execute(
        self, query: str, params: Optional[Iterable[Any]] = None
    ) -> int:
        await self.ensure_schema()
        return await self._run(self._execute_sync, query, params, "none")

    async def executemany(
        self, query: str, params: Optional[Iterable[Iterable[Any]]] = None
    ) -> int:
        await self.ensure_schema()
        return await self._run(self._execute_sync, query, params, "none", True)

    async def ping(self) -> bool:
        if not _requires_seekdb() and not get_seekdb_dsn():
            return False
        try:
            result = await self.fetch_one("SELECT 1 AS ok")
            return bool(result and result.get("ok") == 1)
        except Exception as e:
            logger.warning(f"SeekDB ping failed: {e}")
            return False

    async def ensure_schema(self) -> None:
        if not _requires_seekdb() and not get_seekdb_dsn():
            return

        async with self._schema_lock:
            if self._schema_initialized:
                return

            statements = [
                """
                CREATE TABLE IF NOT EXISTS ai_credentials (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    provider VARCHAR(128) NOT NULL,
                    modalities_json TEXT NOT NULL,
                    api_key TEXT NULL,
                    base_url TEXT NULL,
                    endpoint TEXT NULL,
                    api_version VARCHAR(128) NULL,
                    endpoint_llm TEXT NULL,
                    endpoint_embedding TEXT NULL,
                    endpoint_stt TEXT NULL,
                    endpoint_tts TEXT NULL,
                    project VARCHAR(255) NULL,
                    location VARCHAR(255) NULL,
                    credentials_path TEXT NULL,
                    extra_config_json LONGTEXT NULL,
                    created DATETIME NOT NULL,
                    updated DATETIME NOT NULL,
                    KEY idx_ai_credentials_provider (provider)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_models (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    provider VARCHAR(128) NOT NULL,
                    type VARCHAR(64) NOT NULL,
                    credential VARCHAR(255) NULL,
                    created DATETIME NOT NULL,
                    updated DATETIME NOT NULL,
                    KEY idx_ai_models_provider_type (provider, type),
                    KEY idx_ai_models_credential (credential)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_default_models (
                    id VARCHAR(255) PRIMARY KEY,
                    default_chat_model VARCHAR(255) NULL,
                    default_transformation_model VARCHAR(255) NULL,
                    large_context_model VARCHAR(255) NULL,
                    default_vision_model VARCHAR(255) NULL,
                    default_text_to_speech_model VARCHAR(255) NULL,
                    default_speech_to_text_model VARCHAR(255) NULL,
                    default_embedding_model VARCHAR(255) NULL,
                    default_tools_model VARCHAR(255) NULL,
                    created DATETIME NOT NULL,
                    updated DATETIME NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_source_chunks (
                    id VARCHAR(255) PRIMARY KEY,
                    source_id VARCHAR(255) NOT NULL,
                    page_id VARCHAR(255) NULL,
                    page_no INT NULL,
                    filename TEXT NULL,
                    notebook_ids_json TEXT NOT NULL,
                    title TEXT NULL,
                    content LONGTEXT NOT NULL,
                    order_no INT NOT NULL,
                    chunk_kind VARCHAR(64) NULL,
                    updated_at DATETIME NOT NULL,
                    sync_version BIGINT NOT NULL DEFAULT 0,
                    embedding_json LONGTEXT NULL,
                    KEY idx_ai_source_chunks_source (source_id),
                    KEY idx_ai_source_chunks_order (source_id, order_no),
                    KEY idx_ai_source_chunks_page (page_id),
                    KEY idx_ai_source_chunks_page_no (source_id, page_no)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_source_pages (
                    page_id VARCHAR(255) PRIMARY KEY,
                    source_id VARCHAR(255) NOT NULL,
                    filename TEXT NULL,
                    page_no INT NOT NULL,
                    raw_text LONGTEXT NULL,
                    page_summary LONGTEXT NULL,
                    combined_text LONGTEXT NOT NULL,
                    notebook_ids_json TEXT NOT NULL,
                    updated_at DATETIME NOT NULL,
                    sync_version BIGINT NOT NULL DEFAULT 0,
                    embedding_json LONGTEXT NULL,
                    page_image_path TEXT NULL,
                    image_count INT NOT NULL DEFAULT 0,
                    has_visual_summary BOOLEAN NOT NULL DEFAULT FALSE,
                    KEY idx_ai_source_pages_source (source_id),
                    KEY idx_ai_source_pages_page (source_id, page_no)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_note_index (
                    id VARCHAR(255) PRIMARY KEY,
                    note_id VARCHAR(255) NOT NULL,
                    notebook_ids_json TEXT NOT NULL,
                    title TEXT NULL,
                    content LONGTEXT NOT NULL,
                    updated_at DATETIME NOT NULL,
                    sync_version BIGINT NOT NULL DEFAULT 0,
                    embedding_json LONGTEXT NULL,
                    KEY idx_ai_note_index_note (note_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_insight_index (
                    id VARCHAR(255) PRIMARY KEY,
                    insight_id VARCHAR(255) NOT NULL,
                    source_id VARCHAR(255) NOT NULL,
                    notebook_ids_json TEXT NOT NULL,
                    source_title TEXT NULL,
                    insight_type VARCHAR(255) NOT NULL,
                    content LONGTEXT NOT NULL,
                    updated_at DATETIME NOT NULL,
                    sync_version BIGINT NOT NULL DEFAULT 0,
                    embedding_json LONGTEXT NULL,
                    KEY idx_ai_insight_index_insight (insight_id),
                    KEY idx_ai_insight_index_source (source_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_sync_state (
                    id VARCHAR(255) PRIMARY KEY,
                    entity_type VARCHAR(64) NOT NULL,
                    entity_id VARCHAR(255) NOT NULL,
                    sync_version BIGINT NOT NULL DEFAULT 0,
                    last_status VARCHAR(64) NOT NULL DEFAULT 'pending',
                    last_error LONGTEXT NULL,
                    last_synced_at DATETIME NULL,
                    UNIQUE KEY uniq_ai_sync_state_entity (entity_type, entity_id)
                )
                """,
                # VRAG tables for multimodal retrieval
                """
                CREATE TABLE IF NOT EXISTS ai_image_chunks (
                    id VARCHAR(255) PRIMARY KEY,
                    source_id VARCHAR(255) NOT NULL,
                    page_no INT NULL,
                    image_path TEXT NOT NULL,
                    image_summary TEXT NULL,
                    bbox_regions TEXT NULL,
                    embedding_json LONGTEXT NULL,
                    chunk_kind VARCHAR(64) NULL,
                    updated_at DATETIME NOT NULL,
                    sync_version BIGINT NOT NULL DEFAULT 0,
                    KEY idx_ai_image_chunks_source (source_id),
                    KEY idx_ai_image_chunks_page (source_id, page_no)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_vrag_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    notebook_id VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    question_count INT DEFAULT 0,
                    total_steps INT DEFAULT 0,
                    metadata JSON NULL,
                    KEY idx_notebook (notebook_id),
                    KEY idx_updated (updated_at)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_vrag_state (
                    id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    state_type VARCHAR(64) NOT NULL,
                    state_data JSON NOT NULL,
                    version INT DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    KEY idx_session (session_id),
                    KEY idx_type (state_type),
                    KEY idx_session_type (session_id, state_type)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_visual_assets (
                    id VARCHAR(255) PRIMARY KEY,
                    source_id VARCHAR(255) NOT NULL,
                    page_id VARCHAR(255) NULL,
                    legacy_id VARCHAR(255) NULL,
                    asset_type VARCHAR(64) NOT NULL,
                    media_type VARCHAR(128) NULL,
                    page_no INT NULL,
                    file_path TEXT NULL,
                    summary LONGTEXT NULL,
                    raw_text LONGTEXT NULL,
                    bbox_json LONGTEXT NULL,
                    embedding_json LONGTEXT NULL,
                    metadata_json LONGTEXT NULL,
                    index_status VARCHAR(64) NOT NULL DEFAULT 'completed',
                    index_command_id VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    KEY idx_ai_visual_assets_source (source_id),
                    KEY idx_ai_visual_assets_page (source_id, page_no),
                    KEY idx_ai_visual_assets_legacy (legacy_id),
                    KEY idx_ai_visual_assets_status (source_id, index_status)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_visual_rag_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    notebook_id VARCHAR(255) NOT NULL,
                    title TEXT NULL,
                    last_question LONGTEXT NULL,
                    current_answer LONGTEXT NULL,
                    last_answer_preview TEXT NULL,
                    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
                    total_steps INT NOT NULL DEFAULT 0,
                    last_error LONGTEXT NULL,
                    metadata_json LONGTEXT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    KEY idx_ai_visual_rag_sessions_notebook (notebook_id),
                    KEY idx_ai_visual_rag_sessions_updated (updated_at)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS ai_visual_rag_events (
                    id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    event_index INT NOT NULL DEFAULT 0,
                    payload_json LONGTEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    KEY idx_ai_visual_rag_events_session (session_id),
                    KEY idx_ai_visual_rag_events_type (session_id, event_type),
                    KEY idx_ai_visual_rag_events_order (session_id, event_index)
                )
                """,
            ]

            optional_statements = [
                "CREATE FULLTEXT INDEX idx_ai_source_chunks_text ON ai_source_chunks (content, title)",
                "CREATE FULLTEXT INDEX idx_ai_source_pages_text ON ai_source_pages (combined_text, page_summary, filename)",
                "CREATE FULLTEXT INDEX idx_ai_note_index_text ON ai_note_index (content, title)",
                "CREATE FULLTEXT INDEX idx_ai_insight_index_text ON ai_insight_index (content, source_title, insight_type)",
                "CREATE FULLTEXT INDEX idx_ai_visual_assets_text ON ai_visual_assets (summary, raw_text)",
            ]

            alter_statements = [
                "ALTER TABLE ai_credentials ADD COLUMN extra_config_json LONGTEXT NULL",
                "ALTER TABLE ai_default_models ADD COLUMN default_vision_model VARCHAR(255) NULL",
                "ALTER TABLE ai_source_chunks ADD COLUMN page_id VARCHAR(255) NULL",
                "ALTER TABLE ai_source_chunks ADD COLUMN page_no INT NULL",
                "ALTER TABLE ai_source_chunks ADD COLUMN filename TEXT NULL",
                "ALTER TABLE ai_source_chunks ADD COLUMN chunk_kind VARCHAR(64) NULL",
                "ALTER TABLE ai_source_chunks ADD KEY idx_ai_source_chunks_page (page_id)",
                "ALTER TABLE ai_source_chunks ADD KEY idx_ai_source_chunks_page_no (source_id, page_no)",
            ]

            await self._run(self._ensure_database_sync)

            for statement in statements:
                await self._run(self._execute_sync, statement, None, "none")

            for statement in alter_statements:
                try:
                    await self._run(self._execute_sync, statement, None, "none")
                except Exception as e:
                    logger.debug(f"SeekDB optional alter skipped: {e}")

            for statement in optional_statements:
                try:
                    await self._run(self._execute_sync, statement, None, "none")
                except Exception as e:
                    logger.debug(f"SeekDB optional index creation skipped: {e}")

            from .business_store import seekdb_business_store

            await seekdb_business_store.ensure_schema()

            self._schema_initialized = True


seekdb_client = SeekDBClient()
