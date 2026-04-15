"""
SeekDB thin wrapper and legacy SurrealQL compatibility layer.

Primary database access is through seekdb_business_store and seekdb_client.
This module provides:
- ensure_record_id(): ID normalization utility
- repo_query(): SurrealQL-to-MySQL translation (for legacy migration scripts)
- repo_create/update/delete/relate(): Thin wrappers around seekdb_business_store

Note: repo_create/update/delete/relate are deprecated. Use seekdb_business_store
methods directly instead.
"""

import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from loguru import logger

from open_notebook.seekdb import seekdb_business_store, seekdb_client

T = TypeVar("T", Dict[str, Any], List[Dict[str, Any]])
ENTITY_TABLES = {
    "notebook",
    "source",
    "source_embedding",
    "source_insight",
    "note",
    "chat_session",
    "transformation",
    "episode_profile",
    "speaker_profile",
    "episode",
}


def parse_record_ids(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: parse_record_ids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [parse_record_ids(item) for item in obj]
    return obj


def ensure_record_id(value: str) -> str:
    return str(value)


@asynccontextmanager
async def db_connection():
    await seekdb_client.ensure_schema()
    yield seekdb_client


def _normalize_id(value: Any) -> str:
    return str(value)


def _normalize_query(query_str: str) -> str:
    query = " ".join(query_str.strip().split())
    query = re.sub(r"\s*=\s*", " = ", query)
    query = re.sub(r"\s*!=\s*", " != ", query)
    return query


def _map_field(field: str) -> str:
    if field == "in":
        return "in_id"
    if field == "out":
        return "out_id"
    if field == "order":
        return "order_no"
    return field


async def _run_select(
    select_expr: str,
    table: str,
    where_expr: Optional[str],
    order_by: Optional[str],
    limit_expr: Optional[str],
    offset_expr: Optional[str],
    vars: dict[str, Any],
):
    filters: dict[str, Any] = {}
    not_none_fields: set[str] = set()
    where_expr = (where_expr or "").strip()
    if where_expr:
        for clause in re.split(r"\s+AND\s+", where_expr, flags=re.IGNORECASE):
            clause = clause.strip()
            if not clause:
                continue
            if " != none" in clause.lower():
                field = clause.split("!=", 1)[0].strip()
                not_none_fields.add(_map_field(field))
                continue
            field, rhs = [part.strip() for part in clause.split("=", 1)]
            field = _map_field(field)
            if rhs.startswith("$"):
                filters[field] = _normalize_id(vars[rhs[1:]])
            else:
                filters[field] = rhs.strip("'\"")

    limit = (
        int(vars[limit_expr[1:]])
        if limit_expr and limit_expr.startswith("$")
        else int(limit_expr)
        if limit_expr
        else None
    )
    offset = (
        int(vars[offset_expr[1:]])
        if offset_expr and offset_expr.startswith("$")
        else int(offset_expr)
        if offset_expr
        else None
    )

    if table in ENTITY_TABLES:
        rows = await seekdb_business_store.list_entities(
            table,
            order_by=order_by,
            filters=filters or None,
            limit=limit,
            offset=offset,
        )
    else:
        clauses = []
        params: list[Any] = []
        for field, value in filters.items():
            if value is None:
                clauses.append(f"{field} IS NULL")
            else:
                clauses.append(f"{field} = %s")
                params.append(value)
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
    if not_none_fields:
        rows = [
            row
            for row in rows
            if all(row.get(field) not in (None, "") for field in not_none_fields)
        ]

    select_lower = select_expr.lower()
    if select_lower == "*":
        return rows
    if select_lower == "id":
        return [{"id": row.get("id")} for row in rows]
    if select_lower == "value id":
        return [row.get("id") for row in rows if row.get("id") is not None]
    if select_lower.startswith("value "):
        count_match = re.match(r"value\s+count\(\)\s+as\s+([a-z_]+)", select_lower)
        if count_match:
            return [{count_match.group(1): len(rows)}]
        field = _map_field(select_expr[6:].strip())
        return [row.get(field) for row in rows if row.get(field) is not None]
    if select_lower.startswith("count() as "):
        alias = select_expr.split(" as ", 1)[1].strip()
        return [{alias: len(rows)}]
    raise RuntimeError(f"Unsupported select expression: {select_expr}")


async def repo_query(
    query_str: str, vars: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    vars = vars or {}
    query = _normalize_query(query_str)
    lowered = query.lower().rstrip(";")

    try:
        if lowered == "return 1":
            return [{"result": 1}]

        if lowered.startswith("create source_insight content"):
            return [
                await seekdb_business_store.create_entity(
                    "source_insight",
                    {
                        "source": _normalize_id(vars.get("source_id")),
                        "insight_type": vars.get("insight_type"),
                        "content": vars.get("content"),
                    },
                )
            ]

        if lowered in {
            "select * from $id",
            "select * from $record_id",
            "select * from only $record_id",
        }:
            record_id = vars.get("id") or vars.get("record_id")
            if not record_id:
                return []
            row = await seekdb_business_store.get_entity(_normalize_id(record_id))
            if row:
                return [row]
            singleton = await seekdb_business_store.get_singleton(_normalize_id(record_id))
            return [singleton] if singleton else []

        m = re.match(
            r"select\s+(?P<select>.+?)\s+from\s+(?P<table>[a-z_]+)"
            r"(?:\s+where\s+(?P<where>.+?))?"
            r"(?:\s+order by\s+(?P<order>.+?))?"
            r"(?:\s+limit\s+(?P<limit>\$?\w+))?"
            r"(?:\s+(?:start|offset)\s+(?P<offset>\$?\w+))?$",
            lowered,
            flags=re.IGNORECASE,
        )
        if m:
            return await _run_select(
                select_expr=m.group("select"),
                table=m.group("table"),
                where_expr=m.group("where"),
                order_by=m.group("order"),
                limit_expr=m.group("limit"),
                offset_expr=m.group("offset"),
                vars=vars,
            )

        if lowered.startswith("delete from "):
            m = re.match(
                r"delete from (?P<table>[a-z_]+)\s+where\s+(?P<where>.+)$",
                lowered,
                flags=re.IGNORECASE,
            )
            if not m:
                raise RuntimeError(f"Unsupported delete query: {query_str}")
            table = m.group("table")
            filters = {}
            for clause in re.split(r"\s+and\s+", m.group("where"), flags=re.IGNORECASE):
                field, rhs = [part.strip() for part in clause.split("=", 1)]
                filters[_map_field(field)] = _normalize_id(vars[rhs[1:]]) if rhs.startswith("$") else rhs
            if table in {"reference", "artifact", "refers_to"}:
                return [
                    {
                        "deleted": await seekdb_business_store.delete_relations(
                            table,
                            source_id=filters.get("in_id"),
                            target_id=filters.get("out_id"),
                        )
                    }
                ]
            rows = await seekdb_business_store.list_entities(table, filters=filters)
            for row in rows:
                await seekdb_business_store.delete_entity(str(row["id"]))
            return [{"deleted": len(rows)}]

        if lowered.startswith("delete "):
            m = re.match(
                r"delete (?P<table>[a-z_]+)\s+where\s+(?P<where>.+)$",
                lowered,
                flags=re.IGNORECASE,
            )
            if not m:
                raise RuntimeError(f"Unsupported delete query: {query_str}")
            return await repo_query(
                f"DELETE FROM {m.group('table')} WHERE {m.group('where')}",
                vars,
            )

        if lowered.startswith("relate "):
            m = re.match(
                r"relate\s+(?P<source>\$\w+|[a-z_]+:[^ ]+)->(?P<rel>[a-z_]+)->(?P<target>\$\w+|[a-z_]+:[^ ]+)(?:\s+content\s+\$data)?",
                lowered,
                flags=re.IGNORECASE,
            )
            if not m:
                raise RuntimeError(f"Unsupported relate query: {query_str}")
            source = (
                _normalize_id(vars[m.group("source")[1:]])
                if m.group("source").startswith("$")
                else m.group("source")
            )
            target = (
                _normalize_id(vars[m.group("target")[1:]])
                if m.group("target").startswith("$")
                else m.group("target")
            )
            return [
                await seekdb_business_store.create_relation(
                    m.group("rel"), source, target, vars.get("data")
                )
            ]

        raise RuntimeError(f"Unsupported compatibility query: {query_str}")
    except RuntimeError as e:
        logger.debug(str(e))
        raise
    except Exception as e:
        logger.exception(e)
        raise


async def repo_create(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data.pop("id", None)
    data["created"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        return await seekdb_business_store.create_entity(table, data)
    except Exception as e:
        logger.exception(e)
        raise RuntimeError("Failed to create record")


async def repo_relate(
    source: str, relationship: str, target: str, data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    return [
        await seekdb_business_store.create_relation(
            relationship, source, target, data or {}
        )
    ]


async def repo_upsert(
    table: str, id: Optional[str], data: Dict[str, Any], add_timestamp: bool = False
) -> List[Dict[str, Any]]:
    data.pop("id", None)
    if add_timestamp:
        data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record_id = id or data.get("id")
    if table in {"open_notebook", "record"} or ":" in str(record_id or ""):
        return [await seekdb_business_store.upsert_singleton(str(record_id), data)]
    existing = await seekdb_business_store.get_entity(record_id) if record_id else None
    if existing and record_id:
        return [
            await seekdb_business_store.update_entity(
                table, record_id, {**existing, **data}
            )
        ]
    return [await seekdb_business_store.create_entity(table, {"id": record_id, **data})]


async def repo_update(
    table: str, id: str, data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    try:
        record_id = str(id) if ":" in str(id) else f"{table}:{id}"
        data.pop("id", None)
        data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = await seekdb_business_store.get_entity(record_id)
        merged = {**(existing or {}), **data}
        return [await seekdb_business_store.update_entity(table, record_id, merged)]
    except Exception as e:
        raise RuntimeError(f"Failed to update record: {str(e)}")


async def repo_delete(record_id: str):
    try:
        return await seekdb_business_store.delete_entity(record_id)
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to delete record: {str(e)}")


async def repo_insert(
    table: str, data: List[Dict[str, Any]], ignore_duplicates: bool = False
) -> List[Dict[str, Any]]:
    try:
        return await seekdb_business_store.insert_many(table, data)
    except Exception as e:
        if ignore_duplicates:
            return []
        logger.exception(e)
        raise RuntimeError("Failed to create record")
