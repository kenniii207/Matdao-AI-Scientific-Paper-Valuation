# SKILLS.md — AI IDE Instruction Set

## Stack
- Backend: FastAPI (Python 3.11+), Pydantic v2, asyncio, SQLAlchemy 2.0
- Frontend: Next.js 14+ (App Router), TypeScript, Tailwind CSS, Zustand
- DB: PostgreSQL 16 + pgvector
- OCR: Grobid (Docker, port 8070) + GLM-OCR (cloud/self-hosted, 0.9B model)
- PDF: PDFMathTranslate for formula/layout preservation

## Scoring Formula
```
Total = Σ(Score_i × Weight_i / 5 × 100)
Weight_i = 1/9 (MVP equal weights)
Σ Weight_i = 1.0
```

## Integrity Gate
If Dim9 score = 1 → Total = 0. Binary multiplier. Hardcoded. No bypass.

## API Rate Limits
- OpenAlex: 100 req/sec (with API key)
- Semantic Scholar: 100 req/sec (with x-api-key header)
- Crossref: 50 req/min (polite pool with mailto)
- NIH RePORTER: 1 req/sec (strict)
- OSF: 10 req/sec
- ClinicalTrials.gov: 10 req/sec

## Rules
1. Search existing code before writing new patterns
2. Pydantic v2 for ALL models. Validate at runtime boundary.
3. API logic in `backend/api/adapters/` only
4. Scoring logic in `backend/services/scoring/` only
5. Every score links to origin_snippet (auditability)
6. Comments explain "Why" not "What"
7. Run pytest before claiming done
8. Atomic commits: one thing per commit
