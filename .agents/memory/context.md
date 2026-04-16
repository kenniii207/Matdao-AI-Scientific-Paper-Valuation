# MatDAO Session Memory — "Forever" Context
#
# Status: Phase 1 (Grobid) ABANDONED. 

## Session 2026-04-16 (Current)
- **Pivot**: Scrapped Grobid (OOM/Resource heavy). Moved to **Falcon-first** pipeline.
- **Pipeline**:
    1. Falcon-OCR (Local GPU 300M) = Primary.
    2. GLM-OCR (Z.ai API) = Fallback.
    3. LLM Router = Dynamic selection (Gemini/DeepSeek/GLM).
- **Infra**: Render Blueprint simplified to single GPU service. 
- **Purge**: All Grobid adapter code and services DELETED.

## Perpetual Guidelines
- Falcon-300M stays on GPU. 
- Use `low_cpu_mem_usage=True` for transformers.
- Context injection: Prefer small snippets. 
- Integrity Gate: Governance Score 1 = Total 0.
