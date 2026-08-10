from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import configure, datasets, process, tasks

settings = get_settings()

app = FastAPI(
    title="Data Analyst Engine",
    version="0.5.0",
    description=(
        "Data Analyst Engine — Upload · Task · Configure · BI Pipeline. "
        "Architecture: AI/Intent → Semantic → BI → Formula/Lookup/Time/Stats/KPI → Insight → Result."
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
app.include_router(tasks.router)
app.include_router(configure.router)
app.include_router(process.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Data Analyst Engine",
        "tagline": "Your Data. Our Intelligence.",
        "stage": "bi_pipeline",
        "version": "0.5.0",
        "architecture": "/api/process/architecture",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.5.0", "stage": "bi_pipeline"}
