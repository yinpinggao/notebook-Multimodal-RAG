"""VRAG utilities — image processing, bbox, base64, video frame extraction.

Adapted from VRAG/demo/vimrag_utils.py.
"""

import base64
import io
import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

# Image extensions that are supported
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
VISUAL_INDEX_VERSION = 2
NATIVE_IMAGE_MIN_AREA_RATIO = 0.0075
NATIVE_IMAGE_MIN_SIDE_RATIO = 0.05
NATIVE_IMAGE_MAX_ASPECT_RATIO = 8.0
NATIVE_IMAGES_PER_PAGE_LIMIT = 8


def _page_text(page: fitz.Page) -> str:
    try:
        return str(page.get_text("text") or "").strip()
    except Exception:
        return ""


def _normalized_bbox(rect: fitz.Rect, page_rect: fitz.Rect) -> list[float]:
    page_width = max(float(page_rect.width or 0.0), 1.0)
    page_height = max(float(page_rect.height or 0.0), 1.0)
    x0 = min(max(float(rect.x0) / page_width, 0.0), 1.0)
    y0 = min(max(float(rect.y0) / page_height, 0.0), 1.0)
    x1 = min(max(float(rect.x1) / page_width, 0.0), 1.0)
    y1 = min(max(float(rect.y1) / page_height, 0.0), 1.0)
    return [x0, y0, x1, y1]


def _rect_metrics(rect: fitz.Rect, page_rect: fitz.Rect) -> dict[str, float]:
    page_width = max(float(page_rect.width or 0.0), 1.0)
    page_height = max(float(page_rect.height or 0.0), 1.0)
    rect_width = max(float(rect.width or 0.0), 0.0)
    rect_height = max(float(rect.height or 0.0), 0.0)
    area_ratio = (rect_width * rect_height) / (page_width * page_height)
    width_ratio = rect_width / page_width
    height_ratio = rect_height / page_height
    shorter_side = max(min(rect_width, rect_height), 1.0)
    longer_side = max(rect_width, rect_height)
    aspect_ratio = longer_side / shorter_side
    return {
        "area_ratio": area_ratio,
        "width_ratio": width_ratio,
        "height_ratio": height_ratio,
        "aspect_ratio": aspect_ratio,
    }


def _should_keep_native_rect(rect: fitz.Rect, page_rect: fitz.Rect) -> tuple[bool, dict[str, float]]:
    metrics = _rect_metrics(rect, page_rect)
    keep = (
        metrics["area_ratio"] >= NATIVE_IMAGE_MIN_AREA_RATIO
        and metrics["width_ratio"] >= NATIVE_IMAGE_MIN_SIDE_RATIO
        and metrics["height_ratio"] >= NATIVE_IMAGE_MIN_SIDE_RATIO
        and metrics["aspect_ratio"] <= NATIVE_IMAGE_MAX_ASPECT_RATIO
    )
    return keep, metrics


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: Optional[str] = None,
    dpi: int = 150,
    min_width: int = 100,
    min_height: int = 100,
) -> list[dict]:
    """Extract images from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save extracted images. If None, images are kept in memory.
        dpi: Resolution for rendering PDF pages to images.
        min_width: Minimum image width in pixels to keep.
        min_height: Minimum image height in pixels to keep.

    Returns:
        List of dicts with keys: page_no, image_index, image_path, width, height, is_native_image
    """
    doc = fitz.open(pdf_path)
    results = []

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    try:
        for page_no in range(len(doc)):
            page = doc[page_no]
            page_number = page_no + 1
            page_rect = page.rect
            page_text = _page_text(page)

            # Every page gets a canonical full-page render.
            pix = page.get_pixmap(dpi=dpi)
            width = pix.width
            height = pix.height
            page_image_bytes = None

            if width >= min_width and height >= min_height:
                if output_dir:
                    image_name = f"page{page_number}_rendered.png"
                    image_path = output_path / image_name
                    pix.save(str(image_path))
                    image_path_str = str(image_path)
                else:
                    image_path_str = f"page{page_number}_rendered"
                    page_image_bytes = pix.tobytes("png")

                results.append({
                    "page_no": page_number,
                    "image_index": -1,
                    "asset_type": "page_render",
                    "image_path": image_path_str,
                    "image_bytes": page_image_bytes,
                    "width": width,
                    "height": height,
                    "is_native_image": False,
                    "format": "png",
                    "raw_text": page_text,
                    "bbox": [],
                    "metadata": {
                        "index_version": VISUAL_INDEX_VERSION,
                        "page_width": float(page_rect.width or 0.0),
                        "page_height": float(page_rect.height or 0.0),
                    },
                })

            native_candidates: list[dict] = []
            image_list = page.get_images(full=True)
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue

                image_bytes = base_image.get("image")
                image_ext = str(base_image.get("ext") or "png")
                image_width = int(base_image.get("width") or 0)
                image_height = int(base_image.get("height") or 0)
                if not image_bytes:
                    continue

                rects = page.get_image_rects(xref) or []
                unique_rects: list[fitz.Rect] = []
                seen_rects: set[tuple[float, float, float, float]] = set()
                for rect in rects:
                    rect_key = (
                        round(float(rect.x0), 2),
                        round(float(rect.y0), 2),
                        round(float(rect.x1), 2),
                        round(float(rect.y1), 2),
                    )
                    if rect_key in seen_rects:
                        continue
                    seen_rects.add(rect_key)
                    unique_rects.append(rect)

                if not unique_rects:
                    continue

                multiple_rects = len(unique_rects) > 1
                for rect_index, rect in enumerate(unique_rects):
                    keep, metrics = _should_keep_native_rect(rect, page_rect)
                    if not keep:
                        continue

                    if output_dir:
                        suffix = f"_r{rect_index}" if multiple_rects else ""
                        image_name = f"page{page_number}_img{img_index}{suffix}.{image_ext}"
                        image_path = output_path / image_name
                        image_path.write_bytes(image_bytes)
                        image_path_str = str(image_path)
                    else:
                        suffix = f"_r{rect_index}" if multiple_rects else ""
                        image_path_str = f"page{page_number}_img{img_index}{suffix}"

                    normalized_bbox = _normalized_bbox(rect, page_rect)
                    native_candidates.append({
                        "page_no": page_number,
                        "image_index": (img_index * 1000) + rect_index,
                        "asset_type": "native_image",
                        "image_path": image_path_str,
                        "image_bytes": image_bytes,
                        "width": image_width,
                        "height": image_height,
                        "is_native_image": True,
                        "format": image_ext,
                        "raw_text": page_text,
                        "bbox": normalized_bbox,
                        "metadata": {
                            "index_version": VISUAL_INDEX_VERSION,
                            "page_width": float(page_rect.width or 0.0),
                            "page_height": float(page_rect.height or 0.0),
                            "xref": xref,
                            "original_image_index": img_index,
                            "rect_index": rect_index,
                            "bbox_pixels": [
                                float(rect.x0),
                                float(rect.y0),
                                float(rect.x1),
                                float(rect.y1),
                            ],
                            **metrics,
                        },
                    })

            native_candidates.sort(
                key=lambda item: float(item.get("metadata", {}).get("area_ratio") or 0.0),
                reverse=True,
            )
            results.extend(native_candidates[:NATIVE_IMAGES_PER_PAGE_LIMIT])
    finally:
        doc.close()

    logger.info(f"Extracted {len(results)} images from PDF: {pdf_path}")
    return results


def extract_images_from_source(
    source_path: str,
    source_type: str,
    output_dir: Optional[str] = None,
    dpi: int = 150,
) -> list[dict]:
    """Extract images from a source document (PDF, PPT, etc.).

    Args:
        source_path: Path to the source file.
        source_type: Type of source ('pdf', 'ppt', etc.)
        output_dir: Directory to save extracted images.
        dpi: Resolution for rendering pages.

    Returns:
        List of extracted image info dicts.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    if source_type == "pdf":
        return extract_images_from_pdf(
            str(source_path),
            output_dir=output_dir,
            dpi=dpi,
        )
    else:
        raise NotImplementedError(f"Image extraction for source type '{source_type}' is not yet supported.")


def crop_image(
    image_path: str,
    bbox: list[float],
    padding: float = 0.02,
    output_path: Optional[str] = None,
) -> dict:
    """Crop a region from an image using normalized bbox coordinates [x1, y1, x2, y2].

    Args:
        image_path: Path to the source image.
        bbox: Normalized bounding box [x1, y1, x2, y2], values in [0, 1].
        padding: Fraction of padding to add around the cropped region.
        output_path: Path to save the cropped image. If None, returns base64.

    Returns:
        Dict with keys: image_path, image_base64, width, height, description
    """
    x1, y1, x2, y2 = bbox

    # Add padding
    pad_x = (x2 - x1) * padding
    pad_y = (y2 - y1) * padding
    x1 = max(0.0, x1 - pad_x)
    y1 = max(0.0, y1 - pad_y)
    x2 = min(1.0, x2 + pad_x)
    y2 = min(1.0, y2 + pad_y)

    with Image.open(image_path) as img:
        width, height = img.size

        # Convert normalized coords to pixels
        px1 = int(x1 * width)
        py1 = int(y1 * height)
        px2 = int(x2 * width)
        py2 = int(y2 * height)

        # Ensure minimum size
        px2 = max(px1 + 1, px2)
        py2 = max(py1 + 1, py2)

        cropped = img.crop((px1, py1, px2, py2))
        cropped_width, cropped_height = cropped.size

        if output_path:
            cropped.save(output_path)
            image_path_out = output_path
        else:
            buffer = io.BytesIO()
            cropped.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            image_path_out = None

    result = {
        "image_path": image_path_out,
        "original_image": image_path,
        "bbox": bbox,
        "bbox_pixel": [px1, py1, px2, py2],
        "width": cropped_width,
        "height": cropped_height,
    }

    if output_path is None:
        result["image_base64"] = image_base64

    logger.debug(f"Cropped image region {bbox} from {image_path} -> {image_path_out or 'base64'}")
    return result


def image_to_base64(image_path: str) -> str:
    """Convert an image file to base64 string.

    Args:
        image_path: Path to the image file.

    Returns:
        Base64-encoded image string (without data URL prefix).
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def base64_to_image(base64_str: str, output_path: Optional[str] = None) -> Optional[str]:
    """Convert a base64 string to an image file.

    Args:
        base64_str: Base64-encoded image data.
        output_path: Path to save the decoded image. If None, returns PIL Image.

    Returns:
        Path to the saved image, or None if output_path is None.
    """
    image_data = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_data))

    if output_path:
        image.save(output_path)
        return output_path
    return None


def get_image_base64_data_url(image_path: str) -> str:
    """Get the data URL for an image file.

    Args:
        image_path: Path to the image file.

    Returns:
        Data URL string (e.g., "data:image/png;base64,...").
    """
    with Image.open(image_path) as img:
        format_str = img.format.lower() if img.format else "png"
        mime_type = f"image/{format_str}"

    b64_data = image_to_base64(image_path)
    return f"data:{mime_type};base64,{b64_data}"


def resize_image_if_needed(
    image_path: str,
    max_size: int = 2048,
    output_path: Optional[str] = None,
) -> str:
    """Resize an image if it exceeds max_size in any dimension.

    Args:
        image_path: Path to the source image.
        max_size: Maximum width or height.
        output_path: Path to save the resized image. If None, overwrites the original.

    Returns:
        Path to the resized image.
    """
    with Image.open(image_path) as img:
        width, height = img.size

        if width <= max_size and height <= max_size:
            if output_path and output_path != image_path:
                img.save(output_path)
                return output_path
            return image_path

        # Calculate new size maintaining aspect ratio
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))

        resized = img.resize((new_width, new_height), Image.LANCZOS)

        if output_path:
            resized.save(output_path)
            return output_path
        else:
            resized.save(image_path)
            return image_path


def classify_image_kind(image_summary: str) -> str:
    """Classify the kind of an image based on its summary.

    Args:
        image_summary: Text summary of the image.

    Returns:
        One of: 'chart', 'table', 'figure', 'photo', 'diagram', 'screenshot', 'unknown'
    """
    summary_lower = image_summary.lower()

    if any(k in summary_lower for k in ["chart", "graph", "plot", "line", "bar", "scatter", "trend"]):
        return "chart"
    elif any(k in summary_lower for k in ["table", "grid", "spreadsheet"]):
        return "table"
    elif any(k in summary_lower for k in ["figure", "illustration", "drawing"]):
        return "figure"
    elif any(k in summary_lower for k in ["screenshot", "screen", "ui", "interface", "app"]):
        return "screenshot"
    elif any(k in summary_lower for k in ["diagram", "flowchart", "architecture"]):
        return "diagram"
    elif any(k in summary_lower for k in ["photo", "photograph", "image", "picture"]):
        return "photo"
    else:
        return "unknown"


def estimate_tokens_for_image(image_path: str, model: str = "gpt-4o") -> int:
    """Estimate the token count for an image based on its dimensions.

    Uses the token estimation formula from OpenAI:
    - Each 512x512 tile costs ~170 tokens
    - For GPT-4o: num_tiles = ceil(width/512) * ceil(height/512)

    Args:
        image_path: Path to the image file.
        model: Model name (gpt-4o, gpt-4o-mini, etc.)

    Returns:
        Estimated token count for the image.
    """
    with Image.open(image_path) as img:
        width, height = img.size

    tiles_x = (width + 511) // 512
    tiles_y = (height + 511) // 512
    num_tiles = tiles_x * tiles_y

    # Base tokens per tile varies by model
    if "mini" in model.lower():
        tokens_per_tile = 85
    else:
        tokens_per_tile = 170

    return num_tiles * tokens_per_tile
