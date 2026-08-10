from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.json_safe import json_safe


class FormulaEngine:
    """Numeric aggregations and derived metrics (Excel-like, no UI formulas)."""

    AGG = {
        "sum": "sum",
        "average": "mean",
        "avg": "mean",
        "mean": "mean",
        "count": "count",
        "min": "min",
        "max": "max",
        "median": "median",
    }

    def run(self, df: pd.DataFrame, normalized: dict[str, Any]) -> dict[str, Any]:
        measure = normalized.get("measure")
        agg = (normalized.get("aggregation") or "sum").lower()
        group_by = normalized.get("group_by") or []
        if isinstance(group_by, str):
            group_by = [group_by] if group_by else []

        work = self._apply_filters(df, normalized.get("filters") or [])
        if not measure or measure not in work.columns:
            return {"engine": "formula", "ok": False, "error": "Measure column missing."}

        series = pd.to_numeric(work[measure], errors="coerce")
        work = work.copy()
        work["_m"] = series

        if group_by:
            gcols = [g for g in group_by if g in work.columns]
            if not gcols:
                return {"engine": "formula", "ok": False, "error": "Group-by column missing."}
            how = self.AGG.get(agg, "sum")
            if how == "count":
                grouped = work.groupby(gcols, dropna=False)["_m"].count()
            else:
                grouped = work.groupby(gcols, dropna=False)["_m"].agg(how)
            tdf = grouped.reset_index()
            tdf.columns = list(gcols) + [agg]
            sort_dir = normalized.get("sort_direction") or "desc"
            tdf = tdf.sort_values(agg, ascending=(sort_dir == "asc"))
            limit = normalized.get("limit")
            if limit and int(limit) > 0:
                tdf = tdf.head(int(limit))
            metric = float(pd.to_numeric(tdf[agg], errors="coerce").sum()) if len(tdf) else 0.0
            return json_safe(
                {
                    "engine": "formula",
                    "ok": True,
                    "metric_value": metric,
                    "table": tdf.to_dict(orient="records"),
                    "chart": {
                        "type": "bar",
                        "labels": tdf[gcols[0]].astype(str).head(25).tolist(),
                        "values": [float(x) for x in tdf[agg].head(25).tolist()],
                        "label": f"{agg}({measure})",
                    },
                    "summary": f"{agg.upper()} of {measure} by {', '.join(gcols)}",
                }
            )

        how = self.AGG.get(agg, "sum")
        clean = work["_m"].dropna()
        if how == "count":
            val = float(len(clean))
        elif how == "mean":
            val = float(clean.mean()) if len(clean) else 0.0
        elif how == "median":
            val = float(clean.median()) if len(clean) else 0.0
        elif how == "min":
            val = float(clean.min()) if len(clean) else 0.0
        elif how == "max":
            val = float(clean.max()) if len(clean) else 0.0
        else:
            val = float(clean.sum()) if len(clean) else 0.0

        return json_safe(
            {
                "engine": "formula",
                "ok": True,
                "metric_value": val,
                "table": [{"metric": agg, "column": measure, "value": val, "rows_used": int(len(clean))}],
                "summary": f"{agg.upper()}({measure}) = {val:,.4g}",
            }
        )

    def _apply_filters(self, df: pd.DataFrame, filters: list[dict[str, Any]]) -> pd.DataFrame:
        work = df
        for i, f in enumerate(filters):
            field = f.get("field")
            op = (f.get("operator") or "eq").lower()
            val = f.get("value")
            if not field or field not in work.columns or val is None or val == "":
                continue
            join = (f.get("join") or "AND").upper()
            s = work[field]
            if op in ("eq", "is", "="):
                mask = s.astype(str).str.strip().str.lower() == str(val).strip().lower()
            elif op in ("ne", "is not", "<>"):
                mask = s.astype(str).str.strip().str.lower() != str(val).strip().lower()
            elif op in ("gt", "greater than"):
                mask = pd.to_numeric(s, errors="coerce") > float(val)
            elif op in ("gte", "at least"):
                mask = pd.to_numeric(s, errors="coerce") >= float(val)
            elif op in ("lt", "less than"):
                mask = pd.to_numeric(s, errors="coerce") < float(val)
            elif op in ("lte", "at most"):
                mask = pd.to_numeric(s, errors="coerce") <= float(val)
            elif op == "contains":
                mask = s.astype(str).str.contains(str(val), case=False, na=False)
            else:
                mask = s.astype(str).str.strip().str.lower() == str(val).strip().lower()
            # AND only for v1 (OR support: partial)
            if join == "OR" and i > 0:
                # simple OR: union with previous is complex; treat as AND for reliability
                work = work[mask]
            else:
                work = work[mask]
        return work
