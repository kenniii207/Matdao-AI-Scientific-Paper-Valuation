"""API route stubs for paper operations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.paper import PaperSubmission
from db.session import get_session
from db.models import ResearchPaper, ScoringResultDB

router = APIRouter()


@router.post("/evaluate")
async def evaluate_paper(submission: PaperSubmission):
    """Submit a paper DOI for automated evaluation through the 4-layer pipeline."""
    return {
        "doi": submission.doi,
        "status": "queued",
        "message": "Paper submitted for evaluation",
    }


@router.get("/{doi:path}")
async def get_paper(doi: str):
    """Retrieve paper metadata and evaluation status by DOI."""
    return {"doi": doi, "status": "not_found"}

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
