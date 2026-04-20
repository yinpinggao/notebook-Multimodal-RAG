import pytest
from pydantic import ValidationError

from api.schemas import (
    AgentRun,
    AgentStep,
    ArtifactRecord,
    AskResponse,
    CompareSummary,
    EvidenceCard,
    EvidenceThreadDetail,
    EvidenceThreadMessage,
    EvidenceThreadSummary,
    MemoryRecord,
    ProjectArtifactCreateResponse,
    ProjectOverviewResponse,
    ProjectSummary,
    RecentArtifactSummary,
    RecentRunSummary,
)


def test_evidence_card_schema_contains_required_fields():
    schema = EvidenceCard.model_json_schema()
    required = set(schema.get("required", []))

    assert {
        "source_name",
        "source_id",
        "page_no",
        "excerpt",
        "citation_text",
        "internal_ref",
    }.issubset(required)


def test_memory_record_schema_contains_required_fields():
    schema = MemoryRecord.model_json_schema()
    required = set(schema.get("required", []))

    assert {"source_refs", "status", "confidence"}.issubset(required)


def test_artifact_record_schema_contains_created_by_run_id():
    schema = ArtifactRecord.model_json_schema()
    required = set(schema.get("required", []))

    assert "created_by_run_id" in required


def test_artifact_create_response_schema_contains_created_by_run_id():
    schema = ProjectArtifactCreateResponse.model_json_schema()
    required = set(schema.get("required", []))

    assert "created_by_run_id" in required


def test_prd_field_names_are_used_in_serialized_contracts():
    artifact = ArtifactRecord(
        id="artifact:001",
        project_id="project:demo",
        artifact_type="project_summary",
        title="Project Summary",
        content_md="# Summary",
        created_by_run_id="run:001",
        created_at="2026-04-18T10:00:00Z",
        updated_at="2026-04-18T10:00:00Z",
    )
    run = AgentRun(
        id="run:001",
        project_id="project:demo",
        run_type="ask",
        status="completed",
        created_at="2026-04-18T10:00:00Z",
    )
    step = AgentStep(
        id="step:001",
        step_index=0,
        title="Read evidence",
        type="evidence_read",
        status="completed",
    )
    recent_run = RecentRunSummary(
        id="run:summary",
        run_type="ask",
        status="completed",
        created_at="2026-04-18T10:00:00Z",
    )
    recent_artifact = RecentArtifactSummary(
        id="artifact:summary",
        artifact_type="qa_cards",
        title="QA Cards",
        created_at="2026-04-18T10:00:00Z",
    )

    assert "artifact_type" in artifact.model_dump()
    assert "content_md" in artifact.model_dump()
    assert "run_type" in run.model_dump()
    assert "step_index" in step.model_dump()
    assert "run_type" in recent_run.model_dump()
    assert "artifact_type" in recent_artifact.model_dump()
    summary = ProjectSummary(
        id="project:summary",
        name="Summary",
        description="",
        status="active",
        created_at="2026-04-18T10:00:00Z",
        updated_at="2026-04-18T10:00:00Z",
        source_count=0,
        artifact_count=0,
        memory_count=0,
    )
    assert "phase" in summary.model_dump()
    assert "latest_output_title" in summary.model_dump()
    assert "latest_run_status" in summary.model_dump()


def test_transition_aliases_are_still_accepted():
    artifact = ArtifactRecord(
        id="artifact:001",
        project_id="project:demo",
        type="project_summary",
        title="Project Summary",
        content_markdown="# Summary",
        created_by_run_id="run:001",
        created_at="2026-04-18T10:00:00Z",
        updated_at="2026-04-18T10:00:00Z",
    )
    run = AgentRun(
        id="run:001",
        project_id="project:demo",
        task_type="ask",
        status="completed",
        created_at="2026-04-18T10:00:00Z",
    )
    step = AgentStep(
        id="step:001",
        index=0,
        title="Read evidence",
        type="evidence_read",
        status="completed",
    )
    evidence = EvidenceCard(
        source_name="Design Spec",
        source_id="source:alpha",
        page_no=3,
        excerpt="Evidence excerpt",
        citation_text="Design Spec, page 3",
        internal_ref="source:alpha#p3",
        image_thumb_url="https://example.com/thumb.png",
    )
    recent_run = RecentRunSummary(
        id="run:summary",
        task_type="compare",
        status="completed",
        created_at="2026-04-18T10:00:00Z",
    )
    recent_artifact = RecentArtifactSummary(
        id="artifact:summary",
        type="qa_cards",
        title="QA Cards",
        created_at="2026-04-18T10:00:00Z",
    )

    assert artifact.artifact_type == "project_summary"
    assert artifact.content_md == "# Summary"
    assert run.run_type == "ask"
    assert step.step_index == 0
    assert evidence.image_thumb == "https://example.com/thumb.png"
    assert recent_run.run_type == "compare"
    assert recent_artifact.artifact_type == "qa_cards"


def test_required_contract_fields_allow_null_or_empty_values_when_expected():
    evidence = EvidenceCard(
        source_name="Scanned PDF",
        source_id="source:scan",
        page_no=None,
        excerpt="A non-page anchored citation.",
        citation_text="Scanned PDF",
        internal_ref="source:scan#asset",
    )
    memory = MemoryRecord(
        id="memory:001",
        scope="project",
        type="fact",
        text="The project uses evidence-grounded answers.",
        confidence=0.9,
        source_refs=[],
        status="draft",
    )

    assert evidence.page_no is None
    assert memory.source_refs == []


def test_required_contract_fields_fail_when_omitted():
    with pytest.raises(ValidationError):
        EvidenceCard(
            source_name="Design Spec",
            source_id="source:alpha",
            excerpt="Evidence excerpt",
            citation_text="Design Spec, page 3",
            internal_ref="source:alpha#p3",
        )

    with pytest.raises(ValidationError):
        MemoryRecord(
            id="memory:001",
            scope="project",
            type="fact",
            text="The project uses evidence-grounded answers.",
            confidence=0.9,
            status="draft",
        )


def test_project_contracts_are_importable_and_composable():
    run = AgentRun(
        id="run:001",
        project_id="project:demo",
        status="completed",
        task_type="ask",
        input_summary="Summarize the project evidence",
        selected_skill="answer_with_evidence",
        created_at="2026-04-18T10:00:00Z",
        started_at="2026-04-18T10:00:02Z",
        completed_at="2026-04-18T10:00:10Z",
        tool_calls=["seekdb.hybrid_search"],
        evidence_reads=["source:alpha#p3"],
        memory_writes=[],
        outputs=["artifact:summary"],
        steps=[
            AgentStep(
                id="step:1",
                index=0,
                title="Retrieve evidence",
                type="evidence_read",
                status="completed",
                agent_name="evidence_agent",
                started_at="2026-04-18T10:00:02Z",
                completed_at="2026-04-18T10:00:04Z",
                tool_name="seekdb.hybrid_search",
                input_json={"query": "project evidence"},
                output_json={"result_count": 1},
                evidence_refs=["source:alpha#p3"],
                memory_refs=[],
                output_refs=[],
            )
        ],
    )

    response = AskResponse(
        answer="The project focuses on multimodal evidence workflows.",
        confidence=0.82,
        evidence_cards=[
            EvidenceCard(
                id="ev:1",
                project_id="project:demo",
                thread_id="thread:1",
                source_name="Design Spec",
                source_id="source:alpha",
                page_no=3,
                excerpt="The platform prioritizes evidence-grounded answers.",
                citation_text="Design Spec, page 3",
                internal_ref="source:alpha#p3",
                image_thumb="https://example.com/thumb.png",
                score=0.91,
            )
        ],
        memory_updates=[],
        run_id=run.id,
        suggested_followups=["What is the compare workflow?"],
        mode="mixed",
    )

    overview = ProjectOverviewResponse(
        project=ProjectSummary(
            id="project:demo",
            name="Demo Project",
            description="Contract test project",
            status="active",
            created_at="2026-04-18T09:00:00Z",
            updated_at="2026-04-18T10:00:00Z",
            source_count=3,
            artifact_count=1,
            memory_count=0,
        ),
        source_count=3,
        artifact_count=1,
        memory_count=0,
        topics=["Multimodal evidence"],
        risks=["Contract drift"],
        recent_runs=[],
        recent_artifacts=[],
    )

    compare = CompareSummary(
        summary="Source A and Source B agree on the project goal but differ on delivery order.",
        similarities=[],
        differences=[],
        conflicts=[],
        missing_items=[],
        human_review_required=[],
    )
    thread_summary = EvidenceThreadSummary(
        id="chat_session:demo",
        project_id="project:demo",
        title="Why this project matters",
        created_at="2026-04-18T10:00:00Z",
        updated_at="2026-04-18T10:05:00Z",
        message_count=2,
        last_question="What is the main contribution?",
        last_answer_preview="The main contribution is...",
    )
    thread_detail = EvidenceThreadDetail(
        **thread_summary.model_dump(),
        messages=[
            EvidenceThreadMessage(
                id="msg:1",
                type="human",
                content="What is the main contribution?",
            )
        ],
        latest_response=response,
    )

    assert response.run_id == "run:001"
    assert overview.project.name == "Demo Project"
    assert compare.summary.startswith("Source A")
    assert run.run_type == "ask"
    assert run.steps[0].step_index == 0
    assert thread_detail.latest_response is not None
    assert thread_detail.messages[0].type == "human"
