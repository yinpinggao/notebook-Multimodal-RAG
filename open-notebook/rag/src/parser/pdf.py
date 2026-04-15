import logging
import os
import tempfile
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError("Please install pypdf: pip install pypdf")

try:
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available. Install with: pip install pdf2image")

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available. Install with: pip install Pillow")


def extract_images_from_page(pdf_path: str, page_num: int) -> List[str]:
    """
    Extract images from a PDF page and save them as temporary image files.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (1-indexed)

    Returns:
        List of paths to temporary image files containing the extracted images
    """
    logger.debug(f"Extracting images from PDF page: {pdf_path}, page={page_num}")

    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
        if page_num < 1 or page_num > len(reader.pages):
            logger.warning(
                f"Invalid page number {page_num} for PDF with {len(reader.pages)} pages"
            )
            return []

        page = reader.pages[page_num - 1]
        images = page.images

        if not images:
            logger.debug(f"No images found on page {page_num}")
            return []

        logger.debug(f"Found {len(images)} image(s) on page {page_num}")

        image_paths = []
        for idx, image in enumerate(images):
            try:
                # Save image to temporary file
                # Determine file extension from image name or use default
                image_name = (
                    image.name
                    if hasattr(image, "name") and image.name
                    else f"image_{idx}"
                )
                # Try to get extension from image name, default to png
                ext = ".png"
                if "." in image_name:
                    ext = "." + image_name.split(".")[-1].lower()
                    # Validate extension
                    if ext not in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
                        ext = ".png"

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp_file.write(image.data)
                temp_file.close()

                image_paths.append(temp_file.name)
                logger.debug(
                    f"Extracted image {idx + 1}/{len(images)} to {temp_file.name}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to extract image {idx + 1} from page {page_num}: {e}",
                )
                continue

        logger.debug(f"Extracted {len(image_paths)} image(s) from page {page_num}")
        return image_paths

    except Exception as e:
        logger.warning(
            f"Failed to extract images from page {page_num} of {pdf_path}: {e}",
        )
        return []


def pdf_page_to_image(pdf_path: str, page_num: int, dpi: int = 100) -> Optional[str]:
    """
    Convert a PDF page to an image file.
    
    This function uses pdf2image (poppler) which may fail on some PDF files.
    Returns None if conversion fails, allowing graceful degradation.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (1-indexed)
        dpi: DPI for image conversion (default: 100)

    Returns:
        Path to the temporary image file, or None if conversion failed
    """
    logger.debug(f"Converting PDF page to image: {pdf_path}, page={page_num}, dpi={dpi}")

    if not PDF2IMAGE_AVAILABLE:
        logger.debug("pdf2image not available, skipping image conversion")
        return None

    if not os.path.exists(pdf_path):
        logger.warning(f"PDF file not found: {pdf_path}")
        return None

    try:
        # Convert specific page to image
        # Suppress poppler warnings by redirecting stderr
        import subprocess
        import sys
        
        # Use poppler_path if available, otherwise let pdf2image find it
        images = convert_from_path(
            pdf_path, 
            dpi=dpi, 
            first_page=page_num, 
            last_page=page_num,
            strict=False,  # Don't fail on warnings
        )

        if not images:
            logger.debug(f"No image returned for page {page_num}")
            return None

        logger.debug(
            f"Page {page_num} converted successfully, image size: {images[0].size}"
        )
        
    except Exception as e:
        # Catch all poppler/pdf2image errors gracefully
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in [
            "unable to get page count",
            "not a pdf file",
            "trailer dictionary",
            "xref table",
            "poppler",
            "pdftoppm",
        ]):
            logger.debug(f"PDF conversion failed for page {page_num} (poppler issue): {e}")
        else:
            logger.warning(f"PDF conversion failed for page {page_num}: {e}")
        return None

    # Convert to grayscale and save to temporary file
    try:
        if not PIL_AVAILABLE:
            logger.debug("PIL not available, cannot process image")
            return None

        # Convert image to grayscale (black and white)
        img = images[0]
        if img.mode != "L":
            img = img.convert("L")

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(temp_file.name, "PNG")
        temp_file.close()
        logger.debug(f"Grayscale image saved to: {temp_file.name}")
        
        return temp_file.name
        
    except Exception as e:
        logger.warning(f"Failed to save image for page {page_num}: {e}")
        return None


def compress_image(
    image_path: str,
    max_size_mb: float = 5.0,
    max_dimension: int = 2048,
    quality: int = 85,
) -> Optional[str]:
    """
    Compress an image file to reduce its size.
    Returns None if compression fails.

    Args:
        image_path: Path to the image file to compress
        max_size_mb: Maximum file size in MB (default: 5.0)
        max_dimension: Maximum width or height in pixels (default: 2048)
        quality: JPEG quality (1-100, default: 85). Only used for JPEG images.

    Returns:
        Path to the compressed temporary image file, or None if failed
    """
    if not PIL_AVAILABLE:
        logger.debug("PIL not available for image compression")
        return None

    if not os.path.exists(image_path):
        logger.warning(f"Image file not found: {image_path}")
        return None

    try:
        # Get original file size
        original_size = os.path.getsize(image_path)
        original_size_mb = original_size / (1024 * 1024)

        # If already small enough, return original
        if original_size_mb <= max_size_mb:
            return image_path

        # Open and process image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for JPEG)
            if img.mode in ("RGBA", "LA", "P"):
                # Create white background for transparent images
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if dimensions are too large
            width, height = img.size
            if width > max_dimension or height > max_dimension:
                # Calculate new dimensions maintaining aspect ratio
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save compressed image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(temp_file.name, "JPEG", quality=quality, optimize=True)
            temp_file.close()

            compressed_size = os.path.getsize(temp_file.name)
            compressed_size_mb = compressed_size / (1024 * 1024)
            logger.debug(
                f"Image compressed: {original_size_mb:.2f} MB -> {compressed_size_mb:.2f} MB"
            )

            return temp_file.name

    except Exception as e:
        logger.warning(f"Failed to compress image {image_path}: {e}")
        return None
