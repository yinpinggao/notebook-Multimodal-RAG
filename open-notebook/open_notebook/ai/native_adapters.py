from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import threading
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
import numpy as np
import websockets
from esperanto.common_types import (
    AudioResponse,
    EmbeddingTaskType,
    Model,
    TranscriptionResponse,
)
from esperanto.common_types.tts import Voice
from esperanto.providers.embedding.base import EmbeddingModel
from esperanto.providers.llm.openai_compatible import OpenAICompatibleLanguageModel
from esperanto.providers.stt.base import SpeechToTextModel
from esperanto.providers.tts.base import TextToSpeechModel
from loguru import logger

SPARK_HTTP_BASE_URL = "https://spark-api-open.xf-yun.com"
SPARK_IAT_WS_URL = "wss://iat-api.xfyun.cn/v2/iat"
SPARK_TTS_WS_URL = "wss://tts-api.xfyun.cn/v2/tts"
SPARK_EMBED_DOC_URL = "https://cn-huabei-1.xf-yun.com/v1/private/sa8a05c27"
SPARK_EMBED_QUERY_URL = "https://cn-huabei-1.xf-yun.com/v1/private/s50d55a16"

DOUBAO_STT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
DOUBAO_TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"

DEFAULT_SPARK_LANGUAGE_MODELS = ("spark-x", "generalv3.5", "4.0Ultra")
DEFAULT_SPARK_EMBEDDING_MODELS = ("spark-embedding",)
DEFAULT_SPARK_STT_MODELS = ("spark-stt",)
DEFAULT_SPARK_TTS_MODELS = ("spark-tts",)
DEFAULT_DOUBAO_STT_MODELS = ("doubao-stt",)
DEFAULT_DOUBAO_TTS_MODELS = ("doubao-tts",)
DEFAULT_ZHIPU_TTS_MODELS = ("cogtts",)


def _run_async_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _worker():
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive bridge
            error["value"] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def _ensure_parent_dir(path: Optional[Union[str, Path]]) -> None:
    if not path:
        return
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _persist_audio(output_file: Optional[Union[str, Path]], audio_data: bytes) -> None:
    if not output_file:
        return
    _ensure_parent_dir(output_file)
    Path(output_file).expanduser().resolve().write_bytes(audio_data)


def _read_audio_bytes(audio_file: Union[str, BinaryIO]) -> tuple[bytes, str]:
    if isinstance(audio_file, str):
        return Path(audio_file).read_bytes(), Path(audio_file).name

    stream = audio_file
    current = None
    try:
        current = stream.tell()
    except Exception:
        current = None
    payload = stream.read()
    if current is not None:
        try:
            stream.seek(current)
        except Exception:
            pass
    name = getattr(stream, "name", "audio.bin")
    return payload, str(name)


def _extract_wav_pcm(audio_bytes: bytes) -> tuple[bytes, int]:
    with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        if channels != 1:
            raise ValueError("Spark speech-to-text only supports mono PCM wav audio")
        if sample_width != 2:
            raise ValueError("Spark speech-to-text expects 16-bit PCM wav audio")
        return wav_file.readframes(wav_file.getnframes()), sample_rate


def _to_rfc1123_date() -> str:
    return format_datetime(datetime.now(timezone.utc), usegmt=True)


def _xfyun_authorized_url(base_url: str, api_key: str, api_secret: str, method: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.netloc
    path = parsed.path or "/"
    date = _to_rfc1123_date()
    request_line = f"{method.upper()} {path} HTTP/1.1"
    signature_origin = f"host: {host}\ndate: {date}\n{request_line}"
    digest = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    auth_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"authorization": authorization, "date": date, "host": host})
    return urlunparse(parsed._replace(query=urlencode(query)))


def _normalize_language(language: Optional[str]) -> str:
    if not language:
        return "zh_cn"
    normalized = language.lower().replace("-", "_")
    if normalized.startswith("en"):
        return "en_us"
    if normalized.startswith("zh"):
        return "zh_cn"
    return normalized


def _speech_text_from_ws(result: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in result.get("ws", []):
        for candidate in item.get("cw", []):
            token = candidate.get("w")
            if token:
                chunks.append(str(token))
            break
    return "".join(chunks)


def _spark_voice_alias(voice: str) -> str:
    aliases = {
        "xiaoyan": "x4_xiaoyan",
        "xiaoyu": "x4_xiaoyu",
        "xiaofeng": "x4_xiaofeng",
    }
    return aliases.get(voice, voice)


def _doubao_voice_alias(voice: str) -> str:
    aliases = {
        "alloy": "zh_male_M392_conversation_wvae_bigtts",
        "default": "zh_male_M392_conversation_wvae_bigtts",
    }
    return aliases.get(voice, voice)


def _safe_model_name(model_name: Optional[str], default: str) -> str:
    if model_name and model_name.strip():
        return model_name.strip()
    return default


@dataclass
class SparkLanguageAdapter(OpenAICompatibleLanguageModel):
    def _get_default_model(self) -> str:
        return "spark-x"

    @property
    def provider(self) -> str:
        return "spark"

    def __post_init__(self):
        if not self.model_name:
            self.model_name = self._get_default_model()

        config = dict(self.config or {})
        raw_api_key = self.api_key or config.get("api_key")
        api_secret = config.get("api_secret")
        base_url = self.base_url or config.get("base_url")

        if not base_url:
            model_name = _safe_model_name(self.model_name, self._get_default_model())
            if model_name == "spark-x2":
                base_url = f"{SPARK_HTTP_BASE_URL}/x2"
            elif model_name == "spark-x":
                base_url = f"{SPARK_HTTP_BASE_URL}/v2"
            else:
                base_url = f"{SPARK_HTTP_BASE_URL}/v1"

        # Spark officially accepts APIpassword or api_key:api_secret as bearer token.
        if raw_api_key and api_secret and ":" not in raw_api_key:
            raw_api_key = f"{raw_api_key}:{api_secret}"
        if not raw_api_key:
            raise ValueError(
                "Spark language model requires api_key, or api_key plus extra_config.api_secret"
            )

        self.base_url = base_url
        self.api_key = raw_api_key
        config["api_key"] = raw_api_key
        self.config = config
        super().__post_init__()


@dataclass
class SparkEmbeddingAdapter(EmbeddingModel):
    def __post_init__(self):
        super().__post_init__()
        self.model_name = _safe_model_name(self.model_name, self._get_default_model())
        self._config.update(self.config or {})

    @property
    def provider(self) -> str:
        return "spark"

    def _get_default_model(self) -> str:
        return "spark-embedding"

    def _get_models(self) -> List[Model]:
        return [Model(id=name, owned_by="spark") for name in DEFAULT_SPARK_EMBEDDING_MODELS]

    def _resolve_task_endpoint(self, task_type: Optional[Union[str, EmbeddingTaskType]]) -> str:
        if isinstance(task_type, EmbeddingTaskType):
            task_value = task_type.value
        else:
            task_value = str(task_type or "").lower()

        model_name = self.get_model_name().lower()
        if any(token in task_value for token in ("query", "retrieval.query", "retrieval_query")):
            return self._config.get("embedding_query_url") or SPARK_EMBED_QUERY_URL
        if any(token in model_name for token in ("query", "embeddingq")):
            return self._config.get("embedding_query_url") or SPARK_EMBED_QUERY_URL
        return self._config.get("embedding_doc_url") or SPARK_EMBED_DOC_URL

    def _require_auth(self) -> tuple[str, str, str]:
        api_key = self.api_key or self._config.get("api_key")
        app_id = self._config.get("app_id")
        api_secret = self._config.get("api_secret")
        if not api_key or not app_id or not api_secret:
            raise ValueError(
                "Spark embedding requires api_key, extra_config.app_id, and extra_config.api_secret"
            )
        return str(api_key), str(app_id), str(api_secret)

    async def aembed(self, texts: List[str], **kwargs) -> List[List[float]]:
        if not texts:
            return []

        api_key, app_id, api_secret = self._require_auth()
        task_type = kwargs.get("task_type") or self._config.get("task_type")
        endpoint = self._resolve_task_endpoint(task_type)
        signed_url = _xfyun_authorized_url(endpoint, api_key, api_secret, "POST")
        timeout = float(self._config.get("timeout", 60.0))

        results: list[list[float]] = []
        async with httpx.AsyncClient(timeout=timeout) as client:
            for text in texts:
                payload = {
                    "header": {"app_id": app_id, "uid": "open-notebook", "status": 3},
                    "parameter": {"emb": {"feature": {"encoding": "utf8"}}},
                    "payload": {
                        "messages": {
                            "text": base64.b64encode(
                                json.dumps(
                                    {"messages": [{"content": text, "role": "user"}]},
                                    ensure_ascii=False,
                                ).encode("utf-8")
                            ).decode("utf-8")
                        }
                    },
                }
                response = await client.post(signed_url, json=payload)
                response.raise_for_status()
                data = response.json()
                header = data.get("header", {})
                if int(header.get("code", 0)) != 0:
                    raise RuntimeError(f"Spark embedding error: {header.get('message')}")
                encoded = (
                    data.get("payload", {})
                    .get("feature", {})
                    .get("text")
                )
                if not encoded:
                    raise RuntimeError("Spark embedding returned an empty vector payload")
                raw = base64.b64decode(encoded)
                vector = np.frombuffer(
                    raw, dtype=np.dtype(np.float32).newbyteorder("<")
                ).tolist()
                results.append([float(value) for value in vector])
        return results

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        return _run_async_sync(self.aembed(texts, **kwargs))


@dataclass
class SparkSpeechToTextAdapter(SpeechToTextModel):
    def __post_init__(self):
        super().__post_init__()
        self.model_name = _safe_model_name(self.model_name, self._get_default_model())
        self._config.update(self.config or {})

    @property
    def provider(self) -> str:
        return "spark"

    def _get_default_model(self) -> str:
        return "spark-stt"

    def _get_models(self) -> List[Model]:
        return [Model(id=name, owned_by="spark") for name in DEFAULT_SPARK_STT_MODELS]

    def _require_auth(self) -> tuple[str, str, str]:
        api_key = self.api_key or self._config.get("api_key")
        app_id = self._config.get("app_id")
        api_secret = self._config.get("api_secret")
        if not api_key or not app_id or not api_secret:
            raise ValueError(
                "Spark speech-to-text requires api_key, extra_config.app_id, and extra_config.api_secret"
            )
        return str(api_key), str(app_id), str(api_secret)

    async def atranscribe(
        self,
        audio_file: Union[str, BinaryIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResponse:
        del prompt

        api_key, app_id, api_secret = self._require_auth()
        audio_bytes, _filename = _read_audio_bytes(audio_file)
        pcm_audio, sample_rate = _extract_wav_pcm(audio_bytes)
        signed_url = _xfyun_authorized_url(SPARK_IAT_WS_URL, api_key, api_secret, "GET")

        business = {
            "language": _normalize_language(language),
            "domain": self._config.get("domain", "iat"),
            "accent": self._config.get("accent", "mandarin"),
            "ptt": int(self._config.get("ptt", 1)),
        }
        frame_size = int(self._config.get("frame_size", 1280))
        frame_interval = float(self._config.get("frame_interval", 0.04))

        segments: dict[int, str] = {}
        async with websockets.connect(signed_url, max_size=None) as websocket:
            finished = False
            for index in range(0, len(pcm_audio), frame_size):
                chunk = pcm_audio[index : index + frame_size]
                if index == 0:
                    status = 0
                elif index + frame_size >= len(pcm_audio):
                    status = 2
                else:
                    status = 1

                payload: dict[str, Any] = {
                    "data": {
                        "status": status,
                        "format": f"audio/L16;rate={sample_rate}",
                        "encoding": "raw",
                        "audio": base64.b64encode(chunk).decode("utf-8"),
                    }
                }
                if status == 0:
                    payload["common"] = {"app_id": app_id}
                    payload["business"] = business

                await websocket.send(json.dumps(payload, ensure_ascii=False))
                response = await websocket.recv()
                message = json.loads(response)
                code = int(message.get("code", 0))
                if code != 0:
                    raise RuntimeError(
                        f"Spark speech-to-text error {code}: {message.get('message')}"
                    )
                data = message.get("data", {})
                result = data.get("result", {})
                sn = int(result.get("sn", len(segments)))
                text_piece = _speech_text_from_ws(result)
                if text_piece:
                    segments[sn] = text_piece
                if bool(result.get("ls")) or int(data.get("status", 1)) == 2:
                    finished = True
                    break
                await asyncio.sleep(frame_interval)

            if len(pcm_audio) == 0:
                await websocket.send(json.dumps({"data": {"status": 2}}))

            while not finished:
                response = await websocket.recv()
                message = json.loads(response)
                code = int(message.get("code", 0))
                if code != 0:
                    raise RuntimeError(
                        f"Spark speech-to-text error {code}: {message.get('message')}"
                    )
                data = message.get("data", {})
                result = data.get("result", {})
                sn = int(result.get("sn", len(segments)))
                text_piece = _speech_text_from_ws(result)
                if text_piece:
                    segments[sn] = text_piece
                if bool(result.get("ls")) or int(data.get("status", 1)) == 2:
                    finished = True

        ordered = "".join(segments[key] for key in sorted(segments))
        return TranscriptionResponse(
            text=ordered.strip(),
            language=_normalize_language(language),
            model=self.get_model_name(),
            metadata={"provider": self.provider},
        )

    def transcribe(
        self,
        audio_file: Union[str, BinaryIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResponse:
        return _run_async_sync(self.atranscribe(audio_file, language=language, prompt=prompt))


@dataclass
class SparkTextToSpeechAdapter(TextToSpeechModel):
    def __post_init__(self):
        super().__post_init__()
        self.model_name = _safe_model_name(self.model_name, self._get_default_model())
        self._config.update(self.config or {})

    @property
    def provider(self) -> str:
        return "spark"

    def _get_default_model(self) -> str:
        return "spark-tts"

    def _get_models(self) -> List[Model]:
        return [Model(id=name, owned_by="spark") for name in DEFAULT_SPARK_TTS_MODELS]

    @property
    def available_voices(self) -> Dict[str, Voice]:
        return {
            "x4_xiaoyan": Voice(
                id="x4_xiaoyan",
                name="x4_xiaoyan",
                language_code="zh-CN",
                gender="FEMALE",
                description="讯飞小燕",
            ),
            "x4_xiaoyu": Voice(
                id="x4_xiaoyu",
                name="x4_xiaoyu",
                language_code="zh-CN",
                gender="FEMALE",
                description="讯飞小宇",
            ),
        }

    async def agenerate_speech(
        self,
        text: str,
        voice: str,
        output_file: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> AudioResponse:
        api_key = self.api_key or self._config.get("api_key")
        app_id = self._config.get("app_id")
        api_secret = self._config.get("api_secret")
        if not api_key or not app_id or not api_secret:
            raise ValueError(
                "Spark text-to-speech requires api_key, extra_config.app_id, and extra_config.api_secret"
            )

        signed_url = _xfyun_authorized_url(SPARK_TTS_WS_URL, str(api_key), str(api_secret), "GET")
        audio_chunks: list[bytes] = []
        async with websockets.connect(signed_url, max_size=None) as websocket:
            payload = {
                "common": {"app_id": str(app_id)},
                "business": {
                    "aue": kwargs.get("aue", "lame"),
                    "sfl": 1,
                    "vcn": _spark_voice_alias(voice),
                    "speed": int(kwargs.get("speed", 50)),
                    "pitch": int(kwargs.get("pitch", 50)),
                },
                "data": {
                    "status": 2,
                    "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
                },
            }
            await websocket.send(json.dumps(payload, ensure_ascii=False))

            while True:
                response = await websocket.recv()
                message = json.loads(response)
                code = int(message.get("code", 0))
                if code != 0:
                    raise RuntimeError(
                        f"Spark text-to-speech error {code}: {message.get('message')}"
                    )
                data = message.get("data", {})
                encoded = data.get("audio")
                if encoded:
                    audio_chunks.append(base64.b64decode(encoded))
                if int(data.get("status", 1)) == 2:
                    break

        audio_data = b"".join(audio_chunks)
        _persist_audio(output_file, audio_data)
        return AudioResponse(
            audio_data=audio_data,
            content_type="audio/mpeg",
            model=self.get_model_name(),
            voice=_spark_voice_alias(voice),
            provider=self.provider,
            metadata={"provider": self.provider},
        )

    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> AudioResponse:
        return _run_async_sync(
            self.agenerate_speech(text, voice, output_file=output_file, **kwargs)
        )


@dataclass
class DoubaoSpeechToTextAdapter(SpeechToTextModel):
    def __post_init__(self):
        super().__post_init__()
        self.model_name = _safe_model_name(self.model_name, self._get_default_model())
        self._config.update(self.config or {})

    @property
    def provider(self) -> str:
        return "doubao"

    def _get_default_model(self) -> str:
        return "doubao-stt"

    def _get_models(self) -> List[Model]:
        return [Model(id=name, owned_by="doubao") for name in DEFAULT_DOUBAO_STT_MODELS]

    def _build_headers(self) -> dict[str, str]:
        request_id = str(uuid.uuid4())
        resource_id = str(
            self._config.get("speech_resource_id", "volc.bigasr.auc_turbo")
        )
        speech_app_id = self._config.get("speech_app_id")
        speech_token = self._config.get("speech_token")
        api_key = self.api_key or self._config.get("api_key")

        headers = {
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
        }
        if speech_app_id and speech_token:
            headers["X-Api-App-Key"] = str(speech_app_id)
            headers["X-Api-Access-Key"] = str(speech_token)
            return headers
        if api_key:
            headers["X-Api-Key"] = str(api_key)
            return headers
        raise ValueError(
            "Doubao speech-to-text requires either api_key or extra_config.speech_app_id + speech_token"
        )

    async def atranscribe(
        self,
        audio_file: Union[str, BinaryIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResponse:
        del language, prompt

        audio_bytes, _ = _read_audio_bytes(audio_file)
        endpoint = str(self._config.get("speech_endpoint") or DOUBAO_STT_URL)
        body = {
            "user": {"uid": str(self._config.get("speech_app_id") or "open-notebook")},
            "audio": {"data": base64.b64encode(audio_bytes).decode("utf-8")},
            "request": {
                "model_name": self._config.get("speech_model_name", "bigmodel"),
            },
        }

        async with httpx.AsyncClient(timeout=float(self._config.get("timeout", 180.0))) as client:
            response = await client.post(endpoint, json=body, headers=self._build_headers())
            response.raise_for_status()
            payload = response.json()

        status_code = response.headers.get("X-Api-Status-Code", "20000000")
        if status_code != "20000000":
            raise RuntimeError(
                f"Doubao speech-to-text error {status_code}: {response.headers.get('X-Api-Message', 'unknown error')}"
            )

        result = payload.get("result", {})
        return TranscriptionResponse(
            text=str(result.get("text") or ""),
            language=None,
            duration=float(payload.get("audio_info", {}).get("duration", 0)) / 1000.0
            if payload.get("audio_info", {}).get("duration") is not None
            else None,
            model=self.get_model_name(),
            metadata={"provider": self.provider, "raw": payload},
        )

    def transcribe(
        self,
        audio_file: Union[str, BinaryIO],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResponse:
        return _run_async_sync(self.atranscribe(audio_file, language=language, prompt=prompt))


@dataclass
class DoubaoTextToSpeechAdapter(TextToSpeechModel):
    def __post_init__(self):
        super().__post_init__()
        self.model_name = _safe_model_name(self.model_name, self._get_default_model())
        self._config.update(self.config or {})

    @property
    def provider(self) -> str:
        return "doubao"

    def _get_default_model(self) -> str:
        return "doubao-tts"

    def _get_models(self) -> List[Model]:
        return [Model(id=name, owned_by="doubao") for name in DEFAULT_DOUBAO_TTS_MODELS]

    @property
    def available_voices(self) -> Dict[str, Voice]:
        return {
            "zh_male_M392_conversation_wvae_bigtts": Voice(
                id="zh_male_M392_conversation_wvae_bigtts",
                name="zh_male_M392_conversation_wvae_bigtts",
                language_code="zh-CN",
                gender="MALE",
                description="豆包对话男声",
            ),
            "zh_female_vv_uranus_bigtts": Voice(
                id="zh_female_vv_uranus_bigtts",
                name="zh_female_vv_uranus_bigtts",
                language_code="zh-CN",
                gender="FEMALE",
                description="豆包女声",
            ),
        }

    async def agenerate_speech(
        self,
        text: str,
        voice: str,
        output_file: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> AudioResponse:
        speech_app_id = self._config.get("speech_app_id")
        token = self._config.get("speech_token") or self.api_key or self._config.get("api_key")
        if not speech_app_id or not token:
            raise ValueError(
                "Doubao text-to-speech requires extra_config.speech_app_id and speech_token (or api_key)"
            )

        endpoint = str(self._config.get("speech_endpoint") or DOUBAO_TTS_URL)
        headers = {
            "Authorization": f"Bearer;{token}",
            "Content-Type": "application/json",
        }
        body = {
            "app": {
                "appid": str(speech_app_id),
                "token": "unused",
                "cluster": self._config.get("speech_cluster", "volcano_tts"),
            },
            "user": {"uid": str(kwargs.get("uid", "open-notebook"))},
            "audio": {
                "voice_type": _doubao_voice_alias(voice),
                "encoding": kwargs.get("encoding", "mp3"),
                "speed_ratio": float(kwargs.get("speed_ratio", 1.0)),
                "rate": int(kwargs.get("rate", 24000)),
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "query",
            },
        }
        if self.get_model_name() not in DEFAULT_DOUBAO_TTS_MODELS:
            body["request"]["model"] = self.get_model_name()

        async with httpx.AsyncClient(timeout=float(self._config.get("timeout", 120.0))) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

        if int(payload.get("code", 0)) != 3000:
            # 3000 is the common success code for the legacy non-streaming TTS API.
            # Some environments may also return 0, so accept it as well.
            if int(payload.get("code", 0)) != 0:
                raise RuntimeError(
                    f"Doubao text-to-speech error {payload.get('code')}: {payload.get('message')}"
                )

        audio_data = base64.b64decode(payload.get("data", ""))
        _persist_audio(output_file, audio_data)
        return AudioResponse(
            audio_data=audio_data,
            content_type="audio/mpeg",
            duration=float(payload.get("addition", {}).get("duration", 0)) / 1000.0
            if payload.get("addition", {}).get("duration") is not None
            else None,
            model=self.get_model_name(),
            voice=_doubao_voice_alias(voice),
            provider=self.provider,
            metadata={"provider": self.provider, "raw": payload},
        )

    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> AudioResponse:
        return _run_async_sync(
            self.agenerate_speech(text, voice, output_file=output_file, **kwargs)
        )


@dataclass
class ZhipuTextToSpeechAdapter(TextToSpeechModel):
    def __post_init__(self):
        super().__post_init__()
        self.model_name = _safe_model_name(self.model_name, self._get_default_model())
        self.base_url = (self.base_url or self._config.get("base_url") or "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
        self.api_key = self.api_key or self._config.get("api_key")
        self._config.update(self.config or {})

    @property
    def provider(self) -> str:
        return "zhipu"

    def _get_default_model(self) -> str:
        return "cogtts"

    def _get_models(self) -> List[Model]:
        return [Model(id=name, owned_by="zhipu") for name in DEFAULT_ZHIPU_TTS_MODELS]

    @property
    def available_voices(self) -> Dict[str, Voice]:
        return {
            "alloy": Voice(
                id="alloy",
                name="alloy",
                language_code="zh-CN",
                gender="NEUTRAL",
                description="Zhipu default voice",
            )
        }

    async def agenerate_speech(
        self,
        text: str,
        voice: str,
        output_file: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> AudioResponse:
        if not self.api_key:
            raise ValueError("Zhipu text-to-speech requires api_key")

        # Zhipu's public API keeps OpenAI-style audio/speech semantics on the official base URL.
        payload = {
            "model": self.get_model_name(),
            "input": text,
            "voice": kwargs.get("voice", voice),
            "response_format": kwargs.get("response_format", "mp3"),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=float(self._config.get("timeout", 120.0))) as client:
            response = await client.post(
                f"{self.base_url}/audio/speech",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        response_content_type = response.headers.get("content-type", "audio/mpeg")
        if "json" in response_content_type.lower():
            json_payload = response.json()
            encoded_audio = (
                json_payload.get("data")
                or json_payload.get("audio")
                or json_payload.get("audio_data")
            )
            if not encoded_audio:
                raise RuntimeError("Zhipu text-to-speech returned JSON without audio content")
            audio_data = base64.b64decode(encoded_audio)
        else:
            audio_data = response.content
        _persist_audio(output_file, audio_data)
        return AudioResponse(
            audio_data=audio_data,
            content_type=response_content_type,
            model=self.get_model_name(),
            voice=str(payload["voice"]),
            provider=self.provider,
            metadata={"provider": self.provider},
        )

    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> AudioResponse:
        return _run_async_sync(
            self.agenerate_speech(text, voice, output_file=output_file, **kwargs)
        )
