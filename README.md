# MatDAO Automation Framework

> Automated scientific due diligence — converting unstructured research PDFs into structured investment intelligence.

## Overview

MatDAO evaluates scientific research for investment using a **4-layer data extraction pipeline** and a **9-dimension scoring rubric**. The system automates 60-70% of the due diligence process, allowing human experts to focus on qualitative synthesis.

### 4-Layer Pipeline

| Layer | Strategy | Output |
|-------|----------|--------|
| **1. Neural Extraction** | Falcon-OCR (local) + GLM-OCR | Text extraction, table parsing, DOI discovery |
| **2. API Enrichment** | OpenAlex, Semantic Scholar, Crossref | Citation metrics, retraction status, funding verification |
| **3. Autonomous Eval** | LLM Synthesis (GLM-4) | 9-dimension scoring, rationale, audit snippets |
| **4. Expert Audit** | Human-in-the-loop | Final investment grading |

### Integrity Gate (Dimension 9)

If a **retraction** is detected via Crossref, the total score is **forced to 0** regardless of all other dimensions. This is a binary multiplier — no exceptions.

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

## Tech Stack

- **Backend**: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async)
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Zustand
- **Database**: PostgreSQL 16 + pgvector
- **OCR**: Falcon-OCR (300M local inference) + GLM-OCR (API fallback)
- **Evaluation**: GLM-4 (Scientific synthesis & 9-dimension scoring)
- **APIs**: OpenAlex, Semantic Scholar, Crossref (retraction), NIH RePORTER, OSF, ClinicalTrials.gov, Falcon-OCR, GLM-OCR.

## License

Proprietary — MatDAO
