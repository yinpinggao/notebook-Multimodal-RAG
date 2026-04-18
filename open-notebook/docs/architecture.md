# Architecture

Working architecture note for the 智研舱 transition layer.

Related docs:
- [Product PRD](./zhiyancang_prd_codex.md)
- [Issue List](./zhiyancang_codex_issue_list.md)
- [API Contracts](./apis.md)

## Current state

The repository still runs on the existing Open Notebook stack:
- FastAPI routers under `api/routers`
- service-style modules such as `api/*_service.py`
- persistence and retrieval under `open_notebook/seekdb`
- async jobs under `open_notebook/jobs` and `commands/*`
- multimodal reasoning through `graphs`, `visual_rag`, and `vrag`

## ZYC-02 role

`ZYC-02` adds a contract layer for the future project-centric product without replacing the current
notebook-centric runtime.

New schema modules:
- `open_notebook/domain/projects.py`
- `open_notebook/domain/evidence.py`
- `open_notebook/domain/memory.py`
- `open_notebook/domain/artifacts.py`
- `open_notebook/domain/runs.py`

Stable API import path:
- `api/schemas/project_contracts.py`

## Why this layer exists

The current codebase already has runtime entities like `Notebook`, `Source`, `Note`, and
`ChatSession`. Those are tied to the existing persistence model.

The new product needs contracts centered on:
- Project Workspace
- Evidence QA
- Compare
- Memory Center
- Output Studio
- Runs / Trace

Adding these models as pure pydantic contracts gives us:
- stable response shapes for upcoming endpoints
- a clean boundary between current persistence entities and future product entities
- lower migration risk when later issues add `projects/*` APIs
- PRD-aligned serialized field names before the real services land

## Architectural constraint

This issue intentionally does not:
- create new tables
- change current routers
- rename existing notebook persistence models
- introduce a second task system

Later issues should build on this layering order:
1. contract/schema
2. service
3. router
4. UI
