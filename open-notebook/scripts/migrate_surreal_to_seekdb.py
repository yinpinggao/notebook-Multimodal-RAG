#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.seekdb import ai_config_store, seekdb_business_store
from open_notebook.seekdb.business_store import ENTITY_SCHEMAS
from open_notebook.seekdb.client import seekdb_client

ENTITY_TABLES = [
    "notebook",
    "source",
    "note",
    "source_insight",
    "chat_session",
    "transformation",
    "episode_profile",
    "speaker_profile",
    "episode",
]
RELATION_TABLES = ["reference", "artifact", "refers_to"]
AI_TABLES = ["credential", "model"]
SINGLETON_RECORDS = [
    "open_notebook:default_models",
    "open_notebook:provider_configs",
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_surreal_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_surreal_value(item) for item in value]
    if isinstance(value, dict):
        if {"tb", "id"}.issubset(value):
            return f"{value['tb']}:{value['id']}"
        return {key: _normalize_surreal_value(item) for key, item in value.items()}
    return value


def _surreal_sql_endpoint(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    scheme = "https" if parsed.scheme in {"https", "wss"} else "http"
    return f"{scheme}://{parsed.hostname}:{parsed.port or 8000}/sql"


class SurrealHTTPClient:
    def __init__(self, *, url: str, user: str, password: str, namespace: str, database: str) -> None:
        self.endpoint = _surreal_sql_endpoint(url)
        self.auth = (user, password)
        self.headers = {
            "Accept": "application/json",
            "NS": namespace,
            "DB": database,
        }

    async def query(self, sql: str) -> list[Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.endpoint,
                content=sql,
                headers=self.headers,
                auth=self.auth,
            )
            response.raise_for_status()
            payload = response.json()

        if isinstance(payload, dict):
            payload = [payload]

        results: list[Any] = []
        for item in payload:
            if isinstance(item, dict) and item.get("status") == "ERR":
                raise RuntimeError(item.get("detail") or item.get("result") or sql)
            result = item.get("result") if isinstance(item, dict) else item
            if isinstance(result, list):
                results.extend(_normalize_surreal_value(entry) for entry in result)
            elif result is not None:
                results.append(_normalize_surreal_value(result))
        return results


def _entity_payload(table: str, row: dict[str, Any]) -> dict[str, Any]:
    allowed = set(ENTITY_SCHEMAS[table]["columns"]) | {"id", "created", "updated"}
    payload = {key: value for key, value in row.items() if key in allowed}
    payload["id"] = str(payload["id"])
    return payload


async def _upsert_entity(table: str, row: dict[str, Any]) -> None:
    payload = _entity_payload(table, row)
    record_id = str(payload["id"])
    existing = await seekdb_business_store.get_entity(record_id)
    if existing:
        await seekdb_business_store.update_entity(table, record_id, {**existing, **payload})
    else:
        await seekdb_business_store.create_entity(table, payload)


async def _upsert_relation(table: str, row: dict[str, Any]) -> None:
    record_id = str(row.get("id") or f"{table}:imported")
    source_id = str(row.get("in") or row.get("in_id") or "")
    target_id = str(row.get("out") or row.get("out_id") or "")
    target_type = str(row.get("target_type") or target_id.split(":", 1)[0]) if table == "refers_to" else None
    data_json = row.get("data") or row.get("data_json") or {}
    if not source_id or not target_id:
        return
    await seekdb_client.execute(
        f"""
        INSERT INTO {table} (
            id, in_id, out_id, {'target_type,' if table == 'refers_to' else ''} data_json, created, updated
        ) VALUES (%s, %s, %s, {'%s,' if table == 'refers_to' else ''} %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            data_json = VALUES(data_json),
            {'target_type = VALUES(target_type),' if table == 'refers_to' else ''}
            created = VALUES(created),
            updated = VALUES(updated)
        """,
        (
            record_id,
            source_id,
            target_id,
            *([target_type] if table == "refers_to" else []),
            json.dumps(data_json or {}, ensure_ascii=False),
            row.get("created") or _now(),
            row.get("updated") or _now(),
        ),
    )


async def migrate_surreal_to_seekdb(args: argparse.Namespace) -> None:
    client = SurrealHTTPClient(
        url=args.surreal_url,
        user=args.surreal_user,
        password=args.surreal_password,
        namespace=args.surreal_namespace,
        database=args.surreal_database,
    )

    await AsyncMigrationManager().run_migration_up()
    counts: dict[str, int] = defaultdict(int)

    for table in ENTITY_TABLES:
        rows = await client.query(f"SELECT * FROM {table};")
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                await _upsert_entity(table, row)
                counts[table] += 1

    for table in RELATION_TABLES:
        rows = await client.query(f"SELECT * FROM {table};")
        for row in rows:
            if isinstance(row, dict):
                await _upsert_relation(table, row)
                counts[table] += 1

    credential_rows = await client.query("SELECT * FROM credential;")
    for row in credential_rows:
        if isinstance(row, dict):
            row["id"] = str(row.get("id"))
            await ai_config_store.upsert_credential(row)
            counts["credential"] += 1

    model_rows = await client.query("SELECT * FROM model;")
    for row in model_rows:
        if isinstance(row, dict):
            row["id"] = str(row.get("id"))
            if row.get("credential"):
                row["credential"] = str(row["credential"])
            await ai_config_store.upsert_model(row)
            counts["model"] += 1

    default_models = await client.query("SELECT * FROM ONLY open_notebook:default_models;")
    if default_models:
        row = default_models[0]
        if isinstance(row, dict):
            await ai_config_store.upsert_default_models(row)
            counts["default_models"] = 1

    provider_configs = await client.query("SELECT * FROM ONLY open_notebook:provider_configs;")
    if provider_configs:
        row = provider_configs[0]
        if isinstance(row, dict):
            row.pop("id", None)
            await seekdb_business_store.upsert_singleton("open_notebook:provider_configs", row)
            counts["provider_configs"] = 1

    print("Migration complete.")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate SurrealDB business data into SeekDB."
    )
    parser.add_argument(
        "--surreal-url",
        default=os.getenv("SURREAL_URL", "ws://127.0.0.1:8000/rpc"),
    )
    parser.add_argument(
        "--surreal-user",
        default=os.getenv("SURREAL_USER", "root"),
    )
    parser.add_argument(
        "--surreal-password",
        default=os.getenv("SURREAL_PASSWORD", "root"),
    )
    parser.add_argument(
        "--surreal-namespace",
        default=os.getenv("SURREAL_NAMESPACE", "open_notebook"),
    )
    parser.add_argument(
        "--surreal-database",
        default=os.getenv("SURREAL_DATABASE", "open_notebook"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(migrate_surreal_to_seekdb(parse_args()))
