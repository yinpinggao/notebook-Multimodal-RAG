import glob
import logging
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import dotenv
from pyobvector import VECTOR, FtsIndexParam, FtsParser, VectorIndex
from pyobvector.client.hybrid_search import HybridSearch
from sqlalchemy import VARCHAR, Column, Integer

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

from src.integrations.embedding import generate_response as generate_embedding
from src.integrations.vlm import generate_response as generate_vlm_response
from src.parser.pdf import compress_image, pdf_page_to_image
from src.prompt.vlm import VLM_PAGE_SUMMARY_PROMPT
from src.split.split import split_text
from src.storage.oceanbase import get_or_create_client

dotenv.load_dotenv()

# Default embedding dimension (will be auto-detected whenever possible)
DEFAULT_EMBEDDING_DIM = 1024
# Cache resolved dimension to avoid repeated detection
EMBEDDING_DIM: Optional[int] = None

# Table names
TABLE_NAME = "rag_documents"  # Chunk-level index
PAGE_TABLE_NAME = "rag_pages"  # Page-level index

# VLM processing thresholds (adjusted for better multimodal understanding)
MIN_TEXT_CHARS_FOR_VLM = 300  # Use VLM for pages with limited text (increased threshold)
MAX_VLM_PAGES_PER_PDF = 50    # Allow more VLM calls per PDF for better coverage


def create_tables_if_not_exists(client: HybridSearch, vector_dim: int):
    """Create the documents and pages tables if they don't exist."""
    
    # Drop existing tables
    for table in [TABLE_NAME, PAGE_TABLE_NAME]:
        try:
            client.drop_table_if_exist(table_name=table)
            logger.debug(f"Dropped existing table '{table}' if it existed")
        except Exception:
            logger.debug(f"Table '{table}' does not exist")
    
    # Create chunk-level table
    logger.info(f"Creating table '{TABLE_NAME}' with vector dimension {vector_dim}...")
    client.create_table(
        table_name=TABLE_NAME,
        columns=[
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("source_id", VARCHAR(64)),  # Unique identifier for each chunk
            Column("filename", VARCHAR(512)),  # PDF filename
            Column("page", Integer),  # Page number (1-indexed)
            Column("content", VARCHAR(8192)),  # Text content
            Column("vector", VECTOR(vector_dim)),  # Embedding vector
        ],
        indexes=[
            VectorIndex("vec_idx", "vector", params="distance=l2, type=hnsw, lib=vsag"),
        ],
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_organization="heap",
    )
    
    # Create FTS index for chunks
    client.create_fts_idx_with_fts_index_param(
        table_name=TABLE_NAME,
        fts_idx_param=FtsIndexParam(
            index_name="fts_idx_content",
            field_names=["content"],
            parser_type=FtsParser.IK,
        ),
    )
    logger.info(f"Table '{TABLE_NAME}' created successfully")
    
    # Create page-level table
    logger.info(f"Creating table '{PAGE_TABLE_NAME}' with vector dimension {vector_dim}...")
    client.create_table(
        table_name=PAGE_TABLE_NAME,
        columns=[
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("page_id", VARCHAR(64)),  # Unique identifier for each page
            Column("filename", VARCHAR(512)),  # PDF filename
            Column("page", Integer),  # Page number (1-indexed)
            Column("summary", VARCHAR(4096)),  # Page summary from VLM
            Column("full_text", VARCHAR(8192)),  # Full page text
            Column("vector", VECTOR(vector_dim)),  # Embedding of summary
        ],
        indexes=[
            VectorIndex("page_vec_idx", "vector", params="distance=l2, type=hnsw, lib=vsag"),
        ],
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_organization="heap",
    )
    
    # Create FTS index for page summaries
    client.create_fts_idx_with_fts_index_param(
        table_name=PAGE_TABLE_NAME,
        fts_idx_param=FtsIndexParam(
            index_name="fts_idx_summary",
            field_names=["summary"],
            parser_type=FtsParser.IK,
        ),
    )
    
    # Create FTS index for page full text
    client.create_fts_idx_with_fts_index_param(
        table_name=PAGE_TABLE_NAME,
        fts_idx_param=FtsIndexParam(
            index_name="fts_idx_fulltext",
            field_names=["full_text"],
            parser_type=FtsParser.IK,
        ),
    )
    logger.info(f"Table '{PAGE_TABLE_NAME}' created successfully")


def process_pdf_file(
    pdf_file: str,
    client: HybridSearch,
) -> Tuple[int, int]:
    """
    Process a single PDF file with enhanced workflow:
    1. Extract text from each page
    2. Optionally generate page-level summaries using VLM (best-effort)
    3. Create page-level embeddings
    4. Split into chunks and create chunk-level embeddings
    
    Args:
        pdf_file: Path to the PDF file
        client: OceanBase client for database operations
        
    Returns:
        Tuple of (chunks_inserted, pages_inserted)
    """
    filename = os.path.basename(pdf_file)
    logger.info(f"Processing {filename}...")
    
    try:
        # Read PDF
        if PdfReader is None:
            raise ImportError("PdfReader not available")
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        logger.debug(f"  Total pages: {total_pages}")
        
        chunks_to_insert = []
        pages_to_insert = []
        vlm_pages_processed = 0
        
        # Process each page
        for page_num in range(1, total_pages + 1):
            # Check VLM limit
            can_use_vlm = vlm_pages_processed < MAX_VLM_PAGES_PER_PDF
            
            page_data = _process_single_page(
                reader=reader,
                pdf_file=pdf_file,
                filename=filename,
                page_num=page_num,
                total_pages=total_pages,
                enable_vlm=can_use_vlm,
            )
            
            if page_data is None:
                continue
            
            page_record, chunk_records, used_vlm = page_data
            
            if used_vlm:
                vlm_pages_processed += 1
            
            if page_record:
                pages_to_insert.append(page_record)
            
            chunks_to_insert.extend(chunk_records)
        
        # Batch insert pages
        pages_inserted = 0
        if pages_to_insert:
            batch_size = 50
            for i in range(0, len(pages_to_insert), batch_size):
                batch = pages_to_insert[i:i + batch_size]
                try:
                    client.insert(table_name=PAGE_TABLE_NAME, data=batch)
                    pages_inserted += len(batch)
                except Exception as e:
                    logger.error(f"Failed to insert page batch: {e}")
            logger.info(f"Inserted {pages_inserted} pages from {filename}")
        
        # Batch insert chunks
        chunks_inserted = 0
        if chunks_to_insert:
            batch_size = 100
            for i in range(0, len(chunks_to_insert), batch_size):
                batch = chunks_to_insert[i:i + batch_size]
                try:
                    client.insert(table_name=TABLE_NAME, data=batch)
                    chunks_inserted += len(batch)
                except Exception as e:
                    logger.error(f"Failed to insert chunk batch: {e}")
            logger.info(f"Inserted {chunks_inserted} chunks from {filename}")
        
        return chunks_inserted, pages_inserted
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}", exc_info=True)
        return 0, 0


def _process_single_page(
    reader: PdfReader,
    pdf_file: str,
    filename: str,
    page_num: int,
    total_pages: int,
    enable_vlm: bool = True,
) -> Optional[Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], bool]]:
    """
    Process a single page and return page record and chunk records.
    
    Returns:
        Tuple of (page_record, list of chunk_records, whether VLM was used) or None if failed
    """
    # Extract text
    raw_text, page_obj = _extract_pdf_text(reader, page_num)
    
    # Check if VLM processing is beneficial and enabled
    should_use_vlm = enable_vlm and _should_use_vlm(raw_text, page_obj, page_num, total_pages)
    
    # Get VLM summary if needed (best-effort, may fail silently)
    vlm_summary = ""
    vlm_used = False
    if should_use_vlm:
        vlm_summary = _generate_page_summary_safe(pdf_file, page_num, filename, raw_text)
        if vlm_summary:
            vlm_used = True
    
    # Combine text content
    sections = []
    if raw_text:
        sections.append(raw_text)
    if vlm_summary:
        sections.append(vlm_summary)
    
    page_text = "\n\n".join([sec for sec in sections if sec]).strip()
    
    if not page_text:
        logger.debug(f"No content extracted from page {page_num}, skipping")
        return None
    
    # Create page-level record
    page_record = None
    summary_for_embedding = vlm_summary if vlm_summary else raw_text[:1000]
    
    if summary_for_embedding.strip():
        try:
            page_embedding = generate_embedding(summary_for_embedding[:2000])
            page_record = {
                "page_id": str(uuid.uuid4()),
                "filename": filename,
                "page": page_num,
                "summary": summary_for_embedding[:4000],
                "full_text": page_text[:8000],
                "vector": page_embedding,
            }
        except Exception as e:
            logger.warning(f"Failed to generate page embedding for {filename} p{page_num}: {e}")
    
    # Create chunk-level records
    chunk_records = []
    text_chunks = split_text(page_text)
    
    for chunk_text in text_chunks:
        if not chunk_text.strip():
            continue
        
        try:
            chunk_embedding = generate_embedding(chunk_text)
            chunk_records.append({
                "source_id": str(uuid.uuid4()),
                "filename": filename,
                "page": page_num,
                "content": chunk_text[:8190],
                "vector": chunk_embedding,
            })
        except Exception as e:
            logger.warning(
                f"Failed to generate chunk embedding for {filename} p{page_num}: {e}"
            )
    
    return page_record, chunk_records, vlm_used


def _should_use_vlm(
    text: str,
    page_obj: Optional[Any],
    page_num: int,
    total_pages: int,
) -> bool:
    """
    Determine if VLM should be used for this page.
    Conservative logic to avoid too many VLM calls.
    """
    # Use VLM if no text extracted at all
    if not text.strip():
        return True
    
    # Use VLM for pages with very limited text
    if len(text) < MIN_TEXT_CHARS_FOR_VLM:
        return True
    
    # Check for images on the page
    has_images = False
    if page_obj is not None:
        try:
            images = getattr(page_obj, "images", None)
            has_images = bool(images)
        except Exception:
            pass
    
    if has_images:
        return True
    
    # Check for potential table/chart indicators in text
    table_indicators = ["表", "图", "Table", "Figure", "Chart"]
    if any(indicator in text for indicator in table_indicators):
        return True
    
    return False


def _generate_page_summary_safe(
    pdf_file: str,
    page_num: int,
    filename: str,
    existing_text: str,
) -> str:
    """
    Generate a structured summary for a page using VLM.
    This is a best-effort function that returns empty string on any failure.
    """
    page_image_path = None
    try:
        # Try to convert PDF page to image
        page_image_path = pdf_page_to_image(pdf_file, page_num, dpi=100)
        
        # If conversion failed, return empty
        if page_image_path is None:
            logger.debug(f"Image conversion failed for {filename} p{page_num}, skipping VLM")
            return ""
        
        # Use enhanced prompt for better summary
        prompt = VLM_PAGE_SUMMARY_PROMPT.format(
            page_num=page_num,
            existing_text=existing_text[:500] if existing_text else "无已提取文本"
        )
        
        response = _call_vlm_safe(page_image_path, prompt, page_num, filename)
        
        if response and response.strip():
            return _format_page_summary(response, page_num)
        
    except Exception as e:
        logger.debug(f"VLM processing failed for {filename} p{page_num}: {e}")
    finally:
        # Clean up temporary image file
        if page_image_path and os.path.exists(page_image_path):
            try:
                os.unlink(page_image_path)
            except Exception:
                pass
    
    return ""


def _call_vlm_safe(
    image_path: str,
    prompt: str,
    page_num: int,
    filename: str,
) -> str:
    """
    Call the vision model with error handling.
    Returns empty string on any failure.
    """
    try:
        response = generate_vlm_response(prompt, images=image_path)
        if response and response.strip():
            return response
    except Exception as e:
        error_str = str(e).lower()
        is_502_error = (
            "502" in error_str
            or "bad gateway" in error_str
            or (hasattr(e, "status_code") and getattr(e, "status_code", None) == 502)
        )
        
        if is_502_error:
            # Try with compressed image
            logger.debug(f"502 error for {filename} p{page_num}, trying compressed image")
            compressed_path = None
            try:
                compressed_path = compress_image(
                    image_path,
                    max_size_mb=5.0,
                    max_dimension=2048,
                )
                if compressed_path:
                    retry_response = generate_vlm_response(prompt, images=compressed_path)
                    if retry_response and retry_response.strip():
                        return retry_response
            except Exception:
                pass
            finally:
                if compressed_path and compressed_path != image_path and os.path.exists(compressed_path):
                    try:
                        os.unlink(compressed_path)
                    except Exception:
                        pass
        else:
            logger.debug(f"VLM call failed for {filename} p{page_num}: {e}")
    
    return ""


def _format_page_summary(text: str, page_num: int) -> str:
    """Format the VLM-generated page summary."""
    normalized = _normalize_whitespace(text)
    if not normalized:
        return ""
    return f"[第{page_num}页摘要] {normalized}"


def add(dataset_dir: str, max_worker: int):
    """
    Prepare RAG data by parsing PDFs, generating embeddings, and storing in OceanBase.
    
    Args:
        dataset_dir: Directory containing PDF files
        max_worker: Number of parallel workers for processing PDF files
    """
    pdf_files: List[str] = glob.glob(os.path.join(dataset_dir, "*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {dataset_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    # Initialize OceanBase client
    client = get_or_create_client()
    
    # Detect embedding dimension
    vector_dim = _resolve_embedding_dim()
    logger.info(f"Using embedding vector dimension: {vector_dim}")
    
    # Create both tables
    create_tables_if_not_exists(client, vector_dim)
    
    # Process PDF files in parallel
    total_chunks = 0
    total_pages = 0
    
    with ThreadPoolExecutor(max_workers=max_worker) as executor:
        future_to_pdf = {
            executor.submit(process_pdf_file, pdf_file, client): pdf_file
            for pdf_file in pdf_files
        }
        
        for future in as_completed(future_to_pdf):
            pdf_file = future_to_pdf[future]
            try:
                chunks_inserted, pages_inserted = future.result()
                total_chunks += chunks_inserted
                total_pages += pages_inserted
            except Exception as e:
                filename = os.path.basename(pdf_file)
                logger.error(
                    f"Exception processing {filename}: {e}",
                    exc_info=True,
                )
    
    logger.info(
        f"Preparation complete! Total: {total_chunks} chunks, {total_pages} pages"
    )


def _extract_pdf_text(reader: PdfReader, page_num: int) -> Tuple[str, Optional[Any]]:
    """Extract and normalize raw text from a PDF page."""
    try:
        page = reader.pages[page_num - 1]
        raw_text = page.extract_text() or ""
        normalized = _normalize_whitespace(raw_text)
        return normalized, page
    except Exception as e:
        logger.warning(f"Failed to extract text from page {page_num}: {e}")
        return "", None


def _normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace for cleaner downstream chunks."""
    if not text:
        return ""
    cleaned = re.sub(r"[ \t]+", " ", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _resolve_embedding_dim() -> int:
    """Determine embedding dimension via env or the provider once."""
    global EMBEDDING_DIM
    if EMBEDDING_DIM:
        return EMBEDDING_DIM
    
    env_value = os.getenv("EMBEDDING_DIM")
    if env_value:
        try:
            EMBEDDING_DIM = int(env_value)
            logger.info(
                "Embedding dimension resolved from EMBEDDING_DIM env: %d", EMBEDDING_DIM
            )
            return EMBEDDING_DIM
        except ValueError:
            logger.warning(
                "Invalid EMBEDDING_DIM env value '%s', falling back to auto-detect",
                env_value,
            )
    
    try:
        probe_vector = generate_embedding("OceanBase RAG dimension probe")
        detected_dim = len(probe_vector)
        if detected_dim <= 0:
            raise ValueError("provider returned empty embedding vector")
        EMBEDDING_DIM = detected_dim
        logger.info("Auto-detected embedding dimension from provider: %d", EMBEDDING_DIM)
        return EMBEDDING_DIM
    except Exception as exc:
        logger.warning(
            "Failed to auto-detect embedding dimension (%s), using default %d",
            exc,
            DEFAULT_EMBEDDING_DIM,
        )
        EMBEDDING_DIM = DEFAULT_EMBEDDING_DIM
        return EMBEDDING_DIM
