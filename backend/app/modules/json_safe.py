from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import math

import numpy as np
import pandas as pd


def json_safe(obj: Any) -> Any:
    """Recursively convert values to JSON-serializable forms (no NaN/Inf)."""
    if obj is None:
        return None

    # numpy / pandas scalars
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [json_safe(x) for x in obj.tolist()]

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, (datetime, date, pd.Timestamp)):
        try:
            if pd.isna(obj):
                return None
        except Exception:
            pass
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    if isinstance(obj, Decimal):
        try:
            f = float(obj)
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except Exception:
            return str(obj)

    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [json_safe(v) for v in obj]

    # pandas NA
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass

    if isinstance(obj, (str, int, bool)):
        return obj

    # fallback
    try:
        if hasattr(obj, "item"):
            return json_safe(obj.item())
    except Exception:
        pass

    return str(obj)
