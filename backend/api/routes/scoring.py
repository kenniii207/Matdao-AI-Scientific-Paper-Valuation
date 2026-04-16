"""API routes for scoring evaluation and retrieval."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.adapters.openalex_adapter import OpenAlexAdapter
from backend.api.adapters.semantic_scholar_adapter import SemanticScholarAdapter
from backend.api.adapters.serpapi_scholar_adapter import SerpApiScholarAdapter
from backend.db.models import ExtractionLayer, ResearchPaper, ScoringResultDB
from backend.db.session import get_session
from backend.services.scoring.dimension2 import score_dimension2
from backend.services.scoring.dimension9 import score_dimension9
from backend.services.scoring.engine import compute_score

router = APIRouter()

def _derive_frontend_insights(
    dimensions: list[dict],
    integrity_gate_triggered: bool,
    eval_results: dict | None,
) -> tuple[str, list[str], list[str]]:
    if eval_results:
        insight = str(eval_results.get("insight") or "").strip()
        investor_fit = eval_results.get("investor_fit")
        warnings = eval_results.get("warnings")
        if isinstance(investor_fit, list):
            investor_fit = [str(item).strip() for item in investor_fit if str(item).strip()]
        else:
            investor_fit = []
        if isinstance(warnings, list):
            warnings = [str(item).strip() for item in warnings if str(item).strip()]
        else:
            warnings = []
        if insight:
            return insight, investor_fit[:3], warnings[:3]

    by_id = {int(d["dimension_id"]): float(d["raw_score"]) for d in dimensions}
    rigor = by_id.get(2, 3.0)
    market = by_id.get(3, 3.0)
    feasibility = by_id.get(1, 3.0)
    risk = by_id.get(8, 3.0)
    governance = by_id.get(9, 3.0)

    if integrity_gate_triggered or governance <= 1.0:
        return (
            "Governance integrity gate triggered by high-risk compliance signals.",
            ["Special-situations investors only"],
            ["Governance red flag detected", "Total score forced to 0 by integrity policy"],
        )

    insight = (
        "Strong technical quality with credible translational potential."
        if rigor >= 4.0 and feasibility >= 3.5
        else "Scientific signal present, but translation and execution evidence are still emerging."
    )
    investor_fit = (
        ["Early-stage deep tech investors", "University commercialization partners"]
        if market < 3.0
        else ["Category-focused venture funds", "Corporate R&D collaboration"]
    )
    warnings = []
    if market < 3.0:
        warnings.append("Limited go-to-market evidence in current manuscript")
    if risk < 3.0:
        warnings.append("Material technical or execution uncertainty remains")
    if not warnings:
        warnings.append("No critical red flags detected from current automated analysis")
    return insight, investor_fit, warnings


def _derive_executive_summary(
    eval_results: dict | None,
    insight: str,
    dimensions: list[dict],
    integrity_gate_triggered: bool,
    total_score: float,
    grade: str,
) -> str:
    candidate = str((eval_results or {}).get("executive_summary") or "").strip()
    normalized_candidate = " ".join(candidate.lower().split())
    normalized_insight = " ".join((insight or "").lower().split())
    if candidate and normalized_candidate != normalized_insight:
        return candidate

    by_id = {int(d["dimension_id"]): float(d["raw_score"]) for d in dimensions}
    rigor = by_id.get(2, 3.0)
    market = by_id.get(3, 3.0)
    feasibility = by_id.get(1, 3.0)
    ethics = by_id.get(8, 3.0)

    if integrity_gate_triggered:
        return (
            "Automated diligence detected governance/compliance risk signals; "
            "the integrity gate forced total score to 0 pending manual review."
        )

    strengths: list[str] = []
    watch_items: list[str] = []
    if rigor >= 4.0:
        strengths.append("strong scientific rigor")
    if feasibility >= 3.5:
        strengths.append("reasonable execution feasibility")
    if market >= 3.5:
        strengths.append("credible commercialization signal")
    if market < 3.0:
        watch_items.append("limited near-term commercialization evidence")
    if ethics < 3.0:
        watch_items.append("elevated risk/ethics uncertainty")

    headline = f"Overall score {round(total_score)} ({grade}) with "
    if strengths:
        headline += ", ".join(strengths[:2])
    else:
        headline += "mixed strength across core dimensions"
    if watch_items:
        headline += "; key watch items: " + ", ".join(watch_items[:2])
    return headline + "."


def _derive_investment_recommendation(
    eval_results: dict | None,
    integrity_gate_triggered: bool,
    total_score: float,
    grade: str,
) -> str:
    candidate = str((eval_results or {}).get("investment_recommendation") or "").strip()
    if candidate:
        return candidate
    if integrity_gate_triggered:
        return "Reject (Integrity Gate Triggered)"
    if total_score >= 85:
        return "Tier A - High Priority Diligence"
    if total_score >= 75:
        return "Tier B - Targeted Validation"
    if total_score >= 65:
        return "Tier C - Conditional Monitoring"
    return f"Tier D - Defer ({grade})"


@router.post("/evaluate/{doi:path}")
async def evaluate_scoring_for_doi(
    doi: str, session: AsyncSession = Depends(get_session)
):
    paper = await session.scalar(select(ResearchPaper).where(ResearchPaper.doi == doi))
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found for provided DOI")

    oa_adapter = OpenAlexAdapter()
    s2_adapter = SemanticScholarAdapter()
    serp_adapter = SerpApiScholarAdapter()

    s2_paper = None
    oa_work = None
    serpapi_paper = None
    source_errors: dict[str, str] = {}

    try:
        try:
            s2_paper = await s2_adapter.get_paper(doi=paper.doi)
        except Exception as exc:
            source_errors["semantic_scholar"] = str(exc)

        try:
            oa_work = await oa_adapter.get_work(doi=paper.doi)
        except Exception as exc:
            source_errors["openalex"] = str(exc)

        try:
            query = paper.doi if not paper.doi.startswith("10.matdao/") else (paper.title or paper.doi)
            serpapi_paper = await serp_adapter.get_top_paper(query=query)
        except Exception as exc:
            source_errors["serpapi_google_scholar"] = str(exc)

    finally:
        await oa_adapter.close()
        await s2_adapter.close()
        await serp_adapter.close()

    dim2_score, dim2_snippet = score_dimension2(
        s2_paper=s2_paper,
        oa_work=oa_work,
        serpapi_paper=serpapi_paper,
    )
    dim9_score, dim9_snippet, _ = score_dimension9()

    if source_errors:
        dim2_data = json.loads(dim2_snippet)
        dim2_data["source_errors"] = source_errors
        dim2_snippet = json.dumps(dim2_data, default=str)

    scoring_result = compute_score(
        doi=paper.doi,
        raw_scores={2: dim2_score, 9: dim9_score},
        origin_snippets={2: dim2_snippet, 9: dim9_snippet},
        automated_flags={2: True, 9: True},
    )

    latest_version = await session.scalar(
        select(func.max(ScoringResultDB.version)).where(ScoringResultDB.paper_id == paper.id)
    )
    row = ScoringResultDB(
        paper_id=paper.id,
        version=(latest_version or 0) + 1,
        dim1_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 1),
        dim2_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 2),
        dim3_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 3),
        dim4_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 4),
        dim5_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 5),
        dim6_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 6),
        dim7_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 7),
        dim8_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 8),
        dim9_score=next(d.raw_score for d in scoring_result.dimensions if d.dimension_id == 9),
        total_score=scoring_result.total_score,
        grade=scoring_result.grade.value,
        integrity_gate_triggered=scoring_result.integrity_gate_triggered,
        origin_snippets={
            str(d.dimension_id): d.origin_snippet for d in scoring_result.dimensions if d.origin_snippet
        },
        weights_json={str(d.dimension_id): d.weight for d in scoring_result.dimensions},
        scored_by="automated-layer2",
    )
    session.add(row)
    await session.commit()

    return scoring_result.model_dump()


@router.get("/results/{paper_id}")
async def get_scoring_result_by_id(paper_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve latest scoring result by Paper UUID."""
    paper = await session.get(ResearchPaper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    row = await session.scalar(
        select(ScoringResultDB)
        .where(ScoringResultDB.paper_id == paper.id)
        .order_by(ScoringResultDB.version.desc())
        .limit(1)
    )
    if row is None:
        # Avoid hard 404 during background jobs; return pipeline state instead.
        layer = await session.scalar(
            select(ExtractionLayer)
            .where(ExtractionLayer.paper_id == paper.id)
            .order_by(ExtractionLayer.created_at.desc())
            .limit(1)
        )
        if layer is None:
            raise HTTPException(status_code=404, detail="No scoring record found for this paper")

        status = (layer.status or "").lower()
        processed = layer.processed_data or {}
        if status in {"queued", "pending", "processing"}:
            return JSONResponse(
                status_code=202,
                content={
                    "paper_id": str(paper.id),
                    "doi": paper.doi,
                    "status": status or "processing",
                },
            )
        if status == "error":
            return {
                "paper_id": str(paper.id),
                "doi": paper.doi,
                "status": "error",
                "error": processed.get("error") if isinstance(processed, dict) else str(processed),
            }
        return {
            "paper_id": str(paper.id),
            "doi": paper.doi,
            "status": status or "unknown",
        }

    from backend.models.scoring import DIMENSION_NAMES
    layers = (
        await session.scalars(
            select(ExtractionLayer)
            .where(ExtractionLayer.paper_id == paper.id)
            .order_by(ExtractionLayer.created_at.desc())
            .limit(12)
        )
    ).all()
    layer = layers[0] if layers else None
    eval_layer = next(
        (
            candidate
            for candidate in layers
            if isinstance(candidate.processed_data, dict)
            and isinstance(candidate.processed_data.get("eval_results"), dict)
        ),
        None,
    )
    active_layer = eval_layer or layer
    eval_results = {}
    if active_layer is not None and isinstance(active_layer.processed_data, dict):
        maybe_eval = active_layer.processed_data.get("eval_results")
        if isinstance(maybe_eval, dict):
            eval_results = maybe_eval
    
    # Construct frontend-friendly response
    dimensions = []
    for d_id in range(1, 10):
        raw_val = getattr(row, f"dim{d_id}_score") or 3.0
        snip_data = (row.origin_snippets or {}).get(str(d_id), "{}")
        
        # Parse rationale/snippet if stored as JSON string
        rationale = ""
        snippet = ""
        try:
            parsed = json.loads(snip_data)
            if isinstance(parsed, dict):
                rationale = parsed.get("rationale", "")
                snippet = parsed.get("snippet", "")
            else:
                snippet = str(parsed)
        except:
            snippet = str(snip_data)

        dimensions.append({
            "dimension_id": d_id,
            "dimension_name": DIMENSION_NAMES.get(d_id, "Unknown"),
            "raw_score": raw_val,
            "rationale": rationale,
            "origin_snippet": snippet
        })

    insight, investor_fit, warnings = _derive_frontend_insights(
        dimensions=dimensions,
        integrity_gate_triggered=bool(row.integrity_gate_triggered),
        eval_results=eval_results,
    )
    executive_summary = _derive_executive_summary(
        eval_results=eval_results,
        insight=insight,
        dimensions=dimensions,
        integrity_gate_triggered=bool(row.integrity_gate_triggered),
        total_score=float(row.total_score or 0.0),
        grade=str(row.grade or "F"),
    )
    investment_recommendation = _derive_investment_recommendation(
        eval_results=eval_results,
        integrity_gate_triggered=bool(row.integrity_gate_triggered),
        total_score=float(row.total_score or 0.0),
        grade=str(row.grade or "F"),
    )

    return {
        "paper_id": str(paper.id),
        "paper_title": paper.title,
        "doi": paper.doi,
        "total_score": row.total_score,
        "grade": row.grade,
        "integrity_gate_triggered": row.integrity_gate_triggered,
        "dimensions": dimensions,
        "confidence_tier": "HIGH (FALCON-OCR)" if "llm" in (row.scored_by or "") else "AUTOMATED",
        "insight": insight,
        "investor_fit": investor_fit,
        "warnings": warnings,
        "executive_summary": executive_summary,
        "investment_recommendation": investment_recommendation,
    }

@router.get("/{doi:path}")
async def get_scoring_result(doi: str, session: AsyncSession = Depends(get_session)):
    """Retrieve latest scoring result for a paper DOI."""
    paper = await session.scalar(select(ResearchPaper).where(ResearchPaper.doi == doi))
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    row = await session.scalar(
        select(ScoringResultDB)
        .where(ScoringResultDB.paper_id == paper.id)
        .order_by(ScoringResultDB.version.desc())
        .limit(1)
    )
    if row is None:
        return {"doi": doi, "status": "no_score_available"}

    raw_scores = {
        1: row.dim1_score or 3.0,
        2: row.dim2_score or 3.0,
        3: row.dim3_score or 3.0,
        4: row.dim4_score or 3.0,
        5: row.dim5_score or 3.0,
        6: row.dim6_score or 3.0,
        7: row.dim7_score or 3.0,
        8: row.dim8_score or 3.0,
        9: row.dim9_score or 3.0,
    }
    result = compute_score(
        doi=paper.doi,
        raw_scores=raw_scores,
        origin_snippets={int(k): v for k, v in (row.origin_snippets or {}).items()},
    )
    return result.model_dump()
