import pytest

from open_notebook.agents.defense_coach_agent import generate_defense_artifact
from open_notebook.agents.synthesis_agent import generate_synthesis_artifact
from open_notebook.project_os.artifact_service import (
    ArtifactSourceBullet,
    ArtifactSourceQAPair,
    ArtifactSourceSnapshot,
)


def _snapshot() -> ArtifactSourceSnapshot:
    return ArtifactSourceSnapshot(
        origin_kind="thread",
        origin_id="thread:demo",
        label="Demo Thread",
        summary="当前结论指向更稳的证据链，但还有边界条件要补充。",
        bullets=[
            ArtifactSourceBullet(
                title="关键证据",
                detail="资料 A 明确给出了主结论。",
                source_refs=["source:a#p1"],
            )
        ],
        qa_pairs=[
            ArtifactSourceQAPair(
                question="最重要的结论是什么？",
                answer="当前主结论已经成立，但还需补强风险边界。",
                source_refs=["source:a#p1"],
            )
        ],
        open_questions=["还有哪些风险没有回源确认？"],
        source_refs=["source:a#p1", "source:b#p2"],
    )


@pytest.mark.asyncio
async def test_generate_synthesis_artifacts_render_expected_sections():
    snapshot = _snapshot()

    project_summary = await generate_synthesis_artifact(
        "project_summary",
        title="Demo 项目综述",
        snapshot=snapshot,
    )
    qa_cards = await generate_synthesis_artifact(
        "qa_cards",
        title="Demo 问答卡片",
        snapshot=snapshot,
    )

    assert "# Demo 项目综述" in project_summary
    assert "## 关键要点" in project_summary
    assert "## 卡片 1" in qa_cards
    assert "**Q：** 最重要的结论是什么？" in qa_cards


@pytest.mark.asyncio
async def test_generate_defense_artifacts_render_expected_sections():
    snapshot = _snapshot()

    defense_outline = await generate_defense_artifact(
        "defense_outline",
        title="Demo 答辩提纲",
        snapshot=snapshot,
    )
    judge_questions = await generate_defense_artifact(
        "judge_questions",
        title="Demo 评委问题清单",
        snapshot=snapshot,
    )

    assert "# Demo 答辩提纲" in defense_outline
    assert "## 风险与追问准备" in defense_outline
    assert "# Demo 评委问题清单" in judge_questions
    assert "## 建议提问" in judge_questions
