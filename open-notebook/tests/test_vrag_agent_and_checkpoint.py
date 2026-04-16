from types import SimpleNamespace

import pytest

from open_notebook.vrag.agent import VRAGAgent
from open_notebook.vrag.checkpoint import SeekDBSaver
from open_notebook.vrag.memory import MultimodalMemoryGraph
from open_notebook.vrag.tools import SearchResult


class SequencedLLM:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def invoke(self, _messages, config=None):
        return SimpleNamespace(content=self._responses.pop(0))


class FakeTools:
    def __init__(self, *, fail_search: bool = False):
        self.fail_search = fail_search
        self.search_calls: list[str] = []

    async def search(self, query: str, source_ids=None):
        self.search_calls.append(query)
        if self.fail_search:
            raise RuntimeError("search backend unavailable")
        return SearchResult(
            images=[{
                "chunk_id": "img-1",
                "score": 0.9,
                "image_path": "/tmp/chart.png",
                "page_no": 1,
                "source_id": "source-1",
                "summary": "Revenue chart",
                "bbox": None,
            }],
            texts=[],
            total_image_hits=1,
            total_text_hits=0,
        )

    def answer(self, question: str, memory_entries, collected_evidence):
        return f"Answer for: {question}"

    def summarize(self, search_results, question, memory_graph):
        return {"summary": f"Summary for: {question}"}

    def bbox_crop(self, image_path: str, bbox, padding: float = 0.02):
        raise NotImplementedError


class FakeSeekDBClient:
    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.states: dict[str, dict] = {}
        self.executed_sql: list[str] = []

    def fetch_one_sync(self, query: str, params=None):
        query = query.strip()
        if "FROM ai_vrag_sessions" in query:
            session_id = params[0]
            row = self.sessions.get(session_id)
            return dict(row) if row else None
        if "FROM ai_vrag_state" in query:
            state_id = params[0]
            row = self.states.get(state_id)
            return {"state_data": row["state_data"]} if row else None
        return None

    def fetch_all_sync(self, query: str, params=None):
        self.executed_sql.append(query.strip())
        if "FROM ai_vrag_sessions" not in query:
            return []

        rows = list(self.sessions.values())
        if "WHERE notebook_id = %s" in query and params:
            rows = [row for row in rows if row["notebook_id"] == params[0]]
        rows.sort(key=lambda row: row["updated_at"], reverse=True)
        limit = params[-1] if params else 50
        return [dict(row) for row in rows[:limit]]

    def execute_sync(self, query: str, params=None):
        normalized = " ".join(query.strip().split())
        self.executed_sql.append(normalized)

        if normalized.startswith("INSERT INTO ai_vrag_sessions"):
            session_id, notebook_id, created_at, updated_at, metadata = params
            self.sessions[session_id] = {
                "session_id": session_id,
                "notebook_id": notebook_id,
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": metadata,
            }
            return 1

        if normalized.startswith("UPDATE ai_vrag_sessions SET notebook_id"):
            notebook_id, updated_at, metadata, session_id = params
            session = self.sessions[session_id]
            session["notebook_id"] = notebook_id
            session["updated_at"] = updated_at
            session["metadata"] = metadata
            return 1

        if normalized.startswith("UPDATE ai_vrag_sessions SET updated_at"):
            updated_at, session_id = params
            self.sessions[session_id]["updated_at"] = updated_at
            return 1

        if normalized.startswith("INSERT INTO ai_vrag_state"):
            state_id, session_id, state_type, state_data, created_at, updated_at = params
            self.states[state_id] = {
                "id": state_id,
                "session_id": session_id,
                "state_type": state_type,
                "state_data": state_data,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            return 1

        if normalized.startswith("UPDATE ai_vrag_state SET state_data"):
            state_data, updated_at, state_id = params
            state = self.states[state_id]
            state["state_data"] = state_data
            state["updated_at"] = updated_at
            return 1

        if normalized.startswith("DELETE FROM ai_vrag_state WHERE session_id"):
            session_id = params[0]
            to_delete = [state_id for state_id, row in self.states.items() if row["session_id"] == session_id]
            for state_id in to_delete:
                del self.states[state_id]
            return len(to_delete)

        if normalized.startswith("DELETE FROM ai_vrag_sessions WHERE session_id"):
            self.sessions.pop(params[0], None)
            return 1

        raise AssertionError(f"Unhandled SQL in fake client: {normalized}")


@pytest.mark.asyncio
async def test_vrag_agent_non_stream_path_runs_search_then_answer():
    agent = VRAGAgent(
        tools=FakeTools(),
        llm_client=SequencedLLM([
            "<search>revenue chart</search>",
            "<answer></answer>",
        ]),
        max_steps=3,
    )

    state = await agent.run(
        question="What does the chart show?",
        source_ids=["source-1"],
        messages=[{"id": "human-1", "type": "human", "content": "Earlier question", "timestamp": "2024-01-01T00:00:00"}],
        memory_graph=MultimodalMemoryGraph(),
        collected_evidence=[],
    )

    assert state.is_complete is True
    assert state.error is None
    assert state.current_answer == "Answer for: What does the chart show?"
    assert [message["type"] for message in state.messages] == ["human", "human", "ai"]
    assert [action.tool_name for action in state.actions] == ["search", "answer"]


@pytest.mark.asyncio
async def test_vrag_agent_returns_structured_tool_error():
    agent = VRAGAgent(
        tools=FakeTools(fail_search=True),
        llm_client=SequencedLLM(["<search>broken backend</search>"]),
        max_steps=2,
    )

    state = await agent.run(question="Find the chart", source_ids=["source-1"])

    assert state.is_complete is False
    assert state.error == "search backend unavailable"
    assert state.actions[0].tool_output == {"error": "search backend unavailable"}


def test_seekdb_saver_persists_messages_and_merges_metadata_without_hot_path_ddl():
    fake_seekdb = FakeSeekDBClient()
    saver = SeekDBSaver(fake_seekdb)

    saver.save_session("session-1", "notebook-1", {"title": "Revenue Chat"})
    saver.save_session("session-1", "notebook-1", {"is_complete": True, "current_answer": "42"})

    memory_graph = MultimodalMemoryGraph()
    memory_graph.add_node(
        node_type="search",
        summary="Revenue chart found",
        images=["/tmp/chart.png"],
        priority=0.8,
        is_useful=True,
        key_insight="Revenue grows over time",
    )

    saver.checkpoint_state(
        "session-1",
        memory_graph=memory_graph,
        evidence=[{"type": "search", "query": "revenue"}],
        messages=[{"id": "human-1", "type": "human", "content": "Question", "timestamp": "2024-01-01T00:00:00"}],
    )

    loaded_session = saver.load_session("session-1")
    assert loaded_session is not None
    assert loaded_session["metadata"]["title"] == "Revenue Chat"
    assert loaded_session["metadata"]["is_complete"] is True
    assert loaded_session["metadata"]["current_answer"] == "42"

    loaded_messages = saver.load_messages("session-1")
    assert loaded_messages[0]["content"] == "Question"
    loaded_graph = saver.load_memory_graph("session-1")
    assert loaded_graph is not None
    assert loaded_graph.node_order

    assert all("CREATE TABLE" not in sql.upper() for sql in fake_seekdb.executed_sql)
