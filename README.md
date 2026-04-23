# MatDAO Automation Framework

> Automated scientific due diligence — converting unstructured research PDFs into structured investment intelligence.

## Overview

MatDAO evaluates scientific research for investment using a **4-layer data extraction pipeline** and a **9-dimension scoring rubric**. The system automates 60-70% of the due diligence process, allowing human experts to focus on qualitative synthesis.

### 4-Layer Pipeline

| Layer | Strategy | Output |
|-------|----------|--------|
| **1. Neural Extraction** | Falcon-OCR (local) + GLM-OCR | Text extraction, table parsing, DOI discovery |
| **2. API Enrichment** | OpenAlex, Semantic Scholar | Citation metrics, funding verification |
| **3. Autonomous Eval** | LLM Synthesis (Gemini → GLM → fallbacks) | 9-dimension scoring, rationale, audit snippets |
| **4. Expert Audit** | Human-in-the-loop | Final investment grading |

### Integrity Gate (Dimension 9)

If **Dimension 9 (Governance) = 1**, the total score is **forced to 0** regardless of all other dimensions. This is a binary multiplier — no exceptions.

### Scoring Formula

```
Total Score = Σ(Score_i × Weight_i / 5 × 100)
Grade: A (90-100) | B (80-89) | C (70-79) | D (60-69) | F (<60)
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Infrastructure (Render Blueprint)

```bash
# Deploys backend + postgres
render blueprint apply
```

### Run Tests

```bash
cd backend
PYTHONPATH=.. python -m pytest tests/ -v
```

## LLM Fallback Configuration

The evaluator supports a configurable provider chain to reduce 503 outages and avoid neutral-only outputs:

- `LLM_FALLBACK_ORDER=gemini,glm,openrouter,qwen,manus,kimi,minimax,liquid`
- `LLM_PROVIDER_TIMEOUT_SECONDS=120`
- `LLM_ADAPTIVE_ROUTING_ENABLED=true` (auto-prioritizes provider order by paper complexity)
- Provider keys/base URLs are optional; unconfigured providers are skipped.

Recommended minimum for staging:

- `GEMINI_API_KEY` set
- `OPENROUTER_API_KEY` set
- `OPENROUTER_MODELS` with multiple models

## LightOnOCR Rollout (Phased)

The OCR fallback chain is configurable:

- `OCR_FALLBACK_ORDER=pdf_text,glm_ocr,lighton_ocr`
- `LIGHTONOCR_ENABLED=false` by default (canary-safe)

### Phase 1 — Infrastructure

Use optional local llama.cpp server in compose:

```bash
docker compose --profile lighton up -d lighton-ocr postgres backend
```

Required model files:

- `LightOnOCR-2-1B.i1-Q5_K_M.gguf`
- `LightOnOCR-2-1B.mmproj-Q8_0.gguf`

### Phase 2 — Preflight Mode

For remote llama-server (recommended): keep local path checks off.

- `LIGHTONOCR_REQUIRE_LOCAL_PATHS=false`

For same-host deployment with direct file validation:

- `LIGHTONOCR_REQUIRE_LOCAL_PATHS=true`
- Set both `LIGHTONOCR_MODEL_PATH` and `LIGHTONOCR_MMPROJ_PATH`

### Phase 3 — Canary

Enable service and gradually route fallback traffic:

- `LIGHTONOCR_ENABLED=true`
- `LIGHTONOCR_CANARY_PERCENT=5` (then 10, 25, 50, 100)

### Phase 4 — Production Readiness Checks

Check runtime readiness before increasing canary:

```bash
curl -s http://localhost:8000/upload/ocr/readiness
```

Healthy target:

- `"lighton_ready": true`
- `"lighton_preflight_error": null`
- stable extraction latency and no rising 422 rate

## Tech Stack

- **Backend**: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async)
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Zustand
- **Database**: PostgreSQL 16 + pgvector
- **OCR**: Falcon-OCR (300M local inference) + GLM-OCR + LightOnOCR (canary fallback)
- **Evaluation**: Multi-provider LLM fallback (Gemini, GLM, OpenRouter + optional Qwen/Manus/Kimi/Minimax/Liquid)
- **APIs**: OpenAlex, Semantic Scholar, NIH RePORTER, OSF, ClinicalTrials.gov, Falcon-OCR, GLM-OCR.

## License

Proprietary — MatDAO
