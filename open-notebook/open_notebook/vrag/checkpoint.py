"""VRAG checkpoint — DAG state persistence using SeekDB.

This module provides checkpointing for the VRAG workflow state,
enabling multi-turn conversations where the memory graph persists
across requests.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from open_notebook.vrag.memory import MultimodalMemoryGraph

logger = logging.getLogger(__name__)


class SeekDBSaver:
    """Checkpoint saver for VRAG state using SeekDB.

    Persists the following state across sessions:
    - Memory graph (nodes, edges, order)
    - Collected evidence
    - Conversation history
    - Search results cache

    Table: `ai_vrag_sessions`
    Table: `ai_vrag_state`
    """

    def __init__(self, seekdb_client):
        """Initialize the checkpoint saver.

        Args:
            seekdb_client: SeekDB client instance.
        """
        self.seekdb = seekdb_client

    def _upsert_state(self, state_id: str, session_id: str, state_type: str, state_data: str):
        """Upsert a state record into ai_vrag_state table."""
        now = datetime.utcnow().isoformat()

        # Check if exists
        existing = self.seekdb.fetch_one_sync(
            "SELECT id FROM ai_vrag_state WHERE id = %s",
            (state_id,)
        )

        if existing:
            self.seekdb.execute_sync(
                "UPDATE ai_vrag_state SET state_data = %s, updated_at = %s WHERE id = %s",
                (state_data, now, state_id)
            )
        else:
            self.seekdb.execute_sync(
                "INSERT INTO ai_vrag_state (id, session_id, state_type, state_data, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (state_id, session_id, state_type, state_data, now, now)
            )

    def save_session(self, session_id: str, notebook_id: str, metadata: Optional[dict] = None) -> bool:
        """Save or update a VRAG session.

        Args:
            session_id: Unique session identifier.
            notebook_id: Associated notebook ID.
            metadata: Optional session metadata.

        Returns:
            True if successful.
        """
        now = datetime.utcnow().isoformat()

        # Check if session exists
        existing = self.seekdb.fetch_one_sync(
            "SELECT session_id, metadata FROM ai_vrag_sessions WHERE session_id = %s",
            (session_id,)
        )

        merged_metadata: dict[str, Any] = {}
        if existing and existing.get("metadata"):
            try:
                merged_metadata.update(json.loads(existing["metadata"]))
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse metadata for session {session_id}, overwriting")
        if metadata:
            merged_metadata.update(metadata)

        metadata_json = json.dumps(merged_metadata)

        if existing:
            self.seekdb.execute_sync(
                "UPDATE ai_vrag_sessions SET notebook_id = %s, updated_at = %s, metadata = %s WHERE session_id = %s",
                (notebook_id, now, metadata_json, session_id)
            )
        else:
            self.seekdb.execute_sync(
                "INSERT INTO ai_vrag_sessions (session_id, notebook_id, created_at, updated_at, metadata) VALUES (%s, %s, %s, %s, %s)",
                (session_id, notebook_id, now, now, metadata_json)
            )

        return True

    def load_session(self, session_id: str) -> Optional[dict]:
        """Load a VRAG session.

        Args:
            session_id: Session identifier.

        Returns:
            Session metadata dict, or None if not found.
        """
        result = self.seekdb.fetch_one_sync(
            "SELECT * FROM ai_vrag_sessions WHERE session_id = %s",
            (session_id,)
        )
        if result and result.get("metadata"):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def save_memory_graph(self, session_id: str, memory_graph: MultimodalMemoryGraph) -> bool:
        """Save the memory graph for a session.

        Args:
            session_id: Session identifier.
            memory_graph: MultimodalMemoryGraph instance.

        Returns:
            True if successful.
        """
        state_id = f"{session_id}_memory_graph"
        state_data = json.dumps(memory_graph.to_dict())
        self._upsert_state(state_id, session_id, "memory_graph", state_data)

        logger.debug(f"Saved memory graph for session {session_id}")
        return True

    def load_memory_graph(self, session_id: str) -> Optional[MultimodalMemoryGraph]:
        """Load the memory graph for a session.

        Args:
            session_id: Session identifier.

        Returns:
            MultimodalMemoryGraph instance, or None if not found.
        """
        state_id = f"{session_id}_memory_graph"
        result = self.seekdb.fetch_one_sync(
            "SELECT state_data FROM ai_vrag_state WHERE id = %s",
            (state_id,)
        )

        if result and result.get("state_data"):
            try:
                data = json.loads(result["state_data"])
                return MultimodalMemoryGraph.from_dict(data)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning(f"Failed to load memory graph for session {session_id}: {e}")

        return None

    def save_collected_evidence(self, session_id: str, evidence: list[dict]) -> bool:
        """Save collected evidence for a session.

        Args:
            session_id: Session identifier.
            evidence: List of evidence dicts.

        Returns:
            True if successful.
        """
        state_id = f"{session_id}_evidence"
        state_data = json.dumps(evidence)
        self._upsert_state(state_id, session_id, "evidence", state_data)

        logger.debug(f"Saved {len(evidence)} evidence items for session {session_id}")
        return True

    def load_collected_evidence(self, session_id: str) -> list[dict]:
        """Load collected evidence for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of evidence dicts.
        """
        state_id = f"{session_id}_evidence"
        result = self.seekdb.fetch_one_sync(
            "SELECT state_data FROM ai_vrag_state WHERE id = %s",
            (state_id,)
        )

        if result and result.get("state_data"):
            try:
                return json.loads(result["state_data"])
            except (json.JSONDecodeError, TypeError):
                pass

        return []

    def save_messages(self, session_id: str, messages: list[dict]) -> bool:
        """Save conversation messages for a session.

        Args:
            session_id: Session identifier.
            messages: List of message dicts.

        Returns:
            True if successful.
        """
        state_id = f"{session_id}_messages"
        state_data = json.dumps(messages)
        self._upsert_state(state_id, session_id, "messages", state_data)

        return True

    def load_messages(self, session_id: str) -> list[dict]:
        """Load conversation messages for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of message dicts.
        """
        state_id = f"{session_id}_messages"
        result = self.seekdb.fetch_one_sync(
            "SELECT state_data FROM ai_vrag_state WHERE id = %s",
            (state_id,)
        )

        if result and result.get("state_data"):
            try:
                return json.loads(result["state_data"])
            except (json.JSONDecodeError, TypeError):
                pass

        return []

    def delete_session(self, session_id: str) -> int:
        """Delete a VRAG session and all its state.

        Args:
            session_id: Session identifier.

        Returns:
            Number of records deleted.
        """
        deleted = self.seekdb.execute_sync(
            "DELETE FROM ai_vrag_state WHERE session_id = %s",
            (session_id,)
        )
        self.seekdb.execute_sync(
            "DELETE FROM ai_vrag_sessions WHERE session_id = %s",
            (session_id,)
        )
        logger.info(f"Deleted session {session_id} and {deleted} state records")
        return deleted

    def list_sessions(self, notebook_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        """List VRAG sessions.

        Args:
            notebook_id: Optional filter by notebook ID.
            limit: Maximum number of sessions to return.

        Returns:
            List of session metadata dicts.
        """
        if notebook_id:
            results = self.seekdb.fetch_all_sync(
                "SELECT * FROM ai_vrag_sessions WHERE notebook_id = %s ORDER BY updated_at DESC LIMIT %s",
                (notebook_id, limit),
            )
        else:
            results = self.seekdb.fetch_all_sync(
                "SELECT * FROM ai_vrag_sessions ORDER BY updated_at DESC LIMIT %s",
                (limit,),
            )

        for result in results:
            if result.get("metadata"):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass

        return results

    def checkpoint_state(
        self,
        session_id: str,
        memory_graph: Optional[MultimodalMemoryGraph] = None,
        evidence: Optional[list[dict]] = None,
        messages: Optional[list[dict]] = None,
    ) -> bool:
        """Save a complete state checkpoint for a session.

        Args:
            session_id: Session identifier.
            memory_graph: Optional memory graph to save.
            evidence: Optional evidence list to save.
            messages: Optional messages list to save.

        Returns:
            True if all saves successful.
        """
        if memory_graph is not None:
            self.save_memory_graph(session_id, memory_graph)
        if evidence is not None:
            self.save_collected_evidence(session_id, evidence)
        if messages is not None:
            self.save_messages(session_id, messages)

        # Update session timestamp
        self.seekdb.execute_sync(
            "UPDATE ai_vrag_sessions SET updated_at = %s WHERE session_id = %s",
            (datetime.utcnow().isoformat(), session_id),
        )

        return True
