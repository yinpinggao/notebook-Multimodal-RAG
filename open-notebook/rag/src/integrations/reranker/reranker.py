"""
Reranker module for improving search result relevance.
Uses Alibaba Cloud DashScope's text-rerank model.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import dotenv
from openai import APIConnectionError, APIError, OpenAI, RateLimitError

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
)

# Initialize OpenAI client for reranking
rerank_client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


def rerank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    content_key: str = "content",
    top_k: Optional[int] = None,
    model: str = "gte-rerank",
    max_retries: int = 3,
    initial_backoff: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Rerank documents based on their relevance to the query.
    
    This function uses a cross-encoder style reranking model to re-score
    and reorder the documents based on their semantic relevance to the query.
    
    Args:
        query: The search query
        documents: List of document dictionaries to rerank
        content_key: Key to access document content (default: "content")
        top_k: Number of top documents to return (default: return all)
        model: Reranking model to use (default: "gte-rerank")
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        
    Returns:
        Reranked list of documents with added 'rerank_score' field
    """
    if not documents:
        return []
    
    if len(documents) == 1:
        documents[0]["rerank_score"] = 1.0
        return documents
    
    # Extract document contents
    doc_contents = []
    valid_indices = []
    for i, doc in enumerate(documents):
        content = doc.get(content_key, "")
        if content and isinstance(content, str) and content.strip():
            doc_contents.append(content.strip()[:2000])  # Limit content length
            valid_indices.append(i)
    
    if not doc_contents:
        logger.warning("No valid document contents found for reranking")
        return documents
    
    # Try using the rerank API
    rerank_scores = _call_rerank_api(
        query=query,
        documents=doc_contents,
        model=model,
        max_retries=max_retries,
        initial_backoff=initial_backoff,
    )
    
    if rerank_scores is None:
        # Fallback: use LLM-based scoring if rerank API fails
        logger.warning("Rerank API failed, falling back to LLM-based scoring")
        rerank_scores = _llm_based_rerank(query, doc_contents)
    
    # Assign scores to documents
    for idx, score in zip(valid_indices, rerank_scores):
        documents[idx]["rerank_score"] = score
    
    # Assign 0 score to documents without valid content
    for i, doc in enumerate(documents):
        if "rerank_score" not in doc:
            doc["rerank_score"] = 0.0
    
    # Sort by rerank score with page-level bonus
    # Page-level sources are more reliable for page matching (30 points)
    def get_final_score(doc: Dict[str, Any]) -> float:
        base_score = doc.get("rerank_score", 0.0)
        # Give page-level sources a bonus for better page accuracy
        if doc.get("source") == "page":
            base_score += 0.12  # Bonus for page-level sources
        return base_score
    
    sorted_docs = sorted(
        documents,
        key=get_final_score,
        reverse=True,
    )
    
    if top_k is not None and top_k > 0:
        sorted_docs = sorted_docs[:top_k]
    
    return sorted_docs


def _call_rerank_api(
    query: str,
    documents: List[str],
    model: str = "gte-rerank",
    max_retries: int = 3,
    initial_backoff: float = 1.0,
) -> Optional[List[float]]:
    """
    Call the rerank API to get relevance scores.
    
    Returns:
        List of relevance scores, or None if the API call fails
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Construct rerank request using chat completion API
            # Format: ask model to score document relevance
            prompt = _build_rerank_prompt(query, documents)
            
            response = rerank_client.chat.completions.create(
                model="qwen-plus",  # Use qwen-plus for scoring
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的文档相关性评估专家。请根据查询对文档进行相关性评分。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=60.0,
            )
            
            if response.choices and response.choices[0].message.content:
                scores = _parse_rerank_scores(
                    response.choices[0].message.content, 
                    len(documents)
                )
                if scores:
                    return scores
            
            logger.warning("Failed to parse rerank scores from response")
            return None
            
        except RateLimitError as e:
            last_exception = e
            if attempt < max_retries:
                backoff_time = initial_backoff * (2 ** attempt)
                logger.warning(
                    f"Rate limit exceeded. Retrying in {backoff_time:.2f}s... "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(backoff_time)
            
        except APIConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                backoff_time = initial_backoff * (2 ** attempt)
                logger.warning(
                    f"Connection error. Retrying in {backoff_time:.2f}s... "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(backoff_time)
            
        except APIError as e:
            last_exception = e
            status_code = getattr(e, "status_code", None)
            if status_code and 500 <= status_code < 600:
                if attempt < max_retries:
                    backoff_time = initial_backoff * (2 ** attempt)
                    logger.warning(
                        f"Server error. Retrying in {backoff_time:.2f}s... "
                        f"(attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(backoff_time)
            else:
                logger.error(f"Rerank API error: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error in rerank: {e}")
            return None
    
    if last_exception:
        logger.error(f"Rerank failed after {max_retries + 1} attempts: {last_exception}")
    
    return None


def _build_rerank_prompt(query: str, documents: List[str]) -> str:
    """Build a prompt for LLM-based reranking."""
    doc_list = []
    for i, doc in enumerate(documents):
        # Truncate long documents (increased to 1000 for better context)
        truncated = doc[:1000] if len(doc) > 1000 else doc
        doc_list.append(f"[文档{i+1}]: {truncated}")
    
    docs_text = "\n\n".join(doc_list)
    
    prompt = f"""请评估以下文档与查询的相关性，并为每个文档打分（0.0-1.0）。

查询：{query}

文档列表：
{docs_text}

评分标准（请严格遵循）：
- 0.95-1.0: 完全相关，直接回答了查询，信息准确完整
- 0.85-0.94: 高度相关，包含查询所需的主要信息，能很好地回答问题
- 0.75-0.84: 高度相关，包含相关信息，能部分回答问题
- 0.65-0.74: 中等相关，部分相关但不完全匹配，需要推断
- 0.55-0.64: 中等相关，有一定关联但信息不够直接
- 0.45-0.54: 低相关，仅有少量相关信息
- 0.35-0.44: 低相关，关联性很弱
- 0.25-0.34: 几乎不相关，仅有极少量关联
- 0.15-0.24: 不相关，基本无关联
- 0.0-0.14: 完全不相关

评分原则：
1. 优先考虑是否能直接回答查询问题
2. 考虑信息的完整性和准确性
3. 考虑语义相关性和主题匹配度
4. 使用连续评分，避免极端值（除非确实完全相关或完全不相关）

请只输出评分结果，格式如：
文档1: 0.85
文档2: 0.32
..."""
    
    return prompt


def _parse_rerank_scores(response: str, num_docs: int) -> Optional[List[float]]:
    """Parse rerank scores from LLM response."""
    import re
    
    scores = []
    lines = response.strip().split("\n")
    
    for line in lines:
        # Match patterns like "文档1: 0.85" or "1: 0.85" or just "0.85"
        match = re.search(r"(\d+\.?\d*)\s*$", line.strip())
        if match:
            try:
                score = float(match.group(1))
                # Normalize if score > 1 (might be percentage)
                if score > 1.0:
                    score = score / 100.0
                score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                scores.append(score)
            except ValueError:
                continue
    
    # If we got the right number of scores, return them
    if len(scores) == num_docs:
        return scores
    
    # Try to extract all floating point numbers
    all_numbers = re.findall(r"0\.\d+|1\.0|1(?!\d)", response)
    if len(all_numbers) >= num_docs:
        scores = [float(n) for n in all_numbers[:num_docs]]
        return scores
    
    logger.warning(
        f"Expected {num_docs} scores, got {len(scores)}. Response: {response[:200]}"
    )
    return None


def _llm_based_rerank(query: str, documents: List[str]) -> List[float]:
    """
    Fallback: compute simple text overlap scores.
    """
    from difflib import SequenceMatcher
    
    scores = []
    query_lower = query.lower()
    
    for doc in documents:
        doc_lower = doc.lower()[:1000]
        
        # Combine multiple signals
        # 1. SequenceMatcher ratio
        seq_ratio = SequenceMatcher(None, query_lower, doc_lower).ratio()
        
        # 2. Keyword overlap
        query_words = set(query_lower.split())
        doc_words = set(doc_lower.split())
        if query_words:
            keyword_overlap = len(query_words & doc_words) / len(query_words)
        else:
            keyword_overlap = 0.0
        
        # 3. Contains check
        contains_bonus = 0.2 if query_lower in doc_lower else 0.0
        
        # Combine scores
        combined = 0.3 * seq_ratio + 0.5 * keyword_overlap + contains_bonus
        scores.append(min(1.0, combined))
    
    return scores


if __name__ == "__main__":
    # Test reranking
    test_query = "千味央厨的成立时间"
    test_docs = [
        {"content": "千味央厨成立于2012年4月，是一家专注于速冻面米制品的企业。"},
        {"content": "公司在2021年实现营收12.85亿元，同比增长25%。"},
        {"content": "千味央厨的创始人团队来自思念食品，于2012年创立公司。"},
    ]
    
    result = rerank_documents(test_query, test_docs)
    for doc in result:
        print(f"Score: {doc.get('rerank_score', 0):.3f} - {doc['content'][:50]}")


