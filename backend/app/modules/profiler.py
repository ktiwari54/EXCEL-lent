from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.modules.health_score import compute_health_score
from app.modules.json_safe import json_safe
from app.modules.quality_engine import analyze_quality
from app.modules.role_detection import detect_role
from app.modules.type_detection import detect_column_type


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Full column profiling + quality + health for one dataset (raw)."""
    rows = int(len(df))
    cols = int(len(df.columns))
    column_profiles: list[dict[str, Any]] = []
    type_confidences: list[float] = []

    for col in df.columns:
        s = df[col]
        type_info = detect_column_type(s, str(col))
        data_type = type_info["data_type"]
        type_confidences.append(float(type_info["confidence"]))

        non_null = int(s.notna().sum())
        null_count = int(s.isna().sum())
        unique_count = int(s.nunique(dropna=True))
        role_info = detect_role(str(col), data_type, unique_count, rows)

        profile: dict[str, Any] = {
            "name": str(col),
            "data_type": data_type,
            "type_confidence": round(float(type_info["confidence"]), 3),
            "excel_dtype": type_info["excel_dtype"],
            "role": role_info["role"],
            "role_confidence": role_info["confidence"],
            "suggested_uses": role_info["suggested_uses"],
            "non_null": non_null,
            "null_count": null_count,
            "null_pct": round(100 * null_count / max(rows, 1), 2),
            "unique_count": unique_count,
            "sample_values": _samples(s),
        }

        # Type-specific stats
        if data_type in ("number", "integer", "decimal", "currency", "percentage") or pd.api.types.is_numeric_dtype(s):
            nums = pd.to_numeric(
                s.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
                if s.dtype == object
                else s,
                errors="coerce",
            )
            clean = nums.dropna()
            if len(clean):
                profile.update(
                    {
                        "sum": float(clean.sum()),
                        "average": float(clean.mean()),
                        "median": float(clean.median()),
                        "min": float(clean.min()),
                        "max": float(clean.max()),
                        "std": float(clean.std()) if len(clean) > 1 else 0.0,
                    }
                )
        elif data_type in ("date", "datetime"):
            dt = pd.to_datetime(s, errors="coerce")
            clean = dt.dropna()
            if len(clean):
                profile.update(
                    {
                        "min_date": clean.min().isoformat(),
                        "max_date": clean.max().isoformat(),
                        "unique_dates": int(clean.nunique()),
                        "date_range_days": int((clean.max() - clean.min()).days),
                    }
                )
        else:
            # text/category
            vals = s.dropna().astype(str)
            if len(vals):
                vc = vals.value_counts().head(5)
                profile["top_values"] = [
                    {"value": str(i), "count": int(c)} for i, c in vc.items()
                ]
                profile["blank_like"] = int((vals.str.strip() == "").sum())
                profile["duplicate_values"] = int(vals.duplicated().sum())

        column_profiles.append(profile)

    quality = analyze_quality(df, column_profiles)
    health = compute_health_score(
        rows=rows,
        columns=cols,
        missing_cells=quality["missing_cells"],
        duplicate_rows=quality["duplicate_rows"],
        issues=quality["issues"],
        type_confidences=type_confidences,
    )

    numeric_fields = sum(1 for c in column_profiles if c["data_type"] in ("number", "integer", "decimal", "currency", "percentage") or c["role"] == "measure")
    date_fields = sum(1 for c in column_profiles if c["data_type"] in ("date", "datetime") or c["role"] == "date_dimension")
    category_fields = sum(1 for c in column_profiles if c["data_type"] == "category" or c["role"] == "dimension")

    result = {
        "rows": rows,
        "columns": cols,
        "column_profiles": column_profiles,
        "quality": quality,
        "health": health,
        "summary": {
            "rows": rows,
            "columns": cols,
            "numeric_fields": numeric_fields,
            "date_fields": date_fields,
            "category_fields": category_fields,
            "missing_values": quality["missing_cells"],
            "duplicate_records": quality["duplicate_rows"],
            "data_health": health["score"],
        },
        "preview": _preview_records(df, 50),
    }
    return json_safe(result)


def _samples(s: pd.Series, n: int = 5) -> list[Any]:
    vals = s.dropna().head(n).tolist()
    return [json_safe(v) for v in vals]


def _preview_records(df: pd.DataFrame, limit: int = 50) -> list[dict[str, Any]]:
    out = df.head(limit).copy()
    # Replace NA / NaN / NaT with None before to_dict
    out = out.astype(object).where(pd.notnull(out), None)
    records = out.to_dict(orient="records")
    return [json_safe(row) for row in records]
