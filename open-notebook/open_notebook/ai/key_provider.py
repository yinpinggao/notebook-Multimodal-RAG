"""
Database-first runtime config provider for AI models.
"""

import os
from typing import Any, Optional

from loguru import logger

from open_notebook.ai.provider_catalog import (
    get_provider_catalog_entry,
    normalize_provider,
)
from open_notebook.domain.credential import Credential


async def _get_default_credential(provider: str) -> Optional[Credential]:
    try:
        credentials = await Credential.get_by_provider(provider)
        if credentials:
            return credentials[0]
    except Exception as e:
        logger.debug(f"Could not load credential from database for {provider}: {e}")
    return None


def _get_first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _config_from_env(provider: str) -> dict[str, Any]:
    provider = normalize_provider(provider)
    entry = get_provider_catalog_entry(provider)
    extra_config: dict[str, Any] = {}

    if provider == "ollama":
        return {"base_url": _get_first_env("OLLAMA_API_BASE") or entry.default_base_url}
    if provider == "tongyi":
        region = _get_first_env("TONGYI_REGION")
        if region:
            extra_config["region"] = region
        return {
            "api_key": _get_first_env("TONGYI_API_KEY", "DASHSCOPE_API_KEY"),
            "base_url": _get_first_env("TONGYI_BASE_URL"),
            "extra_config": extra_config,
        }
    if provider == "wenxin":
        return {
            "api_key": _get_first_env("WENXIN_API_KEY", "QIANFAN_API_KEY"),
            "base_url": _get_first_env("WENXIN_BASE_URL"),
        }
    if provider == "deepseek":
        return {
            "api_key": _get_first_env("DEEPSEEK_API_KEY"),
            "base_url": _get_first_env("DEEPSEEK_BASE_URL"),
        }
    if provider == "doubao":
        for env_name, key in (
            ("DOUBAO_SPEECH_APP_ID", "speech_app_id"),
            ("DOUBAO_SPEECH_TOKEN", "speech_token"),
            ("DOUBAO_SPEECH_ENDPOINT", "speech_endpoint"),
            ("DOUBAO_SPEECH_WS_URL", "speech_ws_url"),
        ):
            value = _get_first_env(env_name)
            if value:
                extra_config[key] = value
        return {
            "api_key": _get_first_env("DOUBAO_API_KEY", "ARK_API_KEY"),
            "base_url": _get_first_env("DOUBAO_BASE_URL"),
            "extra_config": extra_config,
        }
    if provider == "spark":
        for env_name, key in (
            ("SPARK_APP_ID", "app_id"),
            ("SPARK_API_SECRET", "api_secret"),
        ):
            value = _get_first_env(env_name)
            if value:
                extra_config[key] = value
        return {
            "api_key": _get_first_env("SPARK_API_KEY", "XFYUN_API_KEY"),
            "base_url": _get_first_env("SPARK_BASE_URL"),
            "extra_config": extra_config,
        }
    if provider == "kimi":
        return {
            "api_key": _get_first_env("KIMI_API_KEY", "MOONSHOT_API_KEY"),
            "base_url": _get_first_env("KIMI_BASE_URL"),
        }
    if provider == "hunyuan":
        for env_name, key in (
            ("HUNYUAN_SECRET_ID", "secret_id"),
            ("HUNYUAN_SECRET_KEY", "secret_key"),
            ("HUNYUAN_REGION", "region"),
        ):
            value = _get_first_env(env_name)
            if value:
                extra_config[key] = value
        return {
            "api_key": _get_first_env("HUNYUAN_API_KEY", "TENCENT_HUNYUAN_API_KEY"),
            "base_url": _get_first_env("HUNYUAN_BASE_URL"),
            "extra_config": extra_config,
        }
    if provider == "zhipu":
        return {
            "api_key": _get_first_env("ZHIPU_API_KEY", "BIGMODEL_API_KEY"),
            "base_url": _get_first_env("ZHIPU_BASE_URL"),
        }
    return {}


async def get_provider_runtime_config(provider: str) -> dict[str, Any]:
    provider = normalize_provider(provider)
    cred = await _get_default_credential(provider)
    if cred:
        return cred.to_runtime_config()
    return _config_from_env(provider)


async def get_api_key(provider: str) -> Optional[str]:
    config = await get_provider_runtime_config(provider)
    api_key = config.get("api_key")
    return str(api_key) if api_key else None


async def provision_provider_keys(provider: str) -> bool:
    provider = normalize_provider(provider)
    config = await get_provider_runtime_config(provider)
    if not config:
        return False

    api_key = config.get("api_key")
    base_url = config.get("base_url")
    provider_upper = provider.upper()

    if api_key:
        os.environ[f"{provider_upper}_API_KEY"] = str(api_key)
    if base_url:
        os.environ[f"{provider_upper}_BASE_URL"] = str(base_url)

    if provider in {"tongyi", "wenxin", "doubao", "spark", "kimi", "hunyuan", "zhipu"}:
        if api_key:
            os.environ["OPENAI_COMPATIBLE_API_KEY"] = str(api_key)
        if base_url:
            os.environ["OPENAI_COMPATIBLE_BASE_URL"] = str(base_url)

    if provider == "ollama" and base_url:
        os.environ["OLLAMA_API_BASE"] = str(base_url)
    if provider == "deepseek" and api_key:
        os.environ["DEEPSEEK_API_KEY"] = str(api_key)

    return True


async def provision_all_keys() -> dict[str, bool]:
    results: dict[str, bool] = {}
    for provider in (
        "tongyi",
        "wenxin",
        "deepseek",
        "doubao",
        "spark",
        "kimi",
        "hunyuan",
        "zhipu",
        "ollama",
    ):
        results[provider] = await provision_provider_keys(provider)
    return results
