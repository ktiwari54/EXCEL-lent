from __future__ import annotations

from typing import Any

import pandas as pd

from app.engines.formula_engine import FormulaEngine
from app.modules.json_safe import json_safe


class StatisticsEngine:
    """Ranking, top/bottom N, basic outlier flags."""

    def __init__(self) -> None:
        self.formula = FormulaEngine()

    def run(self, df: pd.DataFrame, normalized: dict[str, Any]) -> dict[str, Any]:
        # Reuse formula for top-n grouped ranks
        n = dict(normalized)
        if not n.get("group_by") and n.get("category"):
            n["group_by"] = [n["category"]]
        if not n.get("group_by") and n.get("compare_by"):
            n["group_by"] = [n["compare_by"]]
        n.setdefault("aggregation", "sum")
        n.setdefault("sort_direction", "desc")
        n.setdefault("limit", 10)
        out = self.formula.run(df, n)
        out["engine"] = "statistics"
        if out.get("ok") and out.get("table"):
            out["summary"] = out.get("summary") or "Ranking complete."
        return json_safe(out)

    def outliers(self, df: pd.DataFrame, measure: str) -> dict[str, Any]:
        if measure not in df.columns:
            return {"engine": "statistics", "ok": False, "error": "Measure missing."}
        s = pd.to_numeric(df[measure], errors="coerce")
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            return {"engine": "statistics", "ok": True, "table": [], "summary": "No outliers detected."}
        mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
        hits = df.loc[mask]
        return json_safe(
            {
                "engine": "statistics",
                "ok": True,
                "summary": f"{len(hits)} outlier row(s) in {measure}.",
                "table": hits.head(100).where(pd.notnull(hits), None).to_dict(orient="records"),
            }
        )
