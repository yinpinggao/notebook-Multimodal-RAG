"""
Connection testing for supported providers and model configs.
"""

import io
import struct
from typing import Optional, Tuple

import httpx
from loguru import logger

from open_notebook.ai.key_provider import get_provider_runtime_config
from open_notebook.ai.provider_catalog import (
    get_provider_catalog_entry,
    get_provider_ids,
)
from open_notebook.ai.provider_runtime import create_runtime_model, get_models_endpoint
from open_notebook.domain.credential import Credential

TEST_MODELS = {
    provider: entry.test_model
    for provider, entry in ((provider_id, get_provider_catalog_entry(provider_id)) for provider_id in get_provider_ids())
}


async def _test_ollama_connection(base_url: str) -> Tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                count = len(models)
                if count > 0:
                    names = ", ".join(m.get("name", "unknown") for m in models[:3])
                    if count > 3:
                        names += f" (+{count - 3} more)"
                    return True, f"Connected. {count} models available: {names}"
                return True, "Connected successfully (no models listed)"
            return False, f"Server returned status {response.status_code}"
    except httpx.ConnectError:
        return False, "Cannot connect to Ollama. Check if Ollama server is running."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check if Ollama server is accessible."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"


async def _test_models_endpoint(provider: str, config: dict) -> Tuple[bool, str]:
    url = get_models_endpoint(provider, config)
    if not url:
        return False, "No models endpoint configured"

    headers = {}
    api_key = config.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                count = len(models)
                if count > 0:
                    names = ", ".join(m.get("id", "unknown") for m in models[:3])
                    if count > 3:
                        names += f" (+{count - 3} more)"
                    return True, f"Connected. {count} models available: {names}"
                return True, "Connected successfully (no models listed)"
            if response.status_code == 401:
                return False, "Invalid API key"
            if response.status_code == 403:
                return False, "API key lacks required permissions"
            return False, f"Server returned status {response.status_code}"
    except httpx.ConnectError:
        return False, "Cannot connect to server. Check the base URL."
    except httpx.TimeoutException:
        return False, "Connection timed out. Check network or endpoint."
    except Exception as e:
        return False, f"Connection error: {str(e)[:100]}"


def _normalize_error_message(error_msg: str) -> Tuple[bool, str]:
    lower = error_msg.lower()
    if "401" in error_msg or "unauthorized" in lower:
        return False, "Invalid API key"
    if "403" in error_msg or "forbidden" in lower:
        return False, "API key lacks required permissions"
    if "rate" in lower and "limit" in lower:
        return True, "Rate limited - but connection works"
    if "not found" in lower and "model" in lower:
        return True, "API key valid (test model not available)"
    if "connection" in lower or "network" in lower:
        return False, "Connection error - check network/endpoint"
    if "timeout" in lower:
        return False, "Connection timed out - check network/endpoint"
    return False, error_msg


async def test_provider_connection(
    provider: str, model_type: str = "language", config_id: Optional[str] = None
) -> Tuple[bool, str]:
    provider_entry = get_provider_catalog_entry(provider)
    config: dict = {}

    if config_id:
        try:
            cred = await Credential.get(config_id)
            config = cred.to_runtime_config()
        except Exception:
            return False, f"Credential not found: {config_id}"
    else:
        config = await get_provider_runtime_config(provider)

    if provider_entry.id == "ollama":
        return await _test_ollama_connection(
            str(config.get("base_url") or provider_entry.default_base_url or "http://localhost:11434")
        )

    success, message = await _test_models_endpoint(provider_entry.id, config)
    if success:
        return success, message

    test_model = TEST_MODELS.get(provider_entry.id)
    if not test_model:
        return False, message

    model_name, test_model_type = test_model
    if not model_name:
        return False, message

    try:
        model = create_runtime_model(
            provider=provider_entry.id,
            model_name=model_name,
            model_type=test_model_type or model_type,
            config=config,
        )
        if (test_model_type or model_type) == "language":
            response = await model.achat_complete(messages=[{"role": "user", "content": "Hi"}])
            _ = response.content if hasattr(response, "content") else response
            return True, "Connection successful"
        if (test_model_type or model_type) == "embedding":
            await model.aembed(["test"])
            return True, "Connection successful"
        if (test_model_type or model_type) == "text_to_speech":
            return True, "Connection successful (model created)"
    except Exception as e:
        success, normalized = _normalize_error_message(str(e))
        if success:
            return True, normalized
        logger.debug(f"Test connection error for {provider}: {e}")
        return False, normalized[:120]

    return False, message


DEFAULT_TEST_VOICES = {
    "tongyi": "Cherry",
    "wenxin": "Kore",
    "doubao": "zh_male_M392_conversation_wvae_bigtts",
    "spark": "x4_xiaoyan",
    "zhipu": "alloy",
    "ollama": "alloy",
}


def _generate_test_wav() -> io.BytesIO:
    sample_rate = 16000
    num_samples = sample_rate // 2
    bits_per_sample = 16
    num_channels = 1
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", bits_per_sample))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)
    buf.seek(0)
    buf.name = "test.wav"
    return buf


async def test_individual_model(model) -> Tuple[bool, str]:
    from open_notebook.ai.models import ModelManager

    try:
        manager = ModelManager()
        esp_model = await manager.get_model(model.id)
        if esp_model is None:
            return False, "Could not create model instance"

        if model.type == "language":
            response = await esp_model.achat_complete(
                messages=[{"role": "user", "content": "Hi!"}]
            )
            text = response.content[:100] if getattr(response, "content", None) else "(empty response)"
            return True, f"Response: {text}"

        if model.type == "embedding":
            result = await esp_model.aembed(["This is a test."])
            if result and len(result) > 0:
                return True, f"Embedding dimensions: {len(result[0])}"
            return True, "Embedding successful"

        if model.type == "text_to_speech":
            voice = DEFAULT_TEST_VOICES.get(model.provider, "alloy")
            result = await esp_model.agenerate_speech(
                text="Hello from Open Notebook", voice=voice
            )
            if result and hasattr(result, "content"):
                return True, f"Audio generated: {len(result.content)} bytes"
            return True, "Speech generation successful"

        if model.type == "speech_to_text":
            audio_file = _generate_test_wav()
            result = await esp_model.atranscribe(audio_file=audio_file, language="en")
            text = str(result.text) if hasattr(result, "text") else str(result)
            return True, f"Transcription: {text[:100]}"

        return False, f"Unsupported model type: {model.type}"
    except Exception as e:
        success, normalized = _normalize_error_message(str(e))
        if success:
            return True, normalized
        logger.debug(f"Test individual model error for {model.id}: {e}")
        return False, normalized
