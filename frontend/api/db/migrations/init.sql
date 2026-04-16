-- MatDAO PostgreSQL initialization with pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tables are managed by SQLAlchemy models in backend/db/models.py
-- This script only ensures the pgvector extension is available.
