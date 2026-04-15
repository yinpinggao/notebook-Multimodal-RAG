"""VRAG indexer — PDF image extraction and multimodal embedding generation.

Supports domestic Chinese models via Esperanto (tongyi, zhipu, wenxin, kimi, doubao)
and legacy OpenAI CLIP API for embedding generation.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from esperanto import EmbeddingModel, LanguageModel

from open_notebook.vrag.utils import (
    classify_image_kind,
    extract_images_from_source,
    get_image_base64_data_url,
    resize_image_if_needed,
)

logger = logging.getLogger(__name__)


class VRAGIndexer:
    """Indexer for creating multimodal embeddings from document sources.

    Pipeline:
    1. Extract images from PDF/PPT (using PyMuPDF)
    2. Generate embeddings via domestic Chinese models (tongyi/zhipu/wenxin/etc) or OpenAI CLIP
    3. Generate image summaries via domestic vision models or GPT-4o/Claude
    4. Store in SeekDB ai_image_chunks table

    Model selection priority:
    - embedding_model: For image embedding (CLIP-style, via embed_image_fn)
    - vision_model: For image summarization (qwen-vl-max, glm-4v-plus, etc)
    - llm_client: Legacy parameter for direct API calls
    """

    def __init__(
        self,
        clip_api_client=None,
        llm_client=None,
        retrieval_service=None,
        seekdb_client=None,
        storage_path: Optional[str] = None,
        default_dpi: int = 150,
        max_image_size: int = 2048,
        embed_text_fn: Optional[Callable[[str], list[float]]] = None,
        embed_image_fn: Optional[Callable[[str], list[float]]] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        vision_model: Optional[LanguageModel] = None,
    ):
        """Initialize the VRAG indexer.

        Args:
            clip_api_client: OpenAI API client for CLIP embeddings (legacy, prefer embed_*_fn).
            llm_client: LLM client for image summarization (GPT-4o / Claude).
            retrieval_service: SeekDB retrieval service.
            seekdb_client: SeekDB client for direct database operations.
            storage_path: Base directory for storing extracted images.
            default_dpi: Default DPI for rendering PDF pages to images.
            max_image_size: Maximum image dimension for CLIP encoding.
            embed_text_fn: Callable for text embedding (takes text, returns list of floats).
            embed_image_fn: Callable for image embedding (takes image_path, returns list of floats).
            embedding_model: Esperanto EmbeddingModel for image embeddings (domestic models).
            vision_model: Esperanto LanguageModel for image summarization (domestic vision models).
        """
        self.clip_client = clip_api_client
        self.llm_client = llm_client
        self.retrieval = retrieval_service
        self.seekdb = seekdb_client
        self.storage_path = storage_path
        self.default_dpi = default_dpi
        self.max_image_size = max_image_size
        self.embed_text_fn = embed_text_fn
        self.embed_image_fn = embed_image_fn
        self.embedding_model = embedding_model
        self.vision_model = vision_model

    def _ensure_storage_dir(self, source_id: str) -> Path:
        """Get/create the storage directory for a source's images."""
        if self.storage_path:
            storage_dir = Path(self.storage_path) / source_id / "vrag_images"
        else:
            storage_dir = Path(f"/tmp/vrag_images/{source_id}")
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    def _encode_image_clip(self, image_path: str) -> list[float]:
        """Encode a single image to CLIP embedding.

        Priority order:
        1. embed_image_fn (injected, legacy)
        2. embedding_model.embed() (Esperanto EmbeddingModel)
        3. clip_client.embeddings.create (direct OpenAI CLIP)

        Args:
            image_path: Path to the image file.

        Returns:
            CLIP embedding vector.
        """
        # Resize if needed for CLIP encoding
        resized_path = resize_image_if_needed(image_path, max_size=self.max_image_size)

        if self.embed_image_fn is not None:
            return self.embed_image_fn(resized_path)

        if self.embedding_model is not None:
            try:
                # Try embedding_model which supports domestic Chinese models
                results = self.embedding_model.embed([resized_path])
                if results and len(results) > 0:
                    embedding = results[0]
                    if isinstance(embedding, list):
                        return embedding
                    return list(embedding)
            except Exception as e:
                logger.warning(f"Embedding model failed, falling back to clip_client: {e}")

        if self.clip_client is None:
            raise RuntimeError(
                "No image embedding available. Provide embed_image_fn, "
                "embedding_model, or ensure clip_client is set."
            )

        image_base64 = get_image_base64_data_url(resized_path)
        try:
            response = self.clip_client.embeddings.create(
                model="clip-ViT-L-14",
                input=[{
                    "type": "image_url",
                    "image_url": {"url": image_base64},
                }],
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"CLIP image encoding failed: {e}")
            raise

    def _generate_image_summary(
        self,
        image_path: str,
        page_no: int,
        context: Optional[str] = None,
    ) -> str:
        """Generate an image summary using the LLM.

        Priority order for vision models:
        1. vision_model (Esperanto LanguageModel, preferred for domestic models)
        2. llm_client.invoke (LangChain chat model)
        3. llm_client.chat.completions.create (direct OpenAI SDK)

        Args:
            image_path: Path to the image file.
            page_no: Page number in the source document.
            context: Optional surrounding text context.

        Returns:
            Text summary of the image content.
        """
        image_base64 = get_image_base64_data_url(image_path)

        prompt = f"""Describe this image in detail. This image appears on page {page_no} of a document.

Context: {context or "No additional context available."}

Provide a concise but thorough description covering:
- What type of content is shown (chart, table, figure, diagram, screenshot, photo, etc.)
- What data or information is presented
- Key labels, axes, colors, or notable visual elements
- Any text visible in the image

Description:"""

        # Try vision_model first (Esperanto LanguageModel, supports domestic vision models)
        if self.vision_model is not None:
            try:
                from langchain_core.messages import HumanMessage

                # Convert to LangChain model if needed
                if hasattr(self.vision_model, "to_langchain"):
                    lc_model = self.vision_model.to_langchain()
                else:
                    lc_model = self.vision_model

                response = lc_model.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}},
                    ])
                ])
                summary = response.content if hasattr(response, "content") else str(response)
                if summary:
                    return summary
            except Exception as e:
                logger.warning(f"vision_model summarization failed: {e}")

        # Try LangChain invoke pattern
        if self.llm_client is not None and hasattr(self.llm_client, "invoke"):
            try:
                from langchain_core.messages import HumanMessage
                response = self.llm_client.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}},
                    ])
                ])
                summary = response.content if hasattr(response, "content") else str(response)
                return summary or "No description available."
            except Exception as e:
                logger.warning(f"LangChain invoke summarization failed: {e}")

        # Fallback to direct OpenAI SDK
        if self.llm_client is not None and hasattr(self.llm_client, "chat"):
            try:
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_base64}},
                        ],
                    }],
                    max_tokens=512,
                    temperature=0.3,
                )
                return response.choices[0].message.content or "No description available."
            except Exception as e:
                logger.warning(f"OpenAI SDK summarization failed: {e}")

        logger.warning("No vision model available for summarization")
        return "Summary generation failed: no vision model available."

    def _store_image_chunk(
        self,
        image_info: dict,
        embedding: list[float],
        summary: str,
        source_id: str,
    ) -> str:
        """Store an image chunk in SeekDB.

        Args:
            image_info: Image info dict from extract_images_from_source.
            embedding: CLIP embedding vector.
            summary: Image summary text.
            source_id: Source document ID.

        Returns:
            The chunk ID of the stored record.
        """
        chunk_id = f"img_{source_id}_p{image_info['page_no']}_i{image_info['image_index']}"

        chunk_data = {
            "id": chunk_id,
            "source_id": source_id,
            "page_no": image_info["page_no"],
            "image_path": image_info["image_path"],
            "image_summary": summary,
            "embedding_json": json.dumps(embedding),
            "chunk_kind": classify_image_kind(summary),
            "updated_at": datetime.utcnow().isoformat(),
            "sync_version": 0,
            # bbox_regions: populated later by the bbox extraction tool
            "bbox_regions": json.dumps([]),
        }

        self.seekdb.upsert("ai_image_chunks", chunk_data)
        logger.debug(f"Stored image chunk: {chunk_id}")
        return chunk_id

    def index_source(
        self,
        source_id: str,
        source_path: str,
        source_type: str = "pdf",
        generate_summaries: bool = True,
        dpi: Optional[int] = None,
        skip_existing: bool = True,
        batch_size: int = 10,
    ) -> dict:
        """Index all images from a source document.

        This is the main entry point for indexing a source's visual content.

        Args:
            source_id: Unique identifier for the source document.
            source_path: Path to the source file.
            source_type: Type of source ('pdf', 'ppt', etc.)
            generate_summaries: Whether to generate image summaries via LLM.
            dpi: DPI for rendering PDF pages (default: self.default_dpi).
            skip_existing: Skip images that are already indexed.
            batch_size: Batch size for CLIP encoding.

        Returns:
            Dict with indexing results: {total, indexed, skipped, errors}
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        dpi = dpi or self.default_dpi
        storage_dir = self._ensure_storage_dir(source_id)

        results = {"total": 0, "indexed": 0, "skipped": 0, "errors": 0}

        # Extract images
        logger.info(f"Extracting images from source: {source_path}")
        extracted = extract_images_from_source(
            source_path=str(source_path),
            source_type=source_type,
            output_dir=str(storage_dir),
            dpi=dpi,
        )

        results["total"] = len(extracted)

        # Process images in batches
        for i, image_info in enumerate(extracted):
            chunk_id = f"img_{source_id}_p{image_info['page_no']}_i{image_info['image_index']}"

            # Check if already indexed
            if skip_existing:
                existing = self.seekdb.get("ai_image_chunks", chunk_id)
                if existing:
                    logger.debug(f"Skipping existing chunk: {chunk_id}")
                    results["skipped"] += 1
                    continue

            try:
                # Generate CLIP embedding
                embedding = self._encode_image_clip(image_info["image_path"])

                # Generate summary
                summary = ""
                if generate_summaries:
                    summary = self._generate_image_summary(
                        image_info["image_path"],
                        page_no=image_info["page_no"],
                    )

                # Store in SeekDB
                self._store_image_chunk(
                    image_info=image_info,
                    embedding=embedding,
                    summary=summary,
                    source_id=source_id,
                )

                results["indexed"] += 1
                logger.info(f"Indexed image {i + 1}/{len(extracted)}: {chunk_id}")

            except Exception as e:
                logger.error(f"Failed to index image {image_info['image_path']}: {e}")
                results["errors"] += 1

        logger.info(
            f"Indexing complete for source {source_id}: "
            f"{results['indexed']} indexed, {results['skipped']} skipped, {results['errors']} errors"
        )
        return results

    def rebuild_index(
        self,
        source_id: str,
        regenerate_embeddings: bool = True,
        regenerate_summaries: bool = True,
    ) -> dict:
        """Rebuild the VRAG index for a source.

        Args:
            source_id: Source document ID.
            regenerate_embeddings: Whether to regenerate CLIP embeddings.
            regenerate_summaries: Whether to regenerate image summaries.

        Returns:
            Dict with rebuild results.
        """
        # Get all existing chunks for this source
        existing_chunks = self.seekdb.query(
            "SELECT * FROM ai_image_chunks WHERE source_id = %s",
            (source_id,),
        )

        results = {"total": len(existing_chunks), "rebuilt": 0, "errors": 0}

        for chunk in existing_chunks:
            try:
                image_path = chunk.get("image_path", "")
                if not image_path or not Path(image_path).exists():
                    logger.warning(f"Image file not found: {image_path}")
                    results["errors"] += 1
                    continue

                update_data = {"updated_at": datetime.utcnow().isoformat()}

                if regenerate_embeddings:
                    embedding = self._encode_image_clip(image_path)
                    update_data["embedding_json"] = json.dumps(embedding)

                if regenerate_summaries:
                    summary = self._generate_image_summary(
                        image_path,
                        page_no=chunk.get("page_no"),
                    )
                    update_data["image_summary"] = summary
                    update_data["chunk_kind"] = classify_image_kind(summary)

                self.seekdb.update("ai_image_chunks", chunk["id"], update_data)
                results["rebuilt"] += 1

            except Exception as e:
                logger.error(f"Failed to rebuild chunk {chunk['id']}: {e}")
                results["errors"] += 1

        logger.info(f"Rebuild complete for source {source_id}: {results}")
        return results

    def delete_source_index(self, source_id: str) -> int:
        """Delete all VRAG index entries for a source.

        Args:
            source_id: Source document ID.

        Returns:
            Number of entries deleted.
        """
        deleted = self.seekdb.delete(
            "ai_image_chunks",
            where="source_id = %s",
            params=(source_id,),
        )
        logger.info(f"Deleted {deleted} image chunks for source {source_id}")
        return deleted
