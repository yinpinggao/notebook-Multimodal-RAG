"""VRAG search engine — multimodal retrieval with domestic Chinese API support.

Adapted from VRAG/search_engine/search_engine.py, supporting:
- Domestic Chinese embedding models via Esperanto (tongyi, zhipu, wenxin, spark, doubao)
- Legacy OpenAI CLIP API via embed_text_fn/embed_image_fn injection
- Direct clip_client fallback for CLIP image encoding
"""

from __future__ import annotations

import asyncio
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
        asset_id: Optional[str] = None,
        file_url: Optional[str] = None,
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
        self.asset_id = asset_id or chunk_id
        self.file_url = file_url

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "asset_id": self.asset_id,
            "score": self.score,
            "type": self.type,
            "image_path": self.image_path,
            "file_url": self.file_url,
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

    def _embedding_model_name(self) -> str:
        return str(getattr(self.embedding_model, "model_name", "") or "").lower()

    def _supports_multimodal_image_embeddings(self) -> bool:
        return "clip" in self._embedding_model_name()

    def _supports_multimodal_text_embeddings(self) -> bool:
        return self._supports_multimodal_image_embeddings()

    async def _encode_text(self, text: str) -> list[float]:
        """Encode text query to embedding vector.

        Priority order:
        1. embed_text_fn (injected CLIP text encoder, matched to image search)
        2. embedding_model (only when no matched CLIP text encoder is available)
        3. clip_client.embeddings.create (direct OpenAI SDK fallback)

        Args:
            text: Text query string.

        Returns:
            Embedding vector as list of floats.

        Raises:
            RuntimeError: If no text embedding is available.
        """
        # Priority 1: use the matched CLIP text encoder when available so text
        # queries stay in the same space as indexed image embeddings.
        if self.embed_text_fn is not None:
            try:
                return await asyncio.to_thread(self.embed_text_fn, text)
            except Exception as e:
                logger.warning(f"CLIP text encoder failed: {e}")

        # Priority 2: fallback to a generic embedding model only when we do not
        # have a matched multimodal text encoder.
        if self.embedding_model is not None and self._supports_multimodal_text_embeddings():
            try:
                results = self.embedding_model.embed([text])
                if results and len(results) > 0:
                    embedding = results[0]
                    if isinstance(embedding, list):
                        return embedding
                    return list(embedding)
            except Exception as e:
                logger.warning(f"Embedding model embed() failed: {e}")
        elif self.embedding_model is not None:
            logger.warning(
                "Skipping generic embedding model for image-search text encoding because "
                "it is not a confirmed multimodal encoder."
            )

        # Priority 3: clip_client (direct OpenAI SDK fallback) — sync, use thread pool
        if self.clip_client is not None:
            try:
                response = await asyncio.to_thread(
                    self.clip_client.embeddings.create,
                    model="clip-ViT-L-14",
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning(f"CLIP text encoding failed: {e}")
                pass

        raise RuntimeError(
            "No text embedding available. Provide embedding_model, embed_text_fn, "
            "or ensure clip_client is set."
        )

    async def _encode_image(self, image_path: str) -> list[float]:
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
        # Priority 1: embed_image_fn (legacy CLIP) — sync, use thread pool
        if self.embed_image_fn is not None:
            return await asyncio.to_thread(self.embed_image_fn, image_path)

        if self.embedding_model is not None and self._supports_multimodal_image_embeddings():
            try:
                results = self.embedding_model.embed([image_path])
                if results and len(results) > 0:
                    embedding = results[0]
                    if isinstance(embedding, list):
                        return embedding
                    return list(embedding)
            except Exception as e:
                logger.warning(f"Embedding model image encoding failed: {e}")
        elif self.embedding_model is not None:
            logger.warning(
                "Skipping generic embedding model for image encoding because it is "
                "not a confirmed multimodal image encoder."
            )

        if self.clip_client is None:
            raise RuntimeError(
                "No image embedding available. Provide embed_image_fn "
                "or ensure clip_client is set for CLIP image encoding."
            )
        image_base64 = image_to_base64(image_path)
        try:
            response = await asyncio.to_thread(
                self.clip_client.embeddings.create,
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

    async def _text_search(
        self,
        query: str,
        source_ids: Optional[list[str]],
        top_k: int,
        result_type: str = "text",
    ) -> list[tuple[str, float, str]]:
        """Perform text-based search via AIRetrievalService.

        Uses AIRetrievalService.text_search which internally generates embeddings
        and performs keyword + semantic matching.

        Args:
            query: Search query string.
            source_ids: Optional filter by source IDs.
            top_k: Number of results.
            result_type: "text" or "image".

        Returns:
            List of (id, score, result_type) tuples.
        """
        results = await self.retrieval.text_search(
            keyword=query,
            source_ids=source_ids,
            results=top_k,
            note=False,
        )
        return [
            (r.get("id", ""), float(r.get("relevance") or r.get("score") or 0.5), result_type)
            for r in results
        ]

    async def _image_search(
        self,
        query: str,
        source_ids: Optional[list[str]],
        top_k: int,
    ) -> list[tuple[str, float, str]]:
        """Perform image search by querying ai_image_chunks table.

        Uses AIRetrievalService.image_hybrid_search() which combines
        keyword matching (on image_summary) with vector similarity
        (CLIP embeddings). This enables semantic image search where
        queries like "charts" match bar charts, pie charts, etc.

        Args:
            query: Search query string.
            source_ids: Optional filter by source IDs.
            top_k: Number of results.

        Returns:
            List of (id, score, "image") tuples.
        """
        # Use hybrid search: keyword + vector similarity for better image retrieval
        results = await self.retrieval.image_hybrid_search(
            keyword=query,
            source_ids=source_ids,
            top_k=top_k,
            image_query_embedding_fn=self.embed_text_fn,
        )
        return [
            (
                r.get("id", ""),
                float(r.get("score") or 0.5),
                "image",
            )
            for r in results[:top_k]
        ]

    async def _get_image_results(
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

        chunks = await self.retrieval.get_image_chunks_by_ids(
            ids=chunk_ids,
        )

        results = []
        for chunk in chunks:
            image_path = chunk.get("image_path", "")
            image_base64 = None
            if include_base64 and image_path:
                try:
                    image_base64 = await asyncio.to_thread(image_to_base64, image_path)
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

    async def _get_text_results(
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

        # Call SeekDB directly (async) instead of the sync wrapper,
        # avoiding the asyncio.get_event_loop() RuntimeError in worker threads.
        chunks = await self.retrieval.get_text_chunks_by_ids(chunk_ids)

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

    async def search_images_by_text(
        self,
        query: str,
        source_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Search images by text query.

        Uses AIRetrievalService.search_images_sync which searches image chunks
        by their text descriptions (image_summary, page text).

        Args:
            query: Text search query.
            source_ids: Optional filter by source IDs.
            top_k: Number of results (default: self.default_top_k).

        Returns:
            List of (chunk_id, score, result_type) tuples.
        """
        top_k = top_k or self.default_top_k
        return await self._image_search(query, source_ids, top_k)

    async def search_images_by_image(
        self,
        image_path: str,
        source_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Search similar images by query image.

        Uses AIRetrievalService.search_images_sync which searches image chunks
        by their text descriptions. True image-to-image similarity requires
        a dedicated multimodal embedding model.

        Args:
            image_path: Path to the query image (used as keyword for search).
            source_ids: Optional filter by source IDs.
            top_k: Number of results (default: self.default_top_k).

        Returns:
            List of (chunk_id, score, result_type) tuples.
        """
        top_k = top_k or self.default_top_k
        # Use the image path filename as a text query for image search
        query = f"image: {image_path.split('/')[-1]}"
        return await self._image_search(query, source_ids, top_k)

    async def search_text_chunks(
        self,
        query: str,
        source_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[tuple[str, float, str]]:
        """Search text chunks using text query.

        Uses AIRetrievalService.text_search for semantic + keyword matching.

        Args:
            query: Text search query.
            source_ids: Optional filter by source IDs.
            top_k: Number of results (default: self.default_top_k).

        Returns:
            List of (chunk_id, score, result_type) tuples.
        """
        top_k = top_k or self.default_top_k
        return await self._text_search(query, source_ids, top_k)

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

    async def search_hybrid(
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

        # Gather all searches in parallel using asyncio.gather
        search_tasks = [
            self.search_images_by_text(
                query=query,
                source_ids=source_ids,
                top_k=image_top_k,
            ),
            self.search_text_chunks(
                query=query,
                source_ids=source_ids,
                top_k=text_top_k,
            ),
        ]
        if query_image_path:
            search_tasks.append(
                self.search_images_by_image(
                    image_path=query_image_path,
                    source_ids=source_ids,
                    top_k=image_top_k,
                )
            )

        search_results = await asyncio.gather(*search_tasks)

        # search_results[0] = image search, [1] = text search, [2] = image→image (optional)
        image_results = search_results[0]
        text_results = search_results[1]

        if image_results:
            ranked_lists.append(image_results)
        if text_results:
            ranked_lists.append(text_results)
        if query_image_path and len(search_results) > 2:
            visual_results = search_results[2]
            if visual_results:
                ranked_lists.append(visual_results)

        # RRF fusion
        if not ranked_lists:
            return []

        fused = self.rrf_fusion(ranked_lists)

        # Fetch full result details in parallel
        image_ids = [cid for cid, score, rtype in fused if rtype == "image"]
        text_ids = [cid for cid, score, rtype in fused if rtype == "text"]

        detail_tasks = []
        if image_ids:
            detail_tasks.append(
                self._get_image_results(image_ids, include_base64=include_image_base64)
            )
        if text_ids:
            detail_tasks.append(self._get_text_results(text_ids))

        if detail_tasks:
            detail_results_list = await asyncio.gather(*detail_tasks)
            detail_results = []
            for dr in detail_results_list:
                detail_results.extend(dr)
        else:
            detail_results = []

        # Re-score and combine
        id_to_result: dict[str, VRAGSearchResult] = {}
        for r in detail_results:
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
