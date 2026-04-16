import pytest

from open_notebook.storage.visual_assets import VisualAssetStore
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
    assert any(result.type == "text" for result in results)


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
