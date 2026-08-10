from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engines.measure_engine import MeasureEngine
from app.modules.json_safe import json_safe


class OutlierEngine:
    """IQR and Z-score outlier detection."""

    def __init__(self) -> None:
        self.measures = MeasureEngine()

    def run(
        self,
        df: pd.DataFrame,
        semantic: dict[str, Any],
        *,
        measure: str,
        method: str = "iqr",
    ) -> dict[str, Any]:
        s = self.measures.series(df, semantic, measure)
        work = df.copy()
        work["_v"] = s
        clean = s.dropna()
        if len(clean) < 4:
            return {"engine": "outlier", "ok": True, "table": [], "summary": "Not enough data for outlier detection."}

        if method == "zscore":
            mu, sigma = float(clean.mean()), float(clean.std() or 0)
            if sigma == 0:
                return {"engine": "outlier", "ok": True, "table": [], "summary": "No variance — no outliers."}
            z = (s - mu) / sigma
            mask = z.abs() > 3
            expected = f"{mu - 3*sigma:,.2f} – {mu + 3*sigma:,.2f}"
        else:
            q1, q3 = float(clean.quantile(0.25)), float(clean.quantile(0.75))
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (s < lo) | (s > hi)
            expected = f"{lo:,.2f} – {hi:,.2f}"

        hits = work.loc[mask.fillna(False)].copy()
        if len(hits):
            hits["expected_range"] = expected
            hits["severity"] = hits["_v"].apply(
                lambda v: "high" if pd.notna(v) and (abs(v) > abs(clean.median()) * 5 if clean.median() else True) else "medium"
            )

        return json_safe(
            {
                "engine": "outlier",
                "ok": True,
                "summary": f"{len(hits)} outlier value(s) in {measure} (method={method}).",
                "table": hits.drop(columns=["_v"], errors="ignore").head(100).where(pd.notnull(hits), None).to_dict(orient="records")
                if len(hits)
                else [],
                "metric_value": float(len(hits)),
                "explanation": {
                    "what": f"Outlier detection on {measure}",
                    "logic": f"{method.upper()} method; expected range {expected}",
                    "fields": [measure],
                    "excel_equivalent": "IQR fences or STANDARDIZE/Z-score",
                },
            }
        )
