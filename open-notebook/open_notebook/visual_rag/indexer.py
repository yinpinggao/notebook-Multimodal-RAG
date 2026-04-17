"""Visual asset indexing for the canonical Visual RAG subsystem."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from loguru import logger

from open_notebook.ai.models import model_manager
from open_notebook.domain.notebook import Source
from open_notebook.storage.visual_assets import safe_source_dir, visual_asset_store
from open_notebook.vrag.utils import (
    extract_images_from_source,
    get_image_base64_data_url,
    resize_image_if_needed,
    VISUAL_INDEX_VERSION,
)


def _supports_multimodal_image_embeddings(embedding_model: Any) -> bool:
    model_name = str(getattr(embedding_model, "model_name", "") or "").lower()
    return "clip" in model_name


class VisualAssetIndexer:
    """Indexes visual assets into `ai_visual_assets`.

    The indexer is intentionally best-effort: image extraction can succeed even
    when no compatible vision or multimodal embedding model is configured.
    """

    def __init__(self, default_dpi: int = 150, max_image_size: int = 2048):
        self.default_dpi = default_dpi
        self.max_image_size = max_image_size

    def _asset_id(self, source_id: str, image_info: dict[str, Any]) -> str:
        page_no = int(image_info.get("page_no") or 0)
        image_index = int(image_info.get("image_index") or 0)
        asset_type = str(image_info.get("asset_type") or "")
        if asset_type == "page_render":
            return f"visual_asset:page_render:{source_id}:{page_no}"
        if asset_type == "native_image":
            return f"visual_asset:native_image:{source_id}:{page_no}:{image_index}"
        return f"visual_asset:image:{source_id}:{page_no}:{image_index}"

    async def index_source(
        self,
        source_id: str,
        *,
        regenerate: bool = False,
        generate_summaries: bool = True,
        dpi: Optional[int] = None,
        command_id: Optional[str] = None,
    ) -> dict[str, Any]:
        start = time.time()
        source = await Source.get(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' not found")

        file_path = source.asset.file_path if source.asset else None
        if not file_path:
            return {
                "total": 0,
                "indexed": 0,
                "skipped": 0,
                "errors": 0,
                "message": "Source has no local file to index.",
                "processing_time": time.time() - start,
            }

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        source_type = "pdf" if path.suffix.lower() == ".pdf" else path.suffix.lower().lstrip(".")
        if source_type != "pdf":
            return {
                "total": 0,
                "indexed": 0,
                "skipped": 0,
                "errors": 0,
                "message": f"Visual indexing currently supports PDF files, got '{source_type}'.",
                "processing_time": time.time() - start,
            }

        if regenerate:
            await visual_asset_store.delete_source_assets(source_id)

        output_dir = safe_source_dir(source_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted = await asyncio.to_thread(
            extract_images_from_source,
            source_path=str(path),
            source_type=source_type,
            output_dir=str(output_dir),
            dpi=dpi or self.default_dpi,
        )

        embedding_model = await model_manager.get_default_model("embedding")
        vision_model = await model_manager.get_default_model("vision") if generate_summaries else None

        result = {
            "total": len(extracted),
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
            "processing_time": 0.0,
        }

        for image_info in extracted:
            page_no = int(image_info.get("page_no") or 0)
            image_index = int(image_info.get("image_index") or 0)
            asset_id = self._asset_id(source_id, image_info)
            if not regenerate and await visual_asset_store.get_asset(asset_id):
                result["skipped"] += 1
                continue

            image_path = str(image_info.get("image_path") or "")
            asset_type = str(image_info.get("asset_type") or "").strip() or (
                "native_image"
                if image_info.get("is_native_image")
                else "page_render"
            )
            raw_text = (
                str(image_info.get("raw_text") or "").strip()
                or str(source.full_text or "")[:1000]
            )
            metadata = {
                **(image_info.get("metadata") or {}),
                "index_version": VISUAL_INDEX_VERSION,
                "image_index": image_index,
                "is_native_image": bool(image_info.get("is_native_image")),
                "width": image_info.get("width"),
                "height": image_info.get("height"),
            }
            try:
                embedding = await self._encode_image(image_path, embedding_model)
                summary = (
                    await self._generate_summary(image_path, page_no, vision_model)
                    if generate_summaries
                    else ""
                )
                await visual_asset_store.upsert_asset(
                    {
                        "id": asset_id,
                        "source_id": source_id,
                        "legacy_id": None,
                        "asset_type": asset_type,
                        "media_type": f"image/{image_info.get('format') or 'png'}",
                        "page_no": page_no,
                        "file_path": image_path,
                        "summary": summary,
                        "raw_text": raw_text,
                        "bbox": image_info.get("bbox") or [],
                        "embedding": embedding or [],
                        "metadata": metadata,
                        "index_status": "completed",
                        "index_command_id": command_id,
                    }
                )
                result["indexed"] += 1
            except Exception as e:
                logger.warning(f"Failed to index visual asset {image_path}: {e}")
                result["errors"] += 1

        result["processing_time"] = time.time() - start
        return result

    async def _encode_image(
        self,
        image_path: str,
        embedding_model: Any,
    ) -> Optional[list[float]]:
        if embedding_model is None or not _supports_multimodal_image_embeddings(embedding_model):
            return None
        try:
            resized_path = await asyncio.to_thread(
                resize_image_if_needed,
                image_path,
                self.max_image_size,
            )
            embeddings = await asyncio.to_thread(embedding_model.embed, [resized_path])
            if embeddings:
                embedding = embeddings[0]
                return embedding if isinstance(embedding, list) else list(embedding)
        except Exception as e:
            logger.debug(f"Visual image embedding skipped for {image_path}: {e}")
        return None

    async def _generate_summary(
        self,
        image_path: str,
        page_no: int,
        vision_model: Any,
    ) -> str:
        if vision_model is None:
            return ""
        prompt = f"""Describe this document image from page {page_no}.

Focus on visible charts, tables, diagrams, labels, text, numbers, and the most
important information that would help answer research questions. Be concise."""
        try:
            lc_model = vision_model.to_langchain() if hasattr(vision_model, "to_langchain") else vision_model
            data_url = await asyncio.to_thread(get_image_base64_data_url, image_path)
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )
            response = await asyncio.to_thread(lc_model.invoke, [message])
            content = response.content if hasattr(response, "content") else str(response)
            return str(content or "").strip()
        except Exception as e:
            logger.debug(f"Visual summary skipped for {image_path}: {e}")
            return ""
