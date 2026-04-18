from __future__ import annotations

from open_notebook.project_os.artifact_service import (
    ArtifactSourceSnapshot,
    artifact_source_summary_lines,
    render_source_refs,
)


def build_defense_outline_markdown(
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    lines = [
        f"# {title}",
        "",
        "## 开场定位",
        "",
        f"- 这份提纲基于 {snapshot.label} 整理。",
        f"- 核心结论：{snapshot.summary}",
        "",
        "## 重点展开",
        "",
        *artifact_source_summary_lines(snapshot, limit=5),
        "",
        "## 风险与追问准备",
        "",
    ]

    if snapshot.open_questions:
        for question in snapshot.open_questions[:5]:
            lines.append(f"- {question}")
    else:
        lines.append("- 重点准备对关键证据、边界条件和未覆盖风险的解释。")

    refs_line = render_source_refs(snapshot.source_refs)
    if refs_line:
        lines.extend(["", f"- {refs_line}"])

    return "\n".join(lines).rstrip() + "\n"


def build_judge_questions_markdown(
    *,
    title: str,
    snapshot: ArtifactSourceSnapshot,
) -> str:
    questions = list(snapshot.open_questions)
    if snapshot.qa_pairs:
        questions.extend(pair.question for pair in snapshot.qa_pairs)
    if not questions:
        questions.extend(
            [
                "这份材料里最需要人工复核的结论是什么？",
                "当前证据链最薄弱的地方在哪里？",
                "如果条件变化，结论会先从哪里失稳？",
            ]
        )

    lines = [f"# {title}", "", "## 建议提问", ""]
    for index, question in enumerate(questions[:8], start=1):
        lines.append(f"{index}. {question}")
    refs_line = render_source_refs(snapshot.source_refs)
    if refs_line:
        lines.extend(["", f"- {refs_line}"])

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "build_defense_outline_markdown",
    "build_judge_questions_markdown",
]
