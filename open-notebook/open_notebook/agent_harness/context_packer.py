from __future__ import annotations

from typing import Any

from open_notebook.agent_harness.guardrails import compact_text


def pack_json_payload(value: Any, *, max_items: int = 12, _depth: int = 0) -> Any:
    if _depth >= 4:
        return compact_text(str(value), limit=240)

    if isinstance(value, dict):
        packed: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                break
            packed[str(key)] = pack_json_payload(item, max_items=max_items, _depth=_depth + 1)
        return packed

    if isinstance(value, (list, tuple, set)):
        return [
            pack_json_payload(item, max_items=max_items, _depth=_depth + 1)
            for item in list(value)[:max_items]
        ]

    if isinstance(value, str):
        return compact_text(value, limit=280)

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    if hasattr(value, "model_dump"):
        return pack_json_payload(value.model_dump(mode="json"), max_items=max_items, _depth=_depth + 1)

    return compact_text(str(value), limit=280)


def build_input_summary(run_type: str, input_json: dict[str, Any] | None = None) -> str:
    payload = input_json or {}

    if run_type == "ask":
        return compact_text(str(payload.get("question") or "项目证据问答"), limit=120)
    if run_type == "compare":
        source_a = payload.get("source_a_title") or payload.get("source_a_id") or "左侧资料"
        source_b = payload.get("source_b_title") or payload.get("source_b_id") or "右侧资料"
        compare_mode = payload.get("compare_mode") or "general"
        return compact_text(f"{source_a} vs {source_b} · {compare_mode}", limit=120)
    if run_type == "artifact":
        artifact_type = payload.get("artifact_type") or "artifact"
        origin_kind = payload.get("origin_kind") or "overview"
        return compact_text(f"生成 {artifact_type} · 来源 {origin_kind}", limit=120)
    if run_type == "memory_rebuild":
        return "重建项目长期记忆"
    if run_type == "overview_rebuild":
        return "重建项目总览"

    return compact_text(str(payload.get("title") or run_type), limit=120)


__all__ = ["build_input_summary", "pack_json_payload"]
