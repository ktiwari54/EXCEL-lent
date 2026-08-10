from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.modules.dataset_manager import manager
from app.modules.workbook_parser import ParseError

router = APIRouter(prefix="/api/datasets", tags=["datasets-step1"])


class RenameBody(BaseModel):
    name: str


class RoleBody(BaseModel):
    column: str
    role: str


class RelationshipBody(BaseModel):
    label: str
    status: str  # accepted | ignored | suggested


class ImportBody(BaseModel):
    """Used when client re-uploads with sheet selection after inspect — optional alternate path."""
    sheet_names: list[str] = Field(default_factory=list)
    dataset_names: dict[str, str] = Field(default_factory=dict)


def _err(e: Exception) -> HTTPException:
    if isinstance(e, ParseError):
        return HTTPException(
            status_code=400,
            detail={"title": e.user_message, "message": e.detail or e.user_message},
        )
    if isinstance(e, KeyError):
        return HTTPException(status_code=404, detail={"title": "Dataset not found", "message": str(e)})
    return HTTPException(status_code=500, detail={"title": "Something went wrong", "message": str(e)})


@router.post("/inspect")
async def inspect_upload(file: UploadFile = File(...)):
    """Step A: parse file, return sheet list — no dataset saved yet."""
    settings = get_settings()
    if not file.filename:
        raise HTTPException(400, detail={"title": "Missing file", "message": "Please choose a file to upload."})
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            400,
            detail={
                "title": "File is too large",
                "message": f"Maximum size is {settings.max_upload_mb} MB. Try exporting a smaller range.",
            },
        )
    try:
        return manager.inspect_file(content, file.filename)
    except Exception as e:
        raise _err(e) from e


@router.post("/import")
async def import_upload(
    file: UploadFile = File(...),
    sheets: str = Form(default=""),
    names: str = Form(default=""),
):
    """
    Import selected sheets as datasets.
    sheets: comma-separated sheet names (excel)
    names: JSON object sheet->name (optional as stringified JSON)
    """
    import json

    settings = get_settings()
    if not file.filename:
        raise HTTPException(400, detail={"title": "Missing file", "message": "Please choose a file."})
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            400,
            detail={
                "title": "File is too large",
                "message": f"Maximum size is {settings.max_upload_mb} MB.",
            },
        )
    sheet_list = [s.strip() for s in sheets.split(",") if s.strip()] or None
    name_map: dict[str, str] = {}
    if names:
        try:
            name_map = json.loads(names)
        except Exception:
            name_map = {}
    try:
        return manager.create_from_upload(
            content,
            file.filename,
            sheet_names=sheet_list,
            dataset_names=name_map,
        )
    except Exception as e:
        raise _err(e) from e


@router.get("")
def list_datasets():
    return {"datasets": manager.list_datasets()}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str):
    try:
        return manager.get_dataset(dataset_id)
    except Exception as e:
        raise _err(e) from e


@router.patch("/{dataset_id}")
def rename_dataset(dataset_id: str, body: RenameBody):
    try:
        return manager.rename(dataset_id, body.name)
    except Exception as e:
        raise _err(e) from e


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str):
    try:
        manager.delete(dataset_id)
        return {"ok": True}
    except Exception as e:
        raise _err(e) from e


@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
    layer: str = "raw",
):
    try:
        return manager.preview_page(
            dataset_id,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            layer=layer,
        )
    except Exception as e:
        raise _err(e) from e


@router.get("/{dataset_id}/columns/{column_name}")
def column_detail(dataset_id: str, column_name: str):
    try:
        ds = manager.get_dataset(dataset_id)
        for cp in ds.get("column_profiles") or []:
            if cp["name"] == column_name:
                return cp
        raise KeyError(f"Column not found: {column_name}")
    except Exception as e:
        raise _err(e) from e


@router.post("/{dataset_id}/roles")
def override_role(dataset_id: str, body: RoleBody):
    try:
        return manager.override_role(dataset_id, body.column, body.role)
    except Exception as e:
        raise _err(e) from e


@router.post("/{dataset_id}/relationships")
def relationship_status(dataset_id: str, body: RelationshipBody):
    try:
        return manager.set_relationship_status(dataset_id, body.label, body.status)
    except Exception as e:
        raise _err(e) from e
