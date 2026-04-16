from unittest.mock import MagicMock

import pytest

from open_notebook.vrag.search_engine import VRAGSearchEngine


class TestVRAGSearchEngineEncoding:
    @pytest.mark.asyncio
    async def test_encode_text_prefers_clip_text_encoder(self):
        clip_text_encoder = MagicMock(return_value=[0.1, 0.2, 0.3])
        embedding_model = MagicMock()

        engine = VRAGSearchEngine(
            embed_text_fn=clip_text_encoder,
            embedding_model=embedding_model,
        )

        result = await engine._encode_text("bar chart")

        assert result == [0.1, 0.2, 0.3]
        clip_text_encoder.assert_called_once_with("bar chart")
        embedding_model.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_encode_text_uses_multimodal_embedding_model_when_clip_compatible(self):
        embedding_model = MagicMock()
        embedding_model.model_name = "multimodal-clip"
        embedding_model.embed.return_value = [[0.4, 0.5, 0.6]]

        engine = VRAGSearchEngine(embedding_model=embedding_model)

        result = await engine._encode_text("architecture diagram")

        assert result == [0.4, 0.5, 0.6]
        embedding_model.embed.assert_called_once_with(["architecture diagram"])

    @pytest.mark.asyncio
    async def test_encode_text_rejects_generic_embedding_model_for_image_space(self):
        embedding_model = MagicMock()
        embedding_model.model_name = "text-embedding-3-large"

        engine = VRAGSearchEngine(embedding_model=embedding_model)

        with pytest.raises(RuntimeError, match="No text embedding available"):
            await engine._encode_text("architecture diagram")

        embedding_model.embed.assert_not_called()
