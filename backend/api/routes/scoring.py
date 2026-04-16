"""API routes for scoring evaluation and retrieval."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.adapters.openalex_adapter import OpenAlexAdapter
from backend.api.adapters.semantic_scholar_adapter import SemanticScholarAdapter
from backend.api.adapters.serpapi_scholar_adapter import SerpApiScholarAdapter
from backend.db.models import ResearchPaper, ScoringResultDB
from backend.db.session import get_session
from backend.services.scoring.dimension2 import score_dimension2
from backend.services.scoring.dimension9 import score_dimension9
from backend.services.scoring.engine import compute_score

router = APIRouter()


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
