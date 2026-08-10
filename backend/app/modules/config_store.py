from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings


class ConfigStore:
    def __init__(self) -> None:
        self.path = get_settings().base_dir / "data" / "saved_configs.json"
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

    def save(self, task_request: dict[str, Any]) -> dict[str, Any]:
        items = self._load()
        entry = {
            "id": str(uuid.uuid4()),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            **task_request,
        }
        items.insert(0, entry)
        self._save(items)
        return entry

    def list(self, limit: int = 20, dataset_id: str | None = None) -> list[dict[str, Any]]:
        items = self._load()
        if dataset_id:
            items = [i for i in items if i.get("dataset_id") == dataset_id]
        return items[:limit]

    def get(self, config_id: str) -> dict[str, Any] | None:
        for i in self._load():
            if i.get("id") == config_id:
                return i
        return None


config_store = ConfigStore()
