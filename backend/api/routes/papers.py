"""API route stubs for paper operations."""

from fastapi import APIRouter

from backend.models.paper import PaperSubmission

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
