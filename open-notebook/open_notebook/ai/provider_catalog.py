from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional

ProviderModality = Literal[
    "language",
    "embedding",
    "vision",
    "speech_to_text",
    "text_to_speech",
]
CredentialFieldType = Literal["text", "password", "url", "path", "select"]
CredentialFieldTarget = Literal["common", "extra"]
RuntimeFamily = Literal["compat", "native_deepseek", "native_ollama", "spark"]


@dataclass(frozen=True)
class ProviderCatalogField:
    name: str
    label: str
    field_type: CredentialFieldType
    target: CredentialFieldTarget = "common"
    required: bool = False
    secret: bool = False
    placeholder: Optional[str] = None
    description: Optional[str] = None
    options: tuple[dict[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["options"] = list(self.options)
        return payload


@dataclass(frozen=True)
class ProviderCatalogEntry:
    id: str
    display_name: str
    docs_url: str
    sort_order: int
    modalities: tuple[ProviderModality, ...]
    runtime_family: RuntimeFamily
    runtime_provider: str
    default_base_url: Optional[str] = None
    default_regions: dict[str, str] = field(default_factory=dict)
    env_config: dict[str, list[str]] = field(default_factory=dict)
    credential_fields: tuple[ProviderCatalogField, ...] = ()
    curated_models: dict[str, tuple[str, ...]] = field(default_factory=dict)
    test_model: Optional[tuple[str, str]] = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "docs_url": self.docs_url,
            "sort_order": self.sort_order,
            "modalities": list(self.modalities),
            "runtime_family": self.runtime_family,
            "default_base_url": self.default_base_url,
            "credential_fields": [field.to_dict() for field in self.credential_fields],
        }


COMMON_API_KEY_FIELD = ProviderCatalogField(
    name="api_key",
    label="API Key",
    field_type="password",
    target="common",
    required=True,
    secret=True,
    placeholder="sk-...",
)

COMMON_BASE_URL_FIELD = ProviderCatalogField(
    name="base_url",
    label="Base URL",
    field_type="url",
    target="common",
    required=False,
    placeholder="https://api.example.com/v1",
    description="Override the default API base URL when needed.",
)

REGION_FIELD = ProviderCatalogField(
    name="region",
    label="Region",
    field_type="select",
    target="extra",
    required=False,
    description="Optional deployment region preset.",
    options=(
        {"label": "China Mainland", "value": "cn"},
        {"label": "International", "value": "intl"},
        {"label": "United States", "value": "us"},
    ),
)


PROVIDER_CATALOG: dict[str, ProviderCatalogEntry] = {
    "tongyi": ProviderCatalogEntry(
        id="tongyi",
        display_name="阿里通义",
        docs_url="https://www.aliyun.com/product/bailian",
        sort_order=10,
        modalities=("language", "embedding", "vision"),
        runtime_family="compat",
        runtime_provider="openai-compatible",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_regions={
            "cn": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "intl": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "us": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        },
        env_config={
            "required_any": ["TONGYI_API_KEY", "DASHSCOPE_API_KEY"],
            "optional": ["TONGYI_REGION", "TONGYI_BASE_URL"],
        },
        credential_fields=(COMMON_API_KEY_FIELD, COMMON_BASE_URL_FIELD, REGION_FIELD),
        curated_models={
            "language": ("qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"),
            "embedding": ("text-embedding-v3", "text-embedding-v2"),
            "vision": ("qwen-vl-max-latest", "qwen2.5-vl-72b-instruct"),
        },
        test_model=("qwen-plus", "language"),
    ),
    "wenxin": ProviderCatalogEntry(
        id="wenxin",
        display_name="百度文心",
        docs_url="https://cloud.baidu.com/product/wenxinworkshop",
        sort_order=20,
        modalities=("language", "embedding", "vision"),
        runtime_family="compat",
        runtime_provider="openai-compatible",
        default_base_url="https://qianfan.baidubce.com/v2",
        env_config={
            "required_any": ["WENXIN_API_KEY", "QIANFAN_API_KEY"],
            "optional": ["WENXIN_BASE_URL"],
        },
        credential_fields=(COMMON_API_KEY_FIELD, COMMON_BASE_URL_FIELD),
        curated_models={
            "language": ("ernie-4.5-turbo-128k", "ernie-4.0-8k", "ernie-speed-128k"),
            "embedding": ("embedding-v1",),
            "vision": ("ernie-4.0-vl-8k",),
        },
        test_model=("ernie-4.5-turbo-128k", "language"),
    ),
    "deepseek": ProviderCatalogEntry(
        id="deepseek",
        display_name="DeepSeek",
        docs_url="https://www.deepseek.com/",
        sort_order=30,
        modalities=("language",),
        runtime_family="native_deepseek",
        runtime_provider="deepseek",
        default_base_url="https://api.deepseek.com",
        env_config={"required": ["DEEPSEEK_API_KEY"], "optional": ["DEEPSEEK_BASE_URL"]},
        credential_fields=(COMMON_API_KEY_FIELD, COMMON_BASE_URL_FIELD),
        curated_models={
            "language": ("deepseek-chat", "deepseek-reasoner", "deepseek-coder"),
        },
        test_model=("deepseek-chat", "language"),
    ),
    "doubao": ProviderCatalogEntry(
        id="doubao",
        display_name="豆包",
        docs_url="https://www.volcengine.com/product/ark",
        sort_order=40,
        modalities=(
            "language",
            "embedding",
            "vision",
            "speech_to_text",
            "text_to_speech",
        ),
        runtime_family="compat",
        runtime_provider="openai-compatible",
        default_base_url="https://ark.cn-beijing.volces.com/api/v3",
        env_config={
            "required_any": ["DOUBAO_API_KEY", "ARK_API_KEY"],
            "optional": [
                "DOUBAO_BASE_URL",
                "DOUBAO_SPEECH_APP_ID",
                "DOUBAO_SPEECH_TOKEN",
                "DOUBAO_SPEECH_ENDPOINT",
                "DOUBAO_SPEECH_WS_URL",
            ],
        },
        credential_fields=(
            COMMON_API_KEY_FIELD,
            COMMON_BASE_URL_FIELD,
            ProviderCatalogField(
                name="speech_app_id",
                label="Speech App ID",
                field_type="text",
                target="extra",
                required=False,
            ),
            ProviderCatalogField(
                name="speech_token",
                label="Speech Token",
                field_type="password",
                target="extra",
                required=False,
                secret=True,
            ),
            ProviderCatalogField(
                name="speech_endpoint",
                label="Speech Endpoint",
                field_type="url",
                target="extra",
                required=False,
            ),
            ProviderCatalogField(
                name="speech_ws_url",
                label="Speech WebSocket URL",
                field_type="url",
                target="extra",
                required=False,
            ),
        ),
        curated_models={
            "language": ("doubao-seed-1-6-thinking-250715", "doubao-seed-1-6-flash-250715"),
            "embedding": ("doubao-embedding-text-240715",),
            "vision": ("doubao-vision-pro-32k",),
            "speech_to_text": ("doubao-stt",),
            "text_to_speech": ("doubao-tts",),
        },
        test_model=("doubao-seed-1-6-flash-250715", "language"),
    ),
    "spark": ProviderCatalogEntry(
        id="spark",
        display_name="讯飞星火",
        docs_url="https://xinghuo.xfyun.cn/",
        sort_order=50,
        modalities=("language", "embedding", "speech_to_text", "text_to_speech"),
        runtime_family="spark",
        runtime_provider="openai-compatible",
        default_base_url="https://spark-api-open.xf-yun.com/v1",
        env_config={
            "required_any": ["SPARK_API_KEY", "XFYUN_API_KEY"],
            "optional": ["SPARK_APP_ID", "SPARK_API_SECRET", "SPARK_BASE_URL"],
        },
        credential_fields=(
            COMMON_API_KEY_FIELD,
            COMMON_BASE_URL_FIELD,
            ProviderCatalogField(
                name="app_id",
                label="App ID",
                field_type="text",
                target="extra",
                required=False,
            ),
            ProviderCatalogField(
                name="api_secret",
                label="API Secret",
                field_type="password",
                target="extra",
                required=False,
                secret=True,
            ),
        ),
        curated_models={
            "language": ("spark-x", "generalv3.5", "4.0Ultra"),
            "embedding": ("spark-embedding",),
            "speech_to_text": ("spark-stt",),
            "text_to_speech": ("spark-tts",),
        },
        test_model=("spark-x", "language"),
    ),
    "kimi": ProviderCatalogEntry(
        id="kimi",
        display_name="Kimi",
        docs_url="https://platform.moonshot.cn/",
        sort_order=60,
        modalities=("language", "vision"),
        runtime_family="compat",
        runtime_provider="openai-compatible",
        default_base_url="https://api.moonshot.cn/v1",
        env_config={"required_any": ["KIMI_API_KEY", "MOONSHOT_API_KEY"], "optional": ["KIMI_BASE_URL"]},
        credential_fields=(COMMON_API_KEY_FIELD, COMMON_BASE_URL_FIELD),
        curated_models={
            "language": ("kimi-k2-0711-preview", "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"),
            "vision": ("moonshot-v1-128k-vision-preview",),
        },
        test_model=("moonshot-v1-8k", "language"),
    ),
    "hunyuan": ProviderCatalogEntry(
        id="hunyuan",
        display_name="腾讯混元",
        docs_url="https://hunyuan.tencent.com/",
        sort_order=70,
        modalities=("language", "vision"),
        runtime_family="compat",
        runtime_provider="openai-compatible",
        default_base_url="https://api.hunyuan.cloud.tencent.com/v1",
        env_config={
            "required_any": ["HUNYUAN_API_KEY", "TENCENT_HUNYUAN_API_KEY"],
            "optional": ["HUNYUAN_BASE_URL", "HUNYUAN_SECRET_ID", "HUNYUAN_SECRET_KEY", "HUNYUAN_REGION"],
        },
        credential_fields=(
            COMMON_API_KEY_FIELD,
            COMMON_BASE_URL_FIELD,
            ProviderCatalogField(
                name="secret_id",
                label="Secret ID",
                field_type="text",
                target="extra",
                required=False,
            ),
            ProviderCatalogField(
                name="secret_key",
                label="Secret Key",
                field_type="password",
                target="extra",
                required=False,
                secret=True,
            ),
            ProviderCatalogField(
                name="region",
                label="Region",
                field_type="text",
                target="extra",
                required=False,
                placeholder="ap-guangzhou",
            ),
        ),
        curated_models={
            "language": ("hunyuan-turbo", "hunyuan-standard", "hunyuan-large"),
            "vision": ("hunyuan-vision",),
        },
        test_model=("hunyuan-turbo", "language"),
    ),
    "zhipu": ProviderCatalogEntry(
        id="zhipu",
        display_name="智谱 AI",
        docs_url="https://www.zhipu.cn/",
        sort_order=80,
        modalities=("language", "embedding", "vision", "text_to_speech"),
        runtime_family="compat",
        runtime_provider="openai-compatible",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        env_config={"required_any": ["ZHIPU_API_KEY", "BIGMODEL_API_KEY"], "optional": ["ZHIPU_BASE_URL"]},
        credential_fields=(COMMON_API_KEY_FIELD, COMMON_BASE_URL_FIELD),
        curated_models={
            "language": ("glm-4.5", "glm-4-air", "glm-4-plus"),
            "embedding": ("embedding-3",),
            "vision": ("glm-4v-plus", "glm-4v"),
            "text_to_speech": ("cogtts",),
        },
        test_model=("glm-4-air", "language"),
    ),
    "ollama": ProviderCatalogEntry(
        id="ollama",
        display_name="Ollama",
        docs_url="https://ollama.com/",
        sort_order=90,
        modalities=("language", "embedding", "vision"),
        runtime_family="native_ollama",
        runtime_provider="ollama",
        default_base_url="http://localhost:11434",
        env_config={"required": ["OLLAMA_API_BASE"]},
        credential_fields=(
            ProviderCatalogField(
                name="base_url",
                label="Base URL",
                field_type="url",
                target="common",
                required=True,
                placeholder="http://localhost:11434",
                description="Ollama server address.",
            ),
        ),
        curated_models={},
        test_model=(None, "language"),
    ),
}

PUBLIC_PROVIDER_IDS = tuple(
    provider_id
    for provider_id, _entry in sorted(
        PROVIDER_CATALOG.items(), key=lambda item: item[1].sort_order
    )
)

DEFAULT_MODEL_PRIORITIES: dict[str, tuple[str, ...]] = {
    "default_chat_model": (
        "tongyi",
        "kimi",
        "zhipu",
        "wenxin",
        "doubao",
        "deepseek",
        "hunyuan",
        "ollama",
    ),
    "default_transformation_model": (
        "tongyi",
        "kimi",
        "zhipu",
        "wenxin",
        "doubao",
        "deepseek",
        "hunyuan",
        "ollama",
    ),
    "large_context_model": (
        "tongyi",
        "kimi",
        "zhipu",
        "wenxin",
        "doubao",
        "deepseek",
        "hunyuan",
        "ollama",
    ),
    "default_tools_model": (
        "tongyi",
        "kimi",
        "zhipu",
        "wenxin",
        "doubao",
        "deepseek",
        "hunyuan",
        "ollama",
    ),
    "default_embedding_model": ("ollama", "tongyi", "zhipu", "wenxin", "spark", "doubao"),
    "default_vision_model": ("ollama", "tongyi", "kimi", "zhipu", "wenxin", "doubao", "hunyuan"),
    "default_text_to_speech_model": ("spark", "zhipu", "doubao"),
    "default_speech_to_text_model": ("spark", "doubao"),
}

SENSITIVE_EXTRA_CONFIG_KEYS: dict[str, set[str]] = {
    provider_id: {field.name for field in entry.credential_fields if field.target == "extra" and field.secret}
    for provider_id, entry in PROVIDER_CATALOG.items()
}


def normalize_provider(provider: str) -> str:
    return provider.strip().lower().replace("-", "_")


def list_public_providers() -> list[ProviderCatalogEntry]:
    return [PROVIDER_CATALOG[provider_id] for provider_id in PUBLIC_PROVIDER_IDS]


def get_provider_catalog_entry(provider: str) -> ProviderCatalogEntry:
    provider_id = normalize_provider(provider)
    if provider_id not in PROVIDER_CATALOG:
        raise KeyError(f"Unsupported provider: {provider}")
    return PROVIDER_CATALOG[provider_id]


def get_provider_catalog_payload() -> list[dict[str, Any]]:
    return [entry.to_public_dict() for entry in list_public_providers()]


def get_provider_modalities(provider: str) -> list[str]:
    return list(get_provider_catalog_entry(provider).modalities)


def get_provider_env_config(provider: str) -> dict[str, list[str]]:
    return dict(get_provider_catalog_entry(provider).env_config)


def get_provider_ids() -> list[str]:
    return list(PUBLIC_PROVIDER_IDS)


def get_default_model_priority(slot_name: str) -> tuple[str, ...]:
    return DEFAULT_MODEL_PRIORITIES.get(slot_name, ())


def get_sensitive_extra_config_keys(provider: str) -> set[str]:
    return set(SENSITIVE_EXTRA_CONFIG_KEYS.get(normalize_provider(provider), set()))


def get_region_base_url(provider: str, region: Optional[str]) -> Optional[str]:
    entry = get_provider_catalog_entry(provider)
    if not region:
        return entry.default_base_url
    return entry.default_regions.get(region, entry.default_base_url)


def get_curated_models(provider: str, model_type: Optional[str] = None) -> dict[str, tuple[str, ...]] | tuple[str, ...]:
    entry = get_provider_catalog_entry(provider)
    if model_type:
        return entry.curated_models.get(model_type, ())
    return dict(entry.curated_models)


def iter_supported_provider_types() -> dict[str, list[str]]:
    return {entry.id: list(entry.modalities) for entry in list_public_providers()}


def is_supported_provider(provider: str) -> bool:
    return normalize_provider(provider) in PROVIDER_CATALOG


def filter_supported_providers(providers: Iterable[str]) -> list[str]:
    return [provider for provider in providers if is_supported_provider(provider)]
