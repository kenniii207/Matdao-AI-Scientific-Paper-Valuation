import hashlib
import re
import logging
import json
import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Any
from pathlib import Path
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import fitz  # PyMuPDF

from backend.db.session import get_session, async_session_factory
from backend.db.models import EvaluationJob, ExtractionLayer, ResearchPaper, ScoringResultDB
from backend.core.config import settings
from backend.core.json_utils import coerce_jsonable
from backend.models.types import JsonDict
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
_QUEUE_WORKER_ID = f"eval-worker-{uuid.uuid4().hex[:10]}"
_WORKER_STOP_EVENT = asyncio.Event()
_WORKER_TASKS: list[asyncio.Task[None]] = []

DOI_REGEX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)

_KNOWN_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "application/vnd.pdf",
    "text/pdf",
}

def _extract_doi(*text_candidates: str) -> str | None:
    for candidate in text_candidates:
        if not candidate:
            continue
        match = DOI_REGEX.search(candidate)
        if match:
            return match.group(0).rstrip(".,);]")
    return None


def _is_likely_pdf(file: UploadFile, contents: bytes) -> bool:
    content_type = (file.content_type or "").lower().strip()
    filename = (file.filename or "").lower().strip()
    has_pdf_header = contents[:5] == b"%PDF-"
    filename_pdf = filename.endswith(".pdf")

    if content_type in _KNOWN_PDF_CONTENT_TYPES:
        return True
    if content_type in {"application/octet-stream", "binary/octet-stream"}:
        return has_pdf_header or filename_pdf
    return has_pdf_header or filename_pdf


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _assess_low_confidence(
    eval_results: JsonDict,
    enriched_data: JsonDict,
    raw_scores: dict[int, float],
) -> JsonDict:
    quality_signals = eval_results.get("_quality_signals", {}) if isinstance(eval_results, dict) else {}
    quality_signals = quality_signals if isinstance(quality_signals, dict) else {}
    source_errors = enriched_data.get("source_errors", {}) if isinstance(enriched_data, dict) else {}
    source_errors = source_errors if isinstance(source_errors, dict) else {}

    reasons: list[str] = []
    confidence_penalty = 0.0

    if quality_signals.get("pipeline_timed_out"):
        reasons.append("pipeline_timeout")
        confidence_penalty += 0.45
    if quality_signals.get("insufficient_evidence"):
        reasons.append("insufficient_evidence")
        confidence_penalty += 0.35
    if quality_signals.get("generic_output_detected"):
        reasons.append("generic_output")
        confidence_penalty += 0.15
    if eval_results.get("error"):
        reasons.append("llm_error")
        confidence_penalty += 0.35

    schema_repair_count = int(_safe_float(quality_signals.get("schema_repair_count"), 0.0))
    if schema_repair_count >= 4:
        reasons.append("heavy_schema_repair")
        confidence_penalty += min(0.25, schema_repair_count * 0.03)

    snippet_coverage = _safe_float(quality_signals.get("snippet_coverage_ratio"), 1.0)
    if snippet_coverage < 0.5:
        reasons.append("low_snippet_coverage")
        confidence_penalty += 0.2

    source_error_count = len(source_errors)
    if source_error_count >= 2:
        reasons.append("multiple_source_errors")
        confidence_penalty += min(0.2, source_error_count * 0.05)

    if len(raw_scores) < 7:
        reasons.append("sparse_dimension_coverage")
        confidence_penalty += 0.1

    confidence_score = max(0.0, min(1.0, round(1.0 - confidence_penalty, 4)))
    high_risk_flags = {"pipeline_timeout", "insufficient_evidence", "llm_error"}
    needs_review = bool(
        reasons
        and (
            confidence_score < 0.7
            or bool(high_risk_flags.intersection(reasons))
            or len(set(reasons)) >= 2
        )
    )

    return {
        "needs_review": needs_review,
        "confidence_score": confidence_score,
        "reasons": sorted(set(reasons)),
    }


def _is_neutral_nine_grid(score_row: Any) -> bool:
    dim_values = [
        _safe_float(getattr(score_row, f"dim{index}_score", None), 3.0)
        for index in range(1, 10)
    ]
    near_neutral = sum(1 for value in dim_values if abs(value - 3.0) <= 0.02)
    return near_neutral >= 8


def _should_rerun_existing_score(
    score_row: Any,
    eval_results: JsonDict | None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    eval_payload = eval_results if isinstance(eval_results, dict) else {}
    quality_signals = eval_payload.get("_quality_signals")
    quality_signals = quality_signals if isinstance(quality_signals, dict) else {}

    if quality_signals.get("llm_hard_failure"):
        reasons.append("llm_hard_failure")
    if quality_signals.get("insufficient_evidence"):
        reasons.append("insufficient_evidence")
    if quality_signals.get("pipeline_timed_out"):
        reasons.append("pipeline_timed_out")
    if eval_payload.get("error"):
        reasons.append("eval_error")
    if _safe_float(getattr(score_row, "total_score", None), 0.0) <= 60.05 and _is_neutral_nine_grid(score_row):
        reasons.append("flat_neutral_score")
    scored_by = str(getattr(score_row, "scored_by", "") or "").lower()
    if "timeout" in scored_by:
        reasons.append("timeout_scoring_version")

    high_value_reasons = {
        "llm_hard_failure",
        "insufficient_evidence",
        "pipeline_timed_out",
        "eval_error",
        "flat_neutral_score",
        "timeout_scoring_version",
    }
    should_rerun = bool(high_value_reasons.intersection(reasons))
    return should_rerun, sorted(set(reasons))


async def _latest_eval_results_for_paper(
    session: AsyncSession,
    paper_id: uuid.UUID,
) -> JsonDict:
    layers = (
        await session.scalars(
            select(ExtractionLayer)
            .where(ExtractionLayer.paper_id == paper_id)
            .order_by(ExtractionLayer.created_at.desc())
            .limit(15)
        )
    ).all()
    for layer in layers:
        processed = layer.processed_data if isinstance(layer.processed_data, dict) else {}
        maybe_eval = processed.get("eval_results")
        if isinstance(maybe_eval, dict):
            return maybe_eval
    return {}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _retry_delay_seconds(attempt_count: int) -> int:
    base = max(1, int(settings.evaluation_job_retry_base_seconds))
    bounded_attempt = max(1, min(attempt_count, 8))
    return base * (2 ** (bounded_attempt - 1))


async def _enqueue_evaluation_job_db(
    session: AsyncSession,
    paper_id: uuid.UUID,
    *,
    max_attempts: int | None = None,
) -> bool:
    active = await session.scalar(
        select(EvaluationJob)
        .where(
            EvaluationJob.paper_id == paper_id,
            EvaluationJob.status.in_(["queued", "retry", "processing"]),
        )
        .order_by(EvaluationJob.created_at.desc())
        .limit(1)
    )
    if active is not None:
        return False

    session.add(
        EvaluationJob(
            paper_id=paper_id,
            status="queued",
            attempt_count=0,
            max_attempts=max_attempts or int(settings.evaluation_job_max_retries),
            next_retry_at=_utcnow(),
            lease_expires_at=None,
            worker_id=None,
        )
    )
    return True


async def _claim_next_evaluation_job() -> EvaluationJob | None:
    now = _utcnow()
    lease_deadline = now + timedelta(seconds=max(15, int(settings.evaluation_job_lease_seconds)))
    async with async_session_factory() as session:
        async with session.begin():
            job = await session.scalar(
                select(EvaluationJob)
                .where(
                    or_(
                        and_(
                            EvaluationJob.status.in_(["queued", "retry"]),
                            or_(EvaluationJob.next_retry_at.is_(None), EvaluationJob.next_retry_at <= now),
                        ),
                        and_(
                            EvaluationJob.status == "processing",
                            EvaluationJob.lease_expires_at.is_not(None),
                            EvaluationJob.lease_expires_at < now,
                        ),
                    )
                )
                .order_by(EvaluationJob.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if job is None:
                return None
            job.status = "processing"
            job.attempt_count = int(job.attempt_count or 0) + 1
            job.worker_id = _QUEUE_WORKER_ID
            job.lease_expires_at = lease_deadline
            if job.started_at is None:
                job.started_at = now
            job.updated_at = now
            await session.flush()
            await session.refresh(job)
            return job


async def _mark_job_completed(job_id: uuid.UUID) -> None:
    now = _utcnow()
    async with async_session_factory() as session:
        job = await session.get(EvaluationJob, job_id)
        if job is None:
            return
        job.status = "completed"
        job.finished_at = now
        job.lease_expires_at = None
        job.worker_id = None
        job.updated_at = now
        await session.commit()


async def _mark_job_failed(job_id: uuid.UUID, error: str) -> None:
    now = _utcnow()
    async with async_session_factory() as session:
        job = await session.get(EvaluationJob, job_id)
        if job is None:
            return

        attempt_count = int(job.attempt_count or 0)
        max_attempts = max(1, int(job.max_attempts or settings.evaluation_job_max_retries))
        if attempt_count >= max_attempts:
            job.status = "dead"
            job.finished_at = now
            job.next_retry_at = None
            layer_status = "error"
        else:
            delay_seconds = _retry_delay_seconds(attempt_count)
            job.status = "retry"
            job.next_retry_at = now + timedelta(seconds=delay_seconds)
            layer_status = "queued"
        job.last_error = error[:2000]
        job.lease_expires_at = None
        job.worker_id = None
        job.updated_at = now

        latest_layer = await session.scalar(
            select(ExtractionLayer)
            .where(ExtractionLayer.paper_id == job.paper_id)
            .order_by(ExtractionLayer.created_at.desc())
            .limit(1)
        )
        if latest_layer is not None:
            latest_layer.status = layer_status
            processed = latest_layer.processed_data if isinstance(latest_layer.processed_data, dict) else {}
            processed["error"] = error[:2000]
            processed["job_attempt"] = attempt_count
            processed["job_max_attempts"] = max_attempts
            processed["next_retry_at"] = (
                job.next_retry_at.isoformat() if job.next_retry_at is not None else None
            )
            latest_layer.processed_data = processed

        await session.commit()


async def _sweep_stale_evaluation_jobs() -> int:
    now = _utcnow()
    async with async_session_factory() as session:
        stale_jobs = (
            await session.scalars(
                select(EvaluationJob).where(
                    EvaluationJob.status == "processing",
                    EvaluationJob.lease_expires_at.is_not(None),
                    EvaluationJob.lease_expires_at < now,
                )
            )
        ).all()
        if not stale_jobs:
            return 0

        reclaimed = 0
        for job in stale_jobs:
            job.status = "retry"
            job.next_retry_at = now
            job.lease_expires_at = None
            job.worker_id = None
            if not job.last_error:
                job.last_error = "stale lease reclaimed by sweeper"
            reclaimed += 1
        await session.commit()
        return reclaimed


async def _evaluate_and_score(paper_id: str) -> None:
    """Run one evaluation pipeline for a paper ID."""
    from backend.db.models import ScoringResultDB
    from backend.services.scoring.engine import compute_score
    from backend.services.evaluation import ScientificEvaluator

    try:
        paper_uuid = uuid.UUID(paper_id)
    except (TypeError, ValueError):
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
                    async def _run_pipeline() -> tuple[JsonDict, JsonDict]:
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
                quality_signals = (
                    eval_results.get("_quality_signals", {})
                    if isinstance(eval_results, dict)
                    else {}
                )
                quality_signals = quality_signals if isinstance(quality_signals, dict) else {}
                schema_repair_count = int(_safe_float(quality_signals.get("schema_repair_count"), 0.0))
                llm_hard_failure = bool(quality_signals.get("llm_hard_failure"))
                unrecoverable_llm_failure = llm_hard_failure or (
                    bool(eval_results.get("error")) and schema_repair_count >= 25
                )
                if unrecoverable_llm_failure:
                    logger.error(
                        "Skipping scoring due to LLM hard failure for paper_id=%s error=%s quality=%s",
                        paper_id,
                        eval_results.get("error"),
                        quality_signals,
                    )
                    if layer is not None:
                        merged_stage_timings = {
                            "pipeline_total_ms": round((time.perf_counter() - pipeline_start) * 1000, 2),
                            **(jsonable_enriched_data.get("stage_timings_ms", {}) if isinstance(jsonable_enriched_data.get("stage_timings_ms"), dict) else {}),
                            **(eval_results.get("stage_timings_ms", {}) if isinstance(eval_results.get("stage_timings_ms"), dict) else {}),
                        }
                        layer.status = "error"
                        layer.processed_data = {
                            "error": "llm_providers_unavailable",
                            "error_detail": str(eval_results.get("error") or "No structured scores"),
                            "document_profile": paper_profile,
                            "eval_results": eval_results,
                            "enriched_data": jsonable_enriched_data,
                            "stage_timings_ms": merged_stage_timings,
                            "pipeline_timed_out": timed_out,
                        }
                        await session.commit()
                    raise RuntimeError("llm_providers_unavailable")

                raw_scores: dict[int, float] = {}
                origin_snippets: dict[int, str] = {}
                if "scores" in eval_results:
                    for dim_id, data in eval_results["scores"].items():
                        try:
                            dim_index = int(str(dim_id).strip())
                        except (TypeError, ValueError):
                            continue
                        if dim_index < 1 or dim_index > 9:
                            continue
                        try:
                            score = float(data.get("score", 3.0))
                        except (AttributeError, TypeError, ValueError):
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
                    scored_by="llm-eval-v2",
                )
                session.add(scoring_db)
                low_confidence = _assess_low_confidence(eval_results, jsonable_enriched_data, raw_scores)
                if low_confidence["needs_review"]:
                    review_layer = ExtractionLayer(
                        paper_id=paper.id,
                        layer_number=3,
                        source="low-confidence-queue",
                        status="pending_review",
                        processed_data={
                            "queue_type": "low_confidence_review",
                            "confidence_score": low_confidence["confidence_score"],
                            "reasons": low_confidence["reasons"],
                            "quality_signals": eval_results.get("_quality_signals", {}),
                            "source_errors": jsonable_enriched_data.get("source_errors", {}),
                            "raw_dimension_scores": {str(key): value for key, value in raw_scores.items()},
                        },
                    )
                    session.add(review_layer)

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
                        "low_confidence_review": low_confidence,
                    }
                await session.commit()
            except Exception as exc:
                logger.exception("Background evaluation failed for paper %s", paper_id)
                if layer is not None:
                    layer.status = "error"
                    layer.processed_data = {"error": str(exc)}
                    await session.commit()
                raise


async def recover_pending_evaluations(max_jobs: int = 50) -> int:
    """Recover queued/processing extraction rows into durable evaluation jobs."""
    queued_statuses = {"queued", "processing"}
    async with async_session_factory() as session:
        now = _utcnow()
        orphaned_processing = (
            await session.scalars(
                select(EvaluationJob).where(
                    EvaluationJob.status == "processing",
                    EvaluationJob.lease_expires_at.is_(None),
                )
            )
        ).all()
        for job in orphaned_processing:
            job.status = "retry"
            job.next_retry_at = now
            job.worker_id = None
            job.last_error = job.last_error or "orphaned processing job recovered on startup"

        candidate_ids = (
            await session.scalars(
                select(ExtractionLayer.paper_id)
                .where(ExtractionLayer.status.in_(queued_statuses))
                .order_by(ExtractionLayer.created_at.desc())
            )
        ).all()

        unique_ids: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        for candidate_id in candidate_ids:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            unique_ids.append(candidate_id)
            if len(unique_ids) >= max_jobs:
                break

        recovered = 0
        for candidate_id in unique_ids:
            has_score = await session.scalar(
                select(ScoringResultDB.id)
                .where(ScoringResultDB.paper_id == candidate_id)
                .limit(1)
            )
            if has_score is not None:
                continue
            if await _enqueue_evaluation_job_db(session, candidate_id):
                recovered += 1
        await session.commit()

    return recovered


async def _evaluation_worker_loop(worker_name: str) -> None:
    poll_interval = max(0.25, float(settings.evaluation_job_poll_interval_seconds))
    while not _WORKER_STOP_EVENT.is_set():
        try:
            job = await _claim_next_evaluation_job()
            if job is None:
                await asyncio.sleep(poll_interval)
                continue

            try:
                await _evaluate_and_score(str(job.paper_id))
            except Exception as exc:
                await _mark_job_failed(job.id, str(exc))
                logger.warning(
                    "Evaluation job failed worker=%s job_id=%s paper_id=%s attempt=%s error=%s",
                    worker_name,
                    job.id,
                    job.paper_id,
                    job.attempt_count,
                    exc,
                )
            else:
                await _mark_job_completed(job.id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Evaluation worker loop crash in %s; continuing", worker_name)
            await asyncio.sleep(poll_interval)


async def _stale_job_sweeper_loop() -> None:
    interval = max(5, int(settings.evaluation_stale_sweep_interval_seconds))
    while not _WORKER_STOP_EVENT.is_set():
        try:
            reclaimed = await _sweep_stale_evaluation_jobs()
            if reclaimed:
                logger.warning("Reclaimed %d stale evaluation job(s)", reclaimed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Stale evaluation sweeper crashed; continuing")
        await asyncio.sleep(interval)


async def start_evaluation_workers() -> None:
    """Start durable queue workers and stale sweeper once per process."""
    if _WORKER_TASKS:
        return
    _WORKER_STOP_EVENT.clear()
    worker_count = max(1, int(settings.max_parallel_evaluations))
    for index in range(worker_count):
        name = f"eval-worker-{index + 1}"
        _WORKER_TASKS.append(asyncio.create_task(_evaluation_worker_loop(name), name=name))
    _WORKER_TASKS.append(asyncio.create_task(_stale_job_sweeper_loop(), name="eval-stale-sweeper"))


async def stop_evaluation_workers() -> None:
    """Stop worker tasks cleanly on shutdown."""
    if not _WORKER_TASKS:
        return
    _WORKER_STOP_EVENT.set()
    for task in _WORKER_TASKS:
        task.cancel()
    results = await asyncio.gather(*_WORKER_TASKS, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.error("Worker shutdown saw exception: %s", result)
    _WORKER_TASKS.clear()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> JsonDict:
    """Upload PDF and trigger extraction + evaluation pipeline.

    Extraction order:
    1) Native PDF text extraction (fast, best for born-digital PDFs)
    2) GLM-OCR fallback on first page (optional; requires `ZAI_API_KEY`)
    """
    contents = await file.read()
    if not _is_likely_pdf(file, contents):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed. Upload a valid .pdf document.",
        )
    file_hash = hashlib.sha256(contents).hexdigest()[:12]
    synthetic_doi = f"10.matdao/{file_hash}"

    save_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with save_path.open("wb") as f:
        f.write(contents)

    existing_paper = await session.scalar(
        select(ResearchPaper).where(ResearchPaper.matdao_id == file_hash)
    )
    if existing_paper:
        existing_score = await session.scalar(
            select(ScoringResultDB)
            .where(ScoringResultDB.paper_id == existing_paper.id)
            .order_by(ScoringResultDB.version.desc())
            .limit(1)
        )
        if existing_score is not None:
            existing_eval_results = await _latest_eval_results_for_paper(session, existing_paper.id)
            should_rerun, rerun_reasons = _should_rerun_existing_score(existing_score, existing_eval_results)
            if should_rerun:
                logger.info(
                    "Re-running evaluation for paper_id=%s due to reasons=%s",
                    existing_paper.id,
                    rerun_reasons,
                )
            else:
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
        paper = existing_paper
    else:
        paper = ResearchPaper(
            matdao_id=file_hash,
            doi=synthetic_doi,
            title=file.filename,
        )
        session.add(paper)
        await session.commit()
        await session.refresh(paper)

    if existing_paper and existing_score is not None:
        stale_rows = (
            await session.scalars(
                select(ScoringResultDB).where(ScoringResultDB.paper_id == paper.id)
            )
        ).all()
        for stale_row in stale_rows:
            await session.delete(stale_row)
        await session.commit()

    if existing_paper and existing_score is not None and should_rerun:
        existing_job = await session.scalar(
            select(EvaluationJob)
            .where(EvaluationJob.paper_id == paper.id, EvaluationJob.status.in_(["queued", "retry", "processing"]))
            .order_by(EvaluationJob.created_at.desc())
            .limit(1)
        )
        if existing_job is not None:
            return {
                "status": "queued",
                "doi": paper.doi,
                "filename": file.filename,
                "paper_id": str(paper.id),
                "deduplicated": True,
                "message": "File already exists and is currently being re-evaluated.",
            }

    layer = ExtractionLayer(
        paper_id=paper.id,
        layer_number=1,
        source="pdf-text",
        status="pending"
    )
    session.add(layer)
    await session.commit()

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

    detected_doi = _extract_doi(final_text) or synthetic_doi
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
    await _enqueue_evaluation_job_db(session, paper.id)
    await session.commit()

    return {
        "status": "queued",
        "doi": paper.doi,
        "filename": file.filename,
        "paper_id": str(paper.id)
    }
