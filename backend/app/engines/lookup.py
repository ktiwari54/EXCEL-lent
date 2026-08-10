from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.excel_io import table_to_records


def xlookup(
    df: pd.DataFrame,
    lookup_value: str,
    lookup_column: str,
    return_column: str,
    exact: bool = True,
) -> dict[str, Any]:
    if lookup_column not in df.columns or return_column not in df.columns:
        raise ValueError("Lookup or return column not found.")

    series_lookup = df[lookup_column].astype(str)
    target = str(lookup_value).strip()

    if exact:
        mask = series_lookup.str.strip().str.lower() == target.lower()
    else:
        mask = series_lookup.str.contains(target, case=False, na=False)

    matches = df.loc[mask]
    if matches.empty:
        return {
            "title": f"Lookup '{lookup_value}' in {lookup_column}",
            "summary": "No match found.",
            "metric_value": None,
            "table": [],
            "insights": [f"No rows matched {lookup_column} = '{lookup_value}'."],
            "meta": {"matches": 0},
        }

    values = matches[return_column].tolist()
    first = values[0]
    if hasattr(first, "item"):
        try:
            first = first.item()
        except Exception:
            first = str(first)

    return {
        "title": f"XLOOKUP: {return_column} where {lookup_column} = {lookup_value}",
        "summary": f"{len(matches)} match(es). First result: {first}",
        "metric_value": float(first) if isinstance(first, (int, float)) else None,
        "table": table_to_records(matches.head(100)),
        "insights": [f"Returned {return_column} for {len(matches)} matching row(s)."],
        "meta": {"matches": len(matches), "first_value": first},
    }


def multi_condition_lookup(
    df: pd.DataFrame,
    conditions: list[dict[str, str]],
    return_columns: list[str] | None = None,
) -> dict[str, Any]:
    """conditions: [{column, value}, ...] AND-ed together."""
    work = df.copy()
    for cond in conditions:
        col = cond.get("column")
        val = cond.get("value")
        if not col or col not in work.columns:
            raise ValueError(f"Condition column '{col}' not found.")
        work = work[work[col].astype(str).str.strip().str.lower() == str(val).strip().lower()]

    cols = return_columns or list(work.columns)
    cols = [c for c in cols if c in work.columns]
    out = work[cols]

    return {
        "title": "Multi-condition lookup",
        "summary": f"{len(out)} row(s) matched {len(conditions)} condition(s).",
        "table": table_to_records(out.head(200)),
        "insights": [f"Matched {len(out)} record(s)."],
        "meta": {"conditions": conditions, "matches": len(out)},
    }


def reconcile(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_on: str,
    right_on: str,
    how: str = "outer",
) -> dict[str, Any]:
    if left_on not in left.columns or right_on not in right.columns:
        raise ValueError("Join keys not found.")

    merged = left.merge(
        right,
        left_on=left_on,
        right_on=right_on,
        how=how,
        indicator=True,
        suffixes=("_left", "_right"),
    )
    only_left = int((merged["_merge"] == "left_only").sum())
    only_right = int((merged["_merge"] == "right_only").sum())
    both = int((merged["_merge"] == "both").sum())

    insights = [
        f"Matched on both sides: {both}",
        f"Only in left: {only_left}",
        f"Only in right: {only_right}",
    ]
    return {
        "title": f"Reconciliation: {left_on} ↔ {right_on}",
        "summary": f"{both} matched · {only_left} left-only · {only_right} right-only",
        "table": table_to_records(merged.head(200)),
        "insights": insights,
        "alerts": (
            [f"Alert: {only_left + only_right} unmatched record(s)."]
            if only_left or only_right
            else []
        ),
        "meta": {"both": both, "left_only": only_left, "right_only": only_right},
    }
