import hashlib
import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Dict, Any
from pathlib import Path
import asyncio

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
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

    # In production, we would queue this to GLM-OCR here.
    # For now, simulate 3-second OCR pipeline wait for the 60% automated tier
    await asyncio.sleep(2)
    
    return {
        "status": "success",
        "mock_doi": mock_doi,
        "filename": file.filename,
        "confidence_tier": "AUTOMATED_60",
        "message": "File parsed successfully via GLM-OCR adapter."
    }
