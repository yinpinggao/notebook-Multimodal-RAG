"""
CLIP image embedding utilities for multimodal retrieval.

Provides image embedding generation using OpenAI's CLIP-compatible embeddings API.
This module bridges the gap between the text-only embedding utilities and
the multimodal retrieval needs of the VRAG system.
"""

import logging
from typing import List, Optional

from open_notebook.ai.key_provider import get_api_key

logger = logging.getLogger(__name__)

DEFAULT_CLIP_MODEL = "clip-ViT-L-14"
FALLBACK_TEXT_MODEL = "text-embedding-3-large"
DEFAULT_EMBEDDING_DIM = 768


def _create_openai_client(api_key: Optional[str] = None):
    """Create an OpenAI client for CLIP embeddings.

    Args:
        api_key: OpenAI API key. If None, will try to get from key provider.

    Returns:
        OpenAI client instance.
    """
    try:
        import openai
    except ImportError:
        raise ImportError(
            "OpenAI client library required for CLIP embeddings. "
            "Install with: pip install openai"
        )

    if api_key is None:
        # Try to get key from key provider (database or env var)
        try:
            import asyncio
            api_key = asyncio.get_event_loop().run_until_complete(
                get_api_key("openai")
            )
        except Exception:
            pass

    if api_key is None:
        # Let OpenAI client raise the error with clear message
        return openai.OpenAI(api_key=None)

    return openai.OpenAI(api_key=api_key)


async def get_clip_api_key() -> Optional[str]:
    """Get OpenAI API key for CLIP embeddings.

    Returns:
        OpenAI API key from database credentials or environment.
    """
    return await get_api_key("openai")


def embed_image(image_base64: str, model: str = DEFAULT_CLIP_MODEL) -> List[float]:
    """Embed an image using CLIP model.

    Args:
        image_base64: Base64-encoded image data (without data URI prefix).
        model: CLIP model name (default: clip-ViT-L-14).

    Returns:
        Embedding vector as list of floats.

    Raises:
        RuntimeError: If no API key is available.
    """
    import openai

    try:
        client = _create_openai_client()
    except openai.OpenAIError:
        raise RuntimeError(
            "No API key available for image embedding. "
            "Configure an embedding model in Settings → Models, "
            "or set OPENAI_API_KEY environment variable."
        )
    try:
        response = client.embeddings.create(
            model=model,
            input=[{
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            }],
        )
        return response.data[0].embedding
    except openai.OpenAIError:
        raise RuntimeError(
            "No API key available for image embedding. "
            "Configure an embedding model in Settings → Models, "
            "or set OPENAI_API_KEY environment variable."
        )


def embed_text(text: str, model: str = DEFAULT_CLIP_MODEL) -> List[float]:
    """Embed a text query using CLIP text encoder.

    Args:
        text: Text query string.
        model: Model name (default: clip-ViT-L-14).

    Returns:
        Embedding vector as list of floats.

    Raises:
        RuntimeError: If no API key is available and no fallback works.
    """
    import openai

    try:
        client = _create_openai_client()
    except openai.OpenAIError:
        raise RuntimeError(
            "No API key available for text embedding. "
            "Configure an embedding model in Settings → Models, "
            "or set OPENAI_API_KEY environment variable."
        )
    try:
        response = client.embeddings.create(model=model, input=text)
        return response.data[0].embedding
    except openai.OpenAIError as e:
        # Catch all OpenAI errors including OpenAIError, APIError, AuthenticationError
        logger.warning(
            f"Embedding failed with model {model}: {e}"
        )
        try:
            response = client.embeddings.create(model=FALLBACK_TEXT_MODEL, input=text)
            return response.data[0].embedding
        except openai.OpenAIError:
            raise RuntimeError(
                "No API key available for text embedding. "
                "Configure an embedding model in Settings → Models, "
                "or set OPENAI_API_KEY environment variable."
            )


def embed_images_batch(
    images_base64: List[str], model: str = DEFAULT_CLIP_MODEL
) -> List[List[float]]:
    """Embed multiple images in a batch.

    Args:
        images_base64: List of base64-encoded images.
        model: CLIP model name.

    Returns:
        List of embedding vectors.
    """
    import openai

    if not images_base64:
        return []

    try:
        client = _create_openai_client()
    except openai.OpenAIError:
        raise RuntimeError(
            "No API key available for image embedding. "
            "Configure an embedding model in Settings → Models, "
            "or set OPENAI_API_KEY environment variable."
        )
    try:
        response = client.embeddings.create(
            model=model,
            input=[
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}
                for img in images_base64
            ],
        )
        return [item.embedding for item in response.data]
    except openai.OpenAIError:
        raise RuntimeError(
            "No API key available for image embedding. "
            "Configure an embedding model in Settings → Models, "
            "or set OPENAI_API_KEY environment variable."
        )
