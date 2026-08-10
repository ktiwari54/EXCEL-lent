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

    def descriptive(self, df: pd.DataFrame, measure: str) -> dict[str, Any]:
        if not measure or measure not in df.columns:
            return {"engine": "statistics", "ok": False, "error": "Measure missing for descriptive stats."}
        s = pd.to_numeric(df[measure], errors="coerce").dropna()
        if s.empty:
            return {"engine": "statistics", "ok": False, "error": "No numeric values."}
        stats = {
            "count": int(len(s)),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "min": float(s.min()),
            "max": float(s.max()),
            "std": float(s.std()) if len(s) > 1 else 0.0,
            "variance": float(s.var()) if len(s) > 1 else 0.0,
            "q1": float(s.quantile(0.25)),
            "q3": float(s.quantile(0.75)),
            "range": float(s.max() - s.min()),
        }
        table = [{"statistic": k, "value": v} for k, v in stats.items()]
        return json_safe(
            {
                "engine": "statistics",
                "ok": True,
                "summary": f"Descriptive stats for {measure}: mean={stats['mean']:,.2f}, median={stats['median']:,.2f}",
                "table": table,
                "metric_value": stats["mean"],
                "kpis": {f"{measure} mean": stats["mean"], f"{measure} median": stats["median"]},
                "explanation": {
                    "what": f"Descriptive statistics for {measure}",
                    "logic": "count, mean, median, min, max, std, variance, quartiles",
                    "fields": [measure],
                    "excel_equivalent": "AVERAGE/MEDIAN/STDEV/QUARTILE",
                },
            }
        )

    def correlation(self, df: pd.DataFrame, a: str, b: str) -> dict[str, Any]:
        if a not in df.columns or b not in df.columns:
            return {"engine": "statistics", "ok": False, "error": "Columns missing for correlation."}
        sa = pd.to_numeric(df[a], errors="coerce")
        sb = pd.to_numeric(df[b], errors="coerce")
        corr = float(sa.corr(sb)) if sa.notna().sum() > 2 else 0.0
        strength = "strong" if abs(corr) >= 0.7 else "moderate" if abs(corr) >= 0.4 else "weak"
        direction = "positive" if corr >= 0 else "negative"
        return json_safe(
            {
                "engine": "statistics",
                "ok": True,
                "metric_value": corr,
                "summary": f"Correlation({a}, {b}) = {corr:.2f} — {strength} {direction} relationship. Correlation does not prove causation.",
                "table": [{"field_a": a, "field_b": b, "correlation": round(corr, 4), "strength": strength}],
                "explanation": {
                    "what": f"Correlation between {a} and {b}",
                    "logic": "Pearson correlation coefficient (−1 to +1)",
                    "fields": [a, b],
                    "excel_equivalent": f"=CORREL({a},{b})",
                },
            }
        )
