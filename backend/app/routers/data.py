from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.config import get_settings
from app.engines.profiling import profile_dataframe, suggest_columns
from app.models.schemas import DatasetProfile
from app.services.excel_io import read_tabular
from app.services.session_store import store

router = APIRouter(prefix="/api", tags=["data"])


@router.post("/upload", response_model=DatasetProfile)
async def upload_file(
    file: UploadFile = File(...),
    sheet: str | None = Query(default=None),
) -> DatasetProfile:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(400, "Missing filename")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(400, f"File exceeds {settings.max_upload_mb} MB limit")

    try:
        df, sheets, active = read_tabular(content, file.filename, sheet_name=sheet or 0)
    except Exception as e:
        raise HTTPException(400, str(e)) from e

    if df.empty:
        raise HTTPException(400, "Uploaded file has no rows")

    # Normalize column names to strings
    df.columns = [str(c).strip() for c in df.columns]

    session_id = store.create(df, file.filename, sheet_names=sheets, active_sheet=active)
    # also save raw upload
    dest = settings.uploads_dir / f"{session_id}_{file.filename}"
    dest.write_bytes(content)

    return profile_dataframe(df, session_id, file.filename, sheets, active)


@router.get("/session/{session_id}", response_model=DatasetProfile)
def get_session(session_id: str) -> DatasetProfile:
    try:
        df = store.get(session_id)
        meta = store.get_meta(session_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return profile_dataframe(
        df,
        session_id,
        meta.get("filename", "dataset"),
        meta.get("sheet_names") or [],
        meta.get("active_sheet"),
    )


@router.get("/session/{session_id}/suggestions")
def column_suggestions(session_id: str) -> dict:
    try:
        df = store.get(session_id)
        meta = store.get_meta(session_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    profile = profile_dataframe(df, session_id, meta.get("filename", "dataset"))
    return suggest_columns(profile)
