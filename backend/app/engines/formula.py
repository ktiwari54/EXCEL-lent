from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.models.schemas import MetricOp
from app.services.excel_io import table_to_records


def apply_filter(df: pd.DataFrame, column: str | None, value: str | None) -> pd.DataFrame:
    if not column or value is None or column not in df.columns:
        return df
    return df[df[column].astype(str).str.strip().str.lower() == str(value).strip().lower()]


def aggregate_series(s: pd.Series, metric: MetricOp) -> float:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return 0.0
    if metric == MetricOp.sum:
        return float(s.sum())
    if metric == MetricOp.average:
        return float(s.mean())
    if metric == MetricOp.count:
        return float(len(s))
    if metric == MetricOp.counta:
        return float(s.notna().sum())
    if metric == MetricOp.min:
        return float(s.min())
    if metric == MetricOp.max:
        return float(s.max())
    if metric == MetricOp.median:
        return float(s.median())
    if metric == MetricOp.variance:
        return float(s.var(ddof=0)) if len(s) else 0.0
    return float(s.sum())


def calculate(
    df: pd.DataFrame,
    column: str,
    metric: MetricOp = MetricOp.sum,
    group_by: str | None = None,
    filter_column: str | None = None,
    filter_value: str | None = None,
    secondary_column: str | None = None,
) -> dict[str, Any]:
    work = apply_filter(df, filter_column, filter_value)
    if column not in work.columns:
        raise ValueError(f"Column '{column}' not found.")

    # Two-column derived metrics
    if metric in (MetricOp.difference, MetricOp.percentage, MetricOp.growth) and secondary_column:
        if secondary_column not in work.columns:
            raise ValueError(f"Secondary column '{secondary_column}' not found.")
        a = pd.to_numeric(work[column], errors="coerce")
        b = pd.to_numeric(work[secondary_column], errors="coerce")
        if metric == MetricOp.difference:
            val = float((a - b).sum())
            title = f"Difference: {column} − {secondary_column}"
            summary = f"Total difference = {val:,.2f}"
        elif metric == MetricOp.percentage:
            total_b = b.sum()
            val = float(100 * a.sum() / total_b) if total_b else 0.0
            title = f"Percentage: {column} / {secondary_column}"
            summary = f"{val:,.2f}%"
        else:  # growth
            total_b = b.sum()
            val = float(100 * (a.sum() - total_b) / abs(total_b)) if total_b else 0.0
            title = f"Growth %: {column} vs {secondary_column}"
            summary = f"{val:,.2f}%"
        return {
            "title": title,
            "summary": summary,
            "metric_value": val,
            "table": [],
            "meta": {"metric": metric.value, "rows_used": len(work)},
        }

    if group_by and group_by in work.columns:
        g = work.groupby(group_by, dropna=False)[column]
        if metric == MetricOp.average:
            res = g.apply(lambda s: pd.to_numeric(s, errors="coerce").mean())
        elif metric == MetricOp.count:
            res = g.count()
        elif metric == MetricOp.min:
            res = g.apply(lambda s: pd.to_numeric(s, errors="coerce").min())
        elif metric == MetricOp.max:
            res = g.apply(lambda s: pd.to_numeric(s, errors="coerce").max())
        elif metric == MetricOp.median:
            res = g.apply(lambda s: pd.to_numeric(s, errors="coerce").median())
        else:
            res = g.apply(lambda s: pd.to_numeric(s, errors="coerce").sum())

        tdf = res.reset_index()
        tdf.columns = [group_by, metric.value]
        tdf = tdf.sort_values(metric.value, ascending=False)

        if metric == MetricOp.contribution:
            total = tdf[metric.value].sum()
            tdf["contribution_pct"] = (100 * tdf[metric.value] / total) if total else 0
            metric_col = "contribution_pct"
        elif metric == MetricOp.running_total:
            tdf = tdf.sort_values(metric.value, ascending=True)
            tdf["running_total"] = tdf[metric.value].cumsum()
            metric_col = "running_total"
        else:
            metric_col = metric.value

        total_val = float(pd.to_numeric(work[column], errors="coerce").sum())
        return {
            "title": f"{metric.value.upper()} of {column} by {group_by}",
            "summary": f"Overall {metric.value} across groups; grand total of {column} ≈ {total_val:,.2f}",
            "metric_value": float(tdf[metric_col].sum()) if metric_col in tdf else total_val,
            "table": table_to_records(tdf),
            "chart": {
                "type": "bar",
                "labels": tdf[group_by].astype(str).tolist()[:25],
                "values": [float(x) for x in tdf[metric_col].tolist()[:25]],
                "label": metric_col,
            },
            "meta": {"metric": metric.value, "group_by": group_by, "rows_used": len(work)},
        }

    val = aggregate_series(work[column], metric)
    return {
        "title": f"{metric.value.upper()} of {column}",
        "summary": f"{metric.value.upper()}({column}) = {val:,.4g}",
        "metric_value": val,
        "table": [{"metric": metric.value, "column": column, "value": val}],
        "meta": {"metric": metric.value, "rows_used": len(work)},
    }


def compare(
    df: pd.DataFrame,
    value_column: str,
    dimension_column: str,
    metric: MetricOp = MetricOp.sum,
    left_value: str | None = None,
    right_value: str | None = None,
) -> dict[str, Any]:
    if value_column not in df.columns or dimension_column not in df.columns:
        raise ValueError("Value or dimension column not found.")

    work = df.copy()
    work["_val"] = pd.to_numeric(work[value_column], errors="coerce")
    grouped = work.groupby(work[dimension_column].astype(str))["_val"]

    if metric == MetricOp.average:
        series = grouped.mean()
    elif metric == MetricOp.count:
        series = grouped.count()
    else:
        series = grouped.sum()

    tdf = series.reset_index()
    tdf.columns = [dimension_column, metric.value]
    tdf = tdf.sort_values(metric.value, ascending=False)

    left = right = None
    growth = None
    if left_value and right_value:
        left = float(series.get(str(left_value), 0) or 0)
        right = float(series.get(str(right_value), 0) or 0)
        growth = 100 * (left - right) / abs(right) if right else None

    summary = f"Compared {value_column} across {dimension_column}."
    if growth is not None:
        summary = (
            f"{left_value}: {left:,.2f} vs {right_value}: {right:,.2f} "
            f"→ change {growth:+.1f}%"
        )

    return {
        "title": f"Compare {value_column} by {dimension_column}",
        "summary": summary,
        "metric_value": growth,
        "table": table_to_records(tdf),
        "chart": {
            "type": "bar",
            "labels": tdf[dimension_column].astype(str).tolist()[:25],
            "values": [float(x) for x in tdf[metric.value].tolist()[:25]],
            "label": metric.value,
        },
        "meta": {
            "left": left_value,
            "right": right_value,
            "left_value": left,
            "right_value": right,
            "growth_pct": growth,
        },
    }


def summarize(
    df: pd.DataFrame,
    group_by: list[str],
    value_column: str,
    metric: MetricOp = MetricOp.sum,
    top_n: int | None = None,
) -> dict[str, Any]:
    for g in group_by:
        if g not in df.columns:
            raise ValueError(f"Group column '{g}' not found.")
    if value_column not in df.columns:
        raise ValueError(f"Value column '{value_column}' not found.")

    work = df.copy()
    work["_val"] = pd.to_numeric(work[value_column], errors="coerce")
    agg_name = metric.value
    if metric == MetricOp.average:
        res = work.groupby(group_by, dropna=False)["_val"].mean()
    elif metric == MetricOp.count:
        res = work.groupby(group_by, dropna=False)["_val"].count()
    elif metric == MetricOp.min:
        res = work.groupby(group_by, dropna=False)["_val"].min()
    elif metric == MetricOp.max:
        res = work.groupby(group_by, dropna=False)["_val"].max()
    else:
        res = work.groupby(group_by, dropna=False)["_val"].sum()

    tdf = res.reset_index()
    tdf.columns = list(group_by) + [agg_name]
    tdf = tdf.sort_values(agg_name, ascending=False)
    if top_n:
        tdf = tdf.head(top_n)

    return {
        "title": f"Summary: {agg_name} of {value_column} by {', '.join(group_by)}",
        "summary": f"{len(tdf)} group(s).",
        "metric_value": float(tdf[agg_name].sum()) if len(tdf) else 0.0,
        "table": table_to_records(tdf),
        "chart": {
            "type": "bar",
            "labels": tdf[group_by[0]].astype(str).tolist()[:20],
            "values": [float(x) for x in tdf[agg_name].tolist()[:20]],
            "label": agg_name,
        },
        "meta": {"group_by": group_by, "metric": metric.value},
    }
