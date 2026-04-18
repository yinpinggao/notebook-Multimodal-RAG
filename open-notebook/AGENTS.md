# AGENTS.md

## Project
This repository is being transformed into "智研舱", an agentic multimodal evidence workspace.
Primary references:
- docs/zhiyancang_prd_codex.md
- docs/zhiyancang_codex_issue_list.md
- docs/zhiyancang_codex_dev_prompts.md

## Working style
- Read the relevant docs before editing code.
- Work on one issue at a time unless explicitly asked to parallelize.
- Prefer minimal, high-confidence changes that fit the existing repo structure.
- Reuse existing modules and patterns; do not rewrite the whole system.

## Architecture constraints
- Keep the current service / router / worker style where possible.
- Add a Project Harness layer instead of replacing existing Open Notebook modules.
- Reuse existing visual_rag, seekdb, worker, and frontend dashboard foundations.

## Implementation rules
- Before coding, restate the task, touched files, and acceptance criteria.
- After coding, run relevant tests/checks.
- Summarize changed files, risks, and follow-up work.
- Do not introduce large new dependencies unless necessary.
- Do not rename or remove major existing modules without explicit instruction.

## Done when
- The requested issue is implemented.
- Relevant tests or checks pass, or failures are explicitly explained.
- API contracts, backend logic, and UI behavior match the issue acceptance criteria.
- The final response includes:
  1. changed files
  2. what was implemented
  3. checks run
  4. remaining risks