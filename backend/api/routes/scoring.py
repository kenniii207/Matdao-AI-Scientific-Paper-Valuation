"""API route stubs for scoring operations."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{doi:path}")
async def get_scoring_result(doi: str):
    """Retrieve scoring result for a paper by DOI."""
    return {"doi": doi, "status": "no_score_available"}
