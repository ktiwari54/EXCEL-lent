from __future__ import annotations

from typing import Any

import pandas as pd

from app.engines.measure_engine import MeasureEngine
from app.modules.json_safe import json_safe


class ParetoEngine:
    """80/20 contribution analysis with ABC segments."""

    def __init__(self) -> None:
        self.measures = MeasureEngine()

    def run(
        self,
        df: pd.DataFrame,
        semantic: dict[str, Any],
        *,
        measure: str,
        group_by: str,
        threshold: float = 80.0,
    ) -> dict[str, Any]:
        if group_by not in df.columns:
            return {"engine": "pareto", "ok": False, "error": "Group column missing."}
        work = df.copy()
        work["_m"] = self.measures.series(df, semantic, measure)
        g = work.groupby(work[group_by].astype(str))["_m"].sum().sort_values(ascending=False)
        tdf = g.reset_index()
        tdf.columns = [group_by, measure]
        total = float(tdf[measure].sum()) or 1.0
        tdf["contribution_pct"] = (100 * tdf[measure] / total).round(2)
        tdf["cumulative_pct"] = tdf["contribution_pct"].cumsum().round(2)

        def segment(cum: float) -> str:
            if cum <= threshold:
                return "A"
            if cum <= 95:
                return "B"
            return "C"

        tdf["segment"] = tdf["cumulative_pct"].map(segment)
        a_count = int((tdf["segment"] == "A").sum())
        return json_safe(
            {
                "engine": "pareto",
                "ok": True,
                "summary": (
                    f"Pareto: {a_count} {group_by}(s) drive ~{threshold:.0f}% of {measure} "
                    f"(80/20 style concentration)."
                ),
                "table": tdf.to_dict(orient="records"),
                "chart": {
                    "type": "bar",
                    "labels": tdf[group_by].astype(str).head(20).tolist(),
                    "values": [float(x) for x in tdf[measure].head(20).tolist()],
                    "label": measure,
                },
                "metric_value": float(tdf["contribution_pct"].head(a_count).sum()) if a_count else 0,
                "explanation": {
                    "what": "Contribution & cumulative % with ABC segments",
                    "logic": f"SUM({measure}) by {group_by}, sort desc, cumulative %, A≤{threshold}%",
                    "fields": [group_by, measure],
                    "excel_equivalent": f"={measure}/SUM({measure}) running total",
                },
            }
        )
