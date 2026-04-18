from open_notebook.evidence.structured_extractor import extract_source_profile


def test_extract_source_profile_collects_multiple_fact_categories():
    profile = extract_source_profile(
        source_id="source:demo",
        title="2026 Smart Research Challenge Rules",
        full_text=(
            "The Smart Research Challenge requires teams to submit a proposal by "
            "2026-06-30. Teams must include at least 3 members and score above 85%. "
            "A major risk is incomplete evidence coverage in the final report. "
            "Tsinghua University and OpenAI Research Lab are reference institutions. "
            "The system uses RAG and OCR pipelines."
        ),
        existing_topics=["Evidence QA"],
        page_summaries=[
            {
                "text": "Requirement: the final proposal must cite every external source.",
                "source_ref": "source:demo#p2",
            },
            {
                "text": "Risk: timeline compression can hurt review quality.",
                "source_ref": "source:demo#p4",
            },
        ],
        visual_summaries=[
            {
                "text": "Figure 2 shows a 92% retrieval accuracy trend.",
                "source_ref": "source:demo#p6",
            }
        ],
    )

    assert "Evidence QA" in profile.topics
    assert profile.keywords
    assert profile.risks
    assert profile.requirements
    assert profile.metrics
    assert profile.timeline_events
    assert any(
        item in profile.people_orgs
        for item in ["Tsinghua University", "OpenAI Research Lab"]
    )
    categories = {fact.category for fact in profile.facts}
    assert {"topic", "keyword", "risk", "requirement"}.issubset(categories)


def test_extract_source_profile_supports_chinese_sources():
    profile = extract_source_profile(
        source_id="source:cn",
        title="项目申报评审规则",
        full_text=(
            "项目必须在2026年6月30日前提交。主要风险是证据覆盖不足。"
            "清华大学人工智能研究院参与评审。指标要求准确率达到92%。"
        ),
        existing_topics=["项目申报"],
        page_summaries=[
            {
                "text": "要求：答辩材料必须给出关键结论的出处。",
                "source_ref": "source:cn#p2",
            }
        ],
    )

    assert "项目申报" in profile.topics
    assert profile.timeline_events
    assert profile.risks
    assert profile.requirements
    assert any("清华大学人工智能研究院" in item for item in profile.people_orgs)
