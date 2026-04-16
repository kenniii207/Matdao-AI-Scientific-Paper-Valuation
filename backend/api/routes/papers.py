"""API route stubs for paper operations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.paper import PaperSubmission
from backend.db.session import get_session
from backend.db.models import ExtractionLayer, ResearchPaper, ScoringResultDB

router = APIRouter()


@router.post("/evaluate")
async def evaluate_paper(submission: PaperSubmission):
    """Submit a paper DOI for automated evaluation through the 4-layer pipeline."""
    return {
        "doi": submission.doi,
        "status": "queued",
        "message": "Paper submitted for evaluation",
    }


@router.get("/stats/summary")
async def get_stats(session: AsyncSession = Depends(get_session)):
    query_total = select(func.count()).select_from(ResearchPaper)
    query_scored = select(func.count()).select_from(ScoringResultDB)
    total_papers = await session.scalar(query_total)
    total_scored = await session.scalar(query_scored)
    
    return {
        "total_papers": total_papers or 0,
        "total_scored": total_scored or 0,
        "progress_percent": round((total_scored / total_papers * 100) if total_papers else 0, 1)
    }


@router.get("/review-queue/low-confidence")
async def get_low_confidence_review_queue(
    limit: int = 25,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    safe_limit = max(1, min(limit, 200))
    status_filter = (status or "").strip().lower()

    query = (
        select(ExtractionLayer, ResearchPaper)
        .join(ResearchPaper, ResearchPaper.id == ExtractionLayer.paper_id)
        .where(
            ExtractionLayer.layer_number == 3,
            ExtractionLayer.source == "low-confidence-queue",
        )
        .order_by(ExtractionLayer.created_at.desc())
        .limit(safe_limit)
    )
    if status_filter:
        query = query.where(ExtractionLayer.status == status_filter)

    rows = (await session.execute(query)).all()
    items = []
    for queue_row, paper in rows:
        payload = queue_row.processed_data if isinstance(queue_row.processed_data, dict) else {}
        items.append(
            {
                "queue_id": str(queue_row.id),
                "paper_id": str(queue_row.paper_id),
                "doi": paper.doi,
                "title": paper.title,
                "status": queue_row.status,
                "created_at": queue_row.created_at.isoformat() if queue_row.created_at else None,
                "confidence_score": payload.get("confidence_score"),
                "reasons": payload.get("reasons", []),
            }
        )

    return {
        "count": len(items),
        "items": items,
    }


@router.get("/{doi:path}")
async def get_paper(doi: str):
    """Retrieve paper metadata and evaluation status by DOI."""
    return {"doi": doi, "status": "not_found"}
