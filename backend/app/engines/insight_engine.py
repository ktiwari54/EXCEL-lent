from __future__ import annotations

from typing import Any


class InsightEngine:
    """Turn engine outputs + semantic context into alerts & recommendations."""

    def run(
        self,
        *,
        semantic: dict[str, Any],
        pieces: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        insights: list[str] = []
        alerts: list[str] = []
        recommendations: list[str] = []

        insights.append(
            f"Analyzed “{semantic.get('dataset_name')}” "
            f"({semantic.get('rows', 0):,} rows · {semantic.get('columns', 0)} columns)."
        )

        if semantic.get("quality_issue_count"):
            alerts.append(
                f"Alert: {semantic['quality_issue_count']} data-quality issue(s) were flagged at profile time."
            )
            recommendations.append("Run Clean Data before relying on executive metrics.")

        for p in pieces:
            if not p.get("ok"):
                alerts.append(p.get("error") or f"{p.get('engine')} could not complete.")
                continue
            if p.get("summary"):
                insights.append(str(p["summary"]))
            # contribution of top row
            table = p.get("table") or []
            if table and isinstance(table, list) and len(table) >= 1:
                row0 = table[0]
                if isinstance(row0, dict) and len(row0) >= 2:
                    keys = list(row0.keys())
                    insights.append(f"Leading segment: {keys[0]}={row0.get(keys[0])} → {keys[-1]}={row0.get(keys[-1])}.")

        if task_id in ("dashboard", "sales_dashboard", "analyze"):
            recommendations.append("Pin this view as a saved analysis and refresh after each data upload.")
        if not recommendations:
            recommendations.append("Try Compare or Charts next for a different angle on the same measure.")

        return {
            "engine": "insight",
            "insights": insights[:12],
            "alerts": alerts[:8],
            "recommendations": recommendations[:6],
        }
