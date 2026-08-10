from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.excel_io import table_to_records


def _mask(df: pd.DataFrame, column: str, op: str, value: str) -> pd.Series:
    s = df[column]
    op = (op or "=").lower().strip()
    if op in ("=", "==", "eq", ""):
        return s.astype(str).str.strip().str.lower() == str(value).strip().lower()
    if op in (">", "gt"):
        return pd.to_numeric(s, errors="coerce") > float(value)
    if op in (">=", "gte"):
        return pd.to_numeric(s, errors="coerce") >= float(value)
    if op in ("<", "lt"):
        return pd.to_numeric(s, errors="coerce") < float(value)
    if op in ("<=", "lte"):
        return pd.to_numeric(s, errors="coerce") <= float(value)
    if op in ("contains",):
        return s.astype(str).str.contains(str(value), case=False, na=False)
    return s.astype(str).str.strip().str.lower() == str(value).strip().lower()


def sumif(
    df: pd.DataFrame,
    criteria_column: str,
    criteria_value: str,
    sum_column: str,
    op: str = "=",
) -> dict[str, Any]:
    if criteria_column not in df.columns or sum_column not in df.columns:
        raise ValueError("Criteria or sum column not found.")
    mask = _mask(df, criteria_column, op, criteria_value)
    total = float(pd.to_numeric(df.loc[mask, sum_column], errors="coerce").sum())
    return {
        "title": f"SUMIF({criteria_column} {op} {criteria_value}, {sum_column})",
        "summary": f"SUMIF = {total:,.4g} over {int(mask.sum())} row(s)",
        "metric_value": total,
        "table": [{"function": "SUMIF", "criteria": f"{criteria_column}{op}{criteria_value}", "sum_column": sum_column, "result": total, "rows": int(mask.sum())}],
        "meta": {"rows_matched": int(mask.sum())},
    }


def sumifs(
    df: pd.DataFrame,
    sum_column: str,
    criteria: list[dict[str, str]],
) -> dict[str, Any]:
    """criteria items: {column, value, op?}"""
    if sum_column not in df.columns:
        raise ValueError(f"Sum column '{sum_column}' not found.")
    mask = pd.Series(True, index=df.index)
    for c in criteria:
        col = c.get("column")
        if not col or col not in df.columns:
            raise ValueError(f"Criteria column '{col}' not found.")
        mask &= _mask(df, col, c.get("op", "="), c.get("value", ""))
    total = float(pd.to_numeric(df.loc[mask, sum_column], errors="coerce").sum())
    return {
        "title": f"SUMIFS({sum_column})",
        "summary": f"SUMIFS = {total:,.4g} over {int(mask.sum())} row(s)",
        "metric_value": total,
        "table": [{"function": "SUMIFS", "sum_column": sum_column, "result": total, "rows": int(mask.sum())}],
        "meta": {"criteria": criteria, "rows_matched": int(mask.sum())},
    }


def countif(
    df: pd.DataFrame,
    criteria_column: str,
    criteria_value: str,
    op: str = "=",
) -> dict[str, Any]:
    if criteria_column not in df.columns:
        raise ValueError(f"Column '{criteria_column}' not found.")
    mask = _mask(df, criteria_column, op, criteria_value)
    n = int(mask.sum())
    return {
        "title": f"COUNTIF({criteria_column} {op} {criteria_value})",
        "summary": f"COUNTIF = {n}",
        "metric_value": float(n),
        "table": [{"function": "COUNTIF", "result": n}],
        "meta": {"rows_matched": n},
    }


def countifs(df: pd.DataFrame, criteria: list[dict[str, str]]) -> dict[str, Any]:
    mask = pd.Series(True, index=df.index)
    for c in criteria:
        col = c.get("column")
        if not col or col not in df.columns:
            raise ValueError(f"Criteria column '{col}' not found.")
        mask &= _mask(df, col, c.get("op", "="), c.get("value", ""))
    n = int(mask.sum())
    return {
        "title": "COUNTIFS",
        "summary": f"COUNTIFS = {n}",
        "metric_value": float(n),
        "table": [{"function": "COUNTIFS", "result": n}],
        "meta": {"criteria": criteria, "rows_matched": n},
    }


def averageif(
    df: pd.DataFrame,
    criteria_column: str,
    criteria_value: str,
    avg_column: str,
    op: str = "=",
) -> dict[str, Any]:
    if criteria_column not in df.columns or avg_column not in df.columns:
        raise ValueError("Criteria or average column not found.")
    mask = _mask(df, criteria_column, op, criteria_value)
    s = pd.to_numeric(df.loc[mask, avg_column], errors="coerce")
    avg = float(s.mean()) if s.notna().any() else 0.0
    return {
        "title": f"AVERAGEIF({criteria_column} {op} {criteria_value}, {avg_column})",
        "summary": f"AVERAGEIF = {avg:,.4g} over {int(mask.sum())} row(s)",
        "metric_value": avg,
        "table": [{"function": "AVERAGEIF", "result": avg, "rows": int(mask.sum())}],
        "meta": {"rows_matched": int(mask.sum())},
    }


def math_expression(
    df: pd.DataFrame,
    left_column: str,
    operator: str,
    right_column: str | None = None,
    right_value: float | None = None,
    result_name: str = "Result",
) -> dict[str, Any]:
    """Row-wise math: Revenue - Cost, Units * Price, etc."""
    if left_column not in df.columns:
        raise ValueError(f"Column '{left_column}' not found.")
    left = pd.to_numeric(df[left_column], errors="coerce")
    if right_column:
        if right_column not in df.columns:
            raise ValueError(f"Column '{right_column}' not found.")
        right = pd.to_numeric(df[right_column], errors="coerce")
        label = f"{left_column} {operator} {right_column}"
    else:
        right = float(right_value or 0)
        label = f"{left_column} {operator} {right}"

    op = operator.strip()
    if op in ("+", "add"):
        series = left + right
    elif op in ("-", "sub", "subtract"):
        series = left - right
    elif op in ("*", "x", "mul", "multiply"):
        series = left * right
    elif op in ("/", "div", "divide"):
        series = left / right.replace(0, pd.NA) if isinstance(right, pd.Series) else left / (right or pd.NA)
    elif op in ("%", "pct", "percent"):
        series = (left / right.replace(0, pd.NA) * 100) if isinstance(right, pd.Series) else (left / (right or pd.NA) * 100)
    else:
        raise ValueError(f"Unsupported operator: {operator}")

    out = df.copy()
    out[result_name] = series
    total = float(pd.to_numeric(series, errors="coerce").sum())
    return {
        "title": f"Calculate: {label}",
        "summary": f"Created column '{result_name}'. Sum = {total:,.4g}",
        "metric_value": total,
        "table": table_to_records(out[[left_column] + ([right_column] if right_column else []) + [result_name]].head(100)),
        "insights": [f"Row-wise {label} → '{result_name}' (total {total:,.2f})."],
        "meta": {"expression": label, "result_column": result_name, "sum": total},
        "dataframe": out,
    }


def logical_flag(
    df: pd.DataFrame,
    column: str,
    op: str,
    value: str,
    true_label: str = "Yes",
    false_label: str = "No",
    result_name: str = "Flag",
) -> dict[str, Any]:
    """IF-like column flag."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
    mask = _mask(df, column, op, value)
    out = df.copy()
    out[result_name] = mask.map({True: true_label, False: false_label})
    return {
        "title": f"IF({column} {op} {value})",
        "summary": f"{int(mask.sum())} rows → {true_label}, {int((~mask).sum())} → {false_label}",
        "table": table_to_records(out[[column, result_name]].head(100)),
        "metric_value": float(mask.sum()),
        "meta": {"true_count": int(mask.sum()), "false_count": int((~mask).sum())},
        "dataframe": out,
    }
