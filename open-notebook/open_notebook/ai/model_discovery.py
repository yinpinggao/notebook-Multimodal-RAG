"""
Model discovery for the supported domestic provider catalog.
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger

from open_notebook.ai.key_provider import get_provider_runtime_config
from open_notebook.ai.models import Model
from open_notebook.ai.provider_catalog import (
    get_curated_models,
    get_provider_catalog_entry,
    get_provider_ids,
    normalize_provider,
)
from open_notebook.ai.provider_runtime import get_models_endpoint
from open_notebook.domain.credential import Credential


@dataclass
class DiscoveredModel:
    name: str
    provider: str
    model_type: str
    description: Optional[str] = None


MODEL_TYPE_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "tongyi": {
        "embedding": ("embedding", "embed"),
        "language": ("qwen", "qwq", "vl", "omni"),
    },
    "wenxin": {
        "embedding": ("embedding",),
        "language": ("ernie",),
    },
    "deepseek": {
        "language": ("deepseek",),
    },
    "doubao": {
        "text_to_speech": ("tts",),
        "speech_to_text": ("stt", "asr", "speech"),
        "embedding": ("embedding", "embed"),
        "language": ("doubao", "seed", "vision"),
    },
    "spark": {
        "text_to_speech": ("tts",),
        "speech_to_text": ("stt", "asr"),
        "embedding": ("embedding", "embed"),
        "language": ("spark", "general", "ultra"),
    },
    "kimi": {
        "language": ("kimi", "moonshot", "vision"),
    },
    "hunyuan": {
        "language": ("hunyuan", "vision"),
    },
    "zhipu": {
        "text_to_speech": ("tts", "cogtts"),
        "embedding": ("embedding", "embed"),
        "language": ("glm",),
    },
    "ollama": {
        "embedding": ("embed", "bge", "e5", "nomic", "mxbai"),
        "language": (
            "llama",
            "qwen",
            "deepseek",
            "gemma",
            "phi",
            "mistral",
            "mixtral",
            "vision",
            "vl",
        ),
    },
}


def classify_model_type(model_name: str, provider: str) -> str:
    provider = normalize_provider(provider)
    name_lower = model_name.lower()
    mapping = MODEL_TYPE_PATTERNS.get(provider, {})
    for model_type in ("speech_to_text", "text_to_speech", "embedding", "language"):
        for pattern in mapping.get(model_type, ()):
            if pattern in name_lower:
                return model_type
    return "language"


async def _discover_compat_models(provider: str, config: dict) -> List[DiscoveredModel]:
    discovery_url = get_models_endpoint(provider, config)
    if not discovery_url:
        return []

    headers = {}
    api_key = config.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(discovery_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            discovered: list[DiscoveredModel] = []
            for row in data.get("data", []):
                name = row.get("id") or row.get("name")
                if not name:
                    continue
                discovered.append(
                    DiscoveredModel(
                        name=name,
                        provider=provider,
                        model_type=classify_model_type(name, provider),
                        description=row.get("name") or row.get("display_name"),
                    )
                )
            return discovered
    except Exception as e:
        logger.warning(f"Failed to discover compat models for {provider}: {e}")
        return []


async def _discover_ollama_models(config: dict) -> List[DiscoveredModel]:
    base_url = config.get("base_url") or "http://localhost:11434"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{str(base_url).rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [
                DiscoveredModel(
                    name=model.get("name", ""),
                    provider="ollama",
                    model_type=classify_model_type(model.get("name", ""), "ollama"),
                )
                for model in data.get("models", [])
                if model.get("name")
            ]
    except Exception as e:
        logger.warning(f"Failed to discover Ollama models: {e}")
        return []


def _curated_discovery(provider: str) -> List[DiscoveredModel]:
    curated = get_curated_models(provider)
    discovered: list[DiscoveredModel] = []
    for model_type, names in curated.items():
        for name in names:
            discovered.append(
                DiscoveredModel(
                    name=name,
                    provider=provider,
                    model_type="language" if model_type == "vision" else model_type,
                )
            )
    return discovered


async def discover_provider_models(provider: str) -> List[DiscoveredModel]:
    provider = normalize_provider(provider)
    entry = get_provider_catalog_entry(provider)
    config = await get_provider_runtime_config(provider)

    if entry.runtime_family in {"compat", "spark", "native_deepseek"}:
        discovered = await _discover_compat_models(provider, config)
    elif entry.runtime_family == "native_ollama":
        discovered = await _discover_ollama_models(config)
    else:
        discovered = []

    if discovered:
        deduped: dict[tuple[str, str], DiscoveredModel] = {}
        for model in discovered:
            deduped[(model.name.lower(), model.model_type)] = model
        return list(deduped.values())

    return _curated_discovery(provider)


async def sync_provider_models(
    provider: str, auto_register: bool = True
) -> Tuple[int, int, int]:
    provider = normalize_provider(provider)
    discovered = await discover_provider_models(provider)
    if not auto_register:
        return len(discovered), 0, 0

    existing_models = await Model.get_all()
    existing_keys = {
        (model.provider.lower(), model.name.lower(), model.type.lower()): model
        for model in existing_models
    }

    linked_credential = None
    credentials = await Credential.get_by_provider(provider)
    if credentials:
        linked_credential = credentials[0].id

    new_count = 0
    existing_count = 0
    for discovered_model in discovered:
        key = (
            discovered_model.provider.lower(),
            discovered_model.name.lower(),
            discovered_model.model_type.lower(),
        )
        if key in existing_keys:
            existing_count += 1
            continue

        model = Model(
            name=discovered_model.name,
            provider=discovered_model.provider,
            type=discovered_model.model_type,
            credential=linked_credential,
        )
        await model.save()
        existing_keys[key] = model
        new_count += 1

    return len(discovered), new_count, existing_count


async def sync_all_providers() -> Dict[str, Tuple[int, int, int]]:
    async def _sync(provider: str) -> tuple[str, Tuple[int, int, int]]:
        config = await get_provider_runtime_config(provider)
        if provider != "ollama" and not (config.get("api_key") or config.get("base_url")):
            return provider, (0, 0, 0)
        return provider, await sync_provider_models(provider, auto_register=True)

    results = await asyncio.gather(*[_sync(provider) for provider in get_provider_ids()])
    return dict(results)


async def get_provider_model_count(provider: str) -> Dict[str, int]:
    provider = normalize_provider(provider)
    counts = {
        "language": 0,
        "embedding": 0,
        "speech_to_text": 0,
        "text_to_speech": 0,
    }
    models = await Model.get_all()
    for model in models:
        if model.provider.lower() != provider:
            continue
        if model.type in counts:
            counts[model.type] += 1
    return counts
