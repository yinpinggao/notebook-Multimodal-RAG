from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from esperanto import AIFactory

from open_notebook.ai.native_adapters import (
    DoubaoSpeechToTextAdapter,
    DoubaoTextToSpeechAdapter,
    SparkEmbeddingAdapter,
    SparkLanguageAdapter,
    SparkSpeechToTextAdapter,
    SparkTextToSpeechAdapter,
    ZhipuTextToSpeechAdapter,
)
from open_notebook.ai.provider_catalog import (
    get_provider_catalog_entry,
    get_region_base_url,
    normalize_provider,
)
from open_notebook.exceptions import ConfigurationError


@dataclass(frozen=True)
class ResolvedProviderRuntime:
    public_provider: str
    runtime_family: str
    runtime_provider: str
    config: dict[str, Any]


def build_runtime_config(
    provider: str,
    config: Optional[dict[str, Any]] = None,
) -> ResolvedProviderRuntime:
    entry = get_provider_catalog_entry(provider)
    payload = dict(config or {})

    extra_config = dict(payload.pop("extra_config", {}) or {})
    if extra_config:
        payload.update(extra_config)

    base_url = payload.get("base_url")
    region = payload.get("region")

    if entry.runtime_family == "compat":
        payload["base_url"] = base_url or get_region_base_url(provider, region)
    elif entry.runtime_family == "spark":
        if base_url:
            payload["base_url"] = base_url
    elif entry.runtime_family == "native_ollama":
        payload["base_url"] = base_url or entry.default_base_url
    elif entry.runtime_family == "native_deepseek":
        if base_url:
            payload["base_url"] = base_url

    if not payload.get("base_url") and entry.default_base_url and entry.runtime_family != "spark":
        payload["base_url"] = entry.default_base_url

    return ResolvedProviderRuntime(
        public_provider=normalize_provider(provider),
        runtime_family=entry.runtime_family,
        runtime_provider=entry.runtime_provider,
        config=payload,
    )


def create_runtime_model(
    *,
    provider: str,
    model_name: str,
    model_type: str,
    config: Optional[dict[str, Any]] = None,
):
    runtime = build_runtime_config(provider, config)

    if runtime.public_provider == "spark":
        if model_type == "language":
            return SparkLanguageAdapter(
                model_name=model_name,
                api_key=runtime.config.get("api_key"),
                base_url=runtime.config.get("base_url"),
                config=runtime.config,
            )
        if model_type == "embedding":
            return SparkEmbeddingAdapter(
                model_name=model_name,
                api_key=runtime.config.get("api_key"),
                base_url=runtime.config.get("base_url"),
                config=runtime.config,
            )
        if model_type == "speech_to_text":
            return SparkSpeechToTextAdapter(
                model_name=model_name,
                api_key=runtime.config.get("api_key"),
                base_url=runtime.config.get("base_url"),
                config=runtime.config,
            )
        if model_type == "text_to_speech":
            return SparkTextToSpeechAdapter(
                model_name=model_name,
                api_key=runtime.config.get("api_key"),
                base_url=runtime.config.get("base_url"),
                config=runtime.config,
            )

    if runtime.public_provider == "doubao":
        if model_type == "speech_to_text":
            return DoubaoSpeechToTextAdapter(
                model_name=model_name,
                api_key=runtime.config.get("api_key"),
                base_url=runtime.config.get("base_url"),
                config=runtime.config,
            )
        if model_type == "text_to_speech":
            return DoubaoTextToSpeechAdapter(
                model_name=model_name,
                api_key=runtime.config.get("api_key"),
                base_url=runtime.config.get("base_url"),
                config=runtime.config,
            )

    if runtime.public_provider == "zhipu" and model_type == "text_to_speech":
        return ZhipuTextToSpeechAdapter(
            model_name=model_name,
            api_key=runtime.config.get("api_key"),
            base_url=runtime.config.get("base_url"),
            config=runtime.config,
        )

    if model_type == "language":
        return AIFactory.create_language(
            model_name=model_name,
            provider=runtime.runtime_provider,
            config=runtime.config,
        )
    if model_type == "embedding":
        return AIFactory.create_embedding(
            model_name=model_name,
            provider=runtime.runtime_provider,
            config=runtime.config,
        )
    if model_type == "speech_to_text":
        return AIFactory.create_speech_to_text(
            model_name=model_name,
            provider=runtime.runtime_provider,
            config=runtime.config,
        )
    if model_type == "text_to_speech":
        return AIFactory.create_text_to_speech(
            model_name=model_name,
            provider=runtime.runtime_provider,
            config=runtime.config,
        )
    raise ConfigurationError(f"Unsupported model type '{model_type}'")


def get_models_endpoint(provider: str, config: Optional[dict[str, Any]] = None) -> Optional[str]:
    runtime = build_runtime_config(provider, config)
    base_url = runtime.config.get("base_url")
    if not base_url:
        return None
    if runtime.runtime_family == "native_ollama":
        return f"{str(base_url).rstrip('/')}/api/tags"
    if runtime.public_provider == "spark":
        return None
    return f"{str(base_url).rstrip('/')}/models"
