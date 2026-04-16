import hashlib
import re
import io
import base64
import logging
import json
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import fitz  # PyMuPDF
import torch

from backend.db.session import get_session
from backend.db.models import ResearchPaper, ExtractionLayer
from backend.api.adapters.glm_ocr_adapter import GLMOCRAdapter
from backend.api.adapters.falcon_ocr_adapter import FalconOCRAdapter

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

DOI_REGEX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)

def _extract_doi(*text_candidates: str) -> str | None:
    for candidate in text_candidates:
        if not candidate:
            continue
        match = DOI_REGEX.search(candidate)
        if match:
            return match.group(0).rstrip(".,);]")
    return None

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Upload PDF and trigger Falcon-first extraction pipeline."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()[:12]
    mock_doi = f"10.matdao/{file_hash}"

    # Save locally for reference
    save_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with save_path.open("wb") as f:
        f.write(contents)

    # Deduplication check
    existing_paper = await session.scalar(
        select(ResearchPaper).where(ResearchPaper.matdao_id == file_hash)
    )
    if existing_paper:
        return {
            "status": "success",
            "mock_doi": existing_paper.doi,
            "filename": file.filename,
            "message": "File already exists. Reusing data.",
            "paper_id": str(existing_paper.id),
            "deduplicated": True,
        }

    # Create record
    paper = ResearchPaper(
        matdao_id=file_hash,
        doi=mock_doi,
        title=file.filename,
    )
    session.add(paper)
    await session.commit()
    await session.refresh(paper)

    layer = ExtractionLayer(
        paper_id=paper.id,
        layer_number=1,
        source="falcon-ocr",
        status="pending"
    )
    session.add(layer)
    await session.commit()

    # Extraction Logic: Falcon-OCR -> GLM-OCR (API Fallback)
    final_text = ""
    extraction_source = "falcon-ocr"

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes))

            # 1. Primary: Falcon-OCR
            try:
                falcon = FalconOCRAdapter()
                final_text = await falcon.ocr(pil_img)
            except Exception as ef:
                logger.error(f"Falcon-OCR failed: {ef}")
                final_text = ""

            # 2. Fallback: GLM-OCR API
            if not final_text or len(final_text) < 100:
                logger.info("Falcon yield low. Falling back to GLM-OCR API.")
                glm = GLMOCRAdapter()
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                glm_res = await glm.parse_image(img_b64)
                final_text = glm_res.get("text", "")
                extraction_source = "glm-ocr-fallback"
        
        doc.close()
    except Exception as e:
        logger.error(f"PDF Processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    # 3. DOI Extraction and Metadata Enrichment
    detected_doi = _extract_doi(final_text) or mock_doi
    paper.doi = detected_doi
    
    # Enrich via APIs if a real DOI was found
    enriched_data = {}
    if not detected_doi.startswith("10.matdao/"):
        from backend.api.adapters.openalex_adapter import OpenAlexAdapter
        from backend.api.adapters.semantic_scholar_adapter import SemanticScholarAdapter
        
        oa = OpenAlexAdapter()
        s2 = SemanticScholarAdapter()
        try:
            enriched_data["openalex"] = await oa.get_work(doi=detected_doi)
            enriched_data["semantic_scholar"] = await s2.get_paper(doi=detected_doi)
        except Exception as ee:
            logger.warning(f"Enrichment failed for {detected_doi}: {ee}")
        finally:
            await oa.close()
            await s2.close()

    # 4. LLM Evaluation
    from backend.services.evaluation import ScientificEvaluator
    evaluator = ScientificEvaluator()
    eval_results = await evaluator.evaluate_content(final_text, enriched_data)

    # 5. Store Results
    layer.status = "completed"
    layer.source = extraction_source
    layer.processed_data = {
        "text_content": final_text[:5000],
        "eval_results": eval_results,
        "enriched_data": enriched_data
    }

    # Store in ScoringResultDB
    from backend.db.models import ScoringResultDB
    from backend.services.scoring.engine import compute_score
    
    raw_scores = {}
    origin_snippets = {}
    if "scores" in eval_results:
        for dim_id, data in eval_results["scores"].items():
            raw_scores[int(dim_id)] = data["score"]
            origin_snippets[int(dim_id)] = json.dumps({
                "rationale": data.get("rationale"),
                "snippet": data.get("origin_snippet")
            })

    scoring_result = compute_score(
        doi=detected_doi,
        raw_scores=raw_scores,
        origin_snippets=origin_snippets,
        automated_flags={i: True for i in range(1, 10)}
    )

    scoring_db = ScoringResultDB(
        paper_id=paper.id,
        version=1,
        total_score=scoring_result.total_score,
        grade=scoring_result.grade.value,
        integrity_gate_triggered=scoring_result.integrity_gate_triggered,
        origin_snippets={str(k): v for k, v in origin_snippets.items()},
        dim1_score=raw_scores.get(1),
        dim2_score=raw_scores.get(2),
        dim3_score=raw_scores.get(3),
        dim4_score=raw_scores.get(4),
        dim5_score=raw_scores.get(5),
        dim6_score=raw_scores.get(6),
        dim7_score=raw_scores.get(7),
        dim8_score=raw_scores.get(8),
        dim9_score=raw_scores.get(9),
        scored_by="llm-eval-v1"
    )
    
    session.add(paper)
    session.add(layer)
    session.add(scoring_db)
    await session.commit()

    return {
        "status": "success",
        "doi": paper.doi,
        "filename": file.filename,
        "score": scoring_db.total_score,
        "grade": scoring_db.grade,
        "eval_summary": eval_results.get("executive_summary"),
        "paper_id": str(paper.id)
    }
