from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from app.models.schemas import ColumnProfile, DatasetProfile
from app.services.excel_io import table_to_records


ID_PATTERN = re.compile(r"(^id$|_id$|sku|code|uuid|customer.?id|order.?id|emp)", re.I)
DATE_HINT = re.compile(r"(date|time|day|month|year|period)", re.I)
MONEY_HINT = re.compile(r"(amount|revenue|sales|price|cost|profit|margin|total|value|fee)", re.I)


def _infer_type(series: pd.Series, name: str) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        if ID_PATTERN.search(name):
            return "id"
        if MONEY_HINT.search(name):
            return "currency"
        return "number"
    # try parse dates
    if DATE_HINT.search(name) or _looks_like_dates(series):
        return "datetime"
    nunique = series.nunique(dropna=True)
    if nunique <= max(20, int(len(series) * 0.05)):
        return "category"
    if ID_PATTERN.search(name):
        return "id"
    return "text"


def _looks_like_dates(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(20)
    if sample.empty:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", utc=False)
    return parsed.notna().mean() > 0.7


def profile_dataframe(
    df: pd.DataFrame,
    session_id: str,
    filename: str,
    sheet_names: list[str] | None = None,
    active_sheet: str | None = None,
) -> DatasetProfile:
    profiles: list[ColumnProfile] = []
    missing_cells = int(df.isna().sum().sum())
    dupes = int(df.duplicated().sum())

    for col in df.columns:
        s = df[col]
        inferred = _infer_type(s, str(col))
        non_null = int(s.notna().sum())
        null_count = int(s.isna().sum())
        unique = int(s.nunique(dropna=True))
        samples = s.dropna().head(5).tolist()
        samples = [x.item() if hasattr(x, "item") else (x.isoformat() if hasattr(x, "isoformat") else x) for x in samples]

        is_numeric = pd.api.types.is_numeric_dtype(s) and inferred not in ("id",)
        is_dt = inferred == "datetime" or pd.api.types.is_datetime64_any_dtype(s)
        is_cat = inferred == "category"
        is_id = inferred == "id"

        mn = mx = mean = None
        if is_numeric:
            mn = float(s.min()) if non_null else None
            mx = float(s.max()) if non_null else None
            mean = float(s.mean()) if non_null else None
        elif is_dt:
            sdt = pd.to_datetime(s, errors="coerce")
            if sdt.notna().any():
                mn = sdt.min().isoformat()
                mx = sdt.max().isoformat()

        profiles.append(
            ColumnProfile(
                name=str(col),
                dtype=str(s.dtype),
                inferred_type=inferred,
                non_null=non_null,
                null_count=null_count,
                null_pct=round(100 * null_count / max(len(df), 1), 2),
                unique_count=unique,
                sample_values=samples,
                is_numeric=bool(is_numeric),
                is_datetime=bool(is_dt),
                is_categorical=bool(is_cat),
                is_id_like=bool(is_id),
                min=mn,
                max=mx,
                mean=mean,
            )
        )

    return DatasetProfile(
        session_id=session_id,
        filename=filename,
        rows=int(len(df)),
        columns=int(len(df.columns)),
        column_profiles=profiles,
        duplicate_rows=dupes,
        missing_cells=missing_cells,
        sheet_names=sheet_names or [],
        active_sheet=active_sheet,
        preview=table_to_records(df, limit=25),
    )


def suggest_columns(profile: DatasetProfile) -> dict[str, str | None]:
    """Heuristic column role suggestions for dashboards."""
    nums = [c for c in profile.column_profiles if c.is_numeric]
    cats = [c for c in profile.column_profiles if c.is_categorical or c.inferred_type == "text"]
    dates = [c for c in profile.column_profiles if c.is_datetime]
    money = [c for c in profile.column_profiles if c.inferred_type == "currency"] or nums

    def pick(cands: list[ColumnProfile], *keywords: str) -> str | None:
        for kw in keywords:
            for c in cands:
                if kw in c.name.lower():
                    return c.name
        return cands[0].name if cands else None

    return {
        "value_column": pick(money, "revenue", "sales", "amount", "total", "price"),
        "date_column": pick(dates, "date", "order", "period"),
        "category_column": pick(cats, "product", "category", "region", "country", "segment"),
        "product_column": pick(cats, "product", "sku", "item"),
        "region_column": pick(cats, "region", "country", "city", "location", "market"),
    }
