# MatDAO Automation Framework

> Automated scientific due diligence — converting unstructured research PDFs into structured investment intelligence.

## Overview

MatDAO evaluates scientific research for investment using a **4-layer data extraction pipeline** and a **9-dimension scoring rubric**. The system automates 60-70% of the due diligence process, allowing human experts to focus on qualitative synthesis.

### 4-Layer Pipeline

| Layer | Strategy | Output |
|-------|----------|--------|
| **1. Neural Extraction** | Grobid + GLM-OCR | DOIs, ORCIDs, metadata, funding statements |
| **2. API Enrichment** | OpenAlex, Semantic Scholar, Crossref, NIH | Citation metrics, retraction status, funding verification |
| **3. Structured Intake** | JSON Schema + RJSF | Pre-filled scoring form for human review |
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

### Docker (Grobid + PostgreSQL)

```bash
docker-compose up -d
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
- **OCR**: Grobid (Docker) + GLM-OCR (0.9B multimodal model)
- **APIs**: OpenAlex, Semantic Scholar, Crossref, NIH RePORTER, OSF, ClinicalTrials.gov

## License

Proprietary — MatDAO
