# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Repository Structure

This is a dual-project repository:

| Directory | Description |
|---|---|
| `open-notebook/` | **Primary project** — Open-source AI research assistant (Google Notebook LM alternative). Next.js frontend + FastAPI backend + SeekDB database. |
| `open-notebook/references/vrag-original/` | **Reference implementation** — Visual RAG (VimRAG + VRAG-RL). Demo/research code, not part of the main project. |

**Most development work happens in `open-notebook/`**.

---

## open-notebook Quick Start

```bash
cd open-notebook

# Install dependencies
uv sync

# Start all services (SeekDB + Redis + API + Frontend)
make start-all

# Or use SeekDB dev config
make seekdb-dev-up

# Run Python linter (auto-fix)
make ruff

# Run type checker
make lint

# Run tests
uv run pytest

# Run single test
uv run pytest tests/test_domain.py

# Start frontend only
cd frontend && npm run dev

# Start API only
make api
```

## open-notebook Architecture Reference

For detailed guidance, read `open-notebook/AGENTS.md`. Key references:

| File | What It Covers |
|---|---|
| `open-notebook/AGENTS.md` | Three-tier architecture, service pattern, deployment |
| `open-notebook/open_notebook/graphs/AGENTS.md` | LangGraph workflows (source/chat/ask/transformation) |
| `open-notebook/open_notebook/ai/AGENTS.md` | ModelManager, Esperanto library, AI provider system |
| `open-notebook/open_notebook/database/AGENTS.md` | SeekDB operations, migrations, async patterns |
| `open-notebook/open_notebook/domain/AGENTS.md` | Domain models, repository pattern |
| `open-notebook/open_notebook/seekdb/AGENTS.md` | SeekDB client, vector retrieval, chunk storage |
| `open-notebook/open_notebook/vrag/AGENTS.md` | VRAG multimodal RAG (image search, bbox crop, memory graph) |
| `open-notebook/api/AGENTS.md` | FastAPI routers, service pattern |
| `open-notebook/frontend/src/AGENTS.md` | Next.js/React, Zustand + TanStack Query, API integration |
| `open-notebook/commands/AGENTS.md` | seekdb-commands job queue handlers |
| `open-notebook/prompts/AGENTS.md` | Jinja2 prompt templates, workflow integration |
| `open-notebook/open_notebook/utils/AGENTS.md` | Chunking, embedding, context building, encryption |
| `open-notebook/open_notebook/podcasts/AGENTS.md` | Podcast generation, speaker profiles |

## VRAG Reference Directory

`open-notebook/references/vrag-original/` is a separate reference implementation of Visual RAG (VimRAG + VRAG-RL). It is NOT runtime code for `open-notebook/`. The canonical Visual RAG implementation used by the main application now lives under `open-notebook/open_notebook/visual_rag/`, with compatibility helpers in `open-notebook/open_notebook/vrag/`.

## Key Architectural Patterns

1. **API pattern**: Route → Service (orchestration) → Domain/Repository → SeekDB. Services invoke LangGraph graphs. Routes only handle HTTP + validation.
2. **Async everywhere**: All database, LLM, and file I/O uses async/await. No sync I/O in request handlers.
3. **LLM provisioning**: `provision_langchain_model()` detects available providers, selects best model, falls back on failure.
4. **VRAG**: ReAct-style agent with multimodal search (text + image), bbox cropping, and a memory graph DAG for visual reasoning.
5. **SeekDB**: Graph database with built-in vector storage. Record IDs use `table:id` syntax. Migrations auto-run on API startup.
6. **AI credentials**: API keys stored as encrypted records in SeekDB (not env vars). Configure via Settings UI.

## Common Development Tasks

### Add a new API endpoint
1. Create router in `open-notebook/api/routers/feature.py`
2. Create service in `open-notebook/api/feature_service.py`
3. Register router in `open-notebook/api/main.py`

### Add a new LangGraph workflow
1. Create `open-notebook/open_notebook/graphs/workflow_name.py`
2. Define StateDict and node functions
3. Build graph with `.add_node()` / `.add_edge()`
4. Invoke in service: `graph.ainvoke({"input": ...})`

### Add a new SeekDB migration
1. Create `open-notebook/open_notebook/database/migrations/N_description.py`
2. API auto-detects on startup; runs if newer than recorded version

## Current Work

The following files have uncommitted changes (from git status):
- `open-notebook/open_notebook/seekdb/retrieval_service.py`
- `open-notebook/open_notebook/vrag/api.py`
- `open-notebook/open_notebook/vrag/search_engine.py`
- `open-notebook/open_notebook/vrag/tools.py`
- `open-notebook/open_notebook/vrag/workflow.py`
