from __future__ import annotations

from typing import Any

from app.modules.task_registry import classify_intent


class AIIntentLayer:
    """
    Maps natural language to task intent + light config hints.
    Replaceable with LLM later without changing BI pipeline.
    """

    def interpret(self, text: str, semantic: dict[str, Any] | None = None) -> dict[str, Any]:
        base = classify_intent(text)
        hints: dict[str, Any] = {}
        q = (text or "").lower()
        measures = (semantic or {}).get("measures") or []
        dimensions = (semantic or {}).get("dimensions") or []
        dates = (semantic or {}).get("dates") or []

        # Light config hints from language + semantic catalog
        if "top" in q or "highest" in q:
            hints["sort_direction"] = "desc"
            hints["limit"] = 10
        if "bottom" in q or "lowest" in q:
            hints["sort_direction"] = "asc"
            hints["limit"] = 10
        if "monthly" in q or "month" in q:
            hints["date_grain"] = "month"
        if measures:
            for m in measures:
                if m["name"].lower() in q:
                    hints["measure"] = m["name"]
                    break
            if "measure" not in hints:
                hints["measure"] = measures[0]["name"]
        if dimensions:
            for d in dimensions:
                if d["name"].lower() in q:
                    hints.setdefault("group_by", [d["name"]])
                    hints.setdefault("category", d["name"])
                    hints.setdefault("compare_by", d["name"])
        if dates and ("trend" in q or "month" in q or "over time" in q):
            hints["date_field"] = dates[0]["name"]

        return {
            **base,
            "config_hints": hints,
            "layer": "ai_intent",
        }
