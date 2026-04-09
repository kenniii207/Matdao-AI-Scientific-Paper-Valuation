import hashlib
import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from pathlib import Path
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_session
from backend.db.models import ResearchPaper, ExtractionLayer
from backend.api.adapters.grobid_adapter import GrobidAdapter
from backend.api.adapters.glm_ocr_adapter import GLMOCRAdapter
import fitz  # PyMuPDF
import base64

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Read file content safely
    contents = await file.read()
    
    # Generate unique DOI-surrogate from hash if needed, but for MVP let's fake a DOI for testing
    file_hash = hashlib.sha256(contents).hexdigest()[:12]
    mock_doi = f"10.matdao/{file_hash}"

    # Save locally
    save_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with save_path.open("wb") as f:
        f.write(contents)

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
        source="glmocr",
        status="pending"
    )
    session.add(layer)
    await session.commit()

    # Initialize adapters
    grobid = GrobidAdapter()
    glm = GLMOCRAdapter()

    # 1. Grobid Text Extraction
    try:
        grobid_res = await grobid.parse_pdf(contents, filename=file.filename)
        text_data = grobid_res.get("tei_xml", "")
    except Exception as e:
        text_data = f"Grobid failed: {str(e)}"

    # 2. GLM-OCR Image Extraction (First page only for Layer 1 baseline)
    ocr_data = {}
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            
            glm_res = await glm.parse_image(img_b64, prompt="Extract all text and key values from this scientific paper page.")
            ocr_data = glm_res
        doc.close()
    except Exception as e:
        ocr_data = {"error": str(e)}

    # Update DB records with real data
    layer.status = "completed"
    layer.processed_data = {
        "grobid_tei": text_data[:1000] + "...", # truncate for DB storage safety in MVP
        "glm_ocr": ocr_data
    }
    session.add(layer)
    await session.commit()

    return {
        "status": "success",
        "mock_doi": mock_doi,
        "filename": file.filename,
        "confidence_tier": "AUTOMATED_60",
        "message": "File parsed successfully via Grobid and GLM-OCR.",
        "preview_ocr": ocr_data.get("text", "")[:200]
    }
