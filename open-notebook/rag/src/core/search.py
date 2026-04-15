import logging
import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Tuple

import dotenv

from src.integrations.embedding import generate_response as generate_embedding
from src.integrations.llm import generate_response as generate_llm_response
from src.integrations.reranker import rerank_documents
from src.prompt import QUERY_SYSTEM_PROMPT, QUERY_USER_PROMPT_TEMPLATE
from src.storage.oceanbase import get_or_create_client
from src.util import Answer

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

# OceanBase connection parameters
OCEANBASE_URI = os.getenv("OCEANBASE_URI")
OCEANBASE_USER = os.getenv("OCEANBASE_USER")
OCEANBASE_PASSWORD = os.getenv("OCEANBASE_PASSWORD")
OCEANBASE_DBNAME = os.getenv("OCEANBASE_DBNAME")

# Table names
TABLE_NAME = "rag_documents"  # Chunk-level index
PAGE_TABLE_NAME = "rag_pages"  # Page-level index

# Retrieval parameters (optimized for better recall and accuracy)
CHUNK_TOP_K = 70  # Initial chunk retrieval count (increased for better recall)
PAGE_TOP_K = 50   # Initial page retrieval count (increased for better page matching)
RERANK_TOP_K = 25  # Final count after reranking (keep more candidates for better selection)

# Maximum number of citations
MAX_CITATIONS = 5


def search(question: str) -> Answer:
    """
    Query the RAG system with a question and return an answer.
    Uses dual-index retrieval: page-level + chunk-level.
    
    Args:
        question: The question to answer
        
    Returns:
        Answer object containing the question, answer, filename, and page
    """
    answer = Answer(question=question)
    
    logger.debug(f"Processing query: '{question[:100]}...'")
    
    # Track contexts for recovery in case of errors
    reranked_contexts = []
    
    try:
        # Generate embedding for the question
        logger.debug("Generating embedding for question...")
        question_embedding = generate_embedding(question)
        
        # Initialize OceanBase client
        client = get_or_create_client()
        
        # Dual retrieval: page-level and chunk-level
        logger.debug("Performing dual-index retrieval...")
        
        # 1. Page-level retrieval
        page_hits = _retrieve_from_pages(client, question, question_embedding)
        logger.debug(f"Page-level retrieval: {len(page_hits)} results")
        
        # 2. Chunk-level retrieval
        chunk_hits = _retrieve_from_chunks(client, question, question_embedding)
        logger.debug(f"Chunk-level retrieval: {len(chunk_hits)} results")
        
        # 3. Merge and deduplicate results
        merged_contexts = _merge_retrieval_results(
            page_hits=page_hits,
            chunk_hits=chunk_hits,
            question=question,
        )
        
        if not merged_contexts:
            logger.warning(f"No results found for: '{question[:50]}...'")
            answer.answer = "抱歉，我没有找到相关的信息来回答这个问题。"
            return answer
        
        logger.debug(f"Merged {len(merged_contexts)} unique contexts")
        
        # 4. Rerank merged results
        logger.debug(f"Reranking {len(merged_contexts)} contexts...")
        reranked_contexts = rerank_documents(
            query=question,
            documents=merged_contexts,
            content_key="content",
            top_k=RERANK_TOP_K,
        )
        
        # Re-assign labels after reranking
        for idx, entry in enumerate(reranked_contexts, 1):
            entry["label"] = idx
        
        logger.debug(
            "After reranking: %d contexts, total %d chars",
            len(reranked_contexts),
            sum(len(e.get("content", "")) for e in reranked_contexts),
        )
        
        # 5. Format context for LLM
        context_text = _format_context_text(reranked_contexts)
        
        # 6. Generate answer using LLM
        logger.debug("Generating answer using LLM...")
        prompt = QUERY_USER_PROMPT_TEMPLATE.format(
            context_text=context_text,
            question=question,
        )
        
        messages = [
            {"role": "system", "content": QUERY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        llm_response = generate_llm_response(messages)
        
        # 7. Parse LLM response to extract source info
        parsed_answer, cited_label = _parse_llm_response(llm_response)
        answer.answer = parsed_answer
        
        # 8. Determine best source based on LLM citation
        # First try with cited label, prioritizing page-level sources
        best_source = _determine_best_source(reranked_contexts, cited_label)
        
        if best_source:
            answer.filename = best_source.get("filename", "").strip()
            answer.page = best_source.get("page", 0)
        else:
            # Fallback: use highest-scored entry, prioritizing page-level
            best_entry = _select_best_entry(reranked_contexts)
            if best_entry:
                answer.filename = best_entry.get("filename", "").strip()
                answer.page = best_entry.get("page", 0)
        
        # 8.5. Enhanced validation: if cited label doesn't exist, try to find best match
        if cited_label is not None:
            # Check if cited label actually exists in contexts
            cited_exists = False
            for ctx in reranked_contexts:
                if ctx.get("label") == cited_label:
                    cited_exists = True
                    break
            
            # If cited label doesn't exist, try to extract from answer text
            if not cited_exists:
                logger.warning(f"Cited label {cited_label} not found in contexts, trying to extract from answer")
                # Try to extract filename and page from answer text
                filename_match = re.search(r'（([^，,]+\.pdf)', answer.answer)
                page_match = re.search(r'第(\d+)页', answer.answer)
                
                if filename_match and page_match:
                    extracted_filename = filename_match.group(1).strip()
                    extracted_page = int(page_match.group(1))
                    
                    # Verify it exists in contexts
                    for ctx in reranked_contexts:
                        if extracted_filename in ctx.get("filename", "") and ctx.get("page", 0) == extracted_page:
                            answer.filename = ctx.get("filename", "").strip()
                            answer.page = extracted_page
                            logger.debug(f"Extracted source from answer text: {answer.filename}, page {answer.page}")
                            break
        
        # 8.6. Final validation: ensure source exists in contexts
        if answer.filename and answer.page > 0:
            source_found = False
            for ctx in reranked_contexts:
                if (ctx.get("filename", "").strip() == answer.filename and 
                    ctx.get("page", 0) == answer.page):
                    source_found = True
                    break
            if not source_found:
                # Source not found, try to find best alternative
                logger.warning(f"Source not found in contexts: {answer.filename}, page {answer.page}, trying fallback")
                best_entry = _select_best_entry(reranked_contexts)
                if best_entry:
                    answer.filename = best_entry.get("filename", "").strip()
                    answer.page = best_entry.get("page", 0)
        
        # Add citation if not present
        if "引用：" not in answer.answer:
            citation_text, _ = _build_citation_text(reranked_contexts[:MAX_CITATIONS])
            if citation_text:
                answer.answer = f"{answer.answer.strip()}\n\n{citation_text}"
        
        logger.debug(
            f"Query completed: filename='{answer.filename}', page={answer.page}"
        )
        
    except Exception as e:
        logger.error(f"Error in query: {e}", exc_info=True)
        # Robust recovery: try to provide best available answer from contexts
        answer = _recover_from_error(answer, reranked_contexts, question, e)
    
    return answer


def _recover_from_error(
    answer: Answer,
    contexts: List[Dict[str, Any]],
    question: str,
    error: Exception,
) -> Answer:
    """
    Attempt to recover from an error by using available context data.
    This ensures we still return meaningful results when possible.
    """
    logger.warning(f"Attempting recovery from error: {type(error).__name__}")
    
    # If we have contexts, try to extract source info at minimum
    if contexts:
        # Assign labels if not present
        for idx, entry in enumerate(contexts, 1):
            if "label" not in entry:
                entry["label"] = idx
        
        # Try to get best source
        best_entry = _select_best_entry(contexts)
        if best_entry:
            answer.filename = best_entry.get("filename", "")
            answer.page = best_entry.get("page", 0)
            
            # Generate a simple answer from the best context content
            content = best_entry.get("content", "")
            if content:
                # Truncate content to reasonable length for answer
                truncated_content = content[:500]
                answer.answer = f"根据检索到的文档信息：{truncated_content}..."
                
                # Add citation
                citation_text, _ = _build_citation_text(contexts[:MAX_CITATIONS])
                if citation_text:
                    answer.answer = f"{answer.answer}\n\n{citation_text}"
                
                logger.info(f"Recovery successful: filename='{answer.filename}', page={answer.page}")
                return answer
    
    # If recovery failed, provide a generic message without exposing internal errors
    answer.answer = "抱歉，处理您的问题时遇到了一些困难，请稍后重试。"
    logger.warning("Recovery failed, returning generic error message")
    return answer


def _retrieve_from_pages(
    client,
    question: str,
    question_embedding: List[float],
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant pages from page-level index.
    """
    all_hits = []
    
    # Try hybrid search on pages
    try:
        page_request = _build_page_hybrid_request(question, question_embedding, PAGE_TOP_K)
        success, hits = _safe_search(client, PAGE_TABLE_NAME, page_request)
        if success and hits:
            all_hits.extend(hits)
    except Exception as e:
        logger.warning(f"Page hybrid search failed: {e}")
    
    # FTS fallback on pages
    if len(all_hits) < PAGE_TOP_K:
        try:
            fts_request = _build_page_fts_request(question, PAGE_TOP_K)
            success, hits = _safe_search(client, PAGE_TABLE_NAME, fts_request)
            if success and hits:
                all_hits = _unique_merge(all_hits, hits, "page_id")
        except Exception as e:
            logger.debug(f"Page FTS fallback failed: {e}")
    
    return all_hits[:PAGE_TOP_K]


def _retrieve_from_chunks(
    client,
    question: str,
    question_embedding: List[float],
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chunks from chunk-level index.
    """
    all_hits = []
    
    # Hybrid search on chunks
    try:
        chunk_request = _build_hybrid_request(question, question_embedding, CHUNK_TOP_K)
        success, hits = _safe_search(client, TABLE_NAME, chunk_request)
        if success and hits:
            all_hits.extend(hits)
    except Exception as e:
        logger.warning(f"Chunk hybrid search failed: {e}")
    
    # Fallbacks
    all_hits = _augment_with_fallbacks(
        client=client,
        question=question,
        question_embedding=question_embedding,
        hits=all_hits,
        top_k=CHUNK_TOP_K,
    )
    
    return all_hits[:CHUNK_TOP_K]


def _merge_retrieval_results(
    page_hits: List[Dict[str, Any]],
    chunk_hits: List[Dict[str, Any]],
    question: str,
) -> List[Dict[str, Any]]:
    """
    Merge page-level and chunk-level results, prioritizing page-level for source accuracy.
    """
    contexts = []
    seen_keys = set()  # (filename, page) combinations
    
    # First, add page-level results (more reliable for page attribution)
    for hit in page_hits:
        record = _extract_page_record(hit)
        filename = record.get("filename", "").strip()
        page = _safe_int(record.get("page"))
        
        # Use summary or full_text as content
        content = record.get("summary", "") or record.get("full_text", "")
        if not content.strip():
            continue
        
        key = (filename, page)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        score = _extract_score(hit)
        text_match = _text_similarity(question, content)
        
        # Page-level sources get higher weight for better page matching (30 points)
        contexts.append({
            "content": content.strip()[:4000],
            "filename": filename,
            "page": page,
            "score": score,
            "text_match": text_match,
            "combined_score": score + 0.35 * text_match,  # Increased weight for page-level
            "source": "page",  # Mark source type
        })
    
    # Then, add chunk-level results
    for hit in chunk_hits:
        record = _extract_record_fields(hit)
        content = record.get("content", "").strip()
        if not content:
            continue
        
        filename = record.get("filename", "").strip()
        page = _safe_int(record.get("page"))
        
        key = (filename, page)
        # Allow chunks from same page if they add different content
        source_id = record.get("source_id", "")
        chunk_key = (filename, page, source_id)
        
        if chunk_key in seen_keys:
            continue
        
        # If we already have a page entry for this (filename, page),
        # only add chunk if it provides significantly different content
        if key in seen_keys:
            # Check if content is substantially different
            existing = [c for c in contexts if c["filename"] == filename and c["page"] == page]
            if existing:
                existing_content = existing[0].get("content", "")
                overlap = SequenceMatcher(None, content[:500], existing_content[:500]).ratio()
                if overlap > 0.7:  # Skip if too similar
                    continue
        
        seen_keys.add(chunk_key)
        
        score = _extract_score(hit)
        text_match = _text_similarity(question, content)
        
        contexts.append({
            "content": content[:4000],
            "filename": filename,
            "page": page,
            "score": score,
            "text_match": text_match,
            "combined_score": score + 0.3 * text_match,  # Reduced text_match weight
            "source": "chunk",
        })
    
    # Assign original indices for stable sorting
    for idx, entry in enumerate(contexts):
        entry["_original_idx"] = idx
    
    # Sort by combined score (use pre-assigned index for stability)
    contexts.sort(
        key=lambda x: (x["combined_score"], x["score"], -x.get("_original_idx", 0)),
        reverse=True,
    )
    
    return contexts


def _extract_page_record(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields from page-level search result."""
    if not isinstance(result, dict):
        return {}
    
    record = {}
    source = result.get("_source")
    if isinstance(source, dict):
        record.update(source)
    else:
        record.update(result)
    
    record.setdefault("page_id", result.get("_id"))
    return record


def _build_page_hybrid_request(
    question: str,
    embedding: List[float],
    top_k: int,
) -> Dict[str, Any]:
    """Build hybrid search request for page-level index."""
    fts_query = {
        "bool": {
            "should": [
                {
                    "query_string": {
                        "fields": ["summary^3", "full_text"],  # Increased summary weight
                        "type": "best_fields",
                        "query": question,
                        "default_operator": "or",
                        "minimum_should_match": "25%",  # More relaxed for better recall
                    }
                }
            ]
        }
    }
    
    knn_block = {
        "field": "vector",
        "k": top_k * 3,  # Increased for better recall
        "num_candidates": top_k * 6,  # Increased candidate pool
        "query_vector": embedding,
        "similarity": 0.15,  # Lower threshold for more candidates
    }
    
    return {
        "query": fts_query,
        "knn": knn_block,
        "from": 0,
        "size": top_k,
    }


def _build_page_fts_request(question: str, top_k: int) -> Dict[str, Any]:
    """Build FTS-only request for page-level index."""
    query = {
        "bool": {
            "should": [
                {
                    "query_string": {
                        "fields": ["summary^3", "full_text"],  # Increased summary weight
                        "type": "best_fields",
                        "query": question,
                        "default_operator": "or",
                    }
                }
            ]
        }
    }
    return {"query": query, "from": 0, "size": top_k}


def _parse_llm_response(response: str) -> Tuple[str, Optional[int]]:
    """
    Parse LLM response to extract the answer and the primary cited label.
    Enhanced to prioritize end citations which are more reliable.
    """
    primary_label = None
    
    # Strategy 1: Check for explicit citation at end (highest priority - most reliable)
    # Pattern: 引用：[编号]（文件名，第X页）
    end_citation_patterns = [
        r'引用[：:]\s*\[(\d+)\]',  # 引用：[3]
        r'引用[：:]\s*\[(\d+)\]\s*[（(]',  # 引用：[3]（
        r'主要来源[：:]\s*\[(\d+)\]',  # 主要来源：[3]
        r'来源[：:]\s*\[(\d+)\]',  # 来源：[3]
    ]
    
    for pattern in end_citation_patterns:
        match = re.search(pattern, response)
        if match:
            try:
                primary_label = int(match.group(1))
                logger.debug(f"Extracted citation label from end: {primary_label}")
                break
            except ValueError:
                continue
    
    # Strategy 2: Find all citation patterns and use the last one (likely the main citation)
    if primary_label is None:
        citation_pattern = r'\[(\d+)\]'
        matches = re.findall(citation_pattern, response)
        if matches:
            try:
                # Use the last citation as it's likely the main one
                primary_label = int(matches[-1])
                logger.debug(f"Extracted citation label from last match: {primary_label}")
            except ValueError:
                pass
    
    # Strategy 3: Use first citation if no end citation found
    if primary_label is None:
        citation_pattern = r'\[(\d+)\]'
        matches = re.findall(citation_pattern, response)
        if matches:
            try:
                primary_label = int(matches[0])
                logger.debug(f"Extracted citation label from first match: {primary_label}")
            except ValueError:
                pass
    
    return response, primary_label


def _determine_best_source(
    context_entries: List[Dict[str, Any]],
    cited_label: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    Determine the best source entry based on LLM's citation.
    Enhanced logic to ensure we always return a valid source if available.
    Strongly prioritizes page-level sources for more accurate page attribution (critical for 30 points).
    """
    # 1. First try to find by LLM's cited label, prioritizing page-level
    if cited_label is not None:
        # First check page-level entries with this label
        for entry in context_entries:
            if entry.get("label") == cited_label and entry.get("source") == "page":
                filename = entry.get("filename", "").strip()
                page = entry.get("page", 0)
                if filename and page > 0:
                    logger.debug(f"Found page-level source by cited label {cited_label}: {filename}, page {page}")
                    return entry
        # Then check any entry with this label
        for entry in context_entries:
            if entry.get("label") == cited_label:
                filename = entry.get("filename", "").strip()
                page = entry.get("page", 0)
                if filename and page > 0:
                    logger.debug(f"Found source by cited label {cited_label}: {filename}, page {page}")
                    return entry
    
    # 2. Fallback: use highest adjusted score with valid source
    # Strongly prioritize page-level sources for better page matching (30 points)
    valid_entries = [
        e for e in context_entries 
        if e.get("filename", "").strip() and e.get("page", 0) > 0
    ]
    
    if valid_entries:
        # Separate page-level and chunk-level entries
        page_entries = [e for e in valid_entries if e.get("source") == "page"]
        chunk_entries = [e for e in valid_entries if e.get("source") != "page"]
        
        # Strongly prefer page-level sources (they have more reliable page attribution)
        if page_entries:
            def get_adjusted_score(entry: Dict[str, Any]) -> float:
                base_score = entry.get("rerank_score", 0) or entry.get("combined_score", 0)
                # Page-level sources get 0.25 bonus (increased from 0.15)
                return base_score + 0.25
            
            page_entries.sort(key=get_adjusted_score, reverse=True)
            logger.debug(f"Selected page-level source: {page_entries[0].get('filename')}, page {page_entries[0].get('page')}")
            return page_entries[0]
        
        # Fallback to chunk-level if no page-level available
        if chunk_entries:
            def get_adjusted_score(entry: Dict[str, Any]) -> float:
                return entry.get("rerank_score", 0) or entry.get("combined_score", 0)
            
            chunk_entries.sort(key=get_adjusted_score, reverse=True)
            logger.debug(f"Selected chunk-level source: {chunk_entries[0].get('filename')}, page {chunk_entries[0].get('page')}")
            return chunk_entries[0]
    
    # 3. Last resort: return first entry with any filename
    for entry in context_entries:
        if entry.get("filename", "").strip():
            return entry
    
    return None


def _augment_with_fallbacks(
    client,
    question: str,
    question_embedding: List[float],
    hits: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Merge results with FTS/vector fallbacks."""
    current_hits = list(hits or [])
    
    # Tight FTS
    success, fts_hits = _safe_search(
        client, TABLE_NAME, _build_fts_only_request(question, top_k, tight=True)
    )
    if success and fts_hits:
        current_hits = _unique_merge(current_hits, fts_hits, "source_id")
    
    # Loose FTS
    if len(current_hits) < top_k:
        success, loose_hits = _safe_search(
            client, TABLE_NAME, _build_fts_only_request(question, top_k * 2, tight=False)
        )
        if success and loose_hits:
            current_hits = _unique_merge(current_hits, loose_hits, "source_id")
    
    # Vector-only fallback
    if len(current_hits) < top_k:
        success, vector_hits = _safe_search(
            client, TABLE_NAME, _build_vector_fallback_request(question_embedding, top_k)
        )
        if success and vector_hits:
            current_hits = _unique_merge(current_hits, vector_hits, "source_id")
    
    return current_hits[:top_k]


def _unique_merge(
    base: List[Dict[str, Any]],
    extra: List[Dict[str, Any]],
    id_key: str = "source_id",
) -> List[Dict[str, Any]]:
    """Merge two lists of hits, avoiding duplicates."""
    seen = set()
    for item in base:
        key = str(item.get("_id") or item.get(id_key) or "")
        if key:
            seen.add(key)
    
    merged = list(base)
    for item in extra:
        key = str(item.get("_id") or item.get(id_key) or "")
        if key and key not in seen:
            seen.add(key)
            merged.append(item)
    
    return merged


def _build_hybrid_request(
    question: str, embedding: List[float], top_k: int
) -> Dict[str, Any]:
    """Construct hybrid search payload for chunk index."""
    # Use more relaxed FTS for better recall
    fts_query = _default_fts_query(question, minimum_should_match="30%")
    knn_filter = _default_fts_query(question, minimum_should_match="20%")
    
    knn_block = {
        "field": "vector",
        "k": top_k * 3,  # Increased for better recall
        "num_candidates": top_k * 8,  # Increased candidate pool
        "query_vector": embedding,
        "similarity": 0.20,  # Lower threshold for more candidates
        "filter": knn_filter,
    }
    
    return {
        "query": fts_query,
        "knn": knn_block,
        "from": 0,
        "size": top_k,
    }


def _build_vector_fallback_request(
    embedding: List[float], top_k: int
) -> Dict[str, Any]:
    """Vector-only fallback payload."""
    knn_block = {
        "field": "vector",
        "k": top_k * 4,  # Increased for fallback scenarios
        "num_candidates": top_k * 10,  # Large candidate pool
        "query_vector": embedding,
        "similarity": 0.10,  # Very relaxed for fallback
    }
    return {
        "query": {"match_all": {}},
        "knn": knn_block,
        "from": 0,
        "size": top_k,
    }


def _build_fts_only_request(
    question: str, top_k: int, tight: bool = True
) -> Dict[str, Any]:
    """Pure FTS fallback."""
    if tight:
        query = _default_fts_query(question, minimum_should_match="30%")  # More relaxed
    else:
        query = _default_fts_query(
            question, minimum_should_match=None, default_operator="or"
        )
    return {"query": query, "from": 0, "size": top_k * 2}  # Return more results


def _safe_search(
    client, table_name: str, body: Dict[str, Any]
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Run search with error handling."""
    try:
        results = client.search(index=table_name, body=body)
        return True, _extract_hits(results)
    except Exception as exc:
        if _is_not_supported_error(exc):
            logger.warning("Search not supported: %s", exc)
            return False, []
        # For table not exists error, just return empty
        if "doesn't exist" in str(exc).lower() or "1146" in str(exc):
            logger.debug(f"Table {table_name} may not exist: {exc}")
            return False, []
        raise


def _is_not_supported_error(exc: Exception) -> bool:
    """Detect unsupported query errors."""
    text = str(exc).lower()
    return "not supported" in text or "1235" in text


def _extract_hits(search_results: Any) -> List[Dict[str, Any]]:
    """Normalize search results to list of dicts."""
    if isinstance(search_results, list):
        return [hit for hit in search_results if isinstance(hit, dict)]
    
    if isinstance(search_results, dict):
        hits_section = search_results.get("hits")
        candidates = []
        if isinstance(hits_section, dict):
            candidates.append(hits_section.get("hits"))
        for key in ("data", "results", "rows"):
            if isinstance(search_results.get(key), list):
                candidates.append(search_results.get(key))
        
        for candidate in candidates:
            if isinstance(candidate, list):
                normalized = [hit for hit in candidate if isinstance(hit, dict)]
                if normalized:
                    return normalized
        
        if "content" in search_results or "summary" in search_results:
            return [search_results]
    
    return []


def _extract_record_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten hit payload to dict with useful fields."""
    if not isinstance(result, dict):
        return {}
    
    record = {}
    source = result.get("_source")
    if isinstance(source, dict):
        record.update(source)
    else:
        record.update(result)
    
    highlight = result.get("highlight")
    if isinstance(highlight, dict):
        hl_content = highlight.get("content")
        if isinstance(hl_content, list) and hl_content:
            record["content"] = " ... ".join(
                s.strip() for s in hl_content if s.strip()
            )
    
    record.setdefault("source_id", result.get("_id"))
    return record


def _extract_score(result: Dict[str, Any]) -> float:
    """Extract ranking score from result."""
    for key in ("_score", "score", "vector_score", "bm25_score"):
        value = result.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return 0.0


def _format_context_text(context_entries: List[Dict[str, Any]]) -> str:
    """Format contexts for LLM prompt."""
    blocks = []
    for entry in context_entries:
        label = entry.get("label", "?")
        filename = entry.get("filename") or "未知文件"
        page = entry.get("page") or "未知"
        header = f"[{label}] 文件：{filename}；页码：{page}"
        blocks.append(f"{header}\n{entry.get('content', '')}")
    return "\n\n".join(blocks)


def _select_best_entry(
    context_entries: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Pick highest quality entry with valid source info.
    Prioritizes page-level sources for more accurate page attribution.
    """
    if not context_entries:
        return None
    
    # Collect all valid entries with filename and page
    valid_entries = []
    
    for entry in context_entries:
        filename = entry.get("filename", "").strip()
        page = entry.get("page", 0)
        if filename and page > 0:
            valid_entries.append(entry)
    
    if valid_entries:
        # Separate page-level and chunk-level entries
        page_entries = [e for e in valid_entries if e.get("source") == "page"]
        chunk_entries = [e for e in valid_entries if e.get("source") != "page"]
        
        # Strongly prefer page-level sources (they have more reliable page attribution)
        if page_entries:
            def get_adjusted_score(entry: Dict[str, Any]) -> float:
                base_score = entry.get("rerank_score", 0) or entry.get("combined_score", 0)
                # Page-level sources get 0.25 bonus (increased from 0.15)
                return base_score + 0.25
            
            page_entries.sort(key=get_adjusted_score, reverse=True)
            return page_entries[0]
        
        # Fallback to chunk-level if no page-level available
        if chunk_entries:
            def get_adjusted_score(entry: Dict[str, Any]) -> float:
                return entry.get("rerank_score", 0) or entry.get("combined_score", 0)
            
            chunk_entries.sort(key=get_adjusted_score, reverse=True)
            return chunk_entries[0]
    
    # Last resort: return first entry with any filename
    for entry in context_entries:
        if entry.get("filename", "").strip():
            return entry
    
    return context_entries[0] if context_entries else None


def _safe_int(value: Any) -> int:
    """Convert to int, return 0 on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _text_similarity(question: str, content: str) -> float:
    """
    Compute text similarity using keyword overlap (better for Chinese).
    Combines character-level matching with keyword overlap.
    """
    if not question or not content:
        return 0.0
    
    try:
        snippet = content[:1000]
        
        # 1. Basic sequence matching (lower weight)
        seq_ratio = SequenceMatcher(None, question[:200], snippet[:500]).ratio()
        
        # 2. Character/keyword overlap (higher weight for Chinese)
        q_chars = set(question.replace(" ", ""))
        c_chars = set(snippet.replace(" ", ""))
        if q_chars:
            char_overlap = len(q_chars & c_chars) / len(q_chars)
        else:
            char_overlap = 0.0
        
        # 3. Check for exact phrase matches (bonus)
        # Extract key terms from question (simple approach)
        key_terms = [term for term in question.split() if len(term) >= 2]
        exact_match_bonus = 0.0
        for term in key_terms[:5]:  # Check first 5 key terms
            if term in snippet:
                exact_match_bonus += 0.05
        exact_match_bonus = min(exact_match_bonus, 0.2)  # Cap at 0.2
        
        # Combine scores with adjusted weights
        combined = 0.3 * seq_ratio + 0.5 * char_overlap + exact_match_bonus
        return min(1.0, combined)
    except Exception:
        return 0.0


def _build_citation_text(
    context_entries: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Generate citation string for answer."""
    citations = []
    valid_entries = []
    seen_keys = set()
    
    for entry in context_entries:
        label = entry.get("label")
        filename = (entry.get("filename") or "").strip()
        page = entry.get("page")
        
        if label is None or not filename:
            continue
        
        key = (filename, page)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        valid_entries.append(entry)
        display_page = page if page not in (None, "", 0) else "未知"
        citations.append(f"[{label}]（{filename}，第{display_page}页）")
    
    if not citations:
        return "", valid_entries
    
    return f"引用：{'；'.join(citations)}", valid_entries


def _default_fts_query(
    question: str,
    minimum_should_match: Optional[str] = "40%",
    default_operator: str = "and",
) -> Dict[str, Any]:
    """Create reusable FTS bool query for content field."""
    query_config: Dict[str, Any] = {
        "fields": ["content"],
        "type": "best_fields",
        "query": question,
        "default_operator": default_operator,
    }
    if minimum_should_match:
        query_config["minimum_should_match"] = minimum_should_match
    
    return {
        "bool": {
            "must": [{"query_string": query_config}]
        }
    }
