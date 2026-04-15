import asyncio
import json
from typing import Any, Iterator, Optional, Sequence, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

from .client import seekdb_client

WRITES_IDX_MAP = {
    "__error__": -1,
    "__scheduled__": -2,
    "__interrupt__": -3,
    "__resume__": -4,
}


def search_where(
    config: RunnableConfig | None,
    filter: dict[str, Any] | None,
    before: RunnableConfig | None = None,
) -> tuple[str, list[Any]]:
    wheres = []
    param_values: list[Any] = []
    if config is not None:
        wheres.append("thread_id = ?")
        param_values.append(config["configurable"]["thread_id"])
        checkpoint_ns = config["configurable"].get("checkpoint_ns")
        if checkpoint_ns is not None:
            wheres.append("checkpoint_ns = ?")
            param_values.append(checkpoint_ns)
        if checkpoint_id := get_checkpoint_id(config):
            wheres.append("checkpoint_id = ?")
            param_values.append(checkpoint_id)
    if before is not None:
        wheres.append("checkpoint_id < ?")
        param_values.append(get_checkpoint_id(before))
    return ("WHERE " + " AND ".join(wheres) if wheres else "", param_values)


def _metadata_matches(metadata: dict[str, Any], filters: Optional[dict[str, Any]]) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        if metadata.get(key) != expected:
            return False
    return True


class SeekDBSaver(BaseCheckpointSaver):
    def __init__(self, *, serde=None) -> None:
        super().__init__(serde=serde)
        self._schema_ready = False

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        seekdb_client._ensure_database_sync()  # type: ignore[attr-defined]
        for statement in (
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
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
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
        ):
            seekdb_client._execute_sync(statement, None, "none")  # type: ignore[attr-defined]
        self._schema_ready = True

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        self._ensure_schema()
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id:
            row = seekdb_client._execute_sync(  # type: ignore[attr-defined]
                """
                SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_json
                FROM langgraph_checkpoints
                WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                """,
                (
                    str(config["configurable"]["thread_id"]),
                    checkpoint_ns,
                    checkpoint_id,
                ),
                "one",
            )
        else:
            row = seekdb_client._execute_sync(  # type: ignore[attr-defined]
                """
                SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_json
                FROM langgraph_checkpoints
                WHERE thread_id = %s AND checkpoint_ns = %s
                ORDER BY checkpoint_id DESC
                LIMIT 1
                """,
                (str(config["configurable"]["thread_id"]), checkpoint_ns),
                "one",
            )
        if not row:
            return None
        if not checkpoint_id:
            config = {
                "configurable": {
                    "thread_id": row["thread_id"],
                    "checkpoint_ns": row["checkpoint_ns"],
                    "checkpoint_id": row["checkpoint_id"],
                }
            }
        writes = seekdb_client._execute_sync(  # type: ignore[attr-defined]
            """
            SELECT task_id, channel, type, value
            FROM langgraph_writes
            WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
            ORDER BY task_id, idx
            """,
            (
                str(config["configurable"]["thread_id"]),
                checkpoint_ns,
                str(config["configurable"]["checkpoint_id"]),
            ),
            "all",
        )
        metadata = json.loads(row.get("metadata_json") or "{}")
        return CheckpointTuple(
            config,
            self.serde.loads_typed((row["type"], row["checkpoint"])),
            cast(CheckpointMetadata, metadata),
            (
                {
                    "configurable": {
                        "thread_id": row["thread_id"],
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["parent_checkpoint_id"],
                    }
                }
                if row.get("parent_checkpoint_id")
                else None
            ),
            [
                (item["task_id"], item["channel"], self.serde.loads_typed((item["type"], item["value"])))
                for item in writes
            ],
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        self._ensure_schema()
        where, values = search_where(config, None, before)
        sql = """
            SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata_json
            FROM langgraph_checkpoints
        """
        if where:
            sql += where.replace("?", "%s")
        sql += " ORDER BY checkpoint_id DESC"
        params = list(values)
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)
        rows = seekdb_client._execute_sync(  # type: ignore[attr-defined]
            sql,
            tuple(params) if params else None,
            "all",
        )
        for row in rows:
            metadata = json.loads(row.get("metadata_json") or "{}")
            if not _metadata_matches(metadata, filter):
                continue
            writes = seekdb_client._execute_sync(  # type: ignore[attr-defined]
                """
                SELECT task_id, channel, type, value
                FROM langgraph_writes
                WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                ORDER BY task_id, idx
                """,
                (row["thread_id"], row["checkpoint_ns"], row["checkpoint_id"]),
                "all",
            )
            yield CheckpointTuple(
                {
                    "configurable": {
                        "thread_id": row["thread_id"],
                        "checkpoint_ns": row["checkpoint_ns"],
                        "checkpoint_id": row["checkpoint_id"],
                    }
                },
                self.serde.loads_typed((row["type"], row["checkpoint"])),
                cast(CheckpointMetadata, metadata),
                (
                    {
                        "configurable": {
                            "thread_id": row["thread_id"],
                            "checkpoint_ns": row["checkpoint_ns"],
                            "checkpoint_id": row["parent_checkpoint_id"],
                        }
                    }
                    if row.get("parent_checkpoint_id")
                    else None
                ),
                [
                    (item["task_id"], item["channel"], self.serde.loads_typed((item["type"], item["value"])))
                    for item in writes
                ],
            )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        self._ensure_schema()
        thread_id = str(config["configurable"]["thread_id"])
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
        serialized_metadata = json.dumps(
            get_checkpoint_metadata(config, metadata), ensure_ascii=False
        )
        seekdb_client._execute_sync(  # type: ignore[attr-defined]
            """
            INSERT INTO langgraph_checkpoints (
                thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                type, checkpoint, metadata_json, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                parent_checkpoint_id = VALUES(parent_checkpoint_id),
                type = VALUES(type),
                checkpoint = VALUES(checkpoint),
                metadata_json = VALUES(metadata_json)
            """,
            (
                thread_id,
                checkpoint_ns,
                checkpoint["id"],
                config["configurable"].get("checkpoint_id"),
                type_,
                serialized_checkpoint,
                serialized_metadata,
            ),
            "none",
        )
        seekdb_client._execute_sync(  # type: ignore[attr-defined]
            """
            INSERT INTO langgraph_threads (thread_id, updated_at)
            VALUES (%s, NOW())
            ON DUPLICATE KEY UPDATE updated_at = NOW()
            """,
            (thread_id,),
            "none",
        )
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._ensure_schema()
        replace = all(item[0] in WRITES_IDX_MAP for item in writes)
        sql = (
            """
            REPLACE INTO langgraph_writes (
                thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value, task_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            if replace
            else """
            INSERT IGNORE INTO langgraph_writes (
                thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value, task_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        )
        params = [
            (
                str(config["configurable"]["thread_id"]),
                str(config["configurable"].get("checkpoint_ns", "")),
                str(config["configurable"]["checkpoint_id"]),
                task_id,
                WRITES_IDX_MAP.get(channel, idx),
                channel,
                *self.serde.dumps_typed(value),
                task_path,
            )
            for idx, (channel, value) in enumerate(writes)
        ]
        seekdb_client._execute_sync(sql, params, "none", many=True)  # type: ignore[attr-defined]

    def delete_thread(self, thread_id: str) -> None:
        self._ensure_schema()
        seekdb_client._execute_sync(  # type: ignore[attr-defined]
            "DELETE FROM langgraph_checkpoints WHERE thread_id = %s",
            (str(thread_id),),
            "none",
        )
        seekdb_client._execute_sync(  # type: ignore[attr-defined]
            "DELETE FROM langgraph_writes WHERE thread_id = %s",
            (str(thread_id),),
            "none",
        )
        seekdb_client._execute_sync(  # type: ignore[attr-defined]
            "DELETE FROM langgraph_threads WHERE thread_id = %s",
            (str(thread_id),),
            "none",
        )

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        for item in await asyncio.to_thread(
            lambda: list(self.list(config, filter=filter, before=before, limit=limit))
        ):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)
