"""Pydantic v2 response models for external API adapters."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# --- OpenAlex ---

class OpenAlexWork(BaseModel):
    """Subset of OpenAlex /works response relevant to scoring."""

    doi: Optional[str] = None
    title: Optional[str] = None
    relevance_score: Optional[float] = None
    cited_by_count: Optional[int] = None
    publication_date: Optional[str] = None
    primary_topic: Optional[dict] = None
    authorships: list[dict] = Field(default_factory=list)
    raw_json: Optional[dict] = Field(default=None, exclude=True)


# --- Semantic Scholar ---

class SemanticScholarPaper(BaseModel):
    """Subset of Semantic Scholar /paper response."""

    paper_id: Optional[str] = None
    title: Optional[str] = None
    influential_citation_count: Optional[int] = None
    citation_count: Optional[int] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    authors: list[dict] = Field(default_factory=list)
    raw_json: Optional[dict] = Field(default=None, exclude=True)


# --- SerpAPI (Google Scholar) ---

class SerpApiScholarPaper(BaseModel):
    """Subset of SerpAPI google_scholar organic result relevant to scoring."""

    title: Optional[str] = None
    result_id: Optional[str] = None
    cited_by_count: Optional[int] = None
    publication_info_summary: Optional[str] = None
    raw_json: Optional[dict] = Field(default=None, exclude=True)


# --- NIH RePORTER ---

class NIHGrant(BaseModel):
    """NIH RePORTER project/grant record."""

    project_num: Optional[str] = None
    project_title: Optional[str] = None
    pi_name: Optional[str] = None
    organization: Optional[str] = None
    total_cost: Optional[float] = None
    fiscal_year: Optional[int] = None
    raw_json: Optional[dict] = Field(default=None, exclude=True)


# --- OSF ---

class OSFRegistration(BaseModel):
    """OSF registration record for pre-registration check."""

    registration_id: Optional[str] = None
    title: Optional[str] = None
    is_preregistration: bool = False
    date_registered: Optional[str] = None
    raw_json: Optional[dict] = Field(default=None, exclude=True)


# --- ClinicalTrials.gov ---

class ClinicalTrial(BaseModel):
    """ClinicalTrials.gov study record."""

    nct_id: Optional[str] = None
    brief_title: Optional[str] = None
    overall_status: Optional[str] = None
    has_results: bool = False
    is_terminated_or_suspended: bool = False
    raw_json: Optional[dict] = Field(default=None, exclude=True)
