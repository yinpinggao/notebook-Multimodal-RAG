from __future__ import annotations

from typing import Any


def extract_page_no(row: dict[str, Any]) -> int | None:
    raw_page = row.get("page")
    if raw_page in (None, ""):
        return None

    try:
        page_no = int(str(raw_page).strip())
    except (TypeError, ValueError):
        return None

    return page_no if page_no >= 1 else None


def build_internal_ref(row: dict[str, Any]) -> str:
    base_ref = str(
        row.get("internal_ref")
        or row.get("parent_id")
        or row.get("source_id")
        or row.get("id")
        or ""
    )
    page = extract_page_no(row)

    if not base_ref:
        return ""

    if page and "#p" not in base_ref:
        return f"{base_ref}#p{page}"

    return base_ref


def build_citation_text(row: dict[str, Any]) -> str:
    existing = row.get("citation_text")
    if existing:
        return str(existing)

    filename = str(row.get("filename") or row.get("title") or "").strip()
    page = extract_page_no(row)
    internal_ref = build_internal_ref(row)

    if filename and page:
        return f"引用：{filename}（第{page}页） | 内部引用：[{internal_ref}]"
    if filename and internal_ref:
        return f"引用：{filename} | 内部引用：[{internal_ref}]"
    if internal_ref:
        return f"内部引用：[{internal_ref}]"
    if filename:
        return filename
    return ""
