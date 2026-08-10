from __future__ import annotations

import re
from typing import Any

import pandas as pd

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[\d\s\-\+\(\)\.]{7,20}$")
URL_RE = re.compile(r"^https?://", re.I)
ID_HINT = re.compile(r"(^id$|_id$|uuid|sku|code|order.?id|customer.?id|emp|invoice.?no)", re.I)
DATE_HINT = re.compile(r"(date|time|day|month|year|period|dob)", re.I)
MONEY_HINT = re.compile(r"(amount|revenue|sales|price|cost|profit|margin|total|fee|salary|budget)", re.I)
PCT_HINT = re.compile(r"(pct|percent|percentage|rate|ratio)", re.I)
STATUS_HINT = re.compile(r"(status|state|stage|phase)", re.I)
QTY_HINT = re.compile(r"(qty|quantity|units|count|number of)", re.I)


def _sample(series: pd.Series, n: int = 80) -> pd.Series:
    s = series.dropna()
    if len(s) > n:
        return s.sample(n, random_state=42)
    return s


def detect_column_type(series: pd.Series, name: str) -> dict[str, Any]:
    """Infer rich type from values + column name. Returns type + confidence 0-1."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return {"data_type": "unknown", "confidence": 0.2, "excel_dtype": str(series.dtype)}

    name_l = str(name).lower()
    conf = 0.55

    # Boolean
    if pd.api.types.is_bool_dtype(series):
        return {"data_type": "boolean", "confidence": 0.95, "excel_dtype": str(series.dtype)}
    sample_str = non_null.astype(str).str.strip().str.lower()
    bool_vals = {"true", "false", "yes", "no", "y", "n", "0", "1"}
    if sample_str.isin(bool_vals).mean() > 0.95 and sample_str.nunique() <= 4:
        return {"data_type": "boolean", "confidence": 0.85, "excel_dtype": str(series.dtype)}

    # Datetime first (before phone — dates like 2025-01-05 can look phone-like)
    if pd.api.types.is_datetime64_any_dtype(series):
        return {"data_type": "datetime", "confidence": 0.95, "excel_dtype": str(series.dtype)}
    if DATE_HINT.search(name_l) or series.dtype == object:
        parsed = pd.to_datetime(_sample(non_null), errors="coerce", utc=False)
        ratio = parsed.notna().mean() if len(parsed) else 0
        # Prefer date when column name hints date, even if parse ratio is moderate
        threshold = 0.6 if DATE_HINT.search(name_l) else 0.75
        if ratio > threshold:
            has_time = False
            try:
                times = parsed.dropna().dt.time
                has_time = any(t.hour or t.minute or t.second for t in times.head(20))
            except Exception:
                pass
            return {
                "data_type": "datetime" if has_time else "date",
                "confidence": min(0.95, 0.6 + ratio * 0.35),
                "excel_dtype": str(series.dtype),
            }

    # Email / phone / url on text
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        strs = _sample(non_null).astype(str).str.strip()
        if len(strs):
            if strs.map(lambda x: bool(EMAIL_RE.match(x))).mean() > 0.7:
                return {"data_type": "email", "confidence": 0.9, "excel_dtype": str(series.dtype)}
            if strs.map(lambda x: bool(URL_RE.match(x))).mean() > 0.7:
                return {"data_type": "url", "confidence": 0.9, "excel_dtype": str(series.dtype)}
            # Phone: require digit density, reject if looks like ISO date
            def _is_phone(x: str) -> bool:
                if re.search(r"\d{4}-\d{2}-\d{2}", x):
                    return False
                digits = sum(c.isdigit() for c in x)
                return bool(PHONE_RE.match(x)) and 7 <= digits <= 15

            if strs.map(_is_phone).mean() > 0.7:
                return {"data_type": "phone", "confidence": 0.75, "excel_dtype": str(series.dtype)}

    # Numeric paths
    numeric = pd.to_numeric(
        non_null.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.replace("$", "", regex=False).str.replace("AED", "", regex=False).str.strip(),
        errors="coerce",
    )
    num_ratio = numeric.notna().mean() if len(numeric) else 0

    if pd.api.types.is_numeric_dtype(series) or num_ratio > 0.8:
        conf = 0.7 + 0.25 * num_ratio
        vals = numeric.dropna() if num_ratio > 0.5 else pd.to_numeric(non_null, errors="coerce").dropna()
        if ID_HINT.search(name_l):
            return {"data_type": "identifier", "confidence": 0.88, "excel_dtype": str(series.dtype)}
        if PCT_HINT.search(name_l) or (
            len(vals) and vals.between(0, 1).mean() > 0.9 and vals.max() <= 1
        ):
            return {"data_type": "percentage", "confidence": 0.8, "excel_dtype": str(series.dtype)}
        if MONEY_HINT.search(name_l):
            return {"data_type": "currency", "confidence": 0.9, "excel_dtype": str(series.dtype)}
        if len(vals) and (vals % 1 == 0).mean() > 0.98:
            return {"data_type": "integer", "confidence": conf, "excel_dtype": str(series.dtype)}
        return {"data_type": "decimal" if len(vals) else "number", "confidence": conf, "excel_dtype": str(series.dtype)}

    # Identifier-like text
    if ID_HINT.search(name_l):
        return {"data_type": "identifier", "confidence": 0.8, "excel_dtype": str(series.dtype)}

    # Category vs text
    nunique = non_null.nunique()
    n = len(non_null)
    unique_ratio = nunique / max(n, 1)
    if unique_ratio <= 0.15 or nunique <= max(20, int(n * 0.05)):
        return {"data_type": "category", "confidence": 0.82, "excel_dtype": str(series.dtype)}

    return {"data_type": "text", "confidence": 0.65, "excel_dtype": str(series.dtype)}
