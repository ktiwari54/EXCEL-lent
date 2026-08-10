from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import configure, datasets, tasks

settings = get_settings()

app = FastAPI(
    title="Data Analyst Engine",
    version="0.4.0-step3",
    description=(
        "Data Analyst Engine — Steps 1–3: Upload, Task Selection, Dynamic Configuration. "
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
app.include_router(configure.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Data Analyst Engine",
        "tagline": "Your Data. Our Intelligence.",
        "stage": "step3_configure",
        "version": "0.4.0-step3",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.4.0-step3", "stage": "step3"}
