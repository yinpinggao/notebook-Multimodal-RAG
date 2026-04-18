from __future__ import annotations

from open_notebook.domain.artifacts import ArtifactType
from open_notebook.exceptions import InvalidInputError
from open_notebook.project_os.artifact_service import (
    ArtifactSourceQAPair,
    ArtifactSourceSnapshot,
    artifact_source_summary_lines,
    render_source_refs,
)


def _build_project_summary_markdown(
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    lines = [
        f"# {title}",
        "",
        "## 摘要",
        "",
        snapshot.summary,
        "",
        "## 关键要点",
        "",
        *artifact_source_summary_lines(snapshot, limit=6),
        "",
    ]

    if snapshot.open_questions:
        lines.extend(["## 下一步问题", ""])
        for question in snapshot.open_questions[:5]:
            lines.append(f"- {question}")
        lines.append("")

    refs_line = render_source_refs(snapshot.source_refs)
    if refs_line:
        lines.extend(["## 来源", "", f"- {refs_line}", ""])

    return "\n".join(lines).rstrip() + "\n"


def _build_diff_report_markdown(
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    lines = [
        f"# {title}",
        "",
        "## 对比摘要",
        "",
        snapshot.summary,
        "",
        "## 结构化差异",
        "",
        *artifact_source_summary_lines(snapshot, limit=10),
        "",
    ]

    if snapshot.open_questions:
        lines.extend(["## 需要继续确认", ""])
        for question in snapshot.open_questions[:5]:
            lines.append(f"- {question}")
        lines.append("")

    refs_line = render_source_refs(snapshot.source_refs)
    if refs_line:
        lines.extend(["## 来源", "", f"- {refs_line}", ""])

    return "\n".join(lines).rstrip() + "\n"


def _build_qa_cards_markdown(
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    lines = [f"# {title}", ""]
    qa_pairs = snapshot.qa_pairs or [
        ArtifactSourceQAPair(
            question="这份材料最重要的结论是什么？",
            answer=snapshot.summary,
            source_refs=snapshot.source_refs,
        )
    ]

    for index, pair in enumerate(qa_pairs[:6], start=1):
        lines.extend(
            [
                f"## 卡片 {index}",
                "",
                f"**Q：** {pair.question}",
                "",
                f"**A：** {pair.answer}",
            ]
        )
        refs_line = render_source_refs(pair.source_refs)
        if refs_line:
            lines.extend(["", f"- {refs_line}"])
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


async def generate_synthesis_artifact(
    artifact_type: ArtifactType,
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    if artifact_type == "project_summary":
        return _build_project_summary_markdown(title=title, snapshot=snapshot)
    if artifact_type == "diff_report":
        return _build_diff_report_markdown(title=title, snapshot=snapshot)
    if artifact_type == "qa_cards":
        return _build_qa_cards_markdown(title=title, snapshot=snapshot)

    raise InvalidInputError(f"Unsupported synthesis artifact type: {artifact_type}")


__all__ = ["generate_synthesis_artifact"]
