"""
Credentials Service

Business logic for managing AI provider credentials.
"""

import ipaddress
import os
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from loguru import logger
from pydantic import SecretStr

from api.models import CredentialResponse
from open_notebook.ai.provider_catalog import (
    get_curated_models,
    get_provider_catalog_entry,
    get_provider_catalog_payload,
    get_provider_env_config,
    get_provider_ids,
    get_provider_modalities,
    get_sensitive_extra_config_keys,
    is_supported_provider,
    normalize_provider,
)
from open_notebook.ai.provider_runtime import get_models_endpoint
from open_notebook.domain.credential import Credential
from open_notebook.utils.encryption import get_secret_from_env


def validate_url(url: str, provider: str) -> None:
    if not url or not url.strip():
        return

    try:
        parsed = urlparse(url.strip())

        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme: '{parsed.scheme}'. Only http and https are allowed."
            )

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: hostname could not be determined.")

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_link_local:
                raise ValueError(
                    "Link-local addresses (169.254.x.x) are not allowed for security reasons."
                )
            if hasattr(ip, "ipv4_mapped") and ip.ipv4_mapped and ip.ipv4_mapped.is_link_local:
                raise ValueError(
                    "Link-local addresses (169.254.x.x) are not allowed for security reasons."
                )
        except ValueError as ve:
            if "Link-local" in str(ve) or "Invalid URL" in str(ve):
                raise
            try:
                resolved_ips = socket.getaddrinfo(hostname, None)
                for _, _, _, _, sockaddr in resolved_ips:
                    ip_addr = sockaddr[0]
                    try:
                        parsed_ip = ipaddress.ip_address(ip_addr)
                        if parsed_ip.is_link_local:
                            raise ValueError(
                                f"Hostname '{hostname}' resolves to a link-local address which is not allowed."
                            )
                    except ValueError as inner_ve:
                        if "link-local" in str(inner_ve).lower():
                            raise
                        continue
            except socket.gaierror:
                pass
    except ValueError:
        raise
    except Exception:
        raise ValueError(f"Invalid URL format for provider '{provider}'.")


def require_encryption_key() -> None:
    if not get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY"):
        raise ValueError(
            "Encryption key not configured. Set OPEN_NOTEBOOK_ENCRYPTION_KEY to enable storing API keys."
        )


def _sanitize_extra_config(provider: str, extra_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = dict(extra_config or {})
    for key in get_sensitive_extra_config_keys(provider):
        if key in payload:
            payload.pop(key, None)
    return payload


def credential_to_response(cred: Credential, model_count: int = 0) -> CredentialResponse:
    return CredentialResponse(
        id=cred.id or "",
        name=cred.name,
        provider=cred.provider,
        modalities=cred.modalities,
        base_url=cred.base_url,
        endpoint=cred.endpoint,
        api_version=cred.api_version,
        endpoint_llm=cred.endpoint_llm,
        endpoint_embedding=cred.endpoint_embedding,
        endpoint_stt=cred.endpoint_stt,
        endpoint_tts=cred.endpoint_tts,
        project=cred.project,
        location=cred.location,
        credentials_path=cred.credentials_path,
        extra_config=_sanitize_extra_config(cred.provider, cred.extra_config),
        has_api_key=cred.api_key is not None,
        created=str(cred.created) if cred.created else "",
        updated=str(cred.updated) if cred.updated else "",
        model_count=model_count,
    )


def get_default_modalities(provider: str) -> List[str]:
    return get_provider_modalities(provider)


def check_env_configured(provider: str) -> bool:
    config = get_provider_env_config(provider)
    if not config:
        return False
    if "required_any" in config:
        return any(bool(os.environ.get(name, "").strip()) for name in config["required_any"])
    if "required" in config:
        return all(bool(os.environ.get(name, "").strip()) for name in config["required"])
    return False


def _get_first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def create_credential_from_env(provider: str) -> Credential:
    provider = normalize_provider(provider)
    entry = get_provider_catalog_entry(provider)
    name = "Default (Migrated from env)"
    extra_config: dict[str, Any] = {}

    if provider == "ollama":
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            base_url=_get_first_env("OLLAMA_API_BASE") or entry.default_base_url,
        )

    if provider == "tongyi":
        api_key = _get_first_env("TONGYI_API_KEY", "DASHSCOPE_API_KEY")
        region = _get_first_env("TONGYI_REGION")
        if region:
            extra_config["region"] = region
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("TONGYI_BASE_URL"),
            extra_config=extra_config,
        )

    if provider == "wenxin":
        api_key = _get_first_env("WENXIN_API_KEY", "QIANFAN_API_KEY")
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("WENXIN_BASE_URL"),
        )

    if provider == "doubao":
        api_key = _get_first_env("DOUBAO_API_KEY", "ARK_API_KEY")
        for env_name, key in (
            ("DOUBAO_SPEECH_APP_ID", "speech_app_id"),
            ("DOUBAO_SPEECH_TOKEN", "speech_token"),
            ("DOUBAO_SPEECH_ENDPOINT", "speech_endpoint"),
            ("DOUBAO_SPEECH_WS_URL", "speech_ws_url"),
        ):
            value = _get_first_env(env_name)
            if value:
                extra_config[key] = value
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("DOUBAO_BASE_URL"),
            extra_config=extra_config,
        )

    if provider == "spark":
        api_key = _get_first_env("SPARK_API_KEY", "XFYUN_API_KEY")
        for env_name, key in (
            ("SPARK_APP_ID", "app_id"),
            ("SPARK_API_SECRET", "api_secret"),
        ):
            value = _get_first_env(env_name)
            if value:
                extra_config[key] = value
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("SPARK_BASE_URL"),
            extra_config=extra_config,
        )

    if provider == "kimi":
        api_key = _get_first_env("KIMI_API_KEY", "MOONSHOT_API_KEY")
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("KIMI_BASE_URL"),
        )

    if provider == "hunyuan":
        api_key = _get_first_env("HUNYUAN_API_KEY", "TENCENT_HUNYUAN_API_KEY")
        for env_name, key in (
            ("HUNYUAN_SECRET_ID", "secret_id"),
            ("HUNYUAN_SECRET_KEY", "secret_key"),
            ("HUNYUAN_REGION", "region"),
        ):
            value = _get_first_env(env_name)
            if value:
                extra_config[key] = value
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("HUNYUAN_BASE_URL"),
            extra_config=extra_config,
        )

    if provider == "zhipu":
        api_key = _get_first_env("ZHIPU_API_KEY", "BIGMODEL_API_KEY")
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(api_key) if api_key else None,
            base_url=_get_first_env("ZHIPU_BASE_URL"),
        )

    if provider == "deepseek":
        return Credential(
            name=name,
            provider=provider,
            modalities=list(entry.modalities),
            api_key=SecretStr(os.environ["DEEPSEEK_API_KEY"]),
            base_url=_get_first_env("DEEPSEEK_BASE_URL"),
        )

    raise ValueError(f"Unsupported provider for env migration: {provider}")


async def get_provider_status() -> dict:
    encryption_configured = bool(get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY"))
    configured: Dict[str, bool] = {}
    source: Dict[str, str] = {}

    for provider in get_provider_ids():
        env_configured = check_env_configured(provider)
        try:
            db_credentials = await Credential.get_by_provider(provider)
            db_configured = len(db_credentials) > 0
        except Exception:
            db_configured = False

        configured[provider] = db_configured or env_configured
        if db_configured:
            source[provider] = "database"
        elif env_configured:
            source[provider] = "environment"
        else:
            source[provider] = "none"

    return {
        "configured": configured,
        "source": source,
        "encryption_configured": encryption_configured,
    }


async def get_env_status() -> Dict[str, bool]:
    return {provider: check_env_configured(provider) for provider in get_provider_ids()}


async def get_provider_catalog() -> dict:
    return {"providers": get_provider_catalog_payload()}


async def test_credential(credential_id: str) -> dict:
    from open_notebook.ai.connection_tester import test_provider_connection

    cred = await Credential.get(credential_id)
    success, message = await test_provider_connection(cred.provider, config_id=credential_id)
    return {"provider": cred.provider, "success": success, "message": message}


async def _discover_compat_models(provider: str, config: dict[str, Any]) -> List[dict[str, Any]]:
    api_key = config.get("api_key")
    discovery_url = get_models_endpoint(provider, config)
    if not discovery_url:
        return []
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(discovery_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "name": model.get("id", ""),
                    "provider": provider,
                    "description": model.get("name") or model.get("display_name"),
                }
                for model in data.get("data", [])
                if model.get("id")
            ]
    except Exception as e:
        logger.warning(f"Failed to discover compat models for {provider}: {e}")
        return []


async def _discover_ollama_models(config: dict[str, Any]) -> List[dict[str, Any]]:
    base_url = config.get("base_url") or "http://localhost:11434"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [
                {"name": model.get("name", ""), "provider": "ollama"}
                for model in data.get("models", [])
                if model.get("name")
            ]
    except Exception as e:
        logger.warning(f"Failed to discover Ollama models: {e}")
        return []


async def discover_with_config(provider: str, config: dict) -> List[dict]:
    provider = normalize_provider(provider)
    if not is_supported_provider(provider):
        return []

    entry = get_provider_catalog_entry(provider)
    discovered: List[dict[str, Any]] = []

    if entry.runtime_family in {"compat", "spark", "native_deepseek"}:
        discovered = await _discover_compat_models(provider, config)
    elif entry.runtime_family == "native_ollama":
        discovered = await _discover_ollama_models(config)

    if discovered:
        return discovered

    curated = get_curated_models(provider)
    rows: List[dict[str, Any]] = []
    for model_type, names in curated.items():
        for model_name in names:
            rows.append(
                {
                    "name": model_name,
                    "provider": provider,
                    "model_type": model_type,
                }
            )
    return rows


async def register_models(credential_id: str, models_data: list) -> dict:
    cred = await Credential.get(credential_id)
    from open_notebook.ai.models import Model

    valid_types = {"language", "embedding", "speech_to_text", "text_to_speech"}
    existing_models = await Model.get_all()
    existing_keys = {
        (m.provider.lower(), m.name.lower(), m.type.lower())
        for m in existing_models
    }

    created = 0
    existing = 0
    for model_data in models_data:
        provider = normalize_provider(model_data.provider or cred.provider)
        if not is_supported_provider(provider):
            continue
        if model_data.model_type not in valid_types:
            logger.warning(
                f"Skipping unsupported model type '{model_data.model_type}' for provider '{provider}'"
            )
            continue
        key = (provider, model_data.name.lower(), model_data.model_type.lower())
        if key in existing_keys:
            existing += 1
            continue
        new_model = Model(
            name=model_data.name,
            provider=provider,
            type=model_data.model_type,
            credential=cred.id,
        )
        await new_model.save()
        existing_keys.add(key)
        created += 1

    return {"created": created, "existing": existing}


async def migrate_from_provider_config() -> dict:
    """
    Legacy ProviderConfig migration.

    Only supported providers from the new catalog are migrated.
    """
    require_encryption_key()

    try:
        from open_notebook.domain.provider_config import ProviderConfig
    except Exception:
        return {
            "message": "ProviderConfig is not available",
            "migrated": [],
            "skipped": [],
            "errors": [],
        }

    config = await ProviderConfig.get_instance()
    migrated: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for provider, credentials_list in getattr(config, "credentials", {}).items():
        normalized_provider = normalize_provider(provider)
        if not is_supported_provider(normalized_provider):
            skipped.append(f"{provider}:unsupported")
            continue

        for old_cred in credentials_list:
            try:
                existing = await Credential.get_by_provider(normalized_provider)
                if any(c.name == old_cred.name for c in existing):
                    skipped.append(f"{normalized_provider}/{old_cred.name}")
                    continue

                new_cred = Credential(
                    name=old_cred.name,
                    provider=normalized_provider,
                    modalities=get_default_modalities(normalized_provider),
                    api_key=old_cred.api_key,
                    base_url=old_cred.base_url,
                    endpoint=old_cred.endpoint,
                    api_version=old_cred.api_version,
                    endpoint_llm=old_cred.endpoint_llm,
                    endpoint_embedding=old_cred.endpoint_embedding,
                    endpoint_stt=old_cred.endpoint_stt,
                    endpoint_tts=old_cred.endpoint_tts,
                    project=old_cred.project,
                    location=old_cred.location,
                    credentials_path=old_cred.credentials_path,
                )
                await new_cred.save()
                migrated.append(f"{normalized_provider}/{old_cred.name}")
            except Exception as e:
                logger.error(f"ProviderConfig migration failed for {provider}/{old_cred.name}: {e}")
                errors.append(f"{provider}/{old_cred.name}: {str(e)}")

    return {
        "message": f"Migrated {len(migrated)} credential(s) from ProviderConfig",
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors,
    }


async def migrate_from_env(force: bool = False) -> dict:
    require_encryption_key()

    migrated: list[str] = []
    skipped: list[str] = []
    not_configured: list[str] = []
    errors: list[str] = []

    for provider in get_provider_ids():
        try:
            if not check_env_configured(provider):
                not_configured.append(provider)
                continue

            existing = await Credential.get_by_provider(provider)
            if existing and not force:
                skipped.append(provider)
                continue

            new_cred = create_credential_from_env(provider)
            if existing and force:
                # overwrite the first credential to preserve references
                new_cred.id = existing[0].id
            await new_cred.save()
            migrated.append(provider)
        except Exception as e:
            logger.error(f"Env migration failed for {provider}: {e}")
            errors.append(f"{provider}: {str(e)}")

    return {
        "message": f"Migrated {len(migrated)} provider credential(s) from environment",
        "migrated": migrated,
        "skipped": skipped,
        "not_configured": not_configured,
        "errors": errors,
    }
