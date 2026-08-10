from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import datasets, tasks

settings = get_settings()

app = FastAPI(
    title="Data Analyst Engine",
    version="0.3.0-step2",
    description=(
        "Data Analyst Engine — Step 1 Upload & Profile · Step 2 Task Selection. "
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
app.include_router(tasks.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Data Analyst Engine",
        "tagline": "Your Data. Our Intelligence.",
        "stage": "step2_task_selection",
        "version": "0.3.0-step2",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.3.0-step2", "stage": "step2"}
