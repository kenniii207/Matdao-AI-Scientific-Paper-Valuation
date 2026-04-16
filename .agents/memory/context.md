# MatDAO Session Memory — "Forever" Context
#
# Rule: Read this at the start of every session. 
# Update this with major decisions and progress.

## Session 2026-04-16 (Current)
- **Goal**: Implement Phase 2 (Falcon-OCR GPU) and Render Blueprint.
- **Status**: Backend code updated with Falcon-OCR (300M) on GPU fallback. Render Blueprint (render.yaml) created for 1-click deploy (standard tier + basic-1gb DB).
- **Decisions**: 
    - Removed retired NIH/Crossref adapters to clean clutter.
    - Added ZAI_API_KEY as general fallback.
    - Used `lfoppiano/grobid:latest-crf` for lightweight extraction.
- **Environment**: Phase 1 (Grobid) confirmed working. Phase 2 pending Render setup.

## Perpetual Guidelines
- Maintain "Caveman" mode for token efficiency.
- Layer 1 Extraction Order: Grobid (Text) -> Falcon-OCR (GPU Vision) -> GLM-OCR (API Vision).
- Integrity Gate: Governance Score 1 = Total 0.
