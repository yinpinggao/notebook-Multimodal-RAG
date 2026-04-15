import base64
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from loguru import logger

from open_notebook.ai.models import Model, model_manager
from open_notebook.ai.provision import provision_langchain_model
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.chunking import ContentType, chunk_text
from open_notebook.utils.embedding import generate_embedding, generate_embeddings
from open_notebook.utils.text_utils import extract_text_content

from .settings import (
    get_page_image_cache_dir,
    get_vlm_max_pages_per_source,
    get_vlm_min_text_chars,
)

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    try:
        from PyPDF2 import PdfReader
    except Exception:  # pragma: no cover - optional dependency
        PdfReader = None

try:
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    PDF2IMAGE_AVAILABLE = False


VLM_PAGE_SUMMARY_PROMPT = """请分析这张 PDF 页面图片，生成结构化摘要。

【已提取文字】
{existing_text}

【要求】
1. 判断页面类型：正文、表格、图表、图片说明、混合
2. 提炼页面核心信息
3. 如有图表或表格，提取关键结论和关键数字
4. 明确提到的实体、时间、数字、百分比
5. 输出简洁、适合检索，不要编造

【输出格式】
- 页面类型：
- 核心内容：
- 关键数据：
- 关键实体：
"""


@dataclass
class PDFIndexBuildResult:
    page_records: list[dict[str, Any]]
    chunks: list[str]
    chunk_embeddings: list[list[float]]
    chunk_metadata: list[dict[str, Any]]
    pages_indexed: int
    visual_summary_pages: int
    page_image_dir: str


def is_pdf_file(file_path: Optional[str]) -> bool:
    return bool(file_path and file_path.lower().endswith(".pdf"))


def get_page_cache_dir(source_id: str) -> Path:
    sanitized = source_id.replace(":", "_").replace("/", "_")
    return Path(get_page_image_cache_dir()) / sanitized


def cleanup_page_cache(source_id: str) -> None:
    page_dir = get_page_cache_dir(source_id)
    if page_dir.exists():
        shutil.rmtree(page_dir, ignore_errors=True)


def _normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _page_has_images(page_obj: Any) -> tuple[bool, int]:
    try:
        images = getattr(page_obj, "images", None)
        if images is None:
            return False, 0
        count = len(images)
        return count > 0, count
    except Exception:
        return False, 0


def _should_use_vlm(
    raw_text: str,
    has_images: bool,
    page_no: int,
    pages_with_vlm: int,
) -> bool:
    if pages_with_vlm >= get_vlm_max_pages_per_source():
        return False
    if not raw_text.strip():
        return True
    if len(raw_text) < get_vlm_min_text_chars():
        return True
    if has_images:
        return True
    indicators = ["表", "图", "chart", "figure", "table"]
    lowered = raw_text.lower()
    return any(indicator in lowered for indicator in indicators)


def _page_to_image(pdf_path: str, page_no: int, output_path: Path) -> Optional[str]:
    if not PDF2IMAGE_AVAILABLE:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        images = convert_from_path(
            pdf_path,
            dpi=110,
            first_page=page_no,
            last_page=page_no,
            strict=False,
        )
        if not images:
            return None
        images[0].save(output_path, "PNG")
        return str(output_path)
    except Exception as e:
        logger.debug(f"Failed to render PDF page {page_no} to image: {e}")
        return None


def _image_to_data_url(image_path: str) -> str:
    mime_type = "image/png"
    suffix = Path(image_path).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime_type = "image/jpeg"
    with open(image_path, "rb") as file_handle:
        encoded = base64.b64encode(file_handle.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


async def _generate_page_summary(image_path: str, raw_text: str) -> str:
    defaults = await model_manager.get_defaults()
    model_id = getattr(defaults, "default_vision_model", None)
    if not model_id:
        return ""

    model_record = await Model.get(model_id)
    if not model_record:
        return ""
    prompt = VLM_PAGE_SUMMARY_PROMPT.format(
        existing_text=(raw_text[:1200] if raw_text else "无已提取文本")
    )
    try:
        langchain_model = await provision_langchain_model(
            prompt,
            model_record.id,
            "vision",
            max_tokens=1800,
        )
        data_url = _image_to_data_url(image_path)
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        )
        response = await langchain_model.ainvoke([message])
        text = clean_thinking_content(extract_text_content(response.content))
        return text.strip()
    except Exception as e:
        logger.debug(
            f"Vision summary generation failed for {image_path} using {model_record.provider}/{model_record.name}: {e}"
        )
        return ""


async def build_pdf_source_index(
    source_id: str,
    pdf_path: str,
    title: Optional[str],
    notebook_ids: list[str],
    updated_at: Optional[Any] = None,
) -> PDFIndexBuildResult:
    if PdfReader is None:
        raise ValueError("PDF indexing requires pypdf or PyPDF2 to be installed")

    cleanup_page_cache(source_id)
    page_image_dir = get_page_cache_dir(source_id)
    page_image_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(pdf_path)
    filename = Path(pdf_path).name

    page_records: list[dict[str, Any]] = []
    chunks: list[str] = []
    chunk_metadata: list[dict[str, Any]] = []
    visual_summary_pages = 0

    for index, page in enumerate(reader.pages, start=1):
        try:
            raw_text = _normalize_whitespace(page.extract_text() or "")
        except Exception as e:
            logger.debug(f"Failed to extract text from {filename} page {index}: {e}")
            raw_text = ""

        has_images, image_count = _page_has_images(page)
        page_image_path: Optional[str] = None
        page_summary = ""

        if _should_use_vlm(raw_text, has_images, index, visual_summary_pages):
            page_image_path = _page_to_image(
                pdf_path,
                index,
                page_image_dir / f"page-{index}.png",
            )
            if page_image_path:
                page_summary = await _generate_page_summary(page_image_path, raw_text)
                if page_summary:
                    visual_summary_pages += 1

        combined_text = "\n\n".join(
            part for part in [raw_text, page_summary] if part and part.strip()
        ).strip()
        if not combined_text:
            continue

        page_id = f"ai_source_page:{source_id}:{index}"
        page_embedding = await generate_embedding(
            combined_text[:6000],
            task_type="retrieval_document",
        )
        page_records.append(
            {
                "page_id": page_id,
                "source_id": source_id,
                "filename": filename,
                "page_no": index,
                "raw_text": raw_text,
                "page_summary": page_summary,
                "combined_text": combined_text,
                "notebook_ids": notebook_ids,
                "updated_at": updated_at,
                "embedding": page_embedding,
                "page_image_path": page_image_path,
                "image_count": image_count,
                "has_visual_summary": bool(page_summary),
                "title": title,
            }
        )

        page_chunks = chunk_text(combined_text, content_type=ContentType.PLAIN)
        for order_no, chunk in enumerate(page_chunks):
            chunks.append(chunk)
            chunk_metadata.append(
                {
                    "page_id": page_id,
                    "page_no": index,
                    "filename": filename,
                    "chunk_kind": "pdf_page_chunk",
                    "order_no": order_no,
                }
            )

    chunk_embeddings = (
        await generate_embeddings(chunks, task_type="retrieval_document")
        if chunks
        else []
    )
    return PDFIndexBuildResult(
        page_records=page_records,
        chunks=chunks,
        chunk_embeddings=chunk_embeddings,
        chunk_metadata=chunk_metadata,
        pages_indexed=len(page_records),
        visual_summary_pages=visual_summary_pages,
        page_image_dir=str(page_image_dir),
    )
