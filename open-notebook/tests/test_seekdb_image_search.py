import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.seekdb.retrieval_service import AIRetrievalService


class TestImageVectorSearch:
    @pytest.mark.asyncio
    async def test_uses_multimodal_text_encoder_for_image_vectors(self):
        image_query_encoder = MagicMock(return_value=[1.0, 0.0])
        service = AIRetrievalService(image_query_embedding_fn=image_query_encoder)
        captured: dict[str, object] = {}

        async def fake_fetch_all(sql, params=None):
            captured["sql"] = sql
            captured["params"] = params
            return [
                {
                    "id": "img-low",
                    "source_id": "source-1",
                    "page_no": 1,
                    "image_path": "/tmp/low.png",
                    "image_summary": "low score image",
                    "bbox_regions": "[]",
                    "embedding_json": json.dumps([0.0, 1.0]),
                },
                {
                    "id": "img-best",
                    "source_id": "source-1",
                    "page_no": 2,
                    "image_path": "/tmp/best.png",
                    "image_summary": "best score image",
                    "bbox_regions": "[]",
                    "embedding_json": json.dumps([1.0, 0.0]),
                },
            ]

        with (
            patch(
                "open_notebook.seekdb.retrieval_service.seekdb_client.fetch_all",
                new=fake_fetch_all,
            ),
            patch(
                "open_notebook.seekdb.retrieval_service.generate_embedding",
                new=AsyncMock(side_effect=AssertionError("generic text embedding should not be used")),
            ),
        ):
            results = await service.image_vector_search(
                keyword="bar chart",
                top_k=1,
                minimum_score=0.0,
            )

        assert [row["id"] for row in results] == ["img-best"]
        image_query_encoder.assert_called_once_with("bar chart")
        assert "LIMIT" not in str(captured["sql"]).upper()
