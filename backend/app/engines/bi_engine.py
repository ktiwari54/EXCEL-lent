from __future__ import annotations

from typing import Any

import pandas as pd

from app.engines.formula_engine import FormulaEngine
from app.engines.insight_engine import InsightEngine
from app.engines.kpi_engine import KPIEngine
from app.engines.lookup_engine import LookupEngine
from app.engines.result_engine import ResultEngine
from app.engines.semantic import SemanticDataLayer
from app.engines.stats_engine import StatisticsEngine
from app.engines.time_engine import TimeEngine


class BusinessIntelligenceEngine:
    """
    Orchestrates specialist engines based on Task Request from Step 3.

    Flow: Semantic → specialists → Insight → Result
    """

    def __init__(self) -> None:
        self.semantic_layer = SemanticDataLayer()
        self.formula = FormulaEngine()
        self.lookup = LookupEngine()
        self.time = TimeEngine()
        self.stats = StatisticsEngine()
        self.kpi = KPIEngine()
        self.insight = InsightEngine()
        self.result = ResultEngine()

    def execute(
        self,
        *,
        task_request: dict[str, Any],
        dataset: dict[str, Any],
        df: pd.DataFrame,
        secondary_df: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        semantic = self.semantic_layer.build(dataset, df)
        normalized = dict(task_request.get("normalized") or task_request.get("configuration") or {})
        task_id = task_request.get("task_id") or ""

        # Fill missing measure/date from semantic
        if not normalized.get("measure"):
            normalized["measure"] = self.semantic_layer.resolve_column(semantic, None, "measures")
        if not normalized.get("date_field"):
            normalized["date_field"] = self.semantic_layer.resolve_column(semantic, None, "dates")
        if not normalized.get("group_by"):
            cat = normalized.get("category") or normalized.get("compare_by")
            if cat:
                normalized["group_by"] = [cat]
            elif semantic.get("dimensions"):
                # only auto-group for summarize-like tasks
                if task_id in ("summarize", "top_n", "charts", "pivot", "compare"):
                    normalized["group_by"] = [semantic["dimensions"][0]["name"]]

        pieces: list[dict[str, Any]] = []

        # Route by task
        if task_id in ("lookup", "match_datasets", "find_duplicates"):
            pieces.append(self.lookup.run(df, normalized, secondary_df))
        elif task_id in ("monthly_trend",):
            pieces.append(self.time.run(df, normalized))
        elif task_id in ("top_n",):
            pieces.append(self.stats.run(df, normalized))
        elif task_id in ("clean",):
            # quality-oriented: duplicates via lookup path
            keys = normalized.get("duplicate_keys") or []
            n2 = dict(normalized)
            if keys:
                n2["lookup_column"] = keys[0]
                n2["duplicate_keys"] = keys
            pieces.append(self.lookup.run(df, n2))
            pieces.append(self.kpi.run(df, semantic, normalized))
        elif task_id in ("dashboard", "sales_dashboard", "analyze", "reports", "inventory_analysis"):
            pieces.append(self.kpi.run(df, semantic, normalized))
            if normalized.get("date_field") and normalized.get("measure"):
                pieces.append(self.time.run(df, normalized))
            if normalized.get("measure") and (normalized.get("group_by") or normalized.get("category")):
                n2 = dict(normalized)
                if not n2.get("group_by") and n2.get("category"):
                    n2["group_by"] = [n2["category"]]
                n2["limit"] = n2.get("limit") or 10
                pieces.append(self.formula.run(df, n2))
        elif task_id in ("charts",):
            n2 = dict(normalized)
            if n2.get("category") and not n2.get("group_by"):
                n2["group_by"] = [n2["category"]]
            pieces.append(self.formula.run(df, n2))
            if pieces[-1].get("chart") and n2.get("chart_type"):
                pieces[-1]["chart"]["type"] = n2["chart_type"]
        elif task_id in ("compare",):
            n2 = dict(normalized)
            if n2.get("compare_by") and not n2.get("group_by"):
                n2["group_by"] = [n2["compare_by"]]
            pieces.append(self.formula.run(df, n2))
        elif task_id in ("pivot", "summarize", "calculate"):
            n2 = dict(normalized)
            if task_id == "pivot":
                rows = n2.get("rows") or n2.get("group_by") or []
                if isinstance(rows, str):
                    rows = [rows] if rows else []
                n2["group_by"] = rows
            pieces.append(self.formula.run(df, n2))
        else:
            # default analyze path
            pieces.append(self.kpi.run(df, semantic, normalized))
            if normalized.get("measure"):
                pieces.append(self.formula.run(df, {**normalized, "group_by": normalized.get("group_by") or []}))

        insights = self.insight.run(semantic=semantic, pieces=pieces, task_id=task_id)
        return self.result.assemble(
            task_request=task_request,
            pieces=pieces,
            insights=insights,
            semantic=semantic,
        )


# Singleton for routers
bi_engine = BusinessIntelligenceEngine()
