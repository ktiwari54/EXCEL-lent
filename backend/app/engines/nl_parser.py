from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.engines.formula import calculate, compare, summarize
from app.engines.insight import analyze_dataset, build_dashboard, find_problems, top_bottom
from app.engines.pivot import chart_data
from app.engines.profiling import profile_dataframe, suggest_columns
from app.models.schemas import MetricOp


def _find_column(df: pd.DataFrame, *keywords: str) -> str | None:
    cols = list(df.columns)
    lower_map = {str(c).lower(): c for c in cols}
    for kw in keywords:
        for lc, orig in lower_map.items():
            if kw in lc:
                return orig
    return None


def _best_value_col(df: pd.DataFrame) -> str | None:
    profile = profile_dataframe(df, "tmp", "tmp")
    return suggest_columns(profile).get("value_column")


def answer_question(df: pd.DataFrame, question: str, session_id: str = "ask") -> dict[str, Any]:
    q = question.strip()
    ql = q.lower()

    # Clean / duplicates
    if any(k in ql for k in ("duplicate", "missing", "problem", "outlier", "issue", "clean")):
        result = find_problems(df)
        result["meta"] = {**(result.get("meta") or {}), "intent": "find_problems", "question": q}
        return result

    # Build my dashboard (free-text) — product vision §8
    if "dashboard" in ql or "build my dashboard" in ql or "create a sales dashboard" in ql:
        dtype = "sales"
        for t in ("inventory", "finance", "crm", "marketing", "hr", "operations"):
            if t in ql:
                dtype = t
                break
        result = build_dashboard(df, dashboard_type=dtype)
        # Honor common free-text intents by layering extra insights
        extras: list[str] = []
        if "gross margin" in ql or "margin" in ql:
            rev = _find_column(df, "revenue", "sales")
            cost = _find_column(df, "cost", "cogs")
            if rev and cost:
                r = float(pd.to_numeric(df[rev], errors="coerce").sum())
                c = float(pd.to_numeric(df[cost], errors="coerce").sum())
                margin = 100 * (r - c) / r if r else 0
                extras.append(f"Gross margin ≈ {margin:.1f}% (Revenue − Cost).")
        if "year-over-year" in ql or "yoy" in ql or "year over year" in ql:
            extras.append("YoY growth requires multi-year dates; MoM trend included when dates exist.")
        if extras:
            result["insights"] = list(result.get("insights") or []) + extras
        result["meta"] = {
            **(result.get("meta") or {}),
            "intent": "dashboard",
            "question": q,
            "build_my_dashboard": True,
        }
        return result

    # Analyze
    if any(k in ql for k in ("analyze", "analysis", "insight", "overview", "what would")):
        result = analyze_dataset(df, session_id=session_id)
        result["meta"] = {**(result.get("meta") or {}), "intent": "analyze", "question": q}
        return result

    # Top / bottom N
    m = re.search(r"(top|bottom)\s+(\d+)", ql)
    if m or "highest" in ql or "lowest" in ql or "top " in ql:
        n = int(m.group(2)) if m else 10
        ascending = bool(m and m.group(1) == "bottom") or "lowest" in ql or "losing" in ql
        value_col = (
            _find_column(df, "revenue", "sales", "amount", "profit", "margin", "total", "qty", "quantity")
            or _best_value_col(df)
        )
        label_col = _find_column(
            df, "customer", "product", "salesperson", "employee", "region", "country", "name", "sku"
        )
        # entity from question
        for ent in ("customer", "product", "salesperson", "employee", "region", "country", "sku"):
            if ent in ql:
                label_col = _find_column(df, ent) or label_col
        if not value_col:
            return {
                "title": "Could not answer",
                "summary": "No numeric measure column found. Specify a value column.",
                "insights": [],
                "table": [],
                "meta": {"intent": "top_bottom", "question": q},
            }
        # If label exists, aggregate first
        if label_col and label_col in df.columns:
            work = df.copy()
            work["_v"] = pd.to_numeric(work[value_col], errors="coerce")
            agg = work.groupby(work[label_col].astype(str))["_v"].sum().reset_index()
            agg.columns = [label_col, value_col]
            result = top_bottom(agg, value_col, n=n, ascending=ascending, label_column=label_col)
        else:
            result = top_bottom(df, value_col, n=n, ascending=ascending)
        result["meta"] = {**(result.get("meta") or {}), "intent": "top_bottom", "question": q}
        return result

    # Compare A and B
    m = re.search(r"compare\s+(.+?)\s+and\s+(.+)", ql)
    if m or " vs " in ql or " versus " in ql:
        if m:
            left, right = m.group(1).strip(" ?."), m.group(2).strip(" ?.")
        else:
            parts = re.split(r"\s+vs\.?\s+|\s+versus\s+", ql)
            left, right = (parts[0].split()[-1], parts[1].split()[0]) if len(parts) == 2 else (None, None)
        dim = _find_column(df, "region", "country", "city", "product", "category", "salesperson")
        val = _best_value_col(df)
        if dim and val and left and right:
            # fuzzy match dimension values
            vals = df[dim].astype(str).unique().tolist()

            def match(x: str) -> str:
                for v in vals:
                    if x.lower() in v.lower() or v.lower() in x.lower():
                        return v
                return x

            result = compare(df, val, dim, MetricOp.sum, match(left), match(right))
            result["meta"] = {**(result.get("meta") or {}), "intent": "compare", "question": q}
            return result

    # Monthly / trend
    if any(k in ql for k in ("monthly", "trend", "by month", "over time", "revenue by month")):
        date_col = _find_column(df, "date", "order date", "period", "month")
        val = _find_column(df, "revenue", "sales", "amount") or _best_value_col(df)
        if date_col and val:
            tmp = df.copy()
            tmp["_dt"] = pd.to_datetime(tmp[date_col], errors="coerce")
            tmp["_v"] = pd.to_numeric(tmp[val], errors="coerce")
            tmp = tmp.dropna(subset=["_dt"])
            tmp["_period"] = tmp["_dt"].dt.to_period("M").astype(str)
            monthly = tmp.groupby("_period")["_v"].sum().sort_index().reset_index()
            monthly.columns = ["Month", val]
            from app.services.excel_io import table_to_records

            return {
                "title": f"Monthly {val}",
                "summary": f"Trend of {val} by month.",
                "table": table_to_records(monthly),
                "chart": {
                    "type": "line",
                    "labels": monthly["Month"].tolist(),
                    "values": [float(x) for x in monthly[val].tolist()],
                    "label": val,
                },
                "meta": {"intent": "trend", "question": q},
            }

    # Chart request
    if any(k in ql for k in ("chart", "graph", "plot", "visualize")):
        cat = _find_column(df, "product", "category", "region", "country", "salesperson")
        val = _best_value_col(df)
        if cat and val:
            result = chart_data(df, cat, val, MetricOp.sum, top_n=10, chart_type="bar")
            result["meta"] = {**(result.get("meta") or {}), "intent": "chart", "question": q}
            return result

    # Total / sum / average
    if any(k in ql for k in ("total", "sum", "average", "avg", "mean", "how much")):
        metric = MetricOp.average if any(k in ql for k in ("average", "avg", "mean")) else MetricOp.sum
        val = _find_column(df, "revenue", "sales", "amount", "profit") or _best_value_col(df)
        group = None
        for g in ("product", "region", "country", "customer", "salesperson", "month", "category"):
            if f"by {g}" in ql or f"per {g}" in ql:
                group = _find_column(df, g)
                break
        if val:
            result = calculate(df, val, metric, group_by=group)
            result["meta"] = {**(result.get("meta") or {}), "intent": "calculate", "question": q}
            return result

    # Default: full analysis
    result = analyze_dataset(df, session_id=session_id)
    result["summary"] = (
        f"Interpreted question loosely and ran full analysis. Original: “{q}”"
    )
    result["meta"] = {**(result.get("meta") or {}), "intent": "fallback_analyze", "question": q}
    return result
