import hashlib
import re
import logging
import json
import asyncio
import time
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import fitz  # PyMuPDF

from backend.db.session import get_session, async_session_factory
from backend.db.models import ResearchPaper, ExtractionLayer
from backend.core.config import settings
from backend.core.json_utils import coerce_jsonable
from backend.api.adapters.glm_ocr_adapter import GLMOCRAdapter
from backend.services.research_enrichment import (
    build_document_profile,
    build_external_enrichment,
)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
_EVALUATION_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.max_parallel_evaluations)))

DOI_REGEX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)

def _extract_doi(*text_candidates: str) -> str | None:
    for candidate in text_candidates:
        if not candidate:
            continue
        match = DOI_REGEX.search(candidate)
        if match:
            return match.group(0).rstrip(".,);]")
    return None


async def _evaluate_and_score(paper_id: str) -> None:
    """Background evaluation job for a paper already extracted into DB."""
    from backend.db.models import ScoringResultDB
    from backend.services.scoring.engine import compute_score
    from backend.services.evaluation import ScientificEvaluator

    try:
        paper_uuid = uuid.UUID(paper_id)
    except Exception:
        logger.error("Background evaluation got invalid paper_id=%r", paper_id)
        return

    async with _EVALUATION_SEMAPHORE:
        async with async_session_factory() as session:
            paper = await session.get(ResearchPaper, paper_uuid)
            if paper is None:
                logger.error("Background evaluation could not find paper_id=%s", paper_id)
                return

            existing_score = await session.scalar(
                select(ScoringResultDB)
                .where(ScoringResultDB.paper_id == paper.id)
                .order_by(ScoringResultDB.version.desc())
                .limit(1)
            )
            if existing_score is not None:
                return

            layer = await session.scalar(
                select(ExtractionLayer)
                .where(ExtractionLayer.paper_id == paper.id)
                .order_by(ExtractionLayer.created_at.desc())
                .limit(1)
            )
            if layer is not None:
                layer.status = "processing"
                await session.commit()

            try:
                pipeline_start = time.perf_counter()
                paper_profile = build_document_profile(
                    paper.raw_text or "",
                    fallback_title=paper.title,
                )
                timeout_seconds = max(15, int(settings.evaluation_pipeline_timeout_seconds))
                timed_out = False
                try:
                    async def _run_pipeline() -> tuple[dict[str, Any], dict[str, Any]]:
                        enriched_payload = await build_external_enrichment(
                            doi=paper.doi or "",
                            document_profile=paper_profile,
                        )
                        evaluator = ScientificEvaluator()
                        jsonable_payload = coerce_jsonable(enriched_payload)
                        eval_payload = await evaluator.evaluate_content(paper.raw_text or "", jsonable_payload)
                        return enriched_payload, eval_payload

                    enriched_data, eval_results = await asyncio.wait_for(
                        _run_pipeline(),
                        timeout=timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    timed_out = True
                    timeout_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
                    enriched_data = {
                        "document_profile": paper_profile,
                        "source_errors": {"pipeline_timeout": f"Timed out after {timeout_seconds}s"},
                        "stage_timings_ms": {"pipeline_timeout_ms": timeout_ms},
                    }
                    eval_results = {
                        "error": "evaluation_timeout",
                        "_quality_signals": {
                            "pipeline_timed_out": True,
                            "timeout_seconds": timeout_seconds,
                        },
                        "stage_timings_ms": {"llm_stage_ms": 0.0},
                    }

                jsonable_enriched_data = coerce_jsonable(enriched_data)

                raw_scores: dict[int, float] = {}
                origin_snippets: dict[int, str] = {}
                if "scores" in eval_results:
                    for dim_id, data in eval_results["scores"].items():
                        try:
                            dim_index = int(str(dim_id).strip())
                        except Exception:
                            continue
                        if dim_index < 1 or dim_index > 9:
                            continue
                        try:
                            score = float(data.get("score", 3.0))
                        except Exception:
                            score = 3.0
                        score = max(1.0, min(5.0, score))
                        raw_scores[dim_index] = score
                        origin_snippets[dim_index] = json.dumps(
                            {
                                "rationale": data.get("rationale"),
                                "snippet": data.get("origin_snippet"),
                            }
                        )

                scoring_result = compute_score(
                    doi=paper.doi or str(paper.id),
                    raw_scores=raw_scores,
                    origin_snippets=origin_snippets,
                    automated_flags={i: True for i in range(1, 10)},
                )

                latest_version = await session.scalar(
                    select(func.max(ScoringResultDB.version)).where(ScoringResultDB.paper_id == paper.id)
                )
                scoring_db = ScoringResultDB(
                    paper_id=paper.id,
                    version=(latest_version or 0) + 1,
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
                    scored_by="llm-timeout-fallback-v1" if timed_out else "llm-eval-v1",
                )
                session.add(scoring_db)

                if layer is not None:
                    enriched_stage = jsonable_enriched_data.get("stage_timings_ms", {})
                    eval_stage = eval_results.get("stage_timings_ms", {}) if isinstance(eval_results, dict) else {}
                    merged_stage_timings = {
                        "pipeline_total_ms": round((time.perf_counter() - pipeline_start) * 1000, 2),
                        **(enriched_stage if isinstance(enriched_stage, dict) else {}),
                        **(eval_stage if isinstance(eval_stage, dict) else {}),
                    }
                    layer.status = "completed"
                    layer.processed_data = {
                        "text_content": (paper.raw_text or "")[:5000],
                        "document_profile": paper_profile,
                        "eval_results": eval_results,
                        "enriched_data": jsonable_enriched_data,
                        "stage_timings_ms": merged_stage_timings,
                        "pipeline_timed_out": timed_out,
                    }
                await session.commit()
            except Exception as exc:
                logger.exception("Background evaluation failed for paper %s", paper_id)
                if layer is not None:
                    layer.status = "error"
                    layer.processed_data = {"error": str(exc)}
                    await session.commit()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Upload PDF and trigger extraction + evaluation pipeline.

    Extraction order:
    1) Native PDF text extraction (fast, best for born-digital PDFs)
    2) GLM-OCR fallback on first page (optional; requires `ZAI_API_KEY`)
    """
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
        from backend.db.models import ScoringResultDB

        existing_score = await session.scalar(
            select(ScoringResultDB)
            .where(ScoringResultDB.paper_id == existing_paper.id)
            .order_by(ScoringResultDB.version.desc())
            .limit(1)
        )
        if existing_score is not None:
            return {
                "status": "success",
                "doi": existing_paper.doi,
                "filename": file.filename,
                "score": existing_score.total_score,
                "grade": existing_score.grade,
                "eval_summary": None,
                "paper_id": str(existing_paper.id),
                "deduplicated": True,
                "message": "File already exists. Reusing latest scoring result.",
            }
        # Paper exists but no scoring record (previous run failed or still processing).
        # Continue pipeline to generate scoring instead of returning a false-success.
        paper = existing_paper
    else:
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
        source="pdf-text",
        status="pending"
    )
    session.add(layer)
    await session.commit()

    # Extraction Logic: PDF text -> GLM-OCR (API fallback)
    final_text = ""
    extraction_source = "pdf-text"
    extraction_start = time.perf_counter()

    doc: fitz.Document | None = None
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        if len(doc) <= 0:
            raise HTTPException(status_code=400, detail="PDF contains no pages")

        text_parts: list[str] = []
        for page in doc:
            try:
                text_parts.append(page.get_text("text"))
            except Exception:
                continue
        native_text = "\n".join(text_parts).strip()

        if native_text and len(native_text) >= 300:
            final_text = native_text
            extraction_source = "pdf-text"
        else:
            logger.info("Native PDF text extraction low. Trying GLM-OCR fallback on first page.")
            if not settings.zai_api_key:
                raise HTTPException(
                    status_code=422,
                    detail="Extraction failed: PDF has little/no embedded text. Configure `ZAI_API_KEY` for GLM-OCR fallback, or upload a text-based PDF.",
                )
            glm = GLMOCRAdapter()
            try:
                pix = doc[0].get_pixmap()
                img_bytes = pix.tobytes("png")
                import base64

                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                glm_res = await glm.parse_image(img_b64)
                final_text = (glm_res.get("text") or "").strip()
                extraction_source = "glm-ocr-fallback"
            except Exception as eg:
                logger.error(f"GLM-OCR failed: {eg}")
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Extraction failed: PDF has little/no embedded text and OCR not working. "
                        f"Details: {eg}"
                    ),
                ) from eg
            finally:
                await glm.close()
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"PDF processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}") from e
    finally:
        try:
            if doc is not None:
                doc.close()
        except Exception:
            pass

    if not final_text or len(final_text.strip()) < 5:
        logger.error("Extraction failed: No text recovered from PDF.")
        raise HTTPException(
            status_code=422, 
            detail="Extraction failed: Could not extract meaningful text from this PDF. It might be corrupted or entirely unreadable."
        )

    # 3. DOI Extraction and Metadata Enrichment
    detected_doi = _extract_doi(final_text) or mock_doi
    parsed_profile = build_document_profile(final_text, fallback_title=file.filename)
    paper.doi = detected_doi
    paper.title = parsed_profile.get("title") or file.filename
    paper.abstract = parsed_profile.get("abstract")
    paper.raw_text = final_text

    layer.status = "queued"
    layer.source = extraction_source
    layer.processed_data = {
        "text_content": final_text[:5000],
        "document_profile": parsed_profile,
        "stage_timings_ms": {
            "extract_ms": round((time.perf_counter() - extraction_start) * 1000, 2),
        },
    }
    session.add(paper)
    session.add(layer)
    await session.commit()

    asyncio.create_task(_evaluate_and_score(str(paper.id)))

    return {
        "status": "queued",
        "doi": paper.doi,
        "filename": file.filename,
        "paper_id": str(paper.id)
    }
