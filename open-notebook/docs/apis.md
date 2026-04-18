# APIs

Working contract reference for the 智研舱 / Project Memory Copilot schema layer.

Related docs:
- [Product PRD](./zhiyancang_prd_codex.md)
- [Issue List](./zhiyancang_codex_issue_list.md)
- [Architecture](./architecture.md)

## Purpose

`ZYC-02` introduces stable backend response contracts before new project APIs are implemented.
The goal is to let later issues build `projects`, `ask`, `compare`, `memory`, `artifacts`, and
`runs` endpoints against a shared schema set instead of inventing ad hoc payloads.

Current import paths:
- domain contracts: `open_notebook.domain.*`
- API-layer re-export: `api.schemas.project_contracts`

Contract rule for this layer:
- serialized field names follow the PRD
- a small set of validation aliases is kept to ease transition from draft names

## Core Schemas

### Project contracts

- `ProjectSummary`
  - `id`
  - `name`
  - `description`
  - `status`
  - `created_at`
  - `updated_at`
  - `source_count`
  - `artifact_count`
  - `memory_count`
  - `last_run_at`

- `ProjectOverviewResponse`
  - `project`
  - `source_count`
  - `artifact_count`
  - `memory_count`
  - `topics`
  - `keywords`
  - `risks`
  - `timeline_events`
  - `recommended_questions`
  - `recent_runs`
  - `recent_artifacts`

### Evidence contracts

- `EvidenceCard`
  - required fields:
    - `source_name`
    - `source_id`
    - `page_no`
    - `excerpt`
    - `citation_text`
    - `internal_ref`
  - optional fields:
    - `relevance_reason`
    - `image_thumb`
    - `score`
    - `id`
    - `project_id`
    - `thread_id`

`page_no` is required in the payload shape, but may be `null` when the evidence is not page-anchored.

- `AskResponse`
  - `answer`
  - `confidence`
  - `evidence_cards`
  - `memory_updates`
  - `run_id`
  - `suggested_followups`
  - `mode`
  - `thread_id`

- `CompareSummary`
  - `summary`
  - `similarities`
  - `differences`
  - `conflicts`
  - `missing_items`
  - `human_review_required`

### Memory contracts

- `MemoryRecord`
  - required fields:
    - `id`
    - `scope`
    - `type`
    - `text`
    - `confidence`
    - `source_refs`
    - `status`
  - optional fields:
    - `freshness`
    - `decay_policy`
    - `conflict_group`

`source_refs` must always be present even when the list is empty.

- `SourceReference`
  - `source_id`
  - `source_name`
  - `page_no`
  - `internal_ref`
  - `citation_text`

### Artifact contracts

- `ArtifactRecord`
  - required fields:
    - `id`
    - `project_id`
    - `artifact_type`
    - `title`
    - `content_md`
    - `created_by_run_id`
    - `created_at`
    - `updated_at`
  - optional fields:
    - `source_refs`
    - `status`
    - `thread_id`

### Run contracts

- `AgentRun`
  - `id`
  - `project_id`
  - `status`
  - `run_type`
  - `input_summary`
  - `input_json`
  - `output_json`
  - `selected_skill`
  - `created_at`
  - `started_at`
  - `completed_at`
  - `tool_calls`
  - `evidence_reads`
  - `memory_writes`
  - `outputs`
  - `steps`
  - `failure_reason`

- `AgentStep`
  - `id`
  - `run_id`
  - `step_index`
  - `agent_name`
  - `title`
  - `type`
  - `status`
  - `started_at`
  - `completed_at`
  - `tool_name`
  - `input_json`
  - `output_json`
  - `evidence_refs`
  - `memory_refs`
  - `output_refs`
  - `error`

## Notes

- These contracts do not change current runtime behavior yet.
- No database migration is included in `ZYC-02`.
- Existing `api/models.py` remains in place for current endpoints; new project endpoints should
  prefer `api.schemas.project_contracts`.
