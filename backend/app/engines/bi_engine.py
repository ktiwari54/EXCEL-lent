from __future__ import annotations

from typing import Any

import pandas as pd

from app.engines.explanation import merge_explanations
from app.engines.formula_engine import FormulaEngine
from app.engines.insight_engine import InsightEngine
from app.engines.kpi_engine import KPIEngine
from app.engines.lookup_engine import LookupEngine
from app.engines.measure_engine import MeasureEngine
from app.engines.outlier_engine import OutlierEngine
from app.engines.pareto_engine import ParetoEngine
from app.engines.ranking_engine import RankingEngine
from app.engines.result_engine import ResultEngine
from app.engines.scenario_engine import ScenarioEngine, TargetEngine
from app.engines.semantic import SemanticDataLayer
from app.engines.stats_engine import StatisticsEngine
from app.engines.time_engine import TimeEngine


class BusinessIntelligenceEngine:
    """
    Step 4 — Intelligent BI & Calculation Engine orchestrator.

    USER REQUEST → Intent → Semantic → Calculation Plan → Specialists
         → Validation → Result → Insight → Explanation
    """

    def __init__(self) -> None:
        self.semantic_layer = SemanticDataLayer()
        self.measures = MeasureEngine()
        self.formula = FormulaEngine()
        self.lookup = LookupEngine()
        self.time = TimeEngine()
        self.stats = StatisticsEngine()
        self.kpi = KPIEngine()
        self.ranking = RankingEngine()
        self.pareto = ParetoEngine()
        self.outlier = OutlierEngine()
        self.scenario = ScenarioEngine()
        self.target = TargetEngine()
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
        semantic["measure_catalog"] = self.measures.catalog(df, semantic)

        normalized = dict(task_request.get("normalized") or task_request.get("configuration") or {})
        task_id = (task_request.get("task_id") or "").lower()

        # Semantic defaults
        if not normalized.get("measure"):
            normalized["measure"] = self.semantic_layer.resolve_column(semantic, None, "measures")
        if not normalized.get("date_field"):
            normalized["date_field"] = self.semantic_layer.resolve_column(semantic, None, "dates")
        if not normalized.get("group_by"):
            cat = normalized.get("category") or normalized.get("compare_by")
            if cat:
                normalized["group_by"] = [cat]
            elif semantic.get("dimensions") and task_id in (
                "summarize",
                "top_n",
                "charts",
                "pivot",
                "compare",
                "analyze",
                "dashboard",
                "sales_dashboard",
            ):
                normalized["group_by"] = [semantic["dimensions"][0]["name"]]

        # Calculation plan (what engines will run)
        plan = self._plan(task_id, normalized, semantic)
        pieces: list[dict[str, Any]] = []

        for step in plan:
            eng = step["engine"]
            if eng == "formula":
                pieces.append(self.formula.run(df, {**normalized, **step.get("params", {})}))
            elif eng == "lookup":
                pieces.append(self.lookup.run(df, {**normalized, **step.get("params", {})}, secondary_df))
            elif eng == "time":
                pieces.append(self.time.run(df, {**normalized, **step.get("params", {})}))
            elif eng == "stats":
                pieces.append(self.stats.run(df, {**normalized, **step.get("params", {})}))
            elif eng == "kpi":
                pieces.append(self.kpi.run(df, semantic, normalized))
            elif eng == "ranking":
                gb = normalized.get("group_by") or []
                g0 = gb[0] if isinstance(gb, list) and gb else normalized.get("category") or normalized.get("compare_by")
                n = int(normalized.get("limit") or 10) or 10
                pieces.append(
                    self.ranking.top_n(
                        df,
                        semantic,
                        measure=normalized.get("measure") or "",
                        group_by=str(g0 or ""),
                        n=n,
                        ascending=(normalized.get("sort_direction") == "asc"),
                        aggregation=normalized.get("aggregation") or "sum",
                    )
                )
            elif eng == "pareto":
                gb = normalized.get("group_by") or []
                g0 = gb[0] if isinstance(gb, list) and gb else normalized.get("category")
                pieces.append(
                    self.pareto.run(
                        df,
                        semantic,
                        measure=normalized.get("measure") or "",
                        group_by=str(g0 or ""),
                    )
                )
            elif eng == "outlier":
                pieces.append(
                    self.outlier.run(df, semantic, measure=normalized.get("measure") or "Revenue")
                )
            elif eng == "scenario":
                pieces.append(
                    self.scenario.run(
                        df,
                        semantic,
                        measure=normalized.get("measure") or "",
                        change_pct=float(normalized.get("change_pct") or 10),
                    )
                )
            elif eng == "descriptive":
                pieces.append(self.stats.descriptive(df, normalized.get("measure") or ""))

        # Always attach measure catalog context for transparency
        if not pieces:
            pieces.append(self.kpi.run(df, semantic, normalized))

        insights = self.insight.run(semantic=semantic, pieces=pieces, task_id=task_id)
        # Concentration insight from pareto
        for p in pieces:
            if p.get("engine") == "pareto" and p.get("ok"):
                insights.setdefault("insights", []).append(p.get("summary"))
                insights.setdefault("recommendations", []).append(
                    "High concentration may indicate risk — diversify top segments if over-dependent."
                )

        explanation = merge_explanations(pieces, {**task_request, "normalized": normalized})
        result = self.result.assemble(
            task_request={**task_request, "normalized": normalized},
            pieces=pieces,
            insights=insights,
            semantic=semantic,
        )
        result["meta"]["explanation"] = explanation
        result["meta"]["calculation_plan"] = plan
        result["meta"]["measure_catalog"] = [
            m for m in semantic.get("measure_catalog") or [] if m.get("available")
        ][:12]
        result["meta"]["pipeline"] = [
            "intent",
            "semantic",
            "business_logic",
            "calculation_plan",
            *[p.get("engine") for p in pieces if p.get("engine")],
            "validation",
            "insight",
            "result",
            "explanation",
        ]
        return result

    def _plan(self, task_id: str, normalized: dict[str, Any], semantic: dict[str, Any]) -> list[dict[str, Any]]:
        """Select specialist engines automatically from task + data shape."""
        plan: list[dict[str, Any]] = []
        has_date = bool(normalized.get("date_field") or semantic.get("dates"))
        has_measure = bool(normalized.get("measure") or semantic.get("measures"))
        has_dim = bool(
            normalized.get("group_by")
            or normalized.get("category")
            or normalized.get("compare_by")
            or semantic.get("dimensions")
        )

        if task_id in ("lookup", "match_datasets", "find_duplicates"):
            plan.append({"engine": "lookup"})
        elif task_id == "clean":
            plan.append({"engine": "lookup", "params": {}})
            plan.append({"engine": "kpi"})
        elif task_id == "monthly_trend":
            plan.append({"engine": "time"})
            plan.append({"engine": "descriptive"})
        elif task_id == "top_n":
            plan.append({"engine": "ranking"})
        elif task_id in ("analyze", "dashboard", "sales_dashboard", "reports", "inventory_analysis"):
            plan.append({"engine": "kpi"})
            if has_date and has_measure:
                plan.append({"engine": "time"})
            if has_measure and has_dim:
                plan.append({"engine": "ranking"})
                plan.append({"engine": "pareto"})
            if has_measure:
                plan.append({"engine": "outlier"})
                plan.append({"engine": "descriptive"})
        elif task_id == "charts":
            plan.append({"engine": "formula", "params": {}})
        elif task_id == "compare":
            plan.append({"engine": "formula"})
            if has_date and has_measure:
                plan.append({"engine": "time"})
        elif task_id in ("pivot", "summarize", "calculate"):
            plan.append({"engine": "formula"})
            if task_id == "summarize" and has_dim and has_measure:
                plan.append({"engine": "pareto"})
        else:
            plan.append({"engine": "kpi"})
            if has_measure:
                plan.append({"engine": "formula"})
        return plan


bi_engine = BusinessIntelligenceEngine()
