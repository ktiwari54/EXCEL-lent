from __future__ import annotations

from typing import Any

import pandas as pd


def analyze_quality(df: pd.DataFrame, column_profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect data-quality issues without modifying data."""
    issues: list[dict[str, Any]] = []
    n_rows = len(df)
    n_cells = max(n_rows * max(len(df.columns), 1), 1)

    # Missing
    missing_total = int(df.isna().sum().sum())
    for col in df.columns:
        nulls = int(df[col].isna().sum())
        if nulls:
            issues.append(
                {
                    "severity": "warning" if nulls / max(n_rows, 1) < 0.1 else "high",
                    "category": "missing",
                    "column": str(col),
                    "message": f"'{col}' has {nulls:,} missing value(s) ({100 * nulls / max(n_rows, 1):.1f}%).",
                    "count": nulls,
                }
            )

    # Duplicate rows
    dup_rows = int(df.duplicated().sum())
    if dup_rows:
        issues.append(
            {
                "severity": "warning",
                "category": "duplicate",
                "column": None,
                "message": f"{dup_rows:,} fully duplicate row(s) detected.",
                "count": dup_rows,
            }
        )

    # Duplicate IDs
    for cp in column_profiles:
        if cp.get("role") == "identifier" or cp.get("data_type") == "identifier":
            col = cp["name"]
            if col in df.columns:
                s = df[col].dropna()
                dups = int(s.duplicated().sum())
                if dups:
                    issues.append(
                        {
                            "severity": "high",
                            "category": "duplicate",
                            "column": col,
                            "message": f"Identifier '{col}' has {dups:,} duplicate value(s).",
                            "count": dups,
                        }
                    )

    # Text / formatting
    for col in df.columns:
        if df[col].dtype != object and not pd.api.types.is_string_dtype(df[col]):
            continue
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        # spaces
        spaced = int((s != s.str.strip()).sum())
        if spaced:
            issues.append(
                {
                    "severity": "info",
                    "category": "formatting",
                    "column": str(col),
                    "message": f"'{col}' has {spaced:,} value(s) with leading/trailing spaces.",
                    "count": spaced,
                }
            )
        # inconsistent case categories
        if s.nunique() <= 50:
            lower_map: dict[str, set[str]] = {}
            for v in s.unique():
                lower_map.setdefault(v.lower(), set()).add(v)
            inconsistent = {k: list(v) for k, v in lower_map.items() if len(v) > 1}
            if inconsistent:
                examples = list(inconsistent.values())[:3]
                issues.append(
                    {
                        "severity": "warning",
                        "category": "consistency",
                        "column": str(col),
                        "message": f"'{col}' has inconsistent capitalization (e.g. {examples}).",
                        "count": len(inconsistent),
                        "examples": examples,
                    }
                )
        # numbers as text
        coerced = pd.to_numeric(s.str.replace(",", "", regex=False).str.replace("%", "", regex=False), errors="coerce")
        if coerced.notna().mean() > 0.85:
            issues.append(
                {
                    "severity": "info",
                    "category": "formatting",
                    "column": str(col),
                    "message": f"'{col}' looks numeric but is stored as text.",
                    "count": int(coerced.notna().sum()),
                }
            )

    # Invalid emails
    for cp in column_profiles:
        if cp.get("data_type") == "email" and cp["name"] in df.columns:
            s = df[cp["name"]].dropna().astype(str)
            bad = int((~s.str.contains(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", regex=True)).sum())
            if bad:
                issues.append(
                    {
                        "severity": "warning",
                        "category": "validity",
                        "column": cp["name"],
                        "message": f"'{cp['name']}' has {bad:,} value(s) that don't look like valid emails.",
                        "count": bad,
                    }
                )

    # Negative quantities
    for cp in column_profiles:
        name = cp["name"]
        if name not in df.columns:
            continue
        if cp.get("role") == "measure" and any(k in name.lower() for k in ("qty", "quantity", "units")):
            nums = pd.to_numeric(df[name], errors="coerce")
            neg = int((nums < 0).sum())
            if neg:
                issues.append(
                    {
                        "severity": "warning",
                        "category": "validity",
                        "column": name,
                        "message": f"'{name}' has {neg:,} negative value(s).",
                        "count": neg,
                    }
                )

    return {
        "issues": issues,
        "issue_count": len(issues),
        "missing_cells": missing_total,
        "duplicate_rows": dup_rows,
        "missing_pct": round(100 * missing_total / n_cells, 2),
    }
