from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.services.excel_io import table_to_records


def filter_rows(
    df: pd.DataFrame,
    column: str,
    op: str,
    value: str,
) -> dict[str, Any]:
    """FILTER-like row selection."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")

    s = df[column]
    op = op.lower().strip()
    work = df.copy()

    if op in ("=", "==", "eq", "equals"):
        mask = s.astype(str).str.strip().str.lower() == str(value).strip().lower()
    elif op in ("!=", "<>", "ne", "not"):
        mask = s.astype(str).str.strip().str.lower() != str(value).strip().lower()
    elif op in (">", "gt"):
        mask = pd.to_numeric(s, errors="coerce") > float(value)
    elif op in (">=", "gte"):
        mask = pd.to_numeric(s, errors="coerce") >= float(value)
    elif op in ("<", "lt"):
        mask = pd.to_numeric(s, errors="coerce") < float(value)
    elif op in ("<=", "lte"):
        mask = pd.to_numeric(s, errors="coerce") <= float(value)
    elif op in ("contains", "like"):
        mask = s.astype(str).str.contains(str(value), case=False, na=False)
    else:
        raise ValueError(f"Unsupported operator: {op}")

    out = work.loc[mask]
    return {
        "title": f"FILTER: {column} {op} {value}",
        "summary": f"{len(out)} of {len(df)} rows matched.",
        "table": table_to_records(out.head(500)),
        "insights": [f"Returned {len(out)} row(s)."],
        "meta": {"rows_matched": len(out), "operator": op},
    }


def unique_values(df: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
    vals = df[column].dropna().astype(str).unique().tolist()
    tdf = pd.DataFrame({column: vals, "count": [int((df[column].astype(str) == v).sum()) for v in vals]})
    tdf = tdf.sort_values("count", ascending=False)
    return {
        "title": f"UNIQUE: {column}",
        "summary": f"{len(vals)} unique value(s).",
        "table": table_to_records(tdf),
        "chart": {
            "type": "bar",
            "labels": tdf[column].tolist()[:25],
            "values": [float(x) for x in tdf["count"].tolist()[:25]],
            "label": "count",
        },
        "meta": {"unique_count": len(vals)},
    }


def sort_data(
    df: pd.DataFrame,
    by: list[str],
    ascending: bool | list[bool] = True,
) -> dict[str, Any]:
    for c in by:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found.")
    out = df.sort_values(by=by, ascending=ascending)
    return {
        "title": f"SORT by {', '.join(by)}",
        "summary": f"Sorted {len(out)} rows.",
        "table": table_to_records(out.head(200)),
        "meta": {"by": by, "ascending": ascending},
    }


def transpose_preview(df: pd.DataFrame, max_cols: int = 20) -> dict[str, Any]:
    sample = df.head(max_cols)
    t = sample.T.reset_index()
    t.columns = ["field"] + [f"row_{i+1}" for i in range(len(sample))]
    return {
        "title": "TRANSPOSE preview",
        "summary": f"Transposed first {len(sample)} rows.",
        "table": table_to_records(t.head(100)),
        "meta": {"source_rows": len(sample)},
    }
