import hashlib
import re
import logging
import json
import asyncio
import time
import uuid
import base64
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
from backend.api.adapters.lighton_ocr_adapter import LightOnOCRAdapter
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
_OCR_MEANINGFUL_TEXT_LEN = 300
_OCR_MIN_ACCEPTABLE_TEXT_LEN = 80
_OCR_SAMPLE_PAGES = 3
_LIGHTON_PREFLIGHT_CACHE: dict[str, Any] = {
    "checked_monotonic": 0.0,
    "checked_unix": 0.0,
    "error": "not_checked",
    "enabled": False,
    "base_url": "",
}

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


def _resolve_ocr_fallback_order(config_value: str | None = None) -> list[str]:
    allowed = {"pdf_text", "glm_ocr", "lighton_ocr"}
    raw = str(config_value if config_value is not None else settings.ocr_fallback_order)
    configured = [item.strip().lower() for item in raw.split(",") if item.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in configured:
        if item not in allowed or item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    if not deduped:
        return ["pdf_text", "glm_ocr", "lighton_ocr"]
    if "pdf_text" not in deduped:
        deduped.insert(0, "pdf_text")
    return deduped


def _build_ocr_quality_signals(
    *,
    provider: str,
    fallback_used: bool,
    error_chain: dict[str, str],
    model_id: str | None,
) -> JsonDict:
    return {
        "ocr_provider": provider,
        "ocr_fallback_used": fallback_used,
        "ocr_error_chain": error_chain,
        "ocr_model_id": model_id or "none",
    }


def _safe_error_fragment(value: Any, max_len: int = 180) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if not text:
        return "unknown_error"
    return text[:max_len]


def _is_upload_size_exceeded(size_bytes: int, max_upload_bytes: int) -> bool:
    return int(size_bytes) > max(1, int(max_upload_bytes))


def _derive_client_error_code(error_value: str) -> str:
    value = (error_value or "").lower()
    if "timeout" in value:
        return "timeout"
    if "missing" in value or "not_configured" in value:
        return "not_configured"
    if "health" in value or "unhealthy" in value:
        return "unhealthy"
    if "skip" in value:
        return "skipped"
    if "empty" in value:
        return "empty"
    return "failed"


def _client_safe_ocr_codes(error_chain: dict[str, str]) -> list[str]:
    safe_codes: list[str] = []
    for provider in ("pdf_text", "glm_ocr", "lighton_ocr", "ocr_chain"):
        error_value = error_chain.get(provider)
        if not error_value:
            continue
        safe_codes.append(f"{provider}:{_derive_client_error_code(error_value)}")
    if not safe_codes:
        safe_codes.append("ocr_chain:failed")
    return safe_codes


def _build_public_ocr_failure_detail(error_chain: dict[str, str]) -> str:
    safe_codes = ",".join(_client_safe_ocr_codes(error_chain))
    return (
        "Extraction failed: Could not extract meaningful text from this PDF. "
        f"It may be unreadable or image-only. error_codes={safe_codes}"
    )


def _merge_with_ocr_quality_signals(payload: JsonDict, ocr_quality_signals: JsonDict | None) -> JsonDict:
    merged = dict(payload)
    if isinstance(ocr_quality_signals, dict) and ocr_quality_signals:
        merged["ocr_quality_signals"] = ocr_quality_signals
    return merged


def _compute_page_render_scale(width: float, height: float, max_pixels: int) -> float:
    safe_width = max(1.0, float(width or 1.0))
    safe_height = max(1.0, float(height or 1.0))
    total_pixels = safe_width * safe_height
    cap = max(1, int(max_pixels))
    if total_pixels <= cap:
        return 1.0
    scale = (cap / total_pixels) ** 0.5
    return max(0.1, min(1.0, scale))


def _ocr_page_indices(total_pages: int, max_pages: int = _OCR_SAMPLE_PAGES) -> list[int]:
    safe_pages = max(1, int(max_pages))
    return list(range(min(max(0, int(total_pages)), safe_pages)))


def _render_doc_page_base64(doc: fitz.Document, page_index: int, max_pixels: int) -> str:
    page = doc[page_index]
    scale = _compute_page_render_scale(page.rect.width, page.rect.height, max_pixels)
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")


def _should_route_lighton(request_key: str, canary_percent: int | None = None) -> bool:
    percent = int(
        settings.lightonocr_canary_percent if canary_percent is None else canary_percent
    )
    percent = max(0, min(100, percent))
    if percent >= 100:
        return True
    if percent <= 0:
        return False
    seed = (request_key or "default").encode("utf-8")
    bucket = int(hashlib.sha256(seed).hexdigest()[:8], 16) % 100
    return bucket < percent


async def _lighton_preflight_error() -> str | None:
    ttl_seconds = max(0, int(settings.lightonocr_readiness_cache_seconds))
    now_monotonic = time.monotonic()
    cached_error = _LIGHTON_PREFLIGHT_CACHE.get("error")
    checked_monotonic = float(_LIGHTON_PREFLIGHT_CACHE.get("checked_monotonic") or 0.0)
    cache_matches_current = (
        bool(_LIGHTON_PREFLIGHT_CACHE.get("enabled")) == bool(settings.lightonocr_enabled)
        and str(_LIGHTON_PREFLIGHT_CACHE.get("base_url") or "") == str(settings.lightonocr_base_url or "")
    )
    if (
        cache_matches_current
        and
        ttl_seconds > 0
        and checked_monotonic > 0.0
        and (now_monotonic - checked_monotonic) <= ttl_seconds
        and isinstance(cached_error, (str, type(None)))
    ):
        return cached_error

    if not settings.lightonocr_enabled:
        computed_error: str | None = "lighton_disabled"
    else:
        contract_errors = LightOnOCRAdapter.runtime_contract_errors()
        if contract_errors:
            computed_error = ",".join(contract_errors)
        else:
            checker = LightOnOCRAdapter()
            try:
                if not await checker.health_check():
                    computed_error = "lighton_health_check_failed"
                else:
                    computed_error = None
            finally:
                await checker.close()

    _LIGHTON_PREFLIGHT_CACHE["checked_monotonic"] = now_monotonic
    _LIGHTON_PREFLIGHT_CACHE["checked_unix"] = time.time()
    _LIGHTON_PREFLIGHT_CACHE["error"] = computed_error
    _LIGHTON_PREFLIGHT_CACHE["enabled"] = bool(settings.lightonocr_enabled)
    _LIGHTON_PREFLIGHT_CACHE["base_url"] = str(settings.lightonocr_base_url or "")
    return computed_error


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
            existing_ocr_quality_signals: JsonDict = {}
            if layer is not None and isinstance(layer.processed_data, dict):
                maybe_ocr_signals = layer.processed_data.get("ocr_quality_signals")
                if isinstance(maybe_ocr_signals, dict):
                    existing_ocr_quality_signals = maybe_ocr_signals
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
                        if layer is not None and isinstance(layer.processed_data, dict):
                            ocr_signals = layer.processed_data.get("ocr_quality_signals")
                            if isinstance(ocr_signals, dict):
                                enriched_payload["ocr_quality_signals"] = ocr_signals
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
                        layer.processed_data = _merge_with_ocr_quality_signals({
                            "error": "llm_providers_unavailable",
                            "error_detail": str(eval_results.get("error") or "No structured scores"),
                            "document_profile": paper_profile,
                            "eval_results": eval_results,
                            "enriched_data": jsonable_enriched_data,
                            "stage_timings_ms": merged_stage_timings,
                            "pipeline_timed_out": timed_out,
                        }, existing_ocr_quality_signals)
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
                    layer.processed_data = _merge_with_ocr_quality_signals({
                        "text_content": (paper.raw_text or "")[:5000],
                        "document_profile": paper_profile,
                        "eval_results": eval_results,
                        "enriched_data": jsonable_enriched_data,
                        "stage_timings_ms": merged_stage_timings,
                        "pipeline_timed_out": timed_out,
                        "low_confidence_review": low_confidence,
                    }, existing_ocr_quality_signals)
                await session.commit()
            except Exception as exc:
                logger.exception("Background evaluation failed for paper %s", paper_id)
                if layer is not None:
                    layer.status = "error"
                    layer.processed_data = _merge_with_ocr_quality_signals({
                        "error": str(exc),
                    }, existing_ocr_quality_signals)
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


@router.get("/jobs/stats")
async def get_job_stats() -> JsonDict:
    """Return live counts of evaluation jobs per state, plus dead job error logs."""
    async with async_session_factory() as session:
        counts_rows = (
            await session.execute(
                select(EvaluationJob.status, func.count(EvaluationJob.id).label("cnt"))
                .group_by(EvaluationJob.status)
            )
        ).all()
        counts: dict[str, int] = {row[0]: row[1] for row in counts_rows}

        dead_jobs_rows = (
            await session.scalars(
                select(EvaluationJob)
                .where(EvaluationJob.status == "dead")
                .order_by(EvaluationJob.updated_at.desc())
                .limit(50)
            )
        ).all()
        dead_log = [
            {
                "job_id": str(job.id),
                "paper_id": str(job.paper_id),
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "error_log": job.last_error or "no error recorded",
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            }
            for job in dead_jobs_rows
        ]

    return {
        "queued": counts.get("queued", 0),
        "processing": counts.get("processing", 0),
        "retry": counts.get("retry", 0),
        "dead": counts.get("dead", 0),
        "completed": counts.get("completed", 0),
        "total_active": counts.get("queued", 0) + counts.get("processing", 0) + counts.get("retry", 0),
        "dead_letter_queue": dead_log,
        "config": {
            "max_retries": int(settings.evaluation_job_max_retries),
            "lease_seconds": int(settings.evaluation_job_lease_seconds),
            "poll_interval_seconds": float(settings.evaluation_job_poll_interval_seconds),
        },
    }


@router.get("/ocr/readiness")
async def get_ocr_readiness() -> JsonDict:
    lighton_error = await _lighton_preflight_error()
    checked_unix = float(_LIGHTON_PREFLIGHT_CACHE.get("checked_unix") or 0.0)
    cache_age = None
    checked_at = None
    if checked_unix > 0.0:
        cache_age = max(0.0, round(time.time() - checked_unix, 3))
        checked_at = datetime.fromtimestamp(checked_unix, UTC).isoformat()
    return {
        "ocr_fallback_order": _resolve_ocr_fallback_order(),
        "lighton_enabled": bool(settings.lightonocr_enabled),
        "lighton_canary_percent": max(0, min(100, int(settings.lightonocr_canary_percent))),
        "lighton_require_local_paths": bool(settings.lightonocr_require_local_paths),
        "lighton_ready": lighton_error is None,
        "lighton_preflight_error": lighton_error,
        "lighton_readiness_checked_at": checked_at,
        "lighton_readiness_cache_age_seconds": cache_age,
    }


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> JsonDict:
    """Upload PDF and trigger extraction + evaluation pipeline.

    Extraction order:
    1) Native PDF text extraction (fast, best for born-digital PDFs)
    2) GLM-OCR fallback (layout parsing + vision fallback)
    3) LightOnOCR fallback via external llama-server (optional; config-gated)
    """
    contents = await file.read()
    max_upload_bytes = max(1_000_000, int(settings.ocr_max_upload_bytes))
    if _is_upload_size_exceeded(len(contents), max_upload_bytes):
        raise HTTPException(
            status_code=413,
            detail=(
                "Upload rejected: PDF exceeds max supported size. "
                f"max_bytes={max_upload_bytes}"
            ),
        )
    if not _is_likely_pdf(file, contents):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed. Upload a valid .pdf document.",
        )
    file_hash = hashlib.sha256(contents).hexdigest()[:12]
    synthetic_doi = f"10.matdao/{file_hash}"

    save_path = UPLOAD_DIR / f"{file_hash}.pdf"
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_path.write_bytes, contents)

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
    ocr_error_chain: dict[str, str] = {}
    ocr_model_id: str | None = None
    fallback_order = _resolve_ocr_fallback_order()
    ocr_fallback_used = False

    doc: fitz.Document | None = None
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
        if len(doc) <= 0:
            raise HTTPException(status_code=400, detail="PDF contains no pages")

        text_parts: list[str] = []
        max_native_pages = max(1, int(settings.ocr_max_pages_sync_text))
        for page_index, page in enumerate(doc):
            if page_index >= max_native_pages:
                break
            try:
                text_parts.append(page.get_text("text"))
            except Exception:
                continue
        native_text = "\n".join(text_parts).strip()
        async def _run_ocr_fallback_chain() -> tuple[str, str, str | None, bool, dict[str, str]]:
            local_error_chain: dict[str, str] = {}
            local_text = ""
            local_source = "pdf-text"
            local_model_id: str | None = None
            local_fallback_used = False

            ocr_page_images: list[tuple[int, str]] = []
            render_errors: list[str] = []
            page_indices = _ocr_page_indices(len(doc), _OCR_SAMPLE_PAGES)
            for page_index in page_indices:
                try:
                    ocr_page_images.append(
                        (
                            page_index,
                            _render_doc_page_base64(
                                doc,
                                page_index,
                                int(settings.ocr_render_max_pixels),
                            ),
                        )
                    )
                except Exception as exc:
                    render_errors.append(
                        f"page_{page_index + 1}_render_failed:{_safe_error_fragment(exc)}"
                    )

            for method in fallback_order:
                if method == "pdf_text":
                    if native_text and len(native_text) >= _OCR_MEANINGFUL_TEXT_LEN:
                        local_text = native_text
                        local_source = "pdf-text"
                        local_model_id = "native_pdf_text"
                        break
                    local_error_chain["pdf_text"] = "native_text_below_threshold"
                    continue

                if not ocr_page_images:
                    local_error_chain[method] = (
                        ";".join(render_errors[:2]) if render_errors else "ocr_page_render_failed"
                    )
                    continue

                if method == "glm_ocr":
                    if not settings.zai_api_key:
                        local_error_chain["glm_ocr"] = "zai_api_key_missing"
                        continue
                    adapter = GLMOCRAdapter(timeout_seconds=int(settings.glm_ocr_timeout_seconds))
                    provider_name = "glm_ocr"
                    source_name = "glm-ocr-fallback"
                    model_fallback_name = str(settings.glm_ocr_model)
                elif method == "lighton_ocr":
                    if not _should_route_lighton(file_hash):
                        local_error_chain["lighton_ocr"] = (
                            f"lighton_canary_skip:{int(settings.lightonocr_canary_percent)}"
                        )
                        continue
                    preflight_error = await _lighton_preflight_error()
                    if preflight_error:
                        local_error_chain["lighton_ocr"] = preflight_error
                        continue
                    adapter = LightOnOCRAdapter()
                    provider_name = "lighton_ocr"
                    source_name = "lighton-ocr-fallback"
                    model_fallback_name = "lightonocr"
                else:
                    continue

                best_candidate = ""
                provider_error = "empty_text_response"
                try:
                    for page_index, image_b64 in ocr_page_images:
                        try:
                            result = await adapter.parse_image(image_b64)
                        except Exception as exc:
                            provider_error = (
                                f"page_{page_index + 1}:{_safe_error_fragment(exc)}"
                            )
                            continue
                        candidate = str(result.get("text") or "").strip()
                        if len(candidate) > len(best_candidate):
                            best_candidate = candidate
                            local_model_id = str(result.get("model_id") or model_fallback_name)
                        if len(candidate) >= _OCR_MEANINGFUL_TEXT_LEN:
                            break
                finally:
                    await adapter.close()

                if best_candidate and len(best_candidate) >= _OCR_MIN_ACCEPTABLE_TEXT_LEN:
                    local_text = best_candidate
                    local_source = source_name
                    local_fallback_used = True
                    if not local_model_id:
                        local_model_id = model_fallback_name
                    break
                local_error_chain[provider_name] = provider_error

            return local_text, local_source, local_model_id, local_fallback_used, local_error_chain

        try:
            (
                final_text,
                extraction_source,
                ocr_model_id,
                ocr_fallback_used,
                ocr_error_chain,
            ) = await asyncio.wait_for(
                _run_ocr_fallback_chain(),
                timeout=max(5, int(settings.ocr_fallback_timeout_seconds)),
            )
        except asyncio.TimeoutError:
            ocr_error_chain["ocr_chain"] = "ocr_fallback_timeout"
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
        logger.error("Extraction failed: No text recovered from PDF. chain=%s", ocr_error_chain)
        layer.status = "error"
        layer.processed_data = {
            "error": "ocr_extraction_failed",
            "ocr_error_chain": ocr_error_chain,
            "ocr_public_codes": _client_safe_ocr_codes(ocr_error_chain),
            "stage_timings_ms": {
                "extract_ms": round((time.perf_counter() - extraction_start) * 1000, 2),
            },
        }
        session.add(layer)
        await session.commit()
        raise HTTPException(
            status_code=422,
            detail=_build_public_ocr_failure_detail(ocr_error_chain),
        )

    detected_doi = _extract_doi(final_text) or synthetic_doi
    parsed_profile = build_document_profile(final_text, fallback_title=file.filename)

    # ── Immediate DOI commit: persist identity NOW so worker restarts can
    # ── re-locate the paper even if the process dies before the final commit.
    paper.doi = detected_doi
    paper.title = parsed_profile.get("title") or file.filename
    paper.abstract = parsed_profile.get("abstract")
    paper.raw_text = final_text
    session.add(paper)
    await session.commit()
    await session.refresh(paper)

    layer.status = "queued"
    layer.source = extraction_source
    layer.processed_data = {
        "text_content": final_text[:5000],
        "document_profile": parsed_profile,
        "ocr_quality_signals": _build_ocr_quality_signals(
            provider=extraction_source,
            fallback_used=ocr_fallback_used,
            error_chain=ocr_error_chain,
            model_id=ocr_model_id,
        ),
        "stage_timings_ms": {
            "extract_ms": round((time.perf_counter() - extraction_start) * 1000, 2),
        },
    }
    session.add(layer)
    await _enqueue_evaluation_job_db(session, paper.id)
    await session.commit()

    return {
        "status": "queued",
        "doi": paper.doi,
        "filename": file.filename,
        "paper_id": str(paper.id)
    }
