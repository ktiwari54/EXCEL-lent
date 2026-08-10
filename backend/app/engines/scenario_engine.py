from __future__ import annotations

from typing import Any

import pandas as pd

from app.engines.measure_engine import MeasureEngine
from app.modules.json_safe import json_safe


class ScenarioEngine:
    """What-if: scale a measure by ±% and show impact."""

    def __init__(self) -> None:
        self.measures = MeasureEngine()

    def run(
        self,
        df: pd.DataFrame,
        semantic: dict[str, Any],
        *,
        measure: str,
        change_pct: float = 10.0,
        scenarios: list[float] | None = None,
    ) -> dict[str, Any]:
        base_s = self.measures.series(df, semantic, measure)
        base = float(base_s.sum())
        scenarios = scenarios or [-10, -5, 0, 5, 10, change_pct]
        rows = []
        for pct in sorted(set(scenarios)):
            val = base * (1 + pct / 100.0)
            rows.append(
                {
                    "scenario": f"{pct:+.0f}%",
                    "change_pct": pct,
                    "value": round(val, 2),
                    "difference": round(val - base, 2),
                    "difference_pct": pct,
                }
            )
        return json_safe(
            {
                "engine": "scenario",
                "ok": True,
                "summary": f"What-if on {measure}: base {base:,.2f}",
                "metric_value": base,
                "table": rows,
                "kpis": {"Base": base, f"Base+{change_pct:.0f}%": base * (1 + change_pct / 100)},
                "explanation": {
                    "what": f"Scenario analysis on {measure}",
                    "logic": f"Base = SUM({measure}); Scenario = Base × (1 + change%)",
                    "fields": [measure],
                    "excel_equivalent": f"={measure}*(1+change%)",
                },
            }
        )


class TargetEngine:
    """Actual vs target variance."""

    def run(self, actual: float, target: float, name: str = "KPI") -> dict[str, Any]:
        variance = actual - target
        var_pct = 100 * variance / abs(target) if target else 0
        achievement = 100 * actual / target if target else 0
        if achievement >= 100:
            status = "Excellent"
        elif achievement >= 90:
            status = "On Track"
        elif achievement >= 75:
            status = "Watch"
        else:
            status = "Critical"
        return json_safe(
            {
                "engine": "target",
                "ok": True,
                "summary": f"{name}: {achievement:.1f}% of target ({status})",
                "metric_value": achievement,
                "table": [
                    {
                        "kpi": name,
                        "actual": actual,
                        "target": target,
                        "variance": variance,
                        "variance_pct": round(var_pct, 2),
                        "achievement_pct": round(achievement, 2),
                        "status": status,
                    }
                ],
                "kpis": {
                    "Actual": actual,
                    "Target": target,
                    "Achievement %": round(achievement, 2),
                    "Status": status,
                },
                "explanation": {
                    "what": f"Actual vs target for {name}",
                    "logic": "Variance = Actual − Target; Achievement % = Actual / Target",
                    "fields": [name],
                    "excel_equivalent": "=(Actual-Target)/Target",
                },
            }
        )
