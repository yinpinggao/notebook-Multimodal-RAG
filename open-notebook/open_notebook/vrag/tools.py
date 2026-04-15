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
                    "score": r.score,
                    "image_path": r.image_path,
                    "image_base64": r.image_base64,
                    "page_no": r.page_no,
                    "source_id": r.source_id,
                    "summary": r.summary,
                    "bbox": r.bbox,
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
        # Build evidence for the prompt
        evidence_parts = []
        for i, ev in enumerate(collected_evidence):
            ev_type = ev.get("type", "unknown")
            if ev_type == "search":
                for img in ev.get("images", [])[:3]:
                    evidence_parts.append(
                        f"[Image] Page {img['page_no']}: {img.get('summary', 'No summary')}\n"
                        f"  Path: {img['image_path']}"
                    )
                for txt in ev.get("texts", [])[:2]:
                    evidence_parts.append(
                        f"[Text] Page {txt['page_no']}: {txt.get('text', '')[:300]}..."
                    )
            elif ev_type == "bbox_crop":
                evidence_parts.append(
                    f"[BBox Crop] {ev.get('description', 'No description')}\n"
                    f"  From: {ev.get('original_image', '')}"
                )

        evidence_str = "\n".join(evidence_parts)

        # Build memory string
        memory_parts = []
        for entry in memory_entries:
            if entry.is_useful:
                memory_parts.append(f"- [{entry.type}] {entry.summary}")
        memory_str = "\n".join(memory_parts) or "No memory entries."

        prompt = f"""## Question

{question}

## Collected Visual Evidence

{evidence_str}

## Memory Graph (reasoning steps)

{memory_str}

---

Based on all the visual evidence and reasoning, provide a comprehensive answer to the question.

**Important formatting guidelines:**
- Cite images by their source and page number, e.g., "As shown in [Figure on page 3]..."
- Describe what you see in the images (charts, data, diagrams, etc.)
- If bounding box crops were used, mention the specific region analyzed
- If the evidence is insufficient to fully answer, clearly state what information is missing

Format your answer with these sections:
1. **Answer**: Direct answer to the question
2. **Visual Evidence**: List of images that support the answer
3. **Limitations**: Any caveats or missing information
"""

        try:
            response = self._llm_invoke(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.3,
            )
            return response or "Failed to generate answer."

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
