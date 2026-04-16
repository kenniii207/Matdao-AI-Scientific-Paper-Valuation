# ── MatDAO FastAPI Backend ──────────────────────────────────────────────────
# Slim image to keep container footprint low on Render Basic (1 GB RAM).
# Grobid runs as a SEPARATE service — this container never starts Grobid.
# ────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# System deps: curl (healthcheck), libmagic (file type detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libmagic1 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for layer-cache efficiency
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/ ./backend/

# Runtime env defaults (override via Render environment panel or docker-compose)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BACKEND_PORT=8000 \
    DATABASE_URL=""

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
