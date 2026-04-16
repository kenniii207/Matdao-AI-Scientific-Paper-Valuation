import hashlib
import re
import io
import base64
import logging
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
    falcon_text = ""
    glm_text = ""
    extraction_source = "falcon-ocr"

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        if len(doc) > 0:
            # Extract first page as preview/metadata source
            page = doc[0]
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes))

            # 1. Primary: Falcon-OCR (High confidence local model)
            try:
                falcon = FalconOCRAdapter()
                falcon_text = await falcon.ocr(pil_img)
            except Exception as ef:
                logger.error(f"Falcon-OCR failed: {ef}")
                falcon_text = ""

            # 2. Fallback: GLM-OCR API (If Falcon failed or light usage is preferred)
            if not falcon_text or len(falcon_text) < 100:
                logger.info("Falcon yield low. Falling back to GLM-OCR API.")
                glm = GLMOCRAdapter()
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                glm_res = await glm.parse_image(img_b64)
                glm_text = glm_res.get("text", "")
                extraction_source = "glm-ocr-fallback"
        
        doc.close()
    except Exception as e:
        logger.error(f"PDF Processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    final_text = falcon_text or glm_text
    detected_doi = _extract_doi(final_text) or mock_doi

    # Update paper with detected DOI
    paper.doi = detected_doi
    layer.status = "completed"
    layer.source = extraction_source
    layer.processed_data = {
        "text_content": final_text[:5000],
        "falcon_used": bool(falcon_text),
        "glm_used": bool(glm_text),
        "detected_doi": detected_doi
    }
    
    session.add(paper)
    session.add(layer)
    await session.commit()

    return {
        "status": "success",
        "doi": paper.doi,
        "filename": file.filename,
        "confidence_tier": "FALCON_300M" if falcon_text else "GLM_API",
        "message": f"Extraction complete via {extraction_source}",
        "preview": final_text[:300],
        "paper_id": str(paper.id),
        "deduplicated": False
    }
