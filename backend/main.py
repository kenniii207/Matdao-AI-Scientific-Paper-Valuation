"""MatDAO Automation Framework — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.exceptions import MatDAOBaseError
from backend.api.routes import papers, scoring, upload
from backend.db.session import engine
from backend.db.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="MatDAO Automation Framework",
    description="Automated scientific due diligence — 4-layer data extraction pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MatDAOBaseError)
async def matdao_exception_handler(request: Request, exc: MatDAOBaseError):
    """Centralized exception handler for all MatDAO domain errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_type, "detail": str(exc)},
    )


app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])
app.include_router(upload.router, prefix="/api", tags=["upload"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
