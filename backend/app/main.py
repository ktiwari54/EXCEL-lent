from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import datasets

settings = get_settings()

app = FastAPI(
    title="Data Analyst Engine",
    version="0.2.0-step1",
    description=(
        "Data Analyst Engine — Step 1: Upload & Data Profiling. "
        "Your Data. Our Intelligence."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Data Analyst Engine",
        "tagline": "Your Data. Our Intelligence.",
        "stage": "step1_upload_profiling",
        "version": "0.2.0-step1",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.2.0-step1", "stage": "step1"}
