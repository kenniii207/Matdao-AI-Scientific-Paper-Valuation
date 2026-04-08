"""Pydantic v2 models for paper metadata."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Author(BaseModel):
    """Author extracted from paper or enriched via API."""

    name: str
    orcid: Optional[str] = None
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    total_citations: Optional[int] = None
    institution: Optional[str] = None
    origin_snippet: Optional[str] = Field(
        default=None, description="API JSON fragment that produced this data"
    )


class Paper(BaseModel):
    """Core paper representation after Layer 1 + Layer 2 processing."""

    doi: str
    title: str
    abstract: Optional[str] = None
    authors: list[Author] = Field(default_factory=list)
    journal: Optional[str] = None
    publication_date: Optional[date] = None
    funding_statements: Optional[str] = None
    matdao_id: Optional[str] = None


class PaperMetadata(BaseModel):
    """Metadata extracted during Layer 1 (NLP)."""

    doi: Optional[str] = None
    orcids: list[str] = Field(default_factory=list)
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors_raw: list[str] = Field(default_factory=list)
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    funding_statements: Optional[str] = None
    raw_text: Optional[str] = None


class PaperSubmission(BaseModel):
    """Incoming request to evaluate a paper."""

    doi: str = Field(..., description="Digital Object Identifier of the paper")
