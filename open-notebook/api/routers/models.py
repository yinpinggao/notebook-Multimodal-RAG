import os
import traceback
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

from api.credentials_service import check_env_configured
from api.models import (
    DefaultModelsResponse,
    ModelCreate,
    ModelResponse,
    ProviderAvailabilityResponse,
)
from open_notebook.ai.connection_tester import test_individual_model
from open_notebook.ai.key_provider import provision_provider_keys
from open_notebook.ai.model_discovery import (
    discover_provider_models,
    get_provider_model_count,
    sync_all_providers,
    sync_provider_models,
)
from open_notebook.ai.models import DefaultModels, Model
from open_notebook.ai.provider_catalog import (
    get_default_model_priority,
    get_provider_ids,
    is_supported_provider,
    iter_supported_provider_types,
)
from open_notebook.domain.credential import Credential
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


# =============================================================================
# Model Discovery Response Models
# =============================================================================


class DiscoveredModelResponse(BaseModel):
    """Response model for a discovered model."""

    name: str
    provider: str
    model_type: str
    description: Optional[str] = None


class ProviderSyncResponse(BaseModel):
    """Response model for provider sync operation."""

    provider: str
    discovered: int
    new: int
    existing: int


class AllProvidersSyncResponse(BaseModel):
    """Response model for syncing all providers."""

    results: Dict[str, ProviderSyncResponse]
    total_discovered: int
    total_new: int


class ProviderModelCountResponse(BaseModel):
    """Response model for provider model counts."""

    provider: str
    counts: Dict[str, int]
    total: int


class AutoAssignResult(BaseModel):
    """Response model for auto-assign operation."""

    assigned: Dict[str, str]  # slot_name -> model_id
    skipped: List[str]  # slots already assigned
    missing: List[str]  # slots with no available models


class ModelTestResponse(BaseModel):
    """Response model for individual model test."""

    success: bool
    message: str
    details: Optional[str] = None


MODEL_PREFERENCES = {
    "tongyi": ["qwen-max", "qwen-plus", "qwen-turbo"],
    "wenxin": ["ernie-4.5", "ernie-4.0", "ernie-speed"],
    "deepseek": ["reasoner", "chat", "coder"],
    "doubao": ["thinking", "flash", "seed"],
    "spark": ["max", "pro", "lite"],
    "kimi": ["kimi-k2", "moonshot-v1-128k", "moonshot-v1-32k"],
    "hunyuan": ["large", "turbo", "standard"],
    "zhipu": ["glm-4.5", "glm-4-plus", "glm-4-air"],
    "ollama": ["qwen", "llama", "deepseek", "mistral"],
}


async def _check_provider_has_credential(provider: str) -> bool:
    """Check if a provider has any credentials configured in the database."""
    try:
        credentials = await Credential.get_by_provider(provider)
        return len(credentials) > 0
    except Exception:
        pass
    return False


@router.get("/models", response_model=List[ModelResponse])
async def get_models(
    type: Optional[str] = Query(None, description="Filter by model type"),
):
    """Get all configured models with optional type filtering."""
    try:
        if type:
            models = await Model.get_models_by_type(type)
        else:
            models = await Model.get_all()

        return [
            ModelResponse(
                id=model.id,
                name=model.name,
                provider=model.provider,
                type=model.type,
                credential=model.credential,
                created=str(model.created),
                updated=str(model.updated),
            )
            for model in models
        ]
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")


@router.post("/models", response_model=ModelResponse)
async def create_model(model_data: ModelCreate):
    """Create a new model configuration."""
    try:
        if not is_supported_provider(model_data.provider):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider. Must be one of: {get_provider_ids()}",
            )

        # Validate model type
        valid_types = ["language", "embedding", "text_to_speech", "speech_to_text"]
        if model_data.type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type. Must be one of: {valid_types}",
            )

        existing = [
            model
            for model in await Model.get_all()
            if model.provider.lower() == model_data.provider.lower()
            and model.name.lower() == model_data.name.lower()
            and model.type.lower() == model_data.type.lower()
        ]
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_data.name}' already exists for provider '{model_data.provider}' with type '{model_data.type}'",
            )

        new_model = Model(
            name=model_data.name,
            provider=model_data.provider,
            type=model_data.type,
            credential=model_data.credential,
        )
        await new_model.save()

        return ModelResponse(
            id=new_model.id or "",
            name=new_model.name,
            provider=new_model.provider,
            type=new_model.type,
            credential=new_model.credential,
            created=str(new_model.created),
            updated=str(new_model.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating model: {str(e)}")


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """Delete a model configuration."""
    try:
        model = await Model.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        await model.delete()

        return {"message": "Model deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting model: {str(e)}")


@router.post("/models/{model_id}/test", response_model=ModelTestResponse)
async def test_model(model_id: str):
    """Test if a specific model is correctly configured and functional."""
    try:
        model = await Model.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        success, message = await test_individual_model(model)
        return ModelTestResponse(success=success, message=message)
    except Exception as e:
        logger.error(f"Error testing model {model_id}: {traceback.format_exc()}")
        return ModelTestResponse(
            success=False,
            message=str(e)[:200],
        )


@router.get("/models/defaults", response_model=DefaultModelsResponse)
async def get_default_models():
    """Get default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()

        return DefaultModelsResponse(
            default_chat_model=defaults.default_chat_model,  # type: ignore[attr-defined]
            default_transformation_model=defaults.default_transformation_model,  # type: ignore[attr-defined]
            large_context_model=defaults.large_context_model,  # type: ignore[attr-defined]
            default_vision_model=defaults.default_vision_model,  # type: ignore[attr-defined]
            default_text_to_speech_model=defaults.default_text_to_speech_model,  # type: ignore[attr-defined]
            default_speech_to_text_model=defaults.default_speech_to_text_model,  # type: ignore[attr-defined]
            default_embedding_model=defaults.default_embedding_model,  # type: ignore[attr-defined]
            default_tools_model=defaults.default_tools_model,  # type: ignore[attr-defined]
        )
    except Exception as e:
        logger.error(f"Error fetching default models: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching default models: {str(e)}"
        )


@router.put("/models/defaults", response_model=DefaultModelsResponse)
async def update_default_models(defaults_data: DefaultModelsResponse):
    """Update default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()

        # Update only provided fields
        if defaults_data.default_chat_model is not None:
            defaults.default_chat_model = defaults_data.default_chat_model  # type: ignore[attr-defined]
        if defaults_data.default_transformation_model is not None:
            defaults.default_transformation_model = (
                defaults_data.default_transformation_model
            )  # type: ignore[attr-defined]
        if defaults_data.large_context_model is not None:
            defaults.large_context_model = defaults_data.large_context_model  # type: ignore[attr-defined]
        if defaults_data.default_vision_model is not None:
            defaults.default_vision_model = defaults_data.default_vision_model  # type: ignore[attr-defined]
        if defaults_data.default_text_to_speech_model is not None:
            defaults.default_text_to_speech_model = (
                defaults_data.default_text_to_speech_model
            )  # type: ignore[attr-defined]
        if defaults_data.default_speech_to_text_model is not None:
            defaults.default_speech_to_text_model = (
                defaults_data.default_speech_to_text_model
            )  # type: ignore[attr-defined]
        if defaults_data.default_embedding_model is not None:
            defaults.default_embedding_model = defaults_data.default_embedding_model  # type: ignore[attr-defined]
        if defaults_data.default_tools_model is not None:
            defaults.default_tools_model = defaults_data.default_tools_model  # type: ignore[attr-defined]

        await defaults.update()

        # No cache refresh needed - next access will fetch fresh data from DB

        return DefaultModelsResponse(
            default_chat_model=defaults.default_chat_model,  # type: ignore[attr-defined]
            default_transformation_model=defaults.default_transformation_model,  # type: ignore[attr-defined]
            large_context_model=defaults.large_context_model,  # type: ignore[attr-defined]
            default_vision_model=defaults.default_vision_model,  # type: ignore[attr-defined]
            default_text_to_speech_model=defaults.default_text_to_speech_model,  # type: ignore[attr-defined]
            default_speech_to_text_model=defaults.default_speech_to_text_model,  # type: ignore[attr-defined]
            default_embedding_model=defaults.default_embedding_model,  # type: ignore[attr-defined]
            default_tools_model=defaults.default_tools_model,  # type: ignore[attr-defined]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating default models: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating default models: {str(e)}"
        )


@router.get("/models/providers", response_model=ProviderAvailabilityResponse)
async def get_provider_availability():
    """Get provider availability based on database config and environment variables."""
    try:
        supported_types = iter_supported_provider_types()
        provider_status = {}
        for provider in get_provider_ids():
            provider_status[provider] = await _check_provider_has_credential(
                provider
            ) or check_env_configured(provider)

        available_providers = [provider for provider, enabled in provider_status.items() if enabled]
        unavailable_providers = [provider for provider, enabled in provider_status.items() if not enabled]

        return ProviderAvailabilityResponse(
            available=available_providers,
            unavailable=unavailable_providers,
            supported_types=supported_types,
        )
    except Exception as e:
        logger.error(f"Error checking provider availability: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error checking provider availability: {str(e)}"
        )


# =============================================================================
# Model Discovery Endpoints
# =============================================================================


@router.get(
    "/models/discover/{provider}", response_model=List[DiscoveredModelResponse]
)
async def discover_models(provider: str):
    """
    Discover available models from a provider without registering them.

    This endpoint queries the provider's API to list available models
    but does not save them to the database. Use the sync endpoint
    to both discover and register models.
    """
    try:
        if not is_supported_provider(provider):
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        # Provision DB-stored credentials into env vars before discovery
        await provision_provider_keys(provider)
        discovered = await discover_provider_models(provider)
        return [
            DiscoveredModelResponse(
                name=m.name,
                provider=m.provider,
                model_type=m.model_type,
                description=m.description,
            )
            for m in discovered
        ]
    except Exception as e:
        logger.error(f"Error discovering models for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error discovering models. Check server logs for details."
        )


@router.post("/models/sync/{provider}", response_model=ProviderSyncResponse)
async def sync_models(provider: str):
    """
    Sync models for a specific provider.

    Discovers available models from the provider's API and registers
    any new models in the database. Existing models are skipped.

    Returns counts of discovered, new, and existing models.
    """
    try:
        if not is_supported_provider(provider):
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        # Provision DB-stored credentials into env vars before discovery
        await provision_provider_keys(provider)
        discovered, new, existing = await sync_provider_models(
            provider, auto_register=True
        )
        return ProviderSyncResponse(
            provider=provider,
            discovered=discovered,
            new=new,
            existing=existing,
        )
    except Exception as e:
        logger.error(f"Error syncing models for {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error syncing models. Check server logs for details.")


@router.post("/models/sync", response_model=AllProvidersSyncResponse)
async def sync_all_models():
    """
    Sync models for all configured providers.

    Discovers and registers models from all providers that have
    valid API keys configured. This is useful for initial setup
    or periodic refresh of available models.
    """
    try:
        results = await sync_all_providers()

        response_results = {}
        total_discovered = 0
        total_new = 0

        for provider, (discovered, new, existing) in results.items():
            response_results[provider] = ProviderSyncResponse(
                provider=provider,
                discovered=discovered,
                new=new,
                existing=existing,
            )
            total_discovered += discovered
            total_new += new

        return AllProvidersSyncResponse(
            results=response_results,
            total_discovered=total_discovered,
            total_new=total_new,
        )
    except Exception as e:
        logger.error(f"Error syncing all models: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error syncing all models: {str(e)}"
        )


@router.get("/models/count/{provider}", response_model=ProviderModelCountResponse)
async def get_model_count(provider: str):
    """
    Get count of registered models for a provider, grouped by type.

    Returns counts for each model type (language, embedding,
    speech_to_text, text_to_speech) as well as total count.
    """
    try:
        if not is_supported_provider(provider):
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        counts = await get_provider_model_count(provider)
        total = sum(counts.values())
        return ProviderModelCountResponse(
            provider=provider,
            counts=counts,
            total=total,
        )
    except Exception as e:
        logger.error(f"Error getting model count for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting model count: {str(e)}"
        )


@router.get("/models/by-provider/{provider}", response_model=List[ModelResponse])
async def get_models_by_provider(provider: str):
    """
    Get all registered models for a specific provider.

    Returns models from the database that belong to the specified provider.
    """
    try:
        if not is_supported_provider(provider):
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        models = [
            model
            for model in await Model.get_all()
            if model.provider.lower() == provider.lower()
        ]
        models.sort(key=lambda model: (model.type, model.name))

        return [
            ModelResponse(
                id=model.id or "",
                name=model.name,
                provider=model.provider,
                type=model.type,
                credential=model.credential,
                created=str(model.created or ""),
                updated=str(model.updated or ""),
            )
            for model in models
        ]
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching models: {str(e)}"
        )


def _get_preferred_model(
    models: List[Dict], provider_priority: List[str], model_preferences: Dict
) -> Optional[Dict]:
    """
    Select the best model from a list based on provider priority and model preferences.

    Args:
        models: List of model dictionaries with 'provider', 'name', 'id' keys
        provider_priority: List of providers in preference order
        model_preferences: Dict mapping provider to list of preferred model name patterns

    Returns:
        The best model dict, or None if no models available
    """
    if not models:
        return None

    # Group models by provider
    by_provider: Dict[str, List[Dict]] = {}
    for model in models:
        provider = model.get("provider", "")
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)

    for provider_models in by_provider.values():
        provider_models.sort(key=lambda item: item.get("name", "").lower())

    for provider in provider_priority:
        if provider in by_provider:
            provider_models = by_provider[provider]

            # Check for preferred models within this provider
            if provider in model_preferences:
                for preference in model_preferences[provider]:
                    for model in provider_models:
                        if preference.lower() in model.get("name", "").lower():
                            return model

            # Fall back to first model from this provider
            return provider_models[0]

    # Fall back to first model from any provider
    return models[0] if models else None


@router.post("/models/auto-assign", response_model=AutoAssignResult)
async def auto_assign_defaults():
    """
    Auto-assign default models based on available models.

    This endpoint intelligently assigns the first available model of each
    required type to the corresponding default slot. It uses provider
    priority (preferring premium providers like OpenAI, Anthropic) and
    model preferences within each provider.

    Returns:
        - assigned: Dict of slot names to assigned model IDs
        - skipped: List of slots that already have models assigned
        - missing: List of slots with no available models
    """
    try:
        # Get current defaults
        defaults = await DefaultModels.get_instance()

        # Get all models grouped by type
        all_models = [
            {
                "id": model.id or "",
                "provider": model.provider,
                "name": model.name,
                "type": model.type,
            }
            for model in await Model.get_all()
        ]

        # Group models by type
        models_by_type: Dict[str, List[Dict]] = {
            "language": [],
            "embedding": [],
            "text_to_speech": [],
            "speech_to_text": [],
        }

        for model in all_models:
            model_type = model.get("type", "")
            if model_type in models_by_type:
                models_by_type[model_type].append(model)

        # Define slot configuration: (slot_name, model_type, current_value)
        slot_configs = [
            ("default_chat_model", "language", defaults.default_chat_model),  # type: ignore[attr-defined]
            ("default_transformation_model", "language", defaults.default_transformation_model),  # type: ignore[attr-defined]
            ("default_tools_model", "language", defaults.default_tools_model),  # type: ignore[attr-defined]
            ("large_context_model", "language", defaults.large_context_model),  # type: ignore[attr-defined]
            ("default_vision_model", "language", defaults.default_vision_model),  # type: ignore[attr-defined]
            ("default_embedding_model", "embedding", defaults.default_embedding_model),  # type: ignore[attr-defined]
            ("default_text_to_speech_model", "text_to_speech", defaults.default_text_to_speech_model),  # type: ignore[attr-defined]
            ("default_speech_to_text_model", "speech_to_text", defaults.default_speech_to_text_model),  # type: ignore[attr-defined]
        ]

        assigned: Dict[str, str] = {}
        skipped: List[str] = []
        missing: List[str] = []

        for slot_name, model_type, current_value in slot_configs:
            if current_value:
                # Slot already has a value
                skipped.append(slot_name)
                continue

            available_models = models_by_type.get(model_type, [])
            if not available_models:
                # No models of this type available
                missing.append(slot_name)
                continue

            # Select best model for this slot
            best_model = _get_preferred_model(
                available_models, list(get_default_model_priority(slot_name)), MODEL_PREFERENCES
            )

            if best_model:
                model_id = best_model.get("id", "")
                assigned[slot_name] = model_id
                # Update the defaults object
                setattr(defaults, slot_name, model_id)

        # Save updated defaults if any assignments were made
        if assigned:
            await defaults.update()

        return AutoAssignResult(
            assigned=assigned,
            skipped=skipped,
            missing=missing,
        )

    except Exception as e:
        logger.error(f"Error auto-assigning defaults: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error auto-assigning defaults: {str(e)}"
        )
