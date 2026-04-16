"""Async session/event persistence for Visual RAG."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from open_notebook.seekdb import seekdb_client
from open_notebook.vrag.memory import MultimodalMemoryGraph


def _now(value: Optional[Any] = None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if value:
        return str(value)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


class VisualRAGSessionStore:
    """Repository for Visual RAG sessions and state snapshots."""

    async def save_session(
        self,
        session_id: str,
        notebook_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        now = _now()
        existing = await self.load_session(session_id)
        merged_metadata: dict[str, Any] = {}
        if existing and isinstance(existing.get("metadata"), dict):
            merged_metadata.update(existing["metadata"])
        if metadata:
            merged_metadata.update(metadata)

        title = merged_metadata.get("title")
        last_question = merged_metadata.get("last_question")
        current_answer = merged_metadata.get("current_answer") or ""
        last_answer_preview = (
            merged_metadata.get("last_answer_preview")
            or (current_answer[:200] if current_answer else "")
        )
        is_complete = bool(merged_metadata.get("is_complete"))
        total_steps = int(merged_metadata.get("total_steps") or 0)
        last_error = merged_metadata.get("last_error")
        created_at = (existing or {}).get("created_at") or now

        await seekdb_client.execute(
            """
            INSERT INTO ai_visual_rag_sessions (
                session_id, notebook_id, title, last_question, current_answer,
                last_answer_preview, is_complete, total_steps, last_error,
                metadata_json, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notebook_id = VALUES(notebook_id),
                title = VALUES(title),
                last_question = VALUES(last_question),
                current_answer = VALUES(current_answer),
                last_answer_preview = VALUES(last_answer_preview),
                is_complete = VALUES(is_complete),
                total_steps = VALUES(total_steps),
                last_error = VALUES(last_error),
                metadata_json = VALUES(metadata_json),
                updated_at = VALUES(updated_at)
            """,
            (
                session_id,
                notebook_id,
                title,
                last_question,
                current_answer,
                last_answer_preview,
                is_complete,
                total_steps,
                last_error,
                _json_dumps(merged_metadata),
                created_at,
                now,
            ),
        )
        return True

    async def load_session(self, session_id: str) -> Optional[dict[str, Any]]:
        row = await seekdb_client.fetch_one(
            """
            SELECT session_id, notebook_id, title, last_question, current_answer,
                   last_answer_preview, is_complete, total_steps, last_error,
                   metadata_json, created_at, updated_at
            FROM ai_visual_rag_sessions
            WHERE session_id = %s
            """,
            (session_id,),
        )
        return self._decode_session(row) if row else None

    async def list_sessions(
        self,
        notebook_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if notebook_id:
            rows = await seekdb_client.fetch_all(
                """
                SELECT session_id, notebook_id, title, last_question, current_answer,
                       last_answer_preview, is_complete, total_steps, last_error,
                       metadata_json, created_at, updated_at
                FROM ai_visual_rag_sessions
                WHERE notebook_id = %s
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (notebook_id, limit),
            )
        else:
            rows = await seekdb_client.fetch_all(
                """
                SELECT session_id, notebook_id, title, last_question, current_answer,
                       last_answer_preview, is_complete, total_steps, last_error,
                       metadata_json, created_at, updated_at
                FROM ai_visual_rag_sessions
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        return [self._decode_session(row) for row in rows]

    async def delete_session(self, session_id: str) -> int:
        deleted_events = await seekdb_client.execute(
            "DELETE FROM ai_visual_rag_events WHERE session_id = %s",
            (session_id,),
        )
        await seekdb_client.execute(
            "DELETE FROM ai_visual_rag_sessions WHERE session_id = %s",
            (session_id,),
        )
        return int(deleted_events or 0)

    async def checkpoint_state(
        self,
        session_id: str,
        memory_graph: Optional[MultimodalMemoryGraph] = None,
        evidence: Optional[list[dict[str, Any]]] = None,
        messages: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        if memory_graph is not None:
            await self.save_state(session_id, "memory_graph", memory_graph.to_dict())
        if evidence is not None:
            await self.save_state(session_id, "evidence", evidence)
        if messages is not None:
            await self.save_state(session_id, "messages", messages)
        await seekdb_client.execute(
            "UPDATE ai_visual_rag_sessions SET updated_at = %s WHERE session_id = %s",
            (_now(), session_id),
        )
        return True

    async def save_state(
        self,
        session_id: str,
        state_type: str,
        payload: Any,
        *,
        event_index: int = 0,
    ) -> str:
        event_id = f"visual_rag_event:{session_id}:{state_type}:{event_index}"
        now = _now()
        await seekdb_client.execute(
            """
            INSERT INTO ai_visual_rag_events (
                id, session_id, event_type, event_index, payload_json, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                payload_json = VALUES(payload_json),
                created_at = VALUES(created_at)
            """,
            (event_id, session_id, state_type, event_index, _json_dumps(payload), now),
        )
        return event_id

    async def append_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        row = await seekdb_client.fetch_one(
            """
            SELECT COALESCE(MAX(event_index), -1) AS max_index
            FROM ai_visual_rag_events
            WHERE session_id = %s AND event_type = %s
            """,
            (session_id, event_type),
        )
        max_index = (row or {}).get("max_index")
        event_index = (int(max_index) if max_index is not None else -1) + 1
        event_id = f"visual_rag_event:{uuid4().hex}"
        await seekdb_client.execute(
            """
            INSERT INTO ai_visual_rag_events (
                id, session_id, event_type, event_index, payload_json, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (event_id, session_id, event_type, event_index, _json_dumps(payload), _now()),
        )
        return event_id

    async def load_state(self, session_id: str, state_type: str, default: Any) -> Any:
        row = await seekdb_client.fetch_one(
            """
            SELECT payload_json
            FROM ai_visual_rag_events
            WHERE session_id = %s AND event_type = %s
            ORDER BY event_index DESC
            LIMIT 1
            """,
            (session_id, state_type),
        )
        return _json_loads((row or {}).get("payload_json"), default)

    async def load_memory_graph(self, session_id: str) -> Optional[MultimodalMemoryGraph]:
        payload = await self.load_state(session_id, "memory_graph", None)
        if not payload:
            return None
        try:
            return MultimodalMemoryGraph.from_dict(payload)
        except Exception:
            return None

    async def load_collected_evidence(self, session_id: str) -> list[dict[str, Any]]:
        return await self.load_state(session_id, "evidence", [])

    async def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        return await self.load_state(session_id, "messages", [])

    def _decode_session(self, row: dict[str, Any]) -> dict[str, Any]:
        metadata = _json_loads(row.get("metadata_json"), {})
        metadata.setdefault("title", row.get("title"))
        metadata.setdefault("last_question", row.get("last_question"))
        metadata.setdefault("current_answer", row.get("current_answer"))
        metadata.setdefault("last_answer_preview", row.get("last_answer_preview"))
        metadata.setdefault("is_complete", bool(row.get("is_complete")))
        metadata.setdefault("total_steps", int(row.get("total_steps") or 0))
        metadata.setdefault("last_error", row.get("last_error"))
        return {
            "session_id": row.get("session_id"),
            "notebook_id": row.get("notebook_id"),
            "title": row.get("title"),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "metadata": metadata,
        }


visual_rag_session_store = VisualRAGSessionStore()
