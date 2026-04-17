import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from open_notebook.storage.visual_assets import VisualAssetStore
from open_notebook.vrag import utils as vrag_utils
from open_notebook.vrag.memory import MultimodalMemoryGraph
from open_notebook.vrag.tools import VRAGTools
from open_notebook.vrag import workflow as vrag_workflow
from open_notebook.visual_rag import api as visual_api
from open_notebook.visual_rag.search_engine import VisualAssetSearchEngine


class FakeVisualAssetClient:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    async def execute(self, query: str, params=None):
        normalized = " ".join(query.strip().split())
        if normalized.startswith("INSERT INTO ai_visual_assets"):
            (
                asset_id,
                source_id,
                page_id,
                legacy_id,
                asset_type,
                media_type,
                page_no,
                file_path,
                summary,
                raw_text,
                bbox_json,
                embedding_json,
                metadata_json,
                index_status,
                index_command_id,
                created_at,
                updated_at,
            ) = params
            self.rows[asset_id] = {
                "id": asset_id,
                "source_id": source_id,
                "page_id": page_id,
                "legacy_id": legacy_id,
                "asset_type": asset_type,
                "media_type": media_type,
                "page_no": page_no,
                "file_path": file_path,
                "summary": summary,
                "raw_text": raw_text,
                "bbox_json": bbox_json,
                "embedding_json": embedding_json,
                "metadata_json": metadata_json,
                "index_status": index_status,
                "index_command_id": index_command_id,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            return 1
        if normalized.startswith("DELETE FROM ai_visual_assets WHERE source_id"):
            source_id = params[0]
            to_delete = [
                asset_id
                for asset_id, row in self.rows.items()
                if row["source_id"] == source_id
            ]
            for asset_id in to_delete:
                del self.rows[asset_id]
            return len(to_delete)
        raise AssertionError(f"Unhandled SQL: {normalized}")

    async def fetch_one(self, query: str, params=None):
        normalized = " ".join(query.strip().split())
        if "WHERE id = %s" in normalized:
            return self.rows.get(params[0])
        if "COUNT(*) AS asset_count" in normalized:
            source_id = params[0]
            rows = [
                row
                for row in self.rows.values()
                if row["source_id"] == source_id and row["asset_type"] != "index_status"
            ]
            return {
                "asset_count": len(rows),
                "last_indexed_at": max((row["updated_at"] for row in rows), default=None),
                "index_command_id": max((row.get("index_command_id") or "" for row in rows), default=None),
                "failed_count": sum(row["index_status"] == "failed" for row in rows),
                "active_count": sum(row["index_status"] in {"queued", "running"} for row in rows),
            }
        if "asset_type = 'index_status'" in normalized:
            source_id = params[0]
            markers = [
                row
                for row in self.rows.values()
                if row["source_id"] == source_id and row["asset_type"] == "index_status"
            ]
            markers.sort(key=lambda row: row["updated_at"], reverse=True)
            return markers[0] if markers else None
        return None

    async def fetch_all(self, query: str, params=None):
        normalized = " ".join(query.strip().split())
        if "FROM ai_visual_assets" not in normalized:
            return []
        keyword = str(params[0]).strip("%").lower()
        return [
            row
            for row in self.rows.values()
            if row["asset_type"] != "index_status"
            and keyword in f"{row.get('summary') or ''} {row.get('raw_text') or ''}".lower()
        ]


@pytest.mark.asyncio
async def test_visual_asset_summary_excludes_status_marker(monkeypatch, tmp_path):
    fake_client = FakeVisualAssetClient()
    monkeypatch.setattr("open_notebook.storage.visual_assets.seekdb_client", fake_client)
    monkeypatch.setattr(
        "open_notebook.storage.visual_assets.VISUAL_ASSETS_FOLDER",
        str(tmp_path),
    )
    store = VisualAssetStore()

    await store.upsert_asset(
        {
            "id": "asset-1",
            "source_id": "source-1",
            "asset_type": "page_render",
            "media_type": "image/png",
            "page_no": 1,
            "summary": "Revenue chart",
            "raw_text": "Revenue increased",
            "index_status": "completed",
            "index_command_id": "command:old",
        }
    )
    await store.mark_source_index_status(
        "source-1",
        status="queued",
        command_id="command:new",
    )

    queued_summary = await store.source_index_summary("source-1")

    assert queued_summary["visual_asset_count"] == 1
    assert queued_summary["visual_index_status"] == "queued"
    assert queued_summary["visual_index_command_id"] == "command:new"

    await store.mark_source_index_status(
        "source-1",
        status="completed",
        command_id="command:new",
    )

    completed_summary = await store.source_index_summary("source-1")

    assert completed_summary["visual_asset_count"] == 1
    assert completed_summary["visual_index_status"] == "completed"


@pytest.mark.asyncio
async def test_visual_asset_summary_recovers_from_stale_queued_marker(
    monkeypatch, tmp_path
):
    fake_client = FakeVisualAssetClient()
    monkeypatch.setattr("open_notebook.storage.visual_assets.seekdb_client", fake_client)
    monkeypatch.setattr(
        "open_notebook.storage.visual_assets.VISUAL_ASSETS_FOLDER",
        str(tmp_path),
    )
    async def fake_get_job(_job_id):
        return None

    monkeypatch.setattr("open_notebook.jobs.job_store.get_job", fake_get_job)

    store = VisualAssetStore()
    stale_at = (datetime.now() - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")

    await store.upsert_asset(
        {
            "id": "asset-1",
            "source_id": "source-1",
            "asset_type": "page_render",
            "media_type": "image/png",
            "page_no": 1,
            "summary": "Revenue chart",
            "raw_text": "Revenue increased",
            "index_status": "completed",
            "index_command_id": "command:old",
            "updated_at": stale_at,
        }
    )
    await store.upsert_asset(
        {
            "id": "visual_asset:index_status:source-1",
            "source_id": "source-1",
            "asset_type": "index_status",
            "summary": "",
            "index_status": "queued",
            "index_command_id": "command:stale",
            "updated_at": stale_at,
            "created_at": stale_at,
        }
    )

    summary = await store.source_index_summary("source-1")

    assert summary["visual_asset_count"] == 1
    assert summary["visual_index_status"] == "completed"
    assert summary["visual_index_command_id"] == "command:stale"


def test_extract_images_from_pdf_renders_page_without_unbound_image_bytes(
    monkeypatch, tmp_path
):
    class FakePixmap:
        width = 800
        height = 600

        def save(self, path: str):
            Path(path).write_bytes(b"png")

    class FakePage:
        rect = vrag_utils.fitz.Rect(0, 0, 600, 800)

        def get_images(self, full=True):
            return []

        def get_pixmap(self, dpi=150):
            return FakePixmap()

        def get_text(self, mode="text"):
            assert mode == "text"
            return "Page 1 text"

    class FakeDoc:
        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return FakePage()

        def close(self):
            return None

    monkeypatch.setattr(vrag_utils.fitz, "open", lambda _path: FakeDoc())

    results = vrag_utils.extract_images_from_pdf(
        str(tmp_path / "demo.pdf"),
        output_dir=str(tmp_path / "images"),
    )

    assert len(results) == 1
    assert results[0]["asset_type"] == "page_render"
    assert results[0]["is_native_image"] is False
    assert results[0]["image_bytes"] is None
    assert results[0]["raw_text"] == "Page 1 text"
    assert Path(results[0]["image_path"]).exists()


def test_extract_images_from_pdf_keeps_page_render_and_filters_native_tiles(
    monkeypatch, tmp_path
):
    class FakePixmap:
        width = 1200
        height = 1600

        def save(self, path: str):
            Path(path).write_bytes(b"png")

    class FakePage:
        rect = vrag_utils.fitz.Rect(0, 0, 600, 800)

        def get_images(self, full=True):
            return [(11,), (12,), (13,)]

        def get_pixmap(self, dpi=150):
            return FakePixmap()

        def get_text(self, mode="text"):
            return "Important page text"

        def get_image_rects(self, xref):
            if xref == 11:
                return [vrag_utils.fitz.Rect(60, 80, 360, 420)]
            if xref == 12:
                return [vrag_utils.fitz.Rect(20, 20, 35, 780)]
            if xref == 13:
                return [vrag_utils.fitz.Rect(20, 20, 40, 40)]
            return []

    class FakeDoc:
        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return FakePage()

        def extract_image(self, xref):
            return {
                "image": f"image-{xref}".encode(),
                "ext": "png",
                "width": 300,
                "height": 220,
            }

        def close(self):
            return None

    monkeypatch.setattr(vrag_utils.fitz, "open", lambda _path: FakeDoc())

    results = vrag_utils.extract_images_from_pdf(
        str(tmp_path / "demo.pdf"),
        output_dir=str(tmp_path / "images"),
    )

    assert [item["asset_type"] for item in results] == ["page_render", "native_image"]
    native_asset = results[1]
    assert native_asset["is_native_image"] is True
    assert native_asset["raw_text"] == "Important page text"
    assert native_asset["bbox"] == pytest.approx([0.1, 0.1, 0.6, 0.525], rel=1e-3)
    assert native_asset["metadata"]["area_ratio"] > 0.2


def test_extract_images_from_pdf_renders_page_when_native_images_are_all_filtered(
    monkeypatch, tmp_path
):
    class FakePixmap:
        width = 900
        height = 1200

        def save(self, path: str):
            Path(path).write_bytes(b"png")

    class FakePage:
        rect = vrag_utils.fitz.Rect(0, 0, 600, 800)

        def get_images(self, full=True):
            return [(99,)]

        def get_pixmap(self, dpi=150):
            return FakePixmap()

        def get_text(self, mode="text"):
            return "Filtered native image page"

        def get_image_rects(self, xref):
            return [vrag_utils.fitz.Rect(15, 20, 35, 40)]

    class FakeDoc:
        def __len__(self):
            return 1

        def __getitem__(self, index):
            return FakePage()

        def extract_image(self, xref):
            return {
                "image": b"tiny",
                "ext": "png",
                "width": 32,
                "height": 32,
            }

        def close(self):
            return None

    monkeypatch.setattr(vrag_utils.fitz, "open", lambda _path: FakeDoc())

    results = vrag_utils.extract_images_from_pdf(
        str(tmp_path / "demo.pdf"),
        output_dir=str(tmp_path / "images"),
    )

    assert len(results) == 1
    assert results[0]["asset_type"] == "page_render"
    assert results[0]["page_no"] == 1


@pytest.mark.asyncio
async def test_visual_search_engine_returns_safe_asset_file_urls(monkeypatch):
    async def fake_search_assets(*_args, **_kwargs):
        return [
            {
                "id": "asset-1",
                "source_id": "source-1",
                "page_no": 2,
                "file_path": "/data/visual-assets/source-1/page.png",
                "score": 3,
                "match": "Revenue chart",
                "summary": "Revenue chart",
                "bbox": [0, 0, 10, 10],
                "asset_type": "page_render",
                "metadata": {"is_native_image": False},
            }
        ]

    async def fake_text_search(*_args, **_kwargs):
        return [
            {
                "id": "text-1",
                "source_id": "source-1",
                "page": 2,
                "match": "Revenue increased",
                "score": 0.4,
                "title": "Annual report",
            }
        ]

    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.visual_asset_store.search_assets",
        fake_search_assets,
    )
    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.ai_retrieval_service.text_search",
        fake_text_search,
    )

    results = await VisualAssetSearchEngine().search_hybrid("revenue")
    image_result = results[0].to_dict()

    assert image_result["asset_id"] == "asset-1"
    assert image_result["file_url"] == "/api/visual-assets/asset-1/file"
    assert image_result["type"] == "image"
    assert image_result["asset_type"] == "page_render"
    assert image_result["is_native_image"] is False
    assert any(result.type == "text" for result in results)


@pytest.mark.asyncio
async def test_visual_search_engine_expands_visual_queries(monkeypatch):
    seen_visual_queries: list[str] = []
    seen_text_queries: list[str] = []

    async def fake_search_assets(query, *_args, **_kwargs):
        seen_visual_queries.append(query)
        if query in {"table", "figure"}:
            return [
                {
                    "id": f"asset-{query}",
                    "source_id": "source-1",
                    "page_no": 4,
                    "file_path": f"/data/{query}.png",
                    "score": 2,
                    "match": f"{query} result",
                    "summary": f"{query} result",
                    "bbox": None,
                    "asset_type": "page_render",
                    "metadata": {"is_native_image": False},
                }
            ]
        return []

    async def fake_text_search(keyword, *_args, **_kwargs):
        seen_text_queries.append(keyword)
        if keyword == "table":
            return [
                {
                    "id": "text-table",
                    "source_id": "source-1",
                    "page": 4,
                    "match": "Table result",
                    "score": 0.7,
                    "title": "Table result",
                }
            ]
        return []

    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.visual_asset_store.search_assets",
        fake_search_assets,
    )
    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.ai_retrieval_service.text_search",
        fake_text_search,
    )

    results = await VisualAssetSearchEngine().search_hybrid(
        "What figures and tables are in this paper?"
    )

    assert "table" in seen_visual_queries
    assert "figure" in seen_visual_queries
    assert "table" in seen_text_queries
    assert any(result.type == "image" for result in results)
    assert any(result.type == "text" for result in results)


@pytest.mark.asyncio
async def test_visual_search_engine_prioritizes_page_renders_for_inventory_queries(monkeypatch):
    async def fake_search_assets(*_args, **_kwargs):
        return [
            {
                "id": "page-3",
                "source_id": "source-1",
                "page_no": 3,
                "file_path": "/data/page3.png",
                "score": 0.8,
                "match": "Page 3 overview",
                "summary": "Page 3 overview",
                "bbox": [],
                "asset_type": "page_render",
                "metadata": {"is_native_image": False},
            },
            {
                "id": "page-4",
                "source_id": "source-1",
                "page_no": 4,
                "file_path": "/data/page4.png",
                "score": 0.9,
                "match": "Page 4 overview",
                "summary": "Page 4 overview",
                "bbox": [],
                "asset_type": "page_render",
                "metadata": {"is_native_image": False},
            },
            {
                "id": "page10-a",
                "source_id": "source-1",
                "page_no": 10,
                "file_path": "/data/page10-a.png",
                "score": 1.8,
                "match": "Tiny strip",
                "summary": "Tiny strip",
                "bbox": [0.11, 0.39, 0.14, 0.40],
                "asset_type": "native_image",
                "metadata": {"is_native_image": True, "area_ratio": 0.008},
            },
            {
                "id": "page10-b",
                "source_id": "source-1",
                "page_no": 10,
                "file_path": "/data/page10-b.png",
                "score": 1.7,
                "match": "Tiny strip",
                "summary": "Tiny strip",
                "bbox": [0.20, 0.39, 0.23, 0.40],
                "asset_type": "native_image",
                "metadata": {"is_native_image": True, "area_ratio": 0.008},
            },
            {
                "id": "page-6",
                "source_id": "source-1",
                "page_no": 6,
                "file_path": "/data/page6.png",
                "score": 0.7,
                "match": "Page 6 overview",
                "summary": "Page 6 overview",
                "bbox": [],
                "asset_type": "page_render",
                "metadata": {"is_native_image": False},
            },
        ]

    async def fake_text_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.visual_asset_store.search_assets",
        fake_search_assets,
    )
    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.ai_retrieval_service.text_search",
        fake_text_search,
    )

    results = await VisualAssetSearchEngine().search_hybrid(
        "你可以看见什么？",
        image_top_k=3,
        text_top_k=1,
    )

    image_results = [result for result in results if result.type == "image"]
    assert [result.asset_type for result in image_results] == [
        "page_render",
        "page_render",
        "page_render",
    ]
    assert [result.page_no for result in image_results] == [4, 3, 6]


@pytest.mark.asyncio
async def test_visual_search_engine_keeps_native_assets_for_specific_figure_queries(monkeypatch):
    async def fake_search_assets(*_args, **_kwargs):
        return [
            {
                "id": "page-10",
                "source_id": "source-1",
                "page_no": 10,
                "file_path": "/data/page10.png",
                "score": 0.9,
                "match": "Figure 3 on page 10",
                "summary": "Figure 3 on page 10",
                "bbox": [],
                "asset_type": "page_render",
                "metadata": {"is_native_image": False},
            },
            {
                "id": "native-10",
                "source_id": "source-1",
                "page_no": 10,
                "file_path": "/data/native10.png",
                "score": 0.85,
                "match": "Figure 3 classification map",
                "summary": "Figure 3 classification map",
                "bbox": [0.2, 0.3, 0.7, 0.8],
                "asset_type": "native_image",
                "metadata": {"is_native_image": True, "area_ratio": 0.18},
            },
        ]

    async def fake_text_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.visual_asset_store.search_assets",
        fake_search_assets,
    )
    monkeypatch.setattr(
        "open_notebook.visual_rag.search_engine.ai_retrieval_service.text_search",
        fake_text_search,
    )

    results = await VisualAssetSearchEngine().search_hybrid(
        "Figure 3 里有什么？",
        image_top_k=2,
        text_top_k=1,
    )

    image_results = [result for result in results if result.type == "image"]
    assert any(result.asset_type == "native_image" for result in image_results)
    assert any(result.asset_type == "page_render" for result in image_results)


def test_memory_graph_to_dag_json_matches_frontend_shape():
    graph = MultimodalMemoryGraph()
    first_id = graph.add_node(
        "search",
        "Found a table on page 4",
        images=["/api/visual-assets/asset-1/file"],
        key_insight="Table IV reports the ablation study.",
        priority=0.7,
    )
    graph.add_node(
        "answer",
        "Summarized the evidence",
        parent_ids=[first_id],
        key_insight="The paper includes both figures and tables.",
        priority=1.0,
    )
    graph.nodes[first_id].images.append(None)

    dag = graph.to_dag_json()

    assert dag["nodes"][0]["summary"] == "Found a table on page 4"
    assert dag["nodes"][0]["images"] == ["/api/visual-assets/asset-1/file"]
    assert dag["nodes"][0]["key_insight"] == "Table IV reports the ablation study."
    assert dag["edges"][0]["source"] == first_id
    assert dag["edges"][0]["target"] == "answer_1"
    assert dag["edges"][0]["relation"] == "depends_on"


def test_legacy_vrag_router_is_deprecated_alias_for_visual_rag_routes():
    canonical_paths = {
        route.path.replace("/visual-rag", "", 1)
        for route in visual_api.router.routes
    }
    legacy_paths = {
        route.path.replace("/vrag", "", 1)
        for route in visual_api.legacy_router.routes
    }

    assert "/search" in canonical_paths
    assert "/chat/stream" in canonical_paths
    assert canonical_paths == legacy_paths


@pytest.mark.asyncio
async def test_agent_node_reuses_existing_evidence_for_language_follow_up():
    graph = MultimodalMemoryGraph()
    graph.add_node("answer", "Previous English answer")
    state = vrag_workflow.VRAGState(question="用中文回答", memory_graph=graph)
    state.collected_evidence.append(
        {"type": "search", "images": [{"summary": "Revenue chart"}], "texts": []}
    )

    class FakeTools:
        llm_client = object()

    result = await vrag_workflow.agent_node(state, FakeTools())

    assert result["current_step"] == "answer"
    assert result["dag_updates"][-1]["action"] == "answer"
    assert "language follow-up" in result["dag_updates"][-1]["thought"]


@pytest.mark.asyncio
async def test_agent_node_answers_visual_inventory_question_after_first_search_hit():
    state = vrag_workflow.VRAGState(question="你现在可以看见什么图片？")
    state.collected_evidence.append(
        {
            "type": "search",
            "images": [{"summary": "Table VI"}],
            "texts": [{"text": "table caption"}],
        }
    )

    class FakeTools:
        llm_client = object()

    result = await vrag_workflow.agent_node(state, FakeTools())

    assert result["current_step"] == "answer"
    assert result["dag_updates"][-1]["action"] == "answer"
    assert result["dag_updates"][-1]["thought"] == (
        "Enough evidence gathered for visual inventory question"
    )


@pytest.mark.asyncio
async def test_agent_node_answers_visual_detail_follow_up_after_search_hit():
    state = vrag_workflow.VRAGState(question="给我详细讲讲图片的内容")
    state.collected_evidence.append(
        {
            "type": "search",
            "images": [{"summary": "Table VI"}],
            "texts": [{"text": "table caption"}],
        }
    )

    class FakeTools:
        llm_client = object()

    result = await vrag_workflow.agent_node(state, FakeTools())

    assert result["current_step"] == "answer"
    assert result["dag_updates"][-1]["action"] == "answer"
    assert result["dag_updates"][-1]["thought"] == (
        "Reuse existing evidence for visual detail follow-up"
    )


@pytest.mark.asyncio
async def test_agent_node_falls_back_to_answer_when_llm_decision_times_out(monkeypatch):
    original_timeout = vrag_workflow.WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS
    monkeypatch.setattr(vrag_workflow, "WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS", 0.01)

    def slow_llm_invoke(*args, **kwargs):
        time.sleep(0.05)
        return "<search>chart</search>"

    monkeypatch.setattr(vrag_workflow, "_llm_invoke", slow_llm_invoke)

    class FakeTools:
        llm_client = object()

    state = vrag_workflow.VRAGState(question="What charts are in this document?")
    result = await vrag_workflow.agent_node(state, FakeTools())

    monkeypatch.setattr(
        vrag_workflow,
        "WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS",
        original_timeout,
    )

    assert result["current_step"] == "answer"
    assert result["dag_updates"][-1]["action"] == "answer"
    assert result["dag_updates"][-1]["thought"] == "LLM decision timeout"


@pytest.mark.asyncio
async def test_answer_action_node_times_out_and_completes(monkeypatch):
    original_timeout = vrag_workflow.WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS
    monkeypatch.setattr(vrag_workflow, "WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS", 0.01)

    class FakeTools:
        def answer(self, **kwargs):
            time.sleep(0.05)
            return "late answer"

    state = vrag_workflow.VRAGState(question="用中文回答")
    result = await vrag_workflow.answer_action_node(state, FakeTools())

    monkeypatch.setattr(
        vrag_workflow,
        "WORKFLOW_SYNC_CALL_TIMEOUT_SECONDS",
        original_timeout,
    )

    assert result["is_complete"] is True
    assert result["current_step"] == "end"
    assert result["final_answer"] == "回答生成超时，请重试。"


@pytest.mark.asyncio
async def test_answer_action_node_reuses_previous_question_for_language_follow_up():
    captured_question: dict[str, str] = {}

    class FakeTools:
        def answer(self, **kwargs):
            captured_question["value"] = kwargs["question"]
            return "中文答案"

    state = vrag_workflow.VRAGState(
        question="用中文回答",
        messages=[
            {"type": "human", "content": "What charts are in this document?"},
            {"type": "ai", "content": "No charts found."},
            {"type": "human", "content": "用中文回答"},
        ],
    )
    state.collected_evidence.append(
        {"type": "search", "images": [{"summary": "Revenue chart"}], "texts": []}
    )

    result = await vrag_workflow.answer_action_node(state, FakeTools())

    assert result["is_complete"] is True
    assert result["final_answer"] == "中文答案"
    assert captured_question["value"] == (
        "What charts are in this document?\n\n补充要求：用中文回答"
    )


@pytest.mark.asyncio
async def test_answer_action_node_reuses_previous_question_for_visual_detail_follow_up():
    captured_question: dict[str, str] = {}

    class FakeTools:
        def answer(self, **kwargs):
            captured_question["value"] = kwargs["question"]
            return "详细答案"

    state = vrag_workflow.VRAGState(
        question="给我详细讲讲图片的内容",
        messages=[
            {"type": "human", "content": "你可以看见什么？"},
            {"type": "ai", "content": "我看到了几张图。"},
            {"type": "human", "content": "给我详细讲讲图片的内容"},
        ],
    )
    state.collected_evidence.append(
        {"type": "search", "images": [{"summary": "Revenue chart"}], "texts": []}
    )

    result = await vrag_workflow.answer_action_node(state, FakeTools())

    assert result["is_complete"] is True
    assert result["final_answer"] == "详细答案"
    assert captured_question["value"] == (
        "你可以看见什么？\n\n补充要求：给我详细讲讲图片的内容"
    )


def test_answer_tool_prompt_defaults_to_chinese_and_marks_visibility():
    captured_prompt: dict[str, str] = {}
    tools = VRAGTools(search_engine=object(), llm_client=object())

    def fake_llm_invoke(*, messages, **kwargs):
        captured_prompt["value"] = messages[0]["content"]
        return "好的"

    tools._llm_invoke = fake_llm_invoke  # type: ignore[method-assign]

    answer = tools.answer(
        question="你现在可以看见什么图片？",
        memory_entries=[],
        collected_evidence=[
            {
                "type": "search",
                "images": [
                    {
                        "asset_id": "asset-visible",
                        "page_no": 11,
                        "summary": "Table VI classification accuracies.",
                        "file_url": "/api/visual-assets/asset-visible/file",
                        "image_path": None,
                    },
                    {
                        "asset_id": "asset-hidden",
                        "page_no": 15,
                        "summary": "Reference entries mentioning GraphMamba.",
                        "file_url": None,
                        "image_path": None,
                    },
                    {
                        "asset_id": "asset-hidden",
                        "page_no": 15,
                        "summary": "Reference entries mentioning GraphMamba.",
                        "file_url": None,
                        "image_path": None,
                    },
                ],
                "texts": [
                    {
                        "chunk_id": "text-1",
                        "page_no": 11,
                        "text": "TABLE VI classification accuracies of compared methods.",
                    }
                ],
            }
        ],
    )

    prompt = captured_prompt["value"]

    assert answer == "好的"
    assert "默认使用简体中文回答" in prompt
    assert "不要输出 “Answer: / Visual Evidence: / Limitations:”" in prompt
    assert "### 可直接查看的图片" in prompt
    assert "### 只有摘要、当前看不到原图的图片" in prompt
    assert "Table VI classification accuracies." in prompt
    assert prompt.count("Reference entries mentioning GraphMamba.") == 1


@pytest.mark.asyncio
async def test_stream_visual_rag_events_emits_complete_when_state_finishes_without_explicit_event(
    monkeypatch,
):
    class FakeSessionStore:
        def __init__(self):
            self.saved_metadata: list[dict] = []
            self.messages: list[dict] = []

        async def load_session(self, _session_id: str):
            return None

        async def load_memory_graph(self, _session_id: str):
            return None

        async def load_collected_evidence(self, _session_id: str):
            return []

        async def load_messages(self, _session_id: str):
            return []

        async def save_session(self, _session_id: str, _notebook_id: str, metadata=None):
            self.saved_metadata.append(metadata or {})
            return True

        async def checkpoint_state(
            self,
            session_id: str,
            memory_graph=None,
            evidence=None,
            messages=None,
        ):
            assert session_id == "session-1"
            if messages is not None:
                self.messages = messages
            return True

        async def append_event(self, _session_id: str, _event_type: str, _payload: dict):
            return "event-1"

    class FakeGraph:
        async def astream(self, state):
            state.memory_graph.add_node("search", "Found the chart")
            state.collected_evidence.append(
                {
                    "type": "search",
                    "images": [{"asset_id": "asset-1", "summary": "Revenue chart"}],
                }
            )
            state.final_answer = "Recovered answer from final state"
            state.is_complete = True
            yield {
                "search": {
                    "dag_updates": [
                        {
                            "node_id": "search_0",
                            "node_type": "search",
                            "summary": "Found the chart",
                        }
                    ]
                }
            }

    def fake_create_vrag_workflow(_tools, max_steps=10):
        def create_initial_state(question: str, source_ids: list[str], context: str):
            class FakeState:
                def __init__(self):
                    self.question = question
                    self.source_ids = source_ids
                    self.context = context
                    self.memory_graph = MultimodalMemoryGraph()
                    self.collected_evidence = []
                    self.final_answer = ""
                    self.is_complete = False
                    self.max_steps = max_steps

            return FakeState()

        return object(), create_initial_state

    fake_store = FakeSessionStore()
    monkeypatch.setattr(visual_api, "visual_rag_session_store", fake_store)
    monkeypatch.setattr(visual_api, "create_vrag_graph", lambda _tools: FakeGraph())
    monkeypatch.setattr(visual_api, "create_vrag_workflow", fake_create_vrag_workflow)

    events = [
        chunk
        async for chunk in visual_api.stream_visual_rag_events(
            question="What does the revenue chart show?",
            notebook_id="notebook-1",
            source_ids=["source-1"],
            context="",
            max_steps=4,
            tools=None,
            session_id="session-1",
        )
    ]

    assert any('"type": "dag_update"' in event for event in events)
    assert any('"type": "complete"' in event for event in events)
    assert any("Recovered answer from final state" in event for event in events)
    assert fake_store.saved_metadata[-1]["is_complete"] is True
    assert fake_store.saved_metadata[-1]["current_answer"] == "Recovered answer from final state"
    assert fake_store.messages[-1]["type"] == "ai"


@pytest.mark.asyncio
async def test_stream_visual_rag_events_preserves_dag_update_event_type(
    monkeypatch,
):
    class FakeSessionStore:
        async def load_session(self, _session_id: str):
            return None

        async def load_memory_graph(self, _session_id: str):
            return None

        async def load_collected_evidence(self, _session_id: str):
            return []

        async def load_messages(self, _session_id: str):
            return []

        async def save_session(self, *_args, **_kwargs):
            return True

        async def checkpoint_state(self, *_args, **_kwargs):
            return True

        async def append_event(self, _session_id: str, _event_type: str, payload: dict):
            self.payload = payload
            return "event-1"

    class FakeGraph:
        async def astream(self, state):
            state.final_answer = "Done"
            state.is_complete = True
            yield {
                "search": {
                    "dag_updates": [
                        {
                            "type": "search",
                            "node_id": "search_0",
                            "images_found": 2,
                            "texts_found": 1,
                        }
                    ]
                }
            }

    def fake_create_vrag_workflow(_tools, max_steps=10):
        def create_initial_state(question: str, source_ids: list[str], context: str):
            class FakeState:
                def __init__(self):
                    self.question = question
                    self.source_ids = source_ids
                    self.context = context
                    self.memory_graph = MultimodalMemoryGraph()
                    self.collected_evidence = []
                    self.messages = []
                    self.final_answer = ""
                    self.is_complete = False
                    self.max_steps = max_steps

            return FakeState()

        return object(), create_initial_state

    fake_store = FakeSessionStore()
    monkeypatch.setattr(visual_api, "visual_rag_session_store", fake_store)
    monkeypatch.setattr(visual_api, "create_vrag_graph", lambda _tools: FakeGraph())
    monkeypatch.setattr(visual_api, "create_vrag_workflow", fake_create_vrag_workflow)

    events = [
        chunk
        async for chunk in visual_api.stream_visual_rag_events(
            question="你现在可以看见什么图片？",
            notebook_id="notebook-1",
            source_ids=["source-1"],
            context="",
            max_steps=4,
            tools=None,
            session_id="session-1",
        )
    ]

    assert any('"type": "dag_update"' in event for event in events)
    assert '"update_type": "search"' in events[0]
    assert '"summary": "\\u627e\\u5230 2 \\u5f20\\u56fe\\u7247\\uff0c1 \\u6bb5\\u6587\\u672c"' in events[0]


@pytest.mark.asyncio
async def test_stream_visual_rag_events_ignores_duplicate_accumulated_updates(
    monkeypatch,
):
    class FakeSessionStore:
        def __init__(self):
            self.appended_payloads: list[dict] = []

        async def load_session(self, _session_id: str):
            return None

        async def load_memory_graph(self, _session_id: str):
            return None

        async def load_collected_evidence(self, _session_id: str):
            return []

        async def load_messages(self, _session_id: str):
            return []

        async def save_session(self, *_args, **_kwargs):
            return True

        async def checkpoint_state(self, *_args, **_kwargs):
            return True

        async def append_event(self, _session_id: str, _event_type: str, payload: dict):
            self.appended_payloads.append(payload)
            return "event-1"

    class FakeGraph:
        async def astream(self, state):
            update_1 = {
                "node_id": "search_0",
                "node_type": "search",
                "summary": "Found the first table",
            }
            update_2 = {
                "node_id": "answer_1",
                "node_type": "answer",
                "summary": "Finished the answer",
            }
            state.final_answer = "Done"
            state.is_complete = True
            yield {"search": {"dag_updates": [update_1]}}
            yield {
                "answer": {
                    "dag_updates": [update_1, update_2],
                    "final_answer": "Done",
                    "is_complete": True,
                }
            }

    def fake_create_vrag_workflow(_tools, max_steps=10):
        def create_initial_state(question: str, source_ids: list[str], context: str):
            class FakeState:
                def __init__(self):
                    self.question = question
                    self.source_ids = source_ids
                    self.context = context
                    self.memory_graph = MultimodalMemoryGraph()
                    self.collected_evidence = []
                    self.final_answer = ""
                    self.is_complete = False
                    self.max_steps = max_steps

            return FakeState()

        return object(), create_initial_state

    fake_store = FakeSessionStore()
    monkeypatch.setattr(visual_api, "visual_rag_session_store", fake_store)
    monkeypatch.setattr(visual_api, "create_vrag_graph", lambda _tools: FakeGraph())
    monkeypatch.setattr(visual_api, "create_vrag_workflow", fake_create_vrag_workflow)

    events = [
        chunk
        async for chunk in visual_api.stream_visual_rag_events(
            question="Which tables are present?",
            notebook_id="notebook-1",
            source_ids=["source-1"],
            context="",
            max_steps=4,
            tools=None,
            session_id="session-1",
        )
    ]

    dag_event_count = sum('"type": "dag_update"' in event for event in events)
    assert dag_event_count == 2
    assert len(fake_store.appended_payloads) == 2


@pytest.mark.asyncio
async def test_stream_visual_rag_events_does_not_fail_session_on_recoverable_node_error(
    monkeypatch,
):
    class FakeSessionStore:
        def __init__(self):
            self.saved_metadata: list[dict] = []

        async def load_session(self, _session_id: str):
            return None

        async def load_memory_graph(self, _session_id: str):
            return None

        async def load_collected_evidence(self, _session_id: str):
            return []

        async def load_messages(self, _session_id: str):
            return []

        async def save_session(self, _session_id: str, _notebook_id: str, metadata=None):
            self.saved_metadata.append(metadata or {})
            return True

        async def checkpoint_state(self, *_args, **_kwargs):
            return True

        async def append_event(self, *_args, **_kwargs):
            return "event-1"

    class FakeGraph:
        async def astream(self, state):
            yield {
                "bbox_crop": {
                    "error": "missing file",
                    "current_step": "agent",
                }
            }
            state.final_answer = "Recovered after node error"
            state.is_complete = True
            state.memory_graph.add_node("answer", "Recovered after node error")
            yield {
                "answer": {
                    "dag_updates": [
                        {
                            "type": "answer",
                            "node_id": "answer_0",
                            "answer_preview": "Recovered after node error",
                        }
                    ],
                    "final_answer": "Recovered after node error",
                    "is_complete": True,
                    "current_step": "end",
                }
            }

    def fake_create_vrag_workflow(_tools, max_steps=10):
        def create_initial_state(question: str, source_ids: list[str], context: str):
            class FakeState:
                def __init__(self):
                    self.question = question
                    self.source_ids = source_ids
                    self.context = context
                    self.memory_graph = MultimodalMemoryGraph()
                    self.collected_evidence = []
                    self.messages = []
                    self.final_answer = ""
                    self.is_complete = False
                    self.max_steps = max_steps

            return FakeState()

        return object(), create_initial_state

    fake_store = FakeSessionStore()
    monkeypatch.setattr(visual_api, "visual_rag_session_store", fake_store)
    monkeypatch.setattr(visual_api, "create_vrag_graph", lambda _tools: FakeGraph())
    monkeypatch.setattr(visual_api, "create_vrag_workflow", fake_create_vrag_workflow)

    events = [
        chunk
        async for chunk in visual_api.stream_visual_rag_events(
            question="给我详细讲讲图片的内容",
            notebook_id="notebook-1",
            source_ids=["source-1"],
            context="",
            max_steps=4,
            tools=None,
            session_id="session-1",
        )
    ]

    assert not any('"type": "error"' in event for event in events)
    assert any('"type": "complete"' in event for event in events)
    assert fake_store.saved_metadata[-1]["is_complete"] is True
    assert fake_store.saved_metadata[-1]["last_error"] is None
