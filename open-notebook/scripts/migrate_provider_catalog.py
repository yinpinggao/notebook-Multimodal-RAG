import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from loguru import logger

from open_notebook.ai.models import DefaultModels, Model
from open_notebook.ai.provider_catalog import get_provider_ids, get_provider_modalities
from open_notebook.domain.credential import Credential

SUPPORTED_PROVIDERS = set(get_provider_ids())
REMOVED_PROVIDERS = {
    "openai",
    "anthropic",
    "google",
    "groq",
    "mistral",
    "xai",
    "openrouter",
    "voyage",
    "elevenlabs",
    "azure",
    "vertex",
    "openai_compatible",
}


def map_openai_compatible(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    host = (urlparse(base_url).netloc or "").lower()
    if "dashscope" in host or "aliyun" in host:
        return "tongyi"
    if "moonshot" in host:
        return "kimi"
    if "bigmodel" in host or "zhipu" in host:
        return "zhipu"
    if "qianfan" in host or "baidubce" in host or "baidu" in host:
        return "wenxin"
    if "volc" in host or "ark" in host:
        return "doubao"
    if "hunyuan" in host or "tencent" in host:
        return "hunyuan"
    return None


def map_provider(provider: str, base_url: Optional[str] = None) -> Optional[str]:
    normalized = provider.lower().replace("-", "_")
    if normalized in SUPPORTED_PROVIDERS:
        return normalized
    if normalized == "openai_compatible":
        return map_openai_compatible(base_url)
    return None


async def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate old provider records to the domestic provider catalog.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without persisting them.")
    args = parser.parse_args()

    audit: dict[str, list[dict]] = {"credentials": [], "models": [], "defaults": []}

    credentials = await Credential.get_all()
    credential_provider_map: dict[str, str] = {}

    for credential in credentials:
        mapped = map_provider(credential.provider, credential.base_url)
        if mapped:
            credential_provider_map[credential.id or ""] = mapped
            if mapped != credential.provider:
                audit["credentials"].append(
                    {
                        "id": credential.id,
                        "action": "remap",
                        "from": credential.provider,
                        "to": mapped,
                        "name": credential.name,
                    }
                )
                if not args.dry_run:
                    credential.provider = mapped
                    credential.modalities = get_provider_modalities(mapped)
                    await credential.save()
        else:
            audit["credentials"].append(
                {
                    "id": credential.id,
                    "action": "delete",
                    "provider": credential.provider,
                    "name": credential.name,
                    "base_url": credential.base_url,
                }
            )
            if not args.dry_run:
                await credential.delete()

    models = await Model.get_all()
    valid_model_ids: set[str] = set()
    for model in models:
        mapped = None
        if model.credential and model.credential in credential_provider_map:
            mapped = credential_provider_map[model.credential]
        else:
            mapped = map_provider(model.provider)

        if mapped:
            valid_model_ids.add(model.id or "")
            if mapped != model.provider:
                audit["models"].append(
                    {
                        "id": model.id,
                        "action": "remap",
                        "from": model.provider,
                        "to": mapped,
                        "name": model.name,
                    }
                )
                if not args.dry_run:
                    model.provider = mapped
                    await model.save()
        else:
            audit["models"].append(
                {
                    "id": model.id,
                    "action": "delete",
                    "provider": model.provider,
                    "name": model.name,
                }
            )
            if not args.dry_run:
                await model.delete()

    defaults = await DefaultModels.get_instance()
    default_fields = [
        "default_chat_model",
        "default_transformation_model",
        "large_context_model",
        "default_vision_model",
        "default_text_to_speech_model",
        "default_speech_to_text_model",
        "default_embedding_model",
        "default_tools_model",
    ]
    changed_defaults = False
    for field_name in default_fields:
        model_id = getattr(defaults, field_name, None)
        if model_id and model_id not in valid_model_ids:
            audit["defaults"].append(
                {"field": field_name, "action": "clear", "value": model_id}
            )
            changed_defaults = True
            if not args.dry_run:
                setattr(defaults, field_name, None)

    if changed_defaults and not args.dry_run:
        await defaults.update()

    audit_dir = Path("/home/gyp/dev/open-notebook/data/migration")
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"provider_catalog_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(
        "Provider catalog migration finished (dry_run={dry_run}). Audit written to {audit_path}",
        dry_run=args.dry_run,
        audit_path=audit_path,
    )


if __name__ == "__main__":
    asyncio.run(main())
