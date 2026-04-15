from datetime import datetime
from typing import Any, ClassVar, Dict, Optional, Union

from esperanto import (
    EmbeddingModel,
    LanguageModel,
    SpeechToTextModel,
    TextToSpeechModel,
)
from loguru import logger
from pydantic import field_validator

from open_notebook.ai.provider_runtime import create_runtime_model
from open_notebook.domain.base import ObjectModel, RecordModel
from open_notebook.exceptions import ConfigurationError, NotFoundError
from open_notebook.seekdb import ai_config_store

ModelType = Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    nullable_fields: ClassVar[set[str]] = {"credential"}
    name: str
    provider: str
    type: str
    credential: Optional[str] = None

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @classmethod
    async def get_all(cls, order_by=None):
        rows = await ai_config_store.list_models()
        return [cls(**row) for row in rows]

    @classmethod
    async def get(cls, id: str):
        row = await ai_config_store.get_model(id)
        if not row:
            raise NotFoundError(f"Model with ID {id} not found")
        return cls(**row)

    @classmethod
    async def get_models_by_type(cls, model_type):
        rows = await ai_config_store.list_models(model_type=model_type)
        return [cls(**row) for row in rows]

    @classmethod
    async def get_by_credential(cls, credential_id: str):
        """Get all models linked to a specific credential."""
        rows = await ai_config_store.list_models_by_credential(credential_id)
        return [cls(**row) for row in rows]

    def _prepare_save_data(self) -> Dict[str, Any]:
        return super()._prepare_save_data()

    async def save(self) -> None:
        row = await ai_config_store.upsert_model(self.model_dump())
        for key, value in row.items():
            if hasattr(self, key):
                setattr(self, key, value)

    async def delete(self) -> bool:
        if not self.id:
            raise NotFoundError("Cannot delete model without an ID")
        await ai_config_store.delete_model(self.id)
        return True

    async def get_credential_obj(self):
        """Get the Credential object linked to this model, if any."""
        if not self.credential:
            return None
        from open_notebook.domain.credential import Credential

        try:
            return await Credential.get(self.credential)
        except Exception:
            logger.warning(
                f"Could not load credential {self.credential} for model {self.id}"
            )
            return None


class DefaultModels(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_models"
    default_chat_model: Optional[str] = None
    default_transformation_model: Optional[str] = None
    large_context_model: Optional[str] = None
    default_vision_model: Optional[str] = None
    default_text_to_speech_model: Optional[str] = None
    default_speech_to_text_model: Optional[str] = None
    default_embedding_model: Optional[str] = None
    default_tools_model: Optional[str] = None

    @classmethod
    async def get_instance(cls) -> "DefaultModels":
        """Always fetch fresh defaults from the active config backend."""
        data = await ai_config_store.get_default_models()
        instance = object.__new__(cls)
        object.__setattr__(instance, "__dict__", {})
        super(RecordModel, instance).__init__(**data)
        return instance

    async def update(self):
        data = await ai_config_store.upsert_default_models(self.model_dump())
        for key, value in data.items():
            if hasattr(self, key):
                object.__setattr__(self, key, value)
        return self


class ModelManager:
    def __init__(self):
        pass

    async def _recover_missing_default(
        self,
        *,
        field_name: str,
        model_type: str,
        fallback_field_names: Optional[list[str]] = None,
    ) -> Optional[str]:
        defaults = await self.get_defaults()

        for fallback_field in fallback_field_names or []:
            candidate = getattr(defaults, fallback_field, None)
            if not candidate:
                continue
            try:
                model = await Model.get(candidate)
                if model.type == model_type:
                    setattr(defaults, field_name, candidate)
                    await defaults.update()
                    logger.warning(
                        f"Recovered missing default '{field_name}' with existing model '{candidate}'"
                    )
                    return candidate
            except Exception:
                continue

        candidates = await Model.get_models_by_type(model_type)
        if candidates:
            candidate_id = candidates[0].id
            setattr(defaults, field_name, candidate_id)
            await defaults.update()
            logger.warning(
                f"Recovered missing default '{field_name}' with fallback model '{candidate_id}'"
            )
            return candidate_id

        setattr(defaults, field_name, None)
        await defaults.update()
        logger.warning(
            f"Cleared stale default '{field_name}' because no {model_type} model is configured"
        )
        return None

    async def get_model(self, model_id: str, **kwargs) -> Optional[ModelType]:
        if not model_id:
            return None

        try:
            model: Model = await Model.get(model_id)
        except Exception:
            raise ConfigurationError(f"Model with ID {model_id} not found")

        if not model.type or model.type not in [
            "language",
            "embedding",
            "speech_to_text",
            "text_to_speech",
        ]:
            raise ConfigurationError(f"Invalid model type: {model.type}")

        config: dict = {}
        if model.credential:
            credential = await model.get_credential_obj()
            if credential:
                config = credential.to_runtime_config()
                logger.debug(
                    f"Using credential '{credential.name}' for model {model.name}"
                )
            else:
                from open_notebook.domain.credential import Credential

                fallback_credential = await Credential.get_latest_valid_for_provider(
                    model.provider
                )
                if fallback_credential:
                    config = fallback_credential.to_runtime_config()
                    logger.warning(
                        f"Model {model.id} is linked to unreadable credential {model.credential}. "
                        f"Using latest valid provider credential {fallback_credential.id} instead."
                    )
                else:
                    logger.warning(
                        f"Model {model.id} has credential {model.credential} but it could not be loaded. "
                        f"Falling back to env vars."
                    )
                    from open_notebook.ai.key_provider import (
                        get_provider_runtime_config,
                    )

                    config = await get_provider_runtime_config(model.provider)
        else:
            from open_notebook.ai.key_provider import get_provider_runtime_config

            config = await get_provider_runtime_config(model.provider)

        config.update(kwargs)
        return create_runtime_model(
            provider=model.provider,
            model_name=model.name,
            model_type=model.type,
            config=config,
        )

    async def get_defaults(self) -> DefaultModels:
        defaults = await DefaultModels.get_instance()
        if not defaults:
            raise RuntimeError("Failed to load default models configuration")
        return defaults

    async def get_speech_to_text(self, **kwargs) -> Optional[SpeechToTextModel]:
        defaults = await self.get_defaults()
        model_id = defaults.default_speech_to_text_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, SpeechToTextModel), (
            f"Expected SpeechToTextModel but got {type(model)}"
        )
        return model

    async def get_text_to_speech(self, **kwargs) -> Optional[TextToSpeechModel]:
        defaults = await self.get_defaults()
        model_id = defaults.default_text_to_speech_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, TextToSpeechModel), (
            f"Expected TextToSpeechModel but got {type(model)}"
        )
        return model

    async def get_embedding_model(self, **kwargs) -> Optional[EmbeddingModel]:
        defaults = await self.get_defaults()
        model_id = defaults.default_embedding_model
        if not model_id:
            return None
        try:
            model = await self.get_model(model_id, **kwargs)
        except ConfigurationError:
            model_id = await self._recover_missing_default(
                field_name="default_embedding_model",
                model_type="embedding",
            )
            if not model_id:
                return None
            model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, EmbeddingModel), (
            f"Expected EmbeddingModel but got {type(model)}"
        )
        return model

    async def get_vision_model(self, **kwargs) -> Optional[LanguageModel]:
        defaults = await self.get_defaults()
        model_id = defaults.default_vision_model
        if not model_id:
            return None
        try:
            model = await self.get_model(model_id, **kwargs)
        except ConfigurationError:
            model_id = await self._recover_missing_default(
                field_name="default_vision_model",
                model_type="language",
                fallback_field_names=["default_chat_model", "default_tools_model"],
            )
            if not model_id:
                return None
            model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, LanguageModel), (
            f"Expected LanguageModel but got {type(model)}"
        )
        return model

    async def get_default_model(self, model_type: str, **kwargs) -> Optional[ModelType]:
        defaults = await self.get_defaults()
        model_id = None

        if model_type == "chat":
            model_id = defaults.default_chat_model
        elif model_type == "transformation":
            model_id = (
                defaults.default_transformation_model or defaults.default_chat_model
            )
        elif model_type == "tools":
            model_id = defaults.default_tools_model or defaults.default_chat_model
        elif model_type == "vision":
            model_id = defaults.default_vision_model or defaults.default_chat_model
        elif model_type == "embedding":
            model_id = defaults.default_embedding_model
        elif model_type == "text_to_speech":
            model_id = defaults.default_text_to_speech_model
        elif model_type == "speech_to_text":
            model_id = defaults.default_speech_to_text_model
        elif model_type == "large_context":
            model_id = defaults.large_context_model

        if not model_id:
            logger.warning(
                f"No default model configured for type '{model_type}'. "
                f"Please go to Settings → Models and set a default model."
            )
            return None

        try:
            return await self.get_model(model_id, **kwargs)
        except (ValueError, ConfigurationError) as e:
            logger.error(
                f"Failed to load default model for type '{model_type}': {e}. "
                f"The configured model_id '{model_id}' may have been deleted or misconfigured. "
                f"Please go to Settings → Models and reconfigure the default model."
            )
            return None


model_manager = ModelManager()
