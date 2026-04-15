import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .client import seekdb_client


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_id(value: str) -> str:
    return str(value)


def _encode_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


JSON_DEFAULTS: dict[str, Any] = {
    "asset": None,
    "topics": [],
    "embedding": [],
    "speakers": [],
    "episode_profile": {},
    "speaker_profile": {},
    "transcript": {},
    "outline": {},
}

BOOLEAN_FIELDS: dict[str, set[str]] = {
    "notebook": {"archived"},
    "transformation": {"apply_default"},
}


ENTITY_SCHEMAS: dict[str, dict[str, Any]] = {
    "notebook": {
        "columns": ["name", "description", "archived"],
        "json_fields": set(),
    },
    "source": {
        "columns": ["title", "asset", "topics", "full_text", "command"],
        "json_fields": {"asset", "topics"},
    },
    "source_embedding": {
        "columns": ["source", "order", "content", "embedding"],
        "json_fields": {"embedding"},
    },
    "source_insight": {
        "columns": ["source", "insight_type", "content"],
        "json_fields": set(),
    },
    "note": {
        "columns": ["title", "note_type", "content"],
        "json_fields": set(),
    },
    "chat_session": {
        "columns": ["title", "model_override"],
        "json_fields": set(),
    },
    "transformation": {
        "columns": ["name", "title", "description", "prompt", "apply_default"],
        "json_fields": set(),
    },
    "episode_profile": {
        "columns": [
            "name",
            "description",
            "speaker_config",
            "outline_provider",
            "outline_model",
            "transcript_provider",
            "transcript_model",
            "outline_llm",
            "transcript_llm",
            "language",
            "default_briefing",
            "num_segments",
        ],
        "json_fields": set(),
    },
    "speaker_profile": {
        "columns": [
            "name",
            "description",
            "tts_provider",
            "tts_model",
            "voice_model",
            "speakers",
        ],
        "json_fields": {"speakers"},
    },
    "episode": {
        "columns": [
            "name",
            "episode_profile",
            "speaker_profile",
            "briefing",
            "content",
            "audio_file",
            "transcript",
            "outline",
            "command",
        ],
        "json_fields": {"episode_profile", "speaker_profile", "transcript", "outline"},
    },
}


RELATION_TABLES = {"reference", "artifact", "refers_to"}


BUSINESS_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS notebook (
        id VARCHAR(255) PRIMARY KEY,
        name TEXT NOT NULL,
        description LONGTEXT NULL,
        archived BOOLEAN NOT NULL DEFAULT FALSE,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source (
        id VARCHAR(255) PRIMARY KEY,
        title TEXT NULL,
        asset_json LONGTEXT NULL,
        topics_json LONGTEXT NULL,
        full_text LONGTEXT NULL,
        command VARCHAR(255) NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        KEY idx_source_command (command)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_embedding (
        id VARCHAR(255) PRIMARY KEY,
        source VARCHAR(255) NOT NULL,
        order_no INT NOT NULL DEFAULT 0,
        content LONGTEXT NOT NULL,
        embedding_json LONGTEXT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        KEY idx_source_embedding_source (source)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_insight (
        id VARCHAR(255) PRIMARY KEY,
        source VARCHAR(255) NOT NULL,
        insight_type VARCHAR(255) NOT NULL,
        content LONGTEXT NOT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        KEY idx_source_insight_source (source)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS note (
        id VARCHAR(255) PRIMARY KEY,
        title TEXT NULL,
        note_type VARCHAR(64) NULL,
        content LONGTEXT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_session (
        id VARCHAR(255) PRIMARY KEY,
        title TEXT NULL,
        model_override VARCHAR(255) NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transformation (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        title TEXT NOT NULL,
        description LONGTEXT NOT NULL,
        prompt LONGTEXT NOT NULL,
        apply_default BOOLEAN NOT NULL DEFAULT FALSE,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        UNIQUE KEY uniq_transformation_name (name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS episode_profile (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description LONGTEXT NULL,
        speaker_config VARCHAR(255) NOT NULL,
        outline_provider VARCHAR(255) NULL,
        outline_model VARCHAR(255) NULL,
        transcript_provider VARCHAR(255) NULL,
        transcript_model VARCHAR(255) NULL,
        outline_llm VARCHAR(255) NULL,
        transcript_llm VARCHAR(255) NULL,
        language VARCHAR(64) NULL,
        default_briefing LONGTEXT NOT NULL,
        num_segments INT NOT NULL DEFAULT 5,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        UNIQUE KEY uniq_episode_profile_name (name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS speaker_profile (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description LONGTEXT NULL,
        tts_provider VARCHAR(255) NULL,
        tts_model VARCHAR(255) NULL,
        voice_model VARCHAR(255) NULL,
        speakers_json LONGTEXT NOT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        UNIQUE KEY uniq_speaker_profile_name (name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS episode (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        episode_profile_json LONGTEXT NOT NULL,
        speaker_profile_json LONGTEXT NOT NULL,
        briefing LONGTEXT NOT NULL,
        content LONGTEXT NOT NULL,
        audio_file TEXT NULL,
        transcript_json LONGTEXT NULL,
        outline_json LONGTEXT NULL,
        command VARCHAR(255) NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        KEY idx_episode_command (command)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reference (
        id VARCHAR(255) PRIMARY KEY,
        in_id VARCHAR(255) NOT NULL,
        out_id VARCHAR(255) NOT NULL,
        data_json LONGTEXT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        UNIQUE KEY uniq_reference_edge (in_id, out_id),
        KEY idx_reference_in (in_id),
        KEY idx_reference_out (out_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifact (
        id VARCHAR(255) PRIMARY KEY,
        in_id VARCHAR(255) NOT NULL,
        out_id VARCHAR(255) NOT NULL,
        data_json LONGTEXT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        UNIQUE KEY uniq_artifact_edge (in_id, out_id),
        KEY idx_artifact_in (in_id),
        KEY idx_artifact_out (out_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS refers_to (
        id VARCHAR(255) PRIMARY KEY,
        in_id VARCHAR(255) NOT NULL,
        out_id VARCHAR(255) NOT NULL,
        target_type VARCHAR(64) NULL,
        data_json LONGTEXT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        UNIQUE KEY uniq_refers_to_edge (in_id, out_id),
        KEY idx_refers_to_in (in_id),
        KEY idx_refers_to_out (out_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS singleton_record (
        id VARCHAR(255) PRIMARY KEY,
        data_json LONGTEXT NOT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id VARCHAR(255) PRIMARY KEY,
        app_name VARCHAR(255) NOT NULL,
        command_name VARCHAR(255) NOT NULL,
        status VARCHAR(64) NOT NULL,
        args_json LONGTEXT NULL,
        result_json LONGTEXT NULL,
        error_message LONGTEXT NULL,
        progress_json LONGTEXT NULL,
        retry_count INT NOT NULL DEFAULT 0,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL,
        started_at DATETIME NULL,
        completed_at DATETIME NULL,
        KEY idx_jobs_status (status),
        KEY idx_jobs_command (command_name, status)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS langgraph_threads (
        thread_id VARCHAR(255) PRIMARY KEY,
        updated_at DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
        thread_id VARCHAR(255) NOT NULL,
        checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
        checkpoint_id VARCHAR(255) NOT NULL,
        parent_checkpoint_id VARCHAR(255) NULL,
        type VARCHAR(255) NOT NULL,
        checkpoint LONGBLOB NOT NULL,
        metadata_json LONGTEXT NULL,
        created_at DATETIME NOT NULL,
        PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id),
        KEY idx_langgraph_parent (thread_id, checkpoint_ns, parent_checkpoint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS langgraph_writes (
        thread_id VARCHAR(255) NOT NULL,
        checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
        checkpoint_id VARCHAR(255) NOT NULL,
        task_id VARCHAR(255) NOT NULL,
        idx INT NOT NULL,
        channel VARCHAR(255) NOT NULL,
        type VARCHAR(255) NOT NULL,
        value LONGBLOB NOT NULL,
        task_path TEXT NULL,
        PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id VARCHAR(255) PRIMARY KEY,
        version INT NOT NULL,
        created DATETIME NOT NULL,
        updated DATETIME NOT NULL
    )
    """,
]


class SeekDBBusinessStore:
    def _new_id(self, prefix: str) -> str:
        return f"{prefix}:{uuid4().hex}"

    async def ensure_schema(self) -> None:
        await seekdb_client._run(seekdb_client._ensure_database_sync)  # type: ignore[attr-defined]
        for statement in BUSINESS_SCHEMA_STATEMENTS:
            await seekdb_client._run(  # type: ignore[attr-defined]
                seekdb_client._execute_sync,
                statement,
                None,
                "none",
            )

    def _schema_for(self, table: str) -> dict[str, Any]:
        if table not in ENTITY_SCHEMAS:
            raise ValueError(f"Unsupported entity table: {table}")
        return ENTITY_SCHEMAS[table]

    def _encode_entity_data(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        schema = self._schema_for(table)
        encoded: dict[str, Any] = {}
        for field in schema["columns"]:
            value = data.get(field)
            if field in schema["json_fields"]:
                encoded[f"{field}_json"] = _json_dumps(value)
            elif field == "order":
                encoded["order_no"] = value
            else:
                encoded[field] = _encode_scalar(value)
        return encoded

    def _decode_entity_row(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        schema = self._schema_for(table)
        decoded: dict[str, Any] = {
            "id": row.get("id"),
            "created": row.get("created"),
            "updated": row.get("updated"),
        }
        for field in schema["columns"]:
            column_name = "order_no" if field == "order" else field
            if field in schema["json_fields"]:
                decoded[field] = _json_loads(
                    row.get(f"{field}_json"), JSON_DEFAULTS.get(field)
                )
            else:
                value = row.get(column_name)
                if field in BOOLEAN_FIELDS.get(table, set()) and value is not None:
                    decoded[field] = bool(value)
                else:
                    decoded[field] = value
        if table == "source" and decoded.get("topics") is None:
            decoded["topics"] = []
        if table == "speaker_profile" and decoded.get("speakers") is None:
            decoded["speakers"] = []
        if table == "episode":
            decoded["transcript"] = decoded.get("transcript") or {}
            decoded["outline"] = decoded.get("outline") or {}
        return decoded

    async def list_entities(
        self,
        table: str,
        *,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        self._schema_for(table)
        clauses = []
        params: list[Any] = []
        for key, value in (filters or {}).items():
            column = "order_no" if key == "order" else key
            if value is None:
                clauses.append(f"{column} IS NULL")
            else:
                clauses.append(f"{column} = %s")
                params.append(_encode_scalar(value))

        query = f"SELECT * FROM {table}"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
        rows = await seekdb_client.fetch_all(query, tuple(params) if params else None)
        return [self._decode_entity_row(table, row) for row in rows]

    async def get_entity(self, record_id: str) -> Optional[dict[str, Any]]:
        record_id_str = _normalize_id(record_id)
        table = record_id_str.split(":", 1)[0]
        row = await seekdb_client.fetch_one(
            f"SELECT * FROM {table} WHERE id = %s",
            (record_id_str,),
        )
        return self._decode_entity_row(table, row) if row else None

    async def create_entity(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        schema = self._schema_for(table)
        record_id = data.get("id") or self._new_id(table)
        now = _now()
        encoded = self._encode_entity_data(table, data)
        columns = ["id", *["order_no" if c == "order" else c for c in schema["columns"]]]
        for field in schema["json_fields"]:
            columns = [c for c in columns if c != field]
            columns.append(f"{field}_json")
        columns.extend(["created", "updated"])
        values = [record_id]
        for field in schema["columns"]:
            if field in schema["json_fields"]:
                values.append(encoded.get(f"{field}_json"))
            elif field == "order":
                values.append(encoded.get("order_no", 0))
            else:
                values.append(encoded.get(field))
        values.extend([data.get("created") or now, data.get("updated") or now])
        placeholders = ", ".join(["%s"] * len(values))
        await seekdb_client.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
        return (await self.get_entity(record_id)) or {}

    async def update_entity(
        self,
        table: str,
        record_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        schema = self._schema_for(table)
        encoded = self._encode_entity_data(table, data)
        assignments: list[str] = []
        params: list[Any] = []
        for field in schema["columns"]:
            column = "order_no" if field == "order" else field
            if field in schema["json_fields"]:
                column = f"{field}_json"
                value = encoded.get(column)
            else:
                value = encoded.get(column)
            assignments.append(f"{column} = %s")
            params.append(value)
        assignments.append("created = %s")
        params.append(data.get("created"))
        assignments.append("updated = %s")
        params.append(data.get("updated") or _now())
        params.append(_normalize_id(record_id))
        await seekdb_client.execute(
            f"UPDATE {table} SET {', '.join(assignments)} WHERE id = %s",
            tuple(params),
        )
        return (await self.get_entity(record_id)) or {}

    async def delete_entity(self, record_id: str) -> bool:
        record_id_str = _normalize_id(record_id)
        table = record_id_str.split(":", 1)[0]
        await seekdb_client.execute(f"DELETE FROM {table} WHERE id = %s", (record_id_str,))
        for relation_table in RELATION_TABLES:
            await seekdb_client.execute(
                f"DELETE FROM {relation_table} WHERE in_id = %s OR out_id = %s",
                (record_id_str, record_id_str),
            )
        return True

    async def insert_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for row in rows:
            created.append(await self.create_entity(table, row))
        return created

    async def upsert_singleton(self, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        current = await seekdb_client.fetch_one(
            "SELECT * FROM singleton_record WHERE id = %s",
            (record_id,),
        )
        created = (current or {}).get("created") or now
        await seekdb_client.execute(
            """
            INSERT INTO singleton_record (id, data_json, created, updated)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                data_json = VALUES(data_json),
                created = VALUES(created),
                updated = VALUES(updated)
            """,
            (record_id, _json_dumps(data) or "{}", created, now),
        )
        return await self.get_singleton(record_id)

    async def get_singleton(self, record_id: str) -> dict[str, Any]:
        row = await seekdb_client.fetch_one(
            "SELECT * FROM singleton_record WHERE id = %s",
            (record_id,),
        )
        if not row:
            return {}
        data = _json_loads(row.get("data_json"), {})
        data["id"] = row.get("id")
        data["created"] = row.get("created")
        data["updated"] = row.get("updated")
        return data

    async def create_relation(
        self,
        relationship: str,
        source: str,
        target: str,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if relationship not in RELATION_TABLES:
            raise ValueError(f"Unsupported relationship table: {relationship}")
        source_id = _normalize_id(source)
        target_id = _normalize_id(target)
        relation_id = f"{relationship}:{uuid4().hex}"
        now = _now()
        target_type = target_id.split(":", 1)[0] if relationship == "refers_to" else None
        await seekdb_client.execute(
            f"""
            INSERT INTO {relationship} (id, in_id, out_id, {'target_type,' if relationship == 'refers_to' else ''} data_json, created, updated)
            VALUES (%s, %s, %s, {'%s,' if relationship == 'refers_to' else ''} %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                data_json = VALUES(data_json),
                updated = VALUES(updated)
            """,
            (
                relation_id,
                source_id,
                target_id,
                *( [target_type] if relationship == "refers_to" else [] ),
                _json_dumps(data or {}),
                now,
                now,
            ),
        )
        return {
            "id": relation_id,
            "in": source_id,
            "out": target_id,
            "data": data or {},
        }

    async def relation_exists(self, relationship: str, source: str, target: str) -> bool:
        row = await seekdb_client.fetch_one(
            f"SELECT id FROM {relationship} WHERE in_id = %s AND out_id = %s",
            (source, target),
        )
        return bool(row)

    async def delete_relations(
        self,
        relationship: str,
        *,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> int:
        clauses = []
        params: list[Any] = []
        if source_id:
            clauses.append("in_id = %s")
            params.append(source_id)
        if target_id:
            clauses.append("out_id = %s")
            params.append(target_id)
        if not clauses:
            return 0
        return await seekdb_client.execute(
            f"DELETE FROM {relationship} WHERE {' AND '.join(clauses)}",
            tuple(params),
        )

    async def list_relation_targets(self, relationship: str, source_id: str) -> list[str]:
        rows = await seekdb_client.fetch_all(
            f"SELECT out_id FROM {relationship} WHERE in_id = %s",
            (source_id,),
        )
        return [str(row.get("out_id")) for row in rows if row.get("out_id")]

    async def list_relation_sources(self, relationship: str, target_id: str) -> list[str]:
        rows = await seekdb_client.fetch_all(
            f"SELECT in_id FROM {relationship} WHERE out_id = %s",
            (target_id,),
        )
        return [str(row.get("in_id")) for row in rows if row.get("in_id")]

    async def count_relations(
        self,
        relationship: str,
        *,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> int:
        clauses = []
        params: list[Any] = []
        if source_id:
            clauses.append("in_id = %s")
            params.append(source_id)
        if target_id:
            clauses.append("out_id = %s")
            params.append(target_id)
        query = f"SELECT COUNT(*) AS count FROM {relationship}"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        row = await seekdb_client.fetch_one(query, tuple(params) if params else None)
        return int((row or {}).get("count") or 0)

    async def notebook_rows(self, order_by: str = "updated desc") -> list[dict[str, Any]]:
        rows = await self.list_entities("notebook", order_by=order_by)
        for row in rows:
            row["source_count"] = await self.count_relations(
                "reference", target_id=str(row.get("id"))
            )
            row["note_count"] = await self.count_relations(
                "artifact", target_id=str(row.get("id"))
            )
        return rows

    async def notebook_row(self, notebook_id: str) -> Optional[dict[str, Any]]:
        row = await self.get_entity(notebook_id)
        if not row:
            return None
        row["source_count"] = await self.count_relations("reference", target_id=notebook_id)
        row["note_count"] = await self.count_relations("artifact", target_id=notebook_id)
        return row

    async def list_notebook_sources(self, notebook_id: str) -> list[dict[str, Any]]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT s.*
            FROM source s
            INNER JOIN reference r ON r.in_id = s.id
            WHERE r.out_id = %s
            ORDER BY s.updated DESC
            """,
            (notebook_id,),
        )
        return [self._decode_entity_row("source", row) for row in rows]

    async def list_notebook_notes(self, notebook_id: str) -> list[dict[str, Any]]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT n.*
            FROM note n
            INNER JOIN artifact a ON a.in_id = n.id
            WHERE a.out_id = %s
            ORDER BY n.updated DESC
            """,
            (notebook_id,),
        )
        return [self._decode_entity_row("note", row) for row in rows]

    async def list_notebook_chat_sessions(self, notebook_id: str) -> list[dict[str, Any]]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT c.*
            FROM chat_session c
            INNER JOIN refers_to r ON r.in_id = c.id
            WHERE r.out_id = %s
            ORDER BY c.updated DESC
            """,
            (notebook_id,),
        )
        return [self._decode_entity_row("chat_session", row) for row in rows]

    async def list_source_chat_sessions(self, source_id: str) -> list[dict[str, Any]]:
        rows = await seekdb_client.fetch_all(
            """
            SELECT c.*
            FROM chat_session c
            INNER JOIN refers_to r ON r.in_id = c.id
            WHERE r.out_id = %s
            ORDER BY c.updated DESC
            """,
            (source_id,),
        )
        return [self._decode_entity_row("chat_session", row) for row in rows]

    async def notebook_delete_preview(self, notebook_id: str) -> dict[str, int]:
        note_count = await self.count_relations("artifact", target_id=notebook_id)
        source_ids = await self.list_relation_sources("reference", notebook_id)
        exclusive_source_count = 0
        shared_source_count = 0
        for source_id in source_ids:
            row = await seekdb_client.fetch_one(
                "SELECT COUNT(*) AS count FROM reference WHERE in_id = %s AND out_id != %s",
                (source_id, notebook_id),
            )
            if int((row or {}).get("count") or 0) > 0:
                shared_source_count += 1
            else:
                exclusive_source_count += 1
        return {
            "note_count": note_count,
            "exclusive_source_count": exclusive_source_count,
            "shared_source_count": shared_source_count,
        }

    async def get_source_insights(self, source_id: str) -> list[dict[str, Any]]:
        return await self.list_entities(
            "source_insight", filters={"source": source_id}, order_by="updated DESC"
        )

    async def get_source_notebook_ids(self, source_id: str) -> list[str]:
        return await self.list_relation_targets("reference", source_id)

    async def get_note_notebook_ids(self, note_id: str) -> list[str]:
        return await self.list_relation_targets("artifact", note_id)

    async def source_list_rows(
        self,
        *,
        notebook_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated",
        sort_order: str = "DESC",
    ) -> list[dict[str, Any]]:
        params: list[Any] = []
        if notebook_id:
            query = f"""
                SELECT s.*
                FROM source s
                INNER JOIN reference r ON r.in_id = s.id
                WHERE r.out_id = %s
                ORDER BY s.{sort_by} {sort_order}
                LIMIT %s OFFSET %s
            """
            params.extend([notebook_id, limit, offset])
        else:
            query = f"""
                SELECT *
                FROM source
                ORDER BY {sort_by} {sort_order}
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
        rows = await seekdb_client.fetch_all(query, tuple(params))
        results = [self._decode_entity_row("source", row) for row in rows]
        for row in results:
            row["insights_count"] = len(
                await self.get_source_insights(str(row.get("id") or ""))
            )
        return results


seekdb_business_store = SeekDBBusinessStore()
