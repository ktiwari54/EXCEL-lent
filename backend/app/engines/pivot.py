from __future__ import annotations

from typing import Any

import pandas as pd

from app.models.schemas import MetricOp
from app.services.excel_io import table_to_records


AGG_MAP = {
    MetricOp.sum: "sum",
    MetricOp.average: "mean",
    MetricOp.count: "count",
    MetricOp.min: "min",
    MetricOp.max: "max",
    MetricOp.median: "median",
}


def create_pivot(
    df: pd.DataFrame,
    rows: list[str],
    columns: list[str],
    values: str,
    aggregation: MetricOp = MetricOp.sum,
) -> dict[str, Any]:
    if values not in df.columns:
        raise ValueError(f"Values column '{values}' not found.")
    for c in rows + columns:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found.")

    work = df.copy()
    work[values] = pd.to_numeric(work[values], errors="coerce")
    aggfunc = AGG_MAP.get(aggregation, "sum")

    if not rows and not columns:
        val = work[values].agg(aggfunc)
        tdf = pd.DataFrame([{"metric": aggregation.value, "value": float(val) if pd.notna(val) else 0}])
    else:
        pivot = pd.pivot_table(
            work,
            index=rows or None,
            columns=columns or None,
            values=values,
            aggfunc=aggfunc,
            fill_value=0,
        )
        if isinstance(pivot, pd.Series):
            tdf = pivot.reset_index()
            tdf.columns = list(rows) + [aggregation.value]
        else:
            tdf = pivot.reset_index()
            # Flatten multiindex columns
            if isinstance(tdf.columns, pd.MultiIndex):
                tdf.columns = [
                    "_".join([str(x) for x in col if str(x) != ""]).strip("_")
                    for col in tdf.columns.values
                ]
            else:
                tdf.columns = [str(c) for c in tdf.columns]

    return {
        "title": f"Pivot: {aggregation.value} of {values}",
        "summary": f"Rows={rows or '—'} | Columns={columns or '—'} | Values={values}",
        "table": table_to_records(tdf, limit=1000),
        "meta": {
            "rows": rows,
            "columns": columns,
            "values": values,
            "aggregation": aggregation.value,
            "shape": list(tdf.shape),
        },
        "dataframe": tdf,
    }


def chart_data(
    df: pd.DataFrame,
    category_column: str,
    value_column: str,
    metric: MetricOp = MetricOp.sum,
    top_n: int = 10,
    chart_type: str = "bar",
) -> dict[str, Any]:
    if category_column not in df.columns or value_column not in df.columns:
        raise ValueError("Category or value column not found.")

    work = df.copy()
    work["_v"] = pd.to_numeric(work[value_column], errors="coerce")
    g = work.groupby(work[category_column].astype(str))["_v"]
    if metric == MetricOp.average:
        series = g.mean()
    elif metric == MetricOp.count:
        series = g.count()
    else:
        series = g.sum()
    series = series.sort_values(ascending=False).head(top_n)

    labels = series.index.astype(str).tolist()
    values = [float(x) for x in series.tolist()]
    tdf = pd.DataFrame({category_column: labels, metric.value: values})

    return {
        "title": f"{chart_type.title()} chart: {metric.value} of {value_column} by {category_column}",
        "summary": f"Top {len(labels)} categories.",
        "table": table_to_records(tdf),
        "chart": {
            "type": chart_type,
            "labels": labels,
            "values": values,
            "label": f"{metric.value}({value_column})",
        },
        "meta": {"top_n": top_n},
    }
