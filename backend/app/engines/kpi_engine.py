from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.json_safe import json_safe


class KPIEngine:
    """KPI cards from semantic measures + optional date grain."""

    def run(self, df: pd.DataFrame, semantic: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
        kpis: dict[str, Any] = {"Records": int(len(df))}
        measure = normalized.get("measure")
        measures = [measure] if measure else [m["name"] for m in (semantic.get("measures") or [])[:4]]

        for m in measures:
            if not m or m not in df.columns:
                continue
            s = pd.to_numeric(df[m], errors="coerce")
            kpis[f"Total {m}"] = float(s.sum())
            kpis[f"Avg {m}"] = float(s.mean()) if s.notna().any() else 0.0

        if semantic.get("health") is not None:
            kpis["Data Health"] = semantic["health"]

        table = [{"kpi": k, "value": v} for k, v in kpis.items()]
        return json_safe(
            {
                "engine": "kpi",
                "ok": True,
                "kpis": kpis,
                "table": table,
                "summary": f"{len(kpis)} KPI(s) computed.",
                "metric_value": kpis.get(f"Total {measure}") if measure else kpis.get("Records"),
            }
        )
