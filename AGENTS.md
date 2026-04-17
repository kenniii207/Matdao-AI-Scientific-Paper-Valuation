# AGENTS.md — MatDAO Automation Framework

## Project Purpose
Automated scientific due diligence system. Evaluates research papers across 9 dimensions for investment decisions.

## Architecture
4-layer pipeline: NLP Extraction → API Enrichment → Structured Intake → Expert Audit.

## Critical Rule: Integrity Gate
Dim9 (Governance) = 1 → Total Score = 0. No exceptions. No override.

## Directory Map
- `backend/api/adapters/` — One class per API provider. Adapter pattern.
- `backend/services/scoring/` — Scoring engine + dimension scorers. ALL scoring logic here.
- `backend/models/` — Pydantic v2 data models.
- `backend/core/` — Config, rate limiter, exceptions.
- `backend/db/` — SQLAlchemy models, PostgreSQL + pgvector.
- `frontend/src/app/` — Next.js 14 App Router pages.
- `frontend/src/store/` — Zustand state stores.

## API Providers
OpenAlex, Semantic Scholar, Crossref (retraction), NIH RePORTER, OSF, ClinicalTrials.gov, Falcon-OCR, GLM-OCR.

## Workflow
1. Search existing patterns before creating new code
2. Run tests after every change: `pytest backend/tests/ -v`
3. Atomic commits with prefix: `feat:/fix:/test:/docs:/chore:`
4. Every score must link to origin_snippet for auditability

## Workflow Addendum (Karpathy Guidelines)
Apply these checks before merging code changes:
1. Think before coding: state assumptions and tradeoffs explicitly.
2. Simplicity first: implement the minimum code that solves the task.
3. Surgical changes: touch only task-related lines and avoid unrelated refactors.
4. Goal-driven execution: define verifiable success criteria and run checks.

## Workflow Addendum (Token + Memory + UI)
1. Use concise communication mode by default (`caveman` style) unless explicitly disabled.
2. Before implementation, check process guidance from `superpowers-main` and apply relevant skill workflow.
3. For UI work, consult `ui-ux-pro-max-skill-main` rules before editing frontend.
4. Reuse prior project context via `claude-mem` workflow/files when available to reduce repeated rediscovery.
