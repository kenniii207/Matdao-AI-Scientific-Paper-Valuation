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
OpenAlex, Semantic Scholar, Crossref (retraction), NIH RePORTER, OSF, ClinicalTrials.gov, Grobid, GLM-OCR.

## Workflow
1. Search existing patterns before creating new code
2. Run tests after every change: `pytest backend/tests/ -v`
3. Atomic commits with prefix: `feat:/fix:/test:/docs:/chore:`
4. Every score must link to origin_snippet for auditability
