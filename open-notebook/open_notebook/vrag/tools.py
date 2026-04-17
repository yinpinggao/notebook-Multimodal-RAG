"""VRAG tools — search, bbox_crop, summarize, answer tools.

These tools are used by the VRAG Agent to interact with the multimodal search
engine, perform image operations, and generate answers.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.messages import HumanMessage

from open_notebook.vrag.search_engine import VRAGSearchEngine, VRAGSearchResult
from open_notebook.vrag.utils import (
    crop_image,
    get_image_base64_data_url,
)

logger = logging.getLogger(__name__)


def _truncate_text(value: str, limit: int = 240) -> str:
    normalized = " ".join((value or "").strip().split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _page_label(page_no: Any) -> str:
    return f"第{page_no}页" if page_no not in (None, "") else "未标注页码"


def _is_directly_viewable_image(image: dict[str, Any]) -> bool:
    return bool(
        image.get("file_url")
        or image.get("image_base64")
        or image.get("image_path")
    )


@dataclass
class SearchResult:
    """Result from the VRAG search tool."""
    images: list[dict] = field(default_factory=list)
    texts: list[dict] = field(default_factory=list)
    total_image_hits: int = 0
    total_text_hits: int = 0

    def to_dict(self) -> dict:
        return {
            "images": self.images,
            "texts": self.texts,
            "total_image_hits": self.total_image_hits,
            "total_text_hits": self.total_text_hits,
        }


@dataclass
class CropResult:
    """Result from the bbox crop tool."""
    cropped_image_path: Optional[str] = None
    cropped_image_base64: Optional[str] = None
    width: int = 0
    height: int = 0
    original_image: str = ""
    bbox: list[float] = field(default_factory=list)
    bbox_pixel: list[int] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "cropped_image_path": self.cropped_image_path,
            "cropped_image_base64": self.cropped_image_base64,
            "width": self.width,
            "height": self.height,
            "original_image": self.original_image,
            "bbox": self.bbox,
            "bbox_pixel": self.bbox_pixel,
            "description": self.description,
        }


@dataclass
class MemoryEntry:
    """A single entry in the multimodal memory graph."""
    id: str
    type: str  # "search" | "bbox_crop" | "summarize" | "answer"
    summary: str
    parent_ids: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)  # image paths
    priority: float = 0.0
    is_useful: bool = True
    key_insight: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "summary": self.summary,
            "parent_ids": self.parent_ids,
            "images": self.images,
            "priority": self.priority,
            "is_useful": self.is_useful,
            "key_insight": self.key_insight,
        }


@dataclass
class VRAGTools:
    """Container for all VRAG tools.

    Provides a unified interface for the VRAG agent to interact with
    the search engine, perform bbox operations, and generate answers.
    """

    search_engine: VRAGSearchEngine
    llm_client: Any
    include_image_base64: bool = True
    default_top_k: int = 5

    async def search(
        self,
        query: str,
        source_ids: Optional[list[str]] = None,
        query_image_path: Optional[str] = None,
        image_top_k: Optional[int] = None,
        text_top_k: Optional[int] = None,
    ) -> SearchResult:
        """Search for relevant images and text using multimodal retrieval.

        Args:
            query: Text search query.
            source_ids: Optional list of source IDs to filter by.
            query_image_path: Optional path to a query image.
            image_top_k: Number of image results to return.
            text_top_k: Number of text results to return.

        Returns:
            SearchResult containing matched images and text chunks.
        """
        results = await self.search_engine.search_hybrid(
            query=query,
            query_image_path=query_image_path,
            source_ids=source_ids,
            image_top_k=image_top_k or self.default_top_k,
            text_top_k=text_top_k or self.default_top_k,
            include_image_base64=self.include_image_base64,
        )

        search_result = SearchResult()
        for r in results:
            if r.type == "image":
                img_dict = {
                    "chunk_id": r.chunk_id,
                    "asset_id": getattr(r, "asset_id", r.chunk_id),
                    "score": r.score,
                    "image_path": r.image_path,
                    "file_url": getattr(r, "file_url", None),
                    "image_base64": r.image_base64,
                    "page_no": r.page_no,
                    "source_id": r.source_id,
                    "summary": r.summary,
                    "bbox": r.bbox,
                    "asset_type": getattr(r, "asset_type", None),
                    "is_native_image": getattr(r, "is_native_image", None),
                }
                search_result.images.append(img_dict)
            else:
                text_dict = {
                    "chunk_id": r.chunk_id,
                    "score": r.score,
                    "text": r.text,
                    "page_no": r.page_no,
                    "source_id": r.source_id,
                }
                search_result.texts.append(text_dict)

        search_result.total_image_hits = len(search_result.images)
        search_result.total_text_hits = len(search_result.texts)

        logger.info(
            f"Search for '{query}': "
            f"{search_result.total_image_hits} images, {search_result.total_text_hits} texts"
        )
        return search_result

    def bbox_crop(
        self,
        image_path: str,
        bbox: list[float],
        padding: float = 0.02,
        output_path: Optional[str] = None,
        describe: bool = True,
    ) -> CropResult:
        """Crop a region from an image using bounding box coordinates.

        Args:
            image_path: Path to the source image.
            bbox: Normalized bbox [x1, y1, x2, y2] with values in [0, 1].
            padding: Fraction of padding to add around the cropped region.
            output_path: Optional path to save the cropped image.
            describe: Whether to generate a description of the cropped region.

        Returns:
            CropResult with cropped image data and optional description.
        """
        crop_data = crop_image(image_path, bbox, padding=padding, output_path=output_path)

        result = CropResult(
            cropped_image_path=crop_data.get("image_path"),
            cropped_image_base64=crop_data.get("image_base64"),
            width=crop_data.get("width", 0),
            height=crop_data.get("height", 0),
            original_image=crop_data.get("original_image", ""),
            bbox=crop_data.get("bbox", []),
            bbox_pixel=crop_data.get("bbox_pixel", []),
        )

        # Generate description using LLM
        if describe and result.cropped_image_base64:
            try:
                prompt = """Describe this cropped region from a document image in detail.
Focus on what is shown, any text visible, labels, data points, or other content.
If the region appears to be part of a larger chart or table, describe the partial content you see.

Description:"""

                response = self._llm_invoke(
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{result.cropped_image_base64}"},
                            },
                        ],
                    }],
                    max_tokens=256,
                    temperature=0.3,
                )
                result.description = response
            except Exception as e:
                logger.warning(f"BBox description generation failed: {e}")
                result.description = "Description generation failed."

        logger.info(f"BBox crop: {bbox} from {image_path} -> {result.cropped_image_path or 'base64'}")
        return result

    def summarize(
        self,
        search_results: list[SearchResult],
        question: str,
        memory_graph: list[MemoryEntry],
        llm_model: str = "gpt-4o",
    ) -> dict:
        """Summarize search results and update the memory graph.

        Args:
            search_results: List of search results from previous searches.
            question: The user's original question.
            memory_graph: Current memory graph state.
            llm_model: LLM model to use for summarization.

        Returns:
            Dict with keys: summary, memory_entries, need_more
        """
        # Build evidence string
        evidence_parts = []
        for i, result in enumerate(search_results):
            evidence_parts.append(f"## Search Result {i + 1}:")

            for img in result.images[:3]:  # Top 3 images per search
                evidence_parts.append(f"- Image (page {img['page_no']}, score={img['score']:.3f})")
                if img.get("summary"):
                    evidence_parts.append(f"  Summary: {img['summary']}")
                if img.get("bbox"):
                    evidence_parts.append(f"  BBox regions: {img['bbox']}")

            for txt in result.texts[:2]:  # Top 2 text chunks per search
                evidence_parts.append(f"- Text (page {txt['page_no']}, score={txt['score']:.3f})")
                evidence_parts.append(f"  {txt['text'][:200]}...")

        evidence_str = "\n".join(evidence_parts)

        # Build memory string
        memory_parts = []
        for entry in memory_graph:
            memory_parts.append(f"- [{entry.type}] {entry.summary}")
        memory_str = "\n".join(memory_parts) or "No previous memory."

        prompt = f"""You have gathered the following visual evidence from the document:

{evidence_str}

## Previous Memory

{memory_str}

## User's Question

{question}

---

Analyze all the evidence. For each piece of evidence:
1. is_useful: Is this relevant to answering the question? (true/false)
2. priority: How important is this evidence? (0-10, higher = more important)
3. key_insight: What specific insight does this provide?

Then provide a concise summary of what you learned and what you still need (if anything).

Output your response in this format:
```
summary: <your summary of the evidence>
need_more: <what additional information you need, or "none">
memorize:
- id: "memory_1", is_useful: true/false, priority: <0-10>, key_insight: "<insight>"
- id: "memory_2", is_useful: true/false, priority: <0-10>, key_insight: "<insight>"
```"""

        try:
            response = self._llm_invoke(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3,
            )
            content = response

            # Parse the response
            summary = ""
            need_more = "none"
            memory_entries = []

            lines = content.split("\n")
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith("summary:"):
                    summary = line[8:].strip()
                    current_section = "summary"
                elif line.startswith("need_more:"):
                    need_more = line[10:].strip()
                    current_section = "need_more"
                elif line.startswith("- id:") or line.startswith("memorize:"):
                    current_section = "memorize"
                elif current_section == "memorize" and line.startswith("-"):
                    # Parse memory entry
                    memory_entries.append(line)

            return {
                "summary": summary,
                "need_more": need_more,
                "memory_entries": memory_entries,
                "raw_response": content,
            }

        except Exception as e:
            logger.error(f"Summarize tool failed: {e}")
            return {
                "summary": "Summarization failed.",
                "need_more": "none",
                "memory_entries": [],
                "error": str(e),
            }

    def answer(
        self,
        question: str,
        memory_entries: list[MemoryEntry],
        collected_evidence: list[dict],
        llm_model: str = "gpt-4o",
    ) -> str:
        """Generate the final answer with visual evidence.

        Args:
            question: The user's question.
            memory_entries: Entries from the memory graph.
            collected_evidence: All evidence collected during the reasoning process.
            llm_model: LLM model to use for answer generation.

        Returns:
            The final answer text with image references.
        """
        visible_image_parts: list[str] = []
        summarized_image_parts: list[str] = []
        text_parts: list[str] = []
        bbox_parts: list[str] = []
        seen_images: set[tuple[Any, ...]] = set()
        seen_texts: set[tuple[Any, ...]] = set()
        seen_bboxes: set[tuple[Any, ...]] = set()

        for ev in collected_evidence:
            ev_type = ev.get("type", "unknown")
            if ev_type == "search":
                for img in ev.get("images", [])[:3]:
                    page_label = _page_label(img.get("page_no"))
                    summary = _truncate_text(img.get("summary") or "无摘要")
                    is_directly_viewable = _is_directly_viewable_image(img)
                    image_key = (
                        img.get("asset_id") or img.get("chunk_id") or img.get("page_no"),
                        summary,
                        is_directly_viewable,
                    )
                    if image_key in seen_images:
                        continue
                    seen_images.add(image_key)

                    target_parts = (
                        visible_image_parts
                        if is_directly_viewable
                        else summarized_image_parts
                    )
                    visibility = (
                        "可直接查看"
                        if is_directly_viewable
                        else "仅有摘要，当前无法直接查看原图"
                    )
                    target_parts.append(f"- {page_label}，{visibility}：{summary}")

                for txt in ev.get("texts", [])[:2]:
                    snippet = _truncate_text(txt.get("text", ""), limit=300)
                    text_key = (
                        txt.get("chunk_id") or txt.get("page_no"),
                        snippet,
                    )
                    if text_key in seen_texts:
                        continue
                    seen_texts.add(text_key)
                    text_parts.append(
                        f"- {_page_label(txt.get('page_no'))}文本：{snippet}"
                    )
            elif ev_type == "bbox_crop":
                bbox = tuple(ev.get("bbox") or [])
                description = _truncate_text(ev.get("description") or "无局部区域描述")
                bbox_key = (
                    ev.get("image_path") or ev.get("original_image"),
                    bbox,
                    description,
                )
                if bbox_key in seen_bboxes:
                    continue
                seen_bboxes.add(bbox_key)
                bbox_parts.append(
                    f"- 区域 {list(bbox) if bbox else '未提供坐标'}：{description}"
                )

        evidence_sections: list[str] = []
        if visible_image_parts:
            evidence_sections.append(
                "### 可直接查看的图片\n" + "\n".join(visible_image_parts)
            )
        if summarized_image_parts:
            evidence_sections.append(
                "### 只有摘要、当前看不到原图的图片\n"
                + "\n".join(summarized_image_parts)
            )
        if bbox_parts:
            evidence_sections.append(
                "### 局部裁剪区域\n" + "\n".join(bbox_parts)
            )
        if text_parts:
            evidence_sections.append(
                "### 相关文本证据\n" + "\n".join(text_parts)
            )
        evidence_str = "\n\n".join(evidence_sections) or "暂无可用证据。"

        # Build memory string
        memory_parts = []
        for entry in memory_entries:
            if entry.is_useful:
                memory_parts.append(
                    f"- [{entry.type}] {_truncate_text(entry.summary, limit=200)}"
                )
        memory_str = "\n".join(memory_parts) or "暂无记忆条目。"

        prompt = f"""你是文档视觉问答助手。

默认使用简体中文回答。只有当用户明确要求英文或其他语言时，才切换语言。

回答要自然，像真正看过证据后的结论，不要写成生硬模板。
不要输出 “Answer: / Visual Evidence: / Limitations:” 这种英文标题。

回答规则：
1. 先直接回答问题。
2. 只有在确有必要时，再用简短中文小标题，比如“结论”“依据”“局限”。
3. 只有“可直接查看的图片”才能说“我看到”或“现在能看到”。
4. 对“只有摘要、当前看不到原图的图片”，只能说“摘要显示”或“检索结果提示”，不能说“我看到”。
5. 不要重复同一条证据。
6. 证据不足时，明确指出缺口，不要过度推断。
7. 如果用户问“你现在可以看见什么图片”，优先区分“能直接看到的图片”和“只能从摘要得知的图片”。

## 用户问题

{question}

## 已收集证据

{evidence_str}

## 记忆图谱

{memory_str}
"""

        try:
            response = self._llm_invoke(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.3,
            )
            return response or "未能生成回答。"

        except Exception as e:
            logger.error(f"Answer tool failed: {e}")
            return f"Failed to generate answer: {e}"

    def _llm_invoke(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.3,
        **kwargs,
    ) -> str:
        """Invoke the LLM with a unified interface.

        Supports both LangChain chat models (from provision_langchain_model)
        and raw OpenAI SDK clients.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            The generated text content.
        """
        if hasattr(self.llm_client, "invoke"):
            # LangChain chat model
            lc_messages = []
            for msg in messages:
                content = msg["content"]
                # If content is a list (multimodal), use it directly
                # If it's a string, wrap in list
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                lc_messages.append(HumanMessage(content=content))

            result = self.llm_client.invoke(lc_messages, config={"max_tokens": max_tokens})
            return result.content if hasattr(result, "content") else str(result)
        else:
            # Raw OpenAI SDK client
            import openai

            model = kwargs.get("model", "gpt-4o")
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
