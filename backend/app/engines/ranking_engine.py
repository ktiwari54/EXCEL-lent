from __future__ import annotations

from typing import Any

import pandas as pd

from app.engines.measure_engine import MeasureEngine
from app.modules.json_safe import json_safe


class RankingEngine:
    """Top/Bottom N, ranks, contribution %."""

    def __init__(self) -> None:
        self.measures = MeasureEngine()

    def top_n(
        self,
        df: pd.DataFrame,
        semantic: dict[str, Any],
        *,
        measure: str,
        group_by: str,
        n: int = 10,
        ascending: bool = False,
        aggregation: str = "sum",
    ) -> dict[str, Any]:
        if group_by not in df.columns:
            return {"engine": "ranking", "ok": False, "error": f"Group column '{group_by}' not found."}
        work = df.copy()
        work["_m"] = self.measures.series(df, semantic, measure)
        if aggregation == "average":
            g = work.groupby(work[group_by].astype(str))["_m"].mean()
        elif aggregation == "count":
            g = work.groupby(work[group_by].astype(str))["_m"].count()
        else:
            g = work.groupby(work[group_by].astype(str))["_m"].sum()
        g = g.sort_values(ascending=ascending).head(n)
        tdf = g.reset_index()
        tdf.columns = [group_by, measure]
        tdf["rank"] = range(1, len(tdf) + 1)
        total = float(g.sum()) if len(g) else 0
        if total:
            tdf["contribution_pct"] = (100 * tdf[measure] / total).round(2)
        return json_safe(
            {
                "engine": "ranking",
                "ok": True,
                "summary": f"{'Bottom' if ascending else 'Top'} {len(tdf)} {group_by} by {measure}",
                "table": tdf.to_dict(orient="records"),
                "chart": {
                    "type": "bar",
                    "labels": tdf[group_by].astype(str).tolist(),
                    "values": [float(x) for x in tdf[measure].tolist()],
                    "label": measure,
                },
                "metric_value": float(tdf[measure].iloc[0]) if len(tdf) else 0,
                "explanation": {
                    "what": f"{'Bottom' if ascending else 'Top'} {n} ranking",
                    "logic": f"Group by {group_by}, {aggregation.upper()}({measure}), sort {'asc' if ascending else 'desc'}, limit {n}",
                    "fields": [group_by, measure],
                    "excel_equivalent": f"=LARGE/SUMIFS style ranking on {measure} by {group_by}",
                },
            }
        )
