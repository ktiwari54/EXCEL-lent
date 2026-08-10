from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings


class TaskHistory:
    def __init__(self) -> None:
        self.path = get_settings().base_dir / "data" / "task_history.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"items": []}), encoding="utf-8")

    def _load(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            return []

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps({"items": items[:100]}, indent=2, default=str), encoding="utf-8")

    def add(
        self,
        *,
        dataset_id: str,
        dataset_name: str,
        task_id: str,
        task_name: str,
        category: str,
        configuration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        items = self._load()
        entry = {
            "id": str(uuid.uuid4()),
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "task_id": task_id,
            "task_name": task_name,
            "category": category,
            "configuration": configuration or {},
            "result_ref": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        items.insert(0, entry)
        self._save(items)
        return entry

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._load()[:limit]


history = TaskHistory()
