"""ClinicaDoc AI – FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.report import router as report_router

app = FastAPI(
    title="ClinicaDoc AI",
    description=(
        "An intelligent, secure, and conversational AI agent designed to bridge patient "
        "history and actionable clinical insights. Ingests scattered patient data—clinical "
        "notes, lab results, imaging reports, and patient-reported symptoms—and produces a "
        "structured, concise, and academically referenced PDF report."
    ),
    version="1.0.0",
    contact={
        "name": "ClinicaDoc AI",
        "url": "https://github.com/harshrajput4343/ClinicaDoc-AI",
    },
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report_router)


@app.get("/", tags=["Health"])
async def root() -> dict:
    """Health check endpoint."""
    return {
        "service": "ClinicaDoc AI",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Detailed health check."""
    return {"status": "healthy"}
