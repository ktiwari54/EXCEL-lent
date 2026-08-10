from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import get_settings
from app.modules.json_safe import json_safe
from app.modules.profiler import profile_dataframe
from app.modules.relationship_detection import detect_relationships
from app.modules.workbook_parser import ParseError, parse_upload, suggest_dataset_name


class DatasetManager:
    """
    Manages RAW (immutable) and WORKING (copy) datasets.
    Library persisted as JSON index + parquet/pickle frames.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.base_dir / "data" / "library"
        self.root.mkdir(parents=True, exist_ok=True)
        self._raw: dict[str, pd.DataFrame] = {}
        self._working: dict[str, pd.DataFrame] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._index_path = self.root / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                data = json.loads(self._index_path.read_text(encoding="utf-8"))
                for item in data.get("datasets", []):
                    self._meta[item["id"]] = item
            except Exception:
                pass

    def _save_index(self) -> None:
        items = [self._public_meta(m) for m in self._meta.values()]
        items.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        self._index_path.write_text(json.dumps({"datasets": items}, indent=2, default=str), encoding="utf-8")

    def _public_meta(self, m: dict[str, Any]) -> dict[str, Any]:
        # strip heavy fields for index
        return {
            k: v
            for k, v in m.items()
            if k
            not in (
                "column_profiles",
                "quality",
                "preview",
                "health",
            )
        } | {
            "health_score": (m.get("health") or {}).get("score") or m.get("health_score"),
            "summary": m.get("summary"),
        }

    def _frame_path(self, dataset_id: str, kind: str) -> Path:
        return self.root / f"{dataset_id}_{kind}.parquet"

    def _persist_frame(self, dataset_id: str, kind: str, df: pd.DataFrame) -> None:
        path = self._frame_path(dataset_id, kind)
        try:
            df.to_parquet(path, index=False)
        except Exception:
            df.to_pickle(self.root / f"{dataset_id}_{kind}.pkl")

    def _load_frame(self, dataset_id: str, kind: str) -> pd.DataFrame:
        key = self._raw if kind == "raw" else self._working
        if dataset_id in key:
            return key[dataset_id]
        pq = self._frame_path(dataset_id, kind)
        pkl = self.root / f"{dataset_id}_{kind}.pkl"
        if pq.exists():
            df = pd.read_parquet(pq)
        elif pkl.exists():
            df = pd.read_pickle(pkl)
        else:
            raise KeyError(f"Dataset not found: {dataset_id}")
        key[dataset_id] = df
        return df

    def inspect_file(self, content: bytes, filename: str) -> dict[str, Any]:
        """Parse file and return sheet list without saving (for UI selection)."""
        parsed = parse_upload(content, filename)
        sheets = []
        for s in parsed["sheets"]:
            sheets.append(
                {
                    "name": s["name"],
                    "rows": s["rows"],
                    "columns": s["columns"],
                    "headers": s["headers"][:30],
                    "empty": s["empty"],
                    "error": s.get("error"),
                    "suggested_name": suggest_dataset_name(filename, s["name"]),
                }
            )
        return {
            "filename": parsed["filename"],
            "kind": parsed["kind"],
            "sheets": sheets,
            "message": "Workbook detected" if parsed["kind"] == "excel" else "CSV detected",
        }

    def create_from_upload(
        self,
        content: bytes,
        filename: str,
        *,
        sheet_names: list[str] | None = None,
        dataset_names: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create one or more datasets from upload.
        sheet_names: which sheets to import (excel). CSV ignores.
        dataset_names: map sheet_name -> display name
        """
        parsed = parse_upload(content, filename)
        # save original bytes
        upload_id = str(uuid.uuid4())
        raw_path = self.settings.uploads_dir / f"{upload_id}_{filename}"
        raw_path.write_bytes(content)

        selected = parsed["sheets"]
        if parsed["kind"] == "excel" and sheet_names:
            wanted = set(sheet_names)
            selected = [s for s in parsed["sheets"] if s["name"] in wanted]
            if not selected:
                raise ParseError(
                    "No matching sheets were selected.",
                    "Please choose at least one sheet that contains data.",
                )

        created: list[dict[str, Any]] = []
        for s in selected:
            if s.get("empty") or s["df"] is None or len(s["df"]) == 0:
                continue
            name = (dataset_names or {}).get(s["name"]) or suggest_dataset_name(filename, s["name"])
            ds = self._register_dataset(
                df=s["df"],
                name=name,
                original_filename=filename,
                sheet_name=s["name"],
                source_upload_id=upload_id,
                source_path=str(raw_path),
            )
            created.append(ds)

        if not created:
            raise ParseError(
                "We couldn't find any data rows to import.",
                "The selected sheet(s) appear empty. Try another sheet or file.",
            )

        # relationships across created in this batch
        rel_payload = []
        for ds in created:
            rel_payload.append(
                {
                    "id": ds["id"],
                    "name": ds["name"],
                    "df": self.get_raw(ds["id"]),
                }
            )
        relationships = detect_relationships(rel_payload)
        # attach to each meta lightly
        for ds in created:
            self._meta[ds["id"]]["relationships"] = [
                r for r in relationships if r["left_dataset_id"] == ds["id"] or r["right_dataset_id"] == ds["id"]
            ]
            self._meta[ds["id"]]["batch_relationships"] = relationships
        self._save_index()

        return json_safe(
            {
                "upload_id": upload_id,
                "filename": filename,
                "datasets": [self.get_dataset(d["id"]) for d in created],
                "relationships": relationships,
            }
        )

    def _register_dataset(
        self,
        df: pd.DataFrame,
        name: str,
        original_filename: str,
        sheet_name: str | None,
        source_upload_id: str,
        source_path: str,
    ) -> dict[str, Any]:
        dataset_id = str(uuid.uuid4())
        raw = df.copy()
        working = df.copy()
        profile = profile_dataframe(raw)

        meta = {
            "id": dataset_id,
            "name": name,
            "original_filename": original_filename,
            "sheet_name": sheet_name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "source_upload_id": source_upload_id,
            "source_path": source_path,
            "rows": profile["rows"],
            "columns": profile["columns"],
            "column_profiles": profile["column_profiles"],
            "quality": profile["quality"],
            "health": profile["health"],
            "health_score": profile["health"]["score"],
            "summary": profile["summary"],
            "preview": profile["preview"],
            "headers": list(raw.columns),
            "relationships": [],
            "role_overrides": {},
        }
        self._raw[dataset_id] = raw
        self._working[dataset_id] = working
        self._meta[dataset_id] = meta
        self._persist_frame(dataset_id, "raw", raw)
        self._persist_frame(dataset_id, "working", working)
        # full profile json
        (self.root / f"{dataset_id}_meta.json").write_text(
            json.dumps(meta, default=str), encoding="utf-8"
        )
        self._save_index()
        return {"id": dataset_id, "name": name}

    def list_datasets(self) -> list[dict[str, Any]]:
        out = []
        for m in self._meta.values():
            out.append(
                {
                    "id": m["id"],
                    "name": m["name"],
                    "original_filename": m.get("original_filename"),
                    "sheet_name": m.get("sheet_name"),
                    "rows": m.get("rows"),
                    "columns": m.get("columns"),
                    "health": m.get("health_score") or (m.get("health") or {}).get("score"),
                    "uploaded_at": m.get("uploaded_at"),
                    "summary": m.get("summary"),
                }
            )
        out.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
        return out

    def get_dataset(self, dataset_id: str, include_preview: bool = True) -> dict[str, Any]:
        if dataset_id not in self._meta:
            # try load meta file
            meta_path = self.root / f"{dataset_id}_meta.json"
            if meta_path.exists():
                self._meta[dataset_id] = json.loads(meta_path.read_text(encoding="utf-8"))
            else:
                raise KeyError(dataset_id)
        m = self._meta[dataset_id]
        # ensure frames loadable
        self.get_raw(dataset_id)
        result = {
            "id": m["id"],
            "name": m["name"],
            "original_filename": m.get("original_filename"),
            "sheet_name": m.get("sheet_name"),
            "uploaded_at": m.get("uploaded_at"),
            "rows": m.get("rows"),
            "columns": m.get("columns"),
            "headers": m.get("headers"),
            "column_profiles": m.get("column_profiles"),
            "quality": m.get("quality"),
            "health": m.get("health"),
            "summary": m.get("summary"),
            "relationships": m.get("relationships") or m.get("batch_relationships") or [],
            "role_overrides": m.get("role_overrides") or {},
            "layers": {"raw": "preserved", "working": "available"},
        }
        if include_preview:
            result["preview"] = m.get("preview") or _safe_preview(self.get_raw(dataset_id))
        return json_safe(result)

    def get_raw(self, dataset_id: str) -> pd.DataFrame:
        return self._load_frame(dataset_id, "raw").copy()

    def get_working(self, dataset_id: str) -> pd.DataFrame:
        return self._load_frame(dataset_id, "working").copy()

    def rename(self, dataset_id: str, name: str) -> dict[str, Any]:
        if dataset_id not in self._meta:
            self.get_dataset(dataset_id)
        self._meta[dataset_id]["name"] = name.strip() or self._meta[dataset_id]["name"]
        (self.root / f"{dataset_id}_meta.json").write_text(
            json.dumps(self._meta[dataset_id], default=str), encoding="utf-8"
        )
        self._save_index()
        return self.get_dataset(dataset_id)

    def delete(self, dataset_id: str) -> None:
        self._meta.pop(dataset_id, None)
        self._raw.pop(dataset_id, None)
        self._working.pop(dataset_id, None)
        for p in self.root.glob(f"{dataset_id}*"):
            try:
                p.unlink()
            except Exception:
                pass
        self._save_index()

    def override_role(self, dataset_id: str, column: str, role: str) -> dict[str, Any]:
        ds = self.get_dataset(dataset_id)
        overrides = self._meta[dataset_id].setdefault("role_overrides", {})
        overrides[column] = role
        for cp in self._meta[dataset_id].get("column_profiles") or []:
            if cp["name"] == column:
                cp["role"] = role
                cp["role_overridden"] = True
        (self.root / f"{dataset_id}_meta.json").write_text(
            json.dumps(self._meta[dataset_id], default=str), encoding="utf-8"
        )
        self._save_index()
        return self.get_dataset(dataset_id)

    def set_relationship_status(self, dataset_id: str, label: str, status: str) -> dict[str, Any]:
        self.get_dataset(dataset_id)
        for key in ("relationships", "batch_relationships"):
            for r in self._meta[dataset_id].get(key) or []:
                if r.get("label") == label:
                    r["status"] = status
        (self.root / f"{dataset_id}_meta.json").write_text(
            json.dumps(self._meta[dataset_id], default=str), encoding="utf-8"
        )
        return self.get_dataset(dataset_id)

    def preview_page(
        self,
        dataset_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        columns: list[str] | None = None,
        layer: str = "raw",
    ) -> dict[str, Any]:
        df = self.get_raw(dataset_id) if layer == "raw" else self.get_working(dataset_id)
        if columns:
            cols = [c for c in columns if c in df.columns]
            if cols:
                df = df[cols]
        if search:
            q = search.lower()
            mask = pd.Series(False, index=df.index)
            for c in df.columns:
                mask |= df[c].astype(str).str.lower().str.contains(q, na=False)
            df = df[mask]
        if sort_by and sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=(sort_dir != "desc"))
        total = len(df)
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        start = (page - 1) * page_size
        chunk = df.iloc[start : start + page_size]
        from app.modules.profiler import _preview_records

        return json_safe(
            {
                "page": page,
                "page_size": page_size,
                "total_rows": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
                "rows": _preview_records(chunk, limit=page_size),
                "layer": layer,
            }
        )


def _safe_preview(df: pd.DataFrame) -> list:
    from app.modules.profiler import _preview_records

    return _preview_records(df, 50)


# singleton
manager = DatasetManager()
