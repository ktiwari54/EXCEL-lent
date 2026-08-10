from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import configure, datasets, process, tasks

settings = get_settings()

app = FastAPI(
    title="Data Analyst Engine",
    version="0.6.0-step4",
    description=(
        "Data Analyst Engine — Steps 1–4: Profile · Task · Configure · Intelligent BI Engine. "
        "AI/Intent → Semantic → Measures → BI → Formula/Lookup/Time/Stats/Ranking/Pareto/Outlier/Scenario/KPI → Insight → Result."
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
        "stage": "step4_bi_engine",
        "version": "0.6.0-step4",
        "architecture": "/api/process/architecture",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.6.0-step4", "stage": "step4"}
