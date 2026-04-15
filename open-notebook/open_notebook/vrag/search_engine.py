"""VRAG search engine — multimodal retrieval with domestic Chinese API support.

Adapted from VRAG/search_engine/search_engine.py, supporting:
- Domestic Chinese embedding models via Esperanto (tongyi, zhipu, wenxin, spark, doubao)
- Legacy OpenAI CLIP API via embed_text_fn/embed_image_fn injection
- Direct clip_client fallback for CLIP image encoding
"""

import json
import logging
import math
from typing import Any, Callable, Optional

from esperanto import EmbeddingModel

from open_notebook.vrag.utils import image_to_base64

logger = logging.getLogger(__name__)

# Default RRF k parameter
RRF_K = 60


class VRAGSearchResult:
    """Container for a single search result."""

    def __init__(
        self,
        chunk_id: str,
        score: float,
        result_type: str,  # "image" | "text"
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        text: Optional[str] = None,
        page_no: Optional[int] = None,
        source_id: Optional[str] = None,
        bbox: Optional[list[float]] = None,
        summary: Optional[str] = None,
    ):
        self.chunk_id = chunk_id
        self.score = score
        self.type = result_type
        self.image_path = image_path
        self.image_base64 = image_base64
        self.text = text
        self.page_no = page_no
        self.source_id = source_id
        self.bbox = bbox
        self.summary = summary

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "score": self.score,
            "type": self.type,
            "image_path": self.image_path,
            "text": self.text,
            "page_no": self.page_no,
            "source_id": self.source_id,
            "bbox": self.bbox,
            "summary": self.summary,
        }


class VRAGSearchEngine:
    """Multimodal search engine for VRAG.

    Supports text and image embedding through multiple backends:
    1. model_manager embedding model (preferred, uses domestic Chinese models)
    2. Injected embed_text_fn / embed_image_fn (legacy OpenAI CLIP)
    3. Direct clip_client usage (fallback)

    Features:
    - Text query → image search
    - Image query → image search
    - RRF fusion of text and image search results
    - Hybrid search combining text chunks and image chunks
    """

    def __init__(
        self,
        clip_api_client=None,
        retrieval_service=None,
        embedding_dim: int = 768,
        default_top_k: int = 5,
        embed_text_fn: Optional[Callable[[str], list[float]]] = None,
        embed_image_fn: Optional[Callable[[str], list[float]]] = None,
        embedding_model: Optional[EmbeddingModel] = None,
    ):
        """Initialize the VRAG search engine.

        Args:
            clip_api_client: OpenAI API client for CLIP embeddings (legacy, prefer embed_*_fn).
            retrieval_service: SeekDB retrieval service for vector search.
            embedding_dim: Dimension of CLIP embeddings (768 for clip-ViT-L-14).
            default_top_k: Default number of results to return.
            embed_text_fn: Callable that takes a text string and returns an embedding vector.
            embed_image_fn: Callable that takes an image path and returns an embedding vector.
            embedding_model: Esperanto EmbeddingModel (preferred, from model_manager).
                             Supports domestic Chinese models via tongyi/zhipu/wenxin/etc.
        """
        self.clip_client = clip_api_client
        self.retrieval = retrieval_service
        self.embedding_dim = embedding_dim
        self.default_top_k = default_top_k
        self.embed_text_fn = embed_text_fn
        self.embed_image_fn = embed_image_fn
        self.embedding_model = embedding_model

    def _encode_text(self, text: str) -> list[float]:
        """Encode text query to embedding vector.

        Priority order:
        1. embed_text_fn (injected, legacy OpenAI CLIP)
        2. embedding_model (Esperanto, preferred for domestic models)
        3. clip_client.embeddings.create (direct OpenAI SDK fallback)

        Args:
            text: Text query string.

        Returns:
            Embedding vector as list of floats.

        Raises:
            RuntimeError: If no text embedding is available.
        """
        if self.embed_text_fn is not None:
            try:
                return self.embed_text_fn(text)
            except RuntimeError:
                # No API key available for text embedding — propagate to caller
                raise

        if self.embedding_model is not None:
            try:
                results = self.embedding_model.embed([text])
                if results and len(results) > 0:
                    embedding = results[0]
                    if isinstance(embedding, list):
                        return embedding
                    return list(embedding)
            except Exception as e:
                logger.warning(f"Embedding model failed: {e}")
                raise RuntimeError(f"Embedding model unavailable: {e}") from e

        if self.clip_client is None:
            raise RuntimeError(
                "No text embedding available. Provide embed_text_fn, "
                "embedding_model, or ensure clip_client is set."
            )
        try:
            response = self.clip_client.embeddings.create(
                model="clip-ViT-L-14",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"CLIP text encoding failed, falling back to text-embedding-3-large: {e}")
            response = self.clip_client.embeddings.create(
                model="text-embedding-3-large",
                input=text,
            )
            return response.data[0].embedding

    def _encode_image(self, image_path: str) -> list[float]:
        """Encode image to CLIP embedding.

        Priority order:
        1. embed_image_fn (injected, legacy)
        2. embedding_model if it supports images (rare - only CLIP/Spark)
        3. clip_client.embeddings.create (direct OpenAI CLIP fallback)

        Note: Most domestic Chinese embedding models (tongyi, zhipu, wenxin)
        only support text embeddings. For image search, use embed_image_fn
        or ensure clip_client is available.

        Args:
            image_path: Path to the image file.

        Returns:
            Embedding vector as list of floats.
        """
        if self.embed_image_fn is not None:
            return self.embed_image_fn(image_path)

        # Most domestic models don't support image embeddings
        # Only try embedding_model if it has image capability
        if self.embedding_model is not None:
            # Check if model supports image embedding (rare for domestic models)
            # For now, skip embedding_model for images as they mostly support text only
            pass

        if self.clip_client is None:
            raise RuntimeError(
                "No image embedding available. Provide embed_image_fn "
                "or ensure clip_client is set for CLIP image encoding."
            )
        image_base64 = image_to_base64(image_path)
        try:
            response = self.clip_client.embeddings.create(
                model="clip-ViT-L-14",
                input=[{
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }],
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"CLIP image encoding failed: {e}")
            raise

    def _vector_search(
        self,
        query_vector: list[float],
        table_name: str,
        vector_column: str,
        id_column: str,
        top_k: int,
        filter_conditions: Optional[dict] = None,
        result_type: str = "image",
    ) -> list[tuple[str, float, str]]:
        """Perform vector search using SeekDB retrieval service.

        Args:
            query_vector: Query embedding vector.
            table_name: Table to search.
            vector_column: Column containing embeddings (stored as JSON).
            id_column: ID column name.
            top_k: Number of results.
            filter_conditions: Optional filter conditions.
            result_type: Type of results ("image" or "text").

        Returns:
            List of (id, score, result_type) tuples.
        """
        results = self.retrieval.vector_search(
            query_vector=query_vector,
            table_name=table_name,
            vector_column=vector_column,
            id_column=id_column,
            top_k=top_k,
            filter_conditions=filter_conditions,
        )
        return [(r["id"], r["score"], result_type) for r in results]

    def _get_image_results(
        self,
        chunk_ids: list[str],
        include_base64: bool = False,
    ) -> list[VRAGSearchResult]:
        """Fetch image chunk details from SeekDB.

        Args:
            chunk_ids: List of chunk IDs to fetch.
            include_base64: Whether to include base64-encoded image data.

        Returns:
            List of VRAGSearchResult objects.
        """
        if not chunk_ids:
            return []

        chunks = self.retrieval.get_chunks_by_ids(
            table_name="ai_image_chunks",
            ids=chunk_ids,
        )

        results = []
        for chunk in chunks:
            image_path = chunk.get("image_path", "")
            image_base64 = None
            if include_base64 and image_path:
                try:
                    image_base64 = image_to_base64(image_path)
                except Exception:
                    pass

            results.append(VRAGSearchResult(
                chunk_id=chunk.get("id", ""),
                score=1.0,  # Score already applied in fusion
                result_type="image",
                image_path=image_path,
                image_base64=image_base64,
                page_no=chunk.get("page_no"),
                source_id=chunk.get("source_id"),
                bbox=json.loads(chunk.get("bbox_regions", "[]")) if chunk.get("bbox_regions") else None,
                summary=chunk.get("image_summary"),
            ))

        return results

    def _get_text_results(
        self,
        chunk_ids: list[str],
    ) -> list[VRAGSearchResult]:
        """Fetch text chunk details from SeekDB.

        Args:
            chunk_ids: List of chunk IDs to fetch.

        Returns:
            List of VRAGSearchResult objects.
        """
        if not chunk_ids:
            return []

        chunks = self.retrieval.get_chunks_by_ids(
            table_name="ai_source_chunks",
            ids=chunk_ids,
        )

        results = []
        for chunk in chunks:
            results.append(VRAGSearchResult(
                chunk_id=chunk.get("id", ""),
                score=1.0,
                result_type="text",
                text=chunk.get("content", ""),
                page_no=chunk.get("page_no"),
                source_id=chunk.get("source_id"),
            ))

        return results

    def search_images_by_text(
        self,
        query: str,
        source_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Search images by text query using CLIP embeddings.

        Args:
            query: Text search query.
            source_ids: Optional filter by source IDs.
            top_k: Number of results (default: self.default_top_k).

        Returns:
            List of (chunk_id, score, result_type) tuples.
        """
        top_k = top_k or self.default_top_k
        try:
            query_vector = self._encode_text(query)
        except RuntimeError as e:
            logger.warning(f"Text encoding failed, skipping image search: {e}")
            return []

        filter_conditions = {}
        if source_ids:
            filter_conditions["source_id"] = source_ids

        return self._vector_search(
            query_vector=query_vector,
            table_name="ai_image_chunks",
            vector_column="embedding_json",
            id_column="id",
            top_k=top_k,
            filter_conditions=filter_conditions if filter_conditions else None,
            result_type="image",
        )

    def search_images_by_image(
        self,
        image_path: str,
        source_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Search images by image query using CLIP embeddings.

        Args:
            image_path: Path to the query image.
            source_ids: Optional filter by source IDs.
            top_k: Number of results (default: self.default_top_k).

        Returns:
            List of (chunk_id, score, result_type) tuples.
        """
        top_k = top_k or self.default_top_k
        query_vector = self._encode_image(image_path)

        filter_conditions = {}
        if source_ids:
            filter_conditions["source_id"] = source_ids

        return self._vector_search(
            query_vector=query_vector,
            table_name="ai_image_chunks",
            vector_column="embedding_json",
            id_column="id",
            top_k=top_k,
            filter_conditions=filter_conditions if filter_conditions else None,
            result_type="image",
        )

    def search_text_chunks(
        self,
        query: str,
        source_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Search text chunks using text embeddings.

        Args:
            query: Text search query.
            source_ids: Optional filter by source IDs.
            top_k: Number of results (default: self.default_top_k).

        Returns:
            List of (chunk_id, score, result_type) tuples.
        """
        top_k = top_k or self.default_top_k

        try:
            query_vector = self._encode_text(query)
        except RuntimeError as e:
            logger.warning(f"Text encoding failed, skipping text search: {e}")
            return []

        filter_conditions = {}
        if source_ids:
            filter_conditions["source_id"] = source_ids

        return self._vector_search(
            query_vector=query_vector,
            table_name="ai_source_chunks",
            vector_column="embedding_json",
            id_column="id",
            top_k=top_k,
            filter_conditions=filter_conditions if filter_conditions else None,
            result_type="text",
        )

    def rrf_fusion(
        self,
        ranked_lists: list[list[tuple[str, float, str]]],
        k: int = RRF_K,
    ) -> list[tuple[str, float, str]]:
        """Reciprocal Rank Fusion (RRF) to combine multiple ranked lists.

        Args:
            ranked_lists: List of ranked lists, each as (id, score, result_type) tuples.
                         Results should already be sorted by relevance within each list.
            k: RRF smoothing parameter (default: 60).

        Returns:
            List of (id, rrf_score, result_type) tuples, sorted by RRF score descending.
            result_type is "image" or "text".
        """
        rrf_scores: dict[str, tuple[float, str]] = {}

        for ranked_list in ranked_lists:
            for rank, (chunk_id, score, result_type) in enumerate(ranked_list, start=1):
                rrf_score = 1.0 / (k + rank)
                if chunk_id in rrf_scores:
                    # Chunk already seen — preserve original type, accumulate RRF score.
                    # Note: In practice chunk IDs are table-specific (image vs text),
                    # so overlap between ranked lists should not occur.
                    existing_score, existing_type = rrf_scores[chunk_id]
                    rrf_scores[chunk_id] = (existing_score + rrf_score, existing_type)
                else:
                    rrf_scores[chunk_id] = (rrf_score, result_type)

        # Sort by RRF score
        sorted_results = sorted(
            [(cid, score, rtype) for cid, (score, rtype) in rrf_scores.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        return sorted_results

    def search_hybrid(
        self,
        query: str,
        query_image_path: Optional[str] = None,
        source_ids: Optional[list[str]] = None,
        image_top_k: Optional[int] = None,
        text_top_k: Optional[int] = None,
        include_image_base64: bool = False,
    ) -> list[VRAGSearchResult]:
        """Hybrid multimodal search combining text and image retrieval with RRF fusion.

        This is the main search method for VRAG. It performs:
        1. Text query → image search (CLIP text embedding)
        2. (Optional) Image query → image search (CLIP image embedding)
        3. Text query → text chunk search
        4. RRF fusion of all results

        Args:
            query: Text search query.
            query_image_path: Optional path to a query image for visual similarity search.
            source_ids: Optional filter by source IDs.
            image_top_k: Top-k for image search results (default: self.default_top_k).
            text_top_k: Top-k for text search results (default: self.default_top_k).
            include_image_base64: Whether to include base64-encoded image data in results.

        Returns:
            List of VRAGSearchResult objects, sorted by relevance.
        """
        image_top_k = image_top_k or self.default_top_k
        text_top_k = text_top_k or self.default_top_k

        ranked_lists = []

        # Text → Image search
        image_results = self.search_images_by_text(
            query=query,
            source_ids=source_ids,
            top_k=image_top_k,
        )
        if image_results:
            ranked_lists.append(image_results)

        # Image → Image search (if query image provided)
        if query_image_path:
            visual_results = self.search_images_by_image(
                image_path=query_image_path,
                source_ids=source_ids,
                top_k=image_top_k,
            )
            if visual_results:
                ranked_lists.append(visual_results)

        # Text → Text search
        text_results = self.search_text_chunks(
            query=query,
            source_ids=source_ids,
            top_k=text_top_k,
        )
        if text_results:
            ranked_lists.append(text_results)

        # RRF fusion
        if not ranked_lists:
            return []

        fused = self.rrf_fusion(ranked_lists)

        # Fetch full result details
        image_ids = [cid for cid, score, rtype in fused if rtype == "image"]
        text_ids = [cid for cid, score, rtype in fused if rtype == "text"]

        image_results_detail = self._get_image_results(image_ids, include_base64=include_image_base64)
        text_results_detail = self._get_text_results(text_ids)

        # Re-score and combine
        id_to_result: dict[str, VRAGSearchResult] = {}
        for r in image_results_detail + text_results_detail:
            id_to_result[r.chunk_id] = r

        # Apply RRF scores
        final_results = []
        for chunk_id, rrf_score, _ in fused:
            if chunk_id in id_to_result:
                result = id_to_result[chunk_id]
                result.score = rrf_score
                final_results.append(result)

        return final_results

    def rerank_results(
        self,
        results: list[VRAGSearchResult],
        query: str,
        top_k: Optional[int] = None,
    ) -> list[VRAGSearchResult]:
        """Rerank search results using a cross-encoder model.

        This is an optional post-processing step that can improve ranking
        by re-scoring results with a cross-encoder that considers
        query-document interaction.

        Currently a placeholder — can be implemented with a cross-encoder API
        (e.g., OpenAI's rerank endpoint or a local model).

        Args:
            results: List of search results to rerank.
            top_k: Number of top results to return after reranking.

        Returns:
            Reranked list of VRAGSearchResult objects.
        """
        # Placeholder: in production, use a cross-encoder reranking API
        top_k = top_k or len(results)
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
