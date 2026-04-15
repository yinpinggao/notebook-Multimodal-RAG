"""
Credential domain model for storing individual provider credentials.

Supports SeekDB as the primary AI config store, with environment variable fallback.
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from loguru import logger
from pydantic import Field, SecretStr

from open_notebook.ai.provider_catalog import get_sensitive_extra_config_keys
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import NotFoundError
from open_notebook.seekdb import ai_config_store
from open_notebook.utils.encryption import decrypt_value, encrypt_value


class Credential(ObjectModel):
    table_name: ClassVar[str] = "credential"
    nullable_fields: ClassVar[set[str]] = {
        "api_key",
        "base_url",
        "endpoint",
        "api_version",
        "endpoint_llm",
        "endpoint_embedding",
        "endpoint_stt",
        "endpoint_tts",
        "project",
        "location",
        "credentials_path",
    }

    name: str
    provider: str
    modalities: List[str] = []
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    api_version: Optional[str] = None
    endpoint_llm: Optional[str] = None
    endpoint_embedding: Optional[str] = None
    endpoint_stt: Optional[str] = None
    endpoint_tts: Optional[str] = None
    project: Optional[str] = None
    location: Optional[str] = None
    credentials_path: Optional[str] = None
    extra_config: Dict[str, Any] = Field(default_factory=dict)

    def _prepare_extra_config_for_storage(self) -> Dict[str, Any]:
        payload = dict(self.extra_config or {})
        secret_keys = get_sensitive_extra_config_keys(self.provider)
        for key in secret_keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                payload[key] = encrypt_value(value)
        return payload

    @classmethod
    def _restore_extra_config(
        cls, provider: str, extra_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        payload = dict(extra_config or {})
        secret_keys = get_sensitive_extra_config_keys(provider)
        for key in secret_keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                try:
                    payload[key] = decrypt_value(value)
                except Exception:
                    logger.warning(
                        f"Failed to decrypt extra_config field '{key}' for provider '{provider}'"
                    )
        return payload

    def to_runtime_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {}
        if self.api_key:
            config["api_key"] = self.api_key.get_secret_value()
        if self.base_url:
            config["base_url"] = self.base_url
        if self.endpoint:
            config["endpoint"] = self.endpoint
        if self.api_version:
            config["api_version"] = self.api_version
        if self.endpoint_llm:
            config["endpoint_llm"] = self.endpoint_llm
        if self.endpoint_embedding:
            config["endpoint_embedding"] = self.endpoint_embedding
        if self.endpoint_stt:
            config["endpoint_stt"] = self.endpoint_stt
        if self.endpoint_tts:
            config["endpoint_tts"] = self.endpoint_tts
        if self.project:
            config["project"] = self.project
        if self.location:
            config["location"] = self.location
        if self.credentials_path:
            config["credentials_path"] = self.credentials_path
        if self.extra_config:
            config["extra_config"] = dict(self.extra_config)
        return config

    def to_esperanto_config(self) -> Dict[str, Any]:
        return self.to_runtime_config()

    @classmethod
    def _decode_rows(cls, rows: List[dict], *, context: str) -> List["Credential"]:
        credentials: List["Credential"] = []
        for row in rows:
            try:
                credentials.append(cls._from_db_row(row))
            except Exception as e:
                row_id = None
                if isinstance(row, dict):
                    row_id = row.get("id")
                logger.warning(
                    f"Skipping unreadable credential {row_id or '<unknown>'} while {context}: {e}"
                )
        return credentials

    @classmethod
    async def get_by_provider(cls, provider: str) -> List["Credential"]:
        rows = await ai_config_store.list_credentials(provider)
        return cls._decode_rows(
            rows, context=f"listing SeekDB credentials for provider '{provider}'"
        )

    @classmethod
    async def get(cls, id: str) -> "Credential":
        row = await ai_config_store.get_credential(id)
        if not row:
            raise NotFoundError(f"Credential with id {id} not found")
        return cls._from_db_row(row)

    @classmethod
    async def get_all(cls, order_by=None) -> List["Credential"]:
        rows = await ai_config_store.list_credentials()
        return cls._decode_rows(rows, context="listing SeekDB credentials")

    @classmethod
    async def get_latest_valid_for_provider(cls, provider: str) -> Optional["Credential"]:
        credentials = await cls.get_by_provider(provider)
        if not credentials:
            return None
        credentials.sort(
            key=lambda cred: cred.updated or cred.created or datetime.min,
        )
        return credentials[-1]

    async def get_linked_models(self) -> list:
        if not self.id:
            return []
        from open_notebook.ai.models import Model

        results = await ai_config_store.list_models_by_credential(self.id)
        return [Model(**row) for row in results]

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = {}
        for key, value in self.model_dump().items():
            if key == "api_key":
                if self.api_key:
                    secret_value = self.api_key.get_secret_value()
                    data["api_key"] = encrypt_value(secret_value)
                else:
                    data["api_key"] = None
            elif value is not None or key in self.__class__.nullable_fields:
                data[key] = value
        data["extra_config"] = self._prepare_extra_config_for_storage()

        return data

    async def save(self) -> None:
        original_api_key = self.api_key

        row = await ai_config_store.upsert_credential(self._prepare_save_data() | {"id": self.id})
        for key, value in row.items():
            if key == "api_key":
                continue
            if hasattr(self, key):
                setattr(self, key, value)
        if original_api_key:
            object.__setattr__(self, "api_key", original_api_key)
        elif row.get("api_key"):
            object.__setattr__(
                self, "api_key", SecretStr(decrypt_value(row["api_key"]))
            )

    async def delete(self) -> bool:
        if not self.id:
            raise NotFoundError("Cannot delete credential without an ID")
        await ai_config_store.delete_credential(self.id)
        return True

    @classmethod
    def _from_db_row(cls, row: dict) -> "Credential":
        row = dict(row)
        api_key_val = row.get("api_key")
        if api_key_val and isinstance(api_key_val, str):
            decrypted = decrypt_value(api_key_val)
            row["api_key"] = SecretStr(decrypted)
        elif api_key_val is None:
            row["api_key"] = None
        row["extra_config"] = cls._restore_extra_config(
            row.get("provider", ""), row.get("extra_config")
        )
        return cls(**row)
