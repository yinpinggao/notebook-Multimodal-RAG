#!/usr/bin/env python3
import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.seekdb import seekdb_client


def _pick_table(conn: sqlite3.Connection, *candidates: str) -> str | None:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    names = {row[0] for row in rows}
    for candidate in candidates:
        if candidate in names:
            return candidate
    return None


def _to_bytes(value: Any) -> bytes:
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytes):
        return value
    return bytes(value or b"")


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _row_value(row: sqlite3.Row, *keys: str) -> Any:
    for key in keys:
        if key in row.keys():
            return row[key]
    return None


async def migrate_sqlite_checkpoints(args: argparse.Namespace) -> None:
    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite checkpoint file not found: {sqlite_path}")

    await AsyncMigrationManager().run_migration_up()

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        checkpoint_table = _pick_table(conn, "checkpoints", "langgraph_checkpoints")
        writes_table = _pick_table(conn, "writes", "langgraph_writes")
        if not checkpoint_table:
            raise RuntimeError("Could not find a checkpoint table in the SQLite file.")

        checkpoint_rows = conn.execute(f"SELECT * FROM {checkpoint_table}").fetchall()
        write_rows = (
            conn.execute(f"SELECT * FROM {writes_table}").fetchall() if writes_table else []
        )

        thread_ids = {
            str(row["thread_id"])
            for row in checkpoint_rows
            if row["thread_id"] is not None
        } | {
            str(row["thread_id"])
            for row in write_rows
            if row["thread_id"] is not None
        }

        if thread_ids:
            await seekdb_client.executemany(
                """
                INSERT INTO langgraph_threads (thread_id, updated_at)
                VALUES (%s, NOW())
                ON DUPLICATE KEY UPDATE updated_at = NOW()
                """,
                [(thread_id,) for thread_id in sorted(thread_ids)],
            )

        await seekdb_client.executemany(
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
            [
                (
                    str(row["thread_id"]),
                    _to_text(row["checkpoint_ns"]) or "",
                    str(row["checkpoint_id"]),
                    _to_text(row["parent_checkpoint_id"]),
                    _to_text(row["type"]) or "json",
                    _to_bytes(row["checkpoint"]),
                    _to_text(_row_value(row, "metadata_json", "metadata")),
                )
                for row in checkpoint_rows
            ],
        )

        if write_rows:
            await seekdb_client.executemany(
                """
                INSERT INTO langgraph_writes (
                    thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value, task_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    channel = VALUES(channel),
                    type = VALUES(type),
                    value = VALUES(value),
                    task_path = VALUES(task_path)
                """,
                [
                    (
                        str(row["thread_id"]),
                        _to_text(row["checkpoint_ns"]) or "",
                        str(row["checkpoint_id"]),
                        str(row["task_id"]),
                        int(row["idx"]),
                        _to_text(row["channel"]) or "",
                        _to_text(row["type"]) or "json",
                        _to_bytes(row["value"]),
                        _to_text(row["task_path"]) or "",
                    )
                    for row in write_rows
                ],
            )
    finally:
        conn.close()

    print(
        f"Migrated {len(checkpoint_rows)} checkpoints and {len(write_rows)} writes from {sqlite_path}."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate LangGraph SQLite checkpoints into SeekDB.")
    parser.add_argument(
        "--sqlite-path",
        default=str(ROOT / "data/sqlite-db/checkpoints.sqlite"),
        help="Path to the legacy SQLite checkpoint file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(migrate_sqlite_checkpoints(parse_args()))
