import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .client import seekdb_client


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _decode_modalities(row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not row:
        return row
    decoded = dict(row)
    decoded["modalities"] = json.loads(decoded.get("modalities_json") or "[]")
    decoded["extra_config"] = json.loads(decoded.get("extra_config_json") or "{}")
    decoded.pop("modalities_json", None)
    decoded.pop("extra_config_json", None)
    return decoded


def _new_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex}"


class AIConfigStore:
    async def list_credentials(
        self, provider: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if provider:
            rows = await seekdb_client.fetch_all(
                """
                SELECT * FROM ai_credentials
                WHERE LOWER(provider) = LOWER(%s)
                ORDER BY created ASC
                """,
                (provider,),
            )
        else:
            rows = await seekdb_client.fetch_all(
                "SELECT * FROM ai_credentials ORDER BY provider ASC, created ASC"
            )
        return [_decode_modalities(row) for row in rows if row]

    async def get_credential(self, credential_id: str) -> Optional[dict[str, Any]]:
        row = await seekdb_client.fetch_one(
            "SELECT * FROM ai_credentials WHERE id = %s",
            (credential_id,),
        )
        return _decode_modalities(row)

    async def upsert_credential(self, data: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        credential_id = data.get("id") or _new_id("credential")
        created = data.get("created") or now

        await seekdb_client.execute(
            """
            INSERT INTO ai_credentials (
                id, name, provider, modalities_json, api_key, base_url, endpoint,
                api_version, endpoint_llm, endpoint_embedding, endpoint_stt,
                endpoint_tts, project, location, credentials_path, extra_config_json, created, updated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                provider = VALUES(provider),
                modalities_json = VALUES(modalities_json),
                api_key = VALUES(api_key),
                base_url = VALUES(base_url),
                endpoint = VALUES(endpoint),
                api_version = VALUES(api_version),
                endpoint_llm = VALUES(endpoint_llm),
                endpoint_embedding = VALUES(endpoint_embedding),
                endpoint_stt = VALUES(endpoint_stt),
                endpoint_tts = VALUES(endpoint_tts),
                project = VALUES(project),
                location = VALUES(location),
                credentials_path = VALUES(credentials_path),
                extra_config_json = VALUES(extra_config_json),
                created = VALUES(created),
                updated = VALUES(updated)
            """,
            (
                credential_id,
                data.get("name"),
                data.get("provider"),
                json.dumps(data.get("modalities") or []),
                data.get("api_key"),
                data.get("base_url"),
                data.get("endpoint"),
                data.get("api_version"),
                data.get("endpoint_llm"),
                data.get("endpoint_embedding"),
                data.get("endpoint_stt"),
                data.get("endpoint_tts"),
                data.get("project"),
                data.get("location"),
                data.get("credentials_path"),
                json.dumps(data.get("extra_config") or {}),
                created,
                now,
            ),
        )
        return (await self.get_credential(credential_id)) or {}

    async def delete_credential(self, credential_id: str) -> None:
        await seekdb_client.execute(
            "DELETE FROM ai_credentials WHERE id = %s", (credential_id,)
        )

    async def list_models(self, model_type: Optional[str] = None) -> list[dict[str, Any]]:
        if model_type:
            return await seekdb_client.fetch_all(
                "SELECT * FROM ai_models WHERE type = %s ORDER BY provider ASC, name ASC",
                (model_type,),
            )
        return await seekdb_client.fetch_all(
            "SELECT * FROM ai_models ORDER BY provider ASC, name ASC"
        )

    async def list_models_by_provider(self, provider: str) -> list[dict[str, Any]]:
        return await seekdb_client.fetch_all(
            "SELECT * FROM ai_models WHERE provider = %s ORDER BY type ASC, name ASC",
            (provider,),
        )

    async def get_model(self, model_id: str) -> Optional[dict[str, Any]]:
        return await seekdb_client.fetch_one(
            "SELECT * FROM ai_models WHERE id = %s",
            (model_id,),
        )

    async def list_models_by_credential(self, credential_id: str) -> list[dict[str, Any]]:
        return await seekdb_client.fetch_all(
            "SELECT * FROM ai_models WHERE credential = %s",
            (credential_id,),
        )

    async def upsert_model(self, data: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        model_id = data.get("id") or _new_id("model")
        created = data.get("created") or now

        await seekdb_client.execute(
            """
            INSERT INTO ai_models (
                id, name, provider, type, credential, created, updated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                provider = VALUES(provider),
                type = VALUES(type),
                credential = VALUES(credential),
                created = VALUES(created),
                updated = VALUES(updated)
            """,
            (
                model_id,
                data.get("name"),
                data.get("provider"),
                data.get("type"),
                data.get("credential"),
                created,
                now,
            ),
        )
        return (await self.get_model(model_id)) or {}

    async def delete_model(self, model_id: str) -> None:
        await seekdb_client.execute("DELETE FROM ai_models WHERE id = %s", (model_id,))

    async def get_default_models(self) -> dict[str, Any]:
        record = await seekdb_client.fetch_one(
            "SELECT * FROM ai_default_models WHERE id = %s",
            ("open_notebook:default_models",),
        )
        if record:
            return record

        now = _now()
        await seekdb_client.execute(
            """
            INSERT INTO ai_default_models (
                id, default_chat_model, default_transformation_model,
                large_context_model, default_vision_model, default_text_to_speech_model,
                default_speech_to_text_model, default_embedding_model,
                default_tools_model, created, updated
            ) VALUES (%s, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, %s, %s)
            """,
            ("open_notebook:default_models", now, now),
        )
        return (
            await seekdb_client.fetch_one(
                "SELECT * FROM ai_default_models WHERE id = %s",
                ("open_notebook:default_models",),
            )
        ) or {"id": "open_notebook:default_models"}

    async def upsert_default_models(self, data: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        current = await self.get_default_models()
        created = current.get("created") or now
        await seekdb_client.execute(
            """
            INSERT INTO ai_default_models (
                id, default_chat_model, default_transformation_model,
                large_context_model, default_vision_model, default_text_to_speech_model,
                default_speech_to_text_model, default_embedding_model,
                default_tools_model, created, updated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                default_chat_model = VALUES(default_chat_model),
                default_transformation_model = VALUES(default_transformation_model),
                large_context_model = VALUES(large_context_model),
                default_vision_model = VALUES(default_vision_model),
                default_text_to_speech_model = VALUES(default_text_to_speech_model),
                default_speech_to_text_model = VALUES(default_speech_to_text_model),
                default_embedding_model = VALUES(default_embedding_model),
                default_tools_model = VALUES(default_tools_model),
                created = VALUES(created),
                updated = VALUES(updated)
            """,
            (
                "open_notebook:default_models",
                data.get("default_chat_model"),
                data.get("default_transformation_model"),
                data.get("large_context_model"),
                data.get("default_vision_model"),
                data.get("default_text_to_speech_model"),
                data.get("default_speech_to_text_model"),
                data.get("default_embedding_model"),
                data.get("default_tools_model"),
                created,
                now,
            ),
        )
        return await self.get_default_models()


ai_config_store = AIConfigStore()
