"""SQLAlchemy models for PostgreSQL + pgvector storage."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ResearchPaper(Base):
    """Layer 1+2 paper metadata and extraction results."""

    __tablename__ = "research_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matdao_id = Column(String(64), unique=True, index=True)
    doi = Column(String(256), unique=True, nullable=False, index=True)
    title = Column(Text)
    abstract = Column(Text)
    authors_json = Column(JSON, default=list)
    journal = Column(String(512))
    publication_date = Column(String(32))
    funding_statements = Column(Text)
    orcids = Column(JSON, default=list)
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    extraction_layers = relationship("ExtractionLayer", back_populates="paper")
    scoring_results = relationship("ScoringResultDB", back_populates="paper")


class ExtractionLayer(Base):
    """Stores raw output from each pipeline layer (Grobid, APIs, etc.)."""

    __tablename__ = "extraction_layers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id"), nullable=False)
    layer_number = Column(Integer, nullable=False)  # 1=NLP, 2=API, 3=Form, 4=Expert
    source = Column(String(128))  # e.g. "ocr", "openalex", "semantic_scholar"
    raw_response = Column(JSON)
    processed_data = Column(JSON)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("ResearchPaper", back_populates="extraction_layers")


class ScoringResultDB(Base):
    """Persisted 9-dimension scoring results with audit trail."""

    __tablename__ = "scoring_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id"), nullable=False)
    version = Column(Integer, default=1)

    dim1_score = Column(Float)
    dim2_score = Column(Float)
    dim3_score = Column(Float)
    dim4_score = Column(Float)
    dim5_score = Column(Float)
    dim6_score = Column(Float)
    dim7_score = Column(Float)
    dim8_score = Column(Float)
    dim9_score = Column(Float)

    total_score = Column(Float)
    grade = Column(String(2))
    integrity_gate_triggered = Column(Boolean, default=False)

    origin_snippets = Column(JSON, default=dict)

    weights_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    scored_by = Column(String(64), default="automated")

    paper = relationship("ResearchPaper", back_populates="scoring_results")


class EvaluationJob(Base):
    """Durable background evaluation queue item."""

    __tablename__ = "evaluation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=4)
    next_retry_at = Column(DateTime, default=datetime.utcnow, index=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    worker_id = Column(String(64), nullable=True)
    last_error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
