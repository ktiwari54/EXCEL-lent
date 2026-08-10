from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import get_settings


class SessionStore:
    """In-memory + disk-backed dataframe sessions."""

    def __init__(self) -> None:
        self._frames: dict[str, pd.DataFrame] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self.settings = get_settings()

    def create(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet_names: list[str] | None = None,
        active_sheet: str | None = None,
    ) -> str:
        session_id = str(uuid.uuid4())
        self._frames[session_id] = df.copy()
        self._meta[session_id] = {
            "filename": filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sheet_names": sheet_names or [],
            "active_sheet": active_sheet,
            "original_rows": int(len(df)),
            "original_columns": int(len(df.columns)),
        }
        self._persist(session_id)
        return session_id

    def get(self, session_id: str) -> pd.DataFrame:
        if session_id in self._frames:
            return self._frames[session_id]
        path = self._parquet_path(session_id)
        if path.exists():
            df = pd.read_parquet(path)
            self._frames[session_id] = df
            meta_path = self._meta_path(session_id)
            if meta_path.exists():
                self._meta[session_id] = json.loads(meta_path.read_text(encoding="utf-8"))
            return df
        raise KeyError(f"Session not found: {session_id}")

    def get_meta(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._meta:
            self.get(session_id)  # load from disk if needed
        return self._meta.get(session_id, {})

    def update(self, session_id: str, df: pd.DataFrame, **meta_updates: Any) -> None:
        self._frames[session_id] = df.copy()
        if session_id not in self._meta:
            self._meta[session_id] = {}
        self._meta[session_id].update(meta_updates)
        self._meta[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist(session_id)

    def _parquet_path(self, session_id: str) -> Path:
        return self.settings.sessions_dir / f"{session_id}.parquet"

    def _meta_path(self, session_id: str) -> Path:
        return self.settings.sessions_dir / f"{session_id}.json"

    def _persist(self, session_id: str) -> None:
        df = self._frames[session_id]
        # Prefer parquet; fall back to pickle if pyarrow missing
        try:
            df.to_parquet(self._parquet_path(session_id), index=False)
        except Exception:
            df.to_pickle(self.settings.sessions_dir / f"{session_id}.pkl")
        self._meta_path(session_id).write_text(
            json.dumps(self._meta[session_id], default=str),
            encoding="utf-8",
        )


store = SessionStore()
