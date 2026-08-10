from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import pandas as pd

from app.modules.json_safe import json_safe


@dataclass
class MeasureDef:
    id: str
    name: str
    source_field: str | None = None  # column name if direct
    formula: str | None = None  # expression using other measure ids or columns
    aggregation: str = "sum"
    format: str = "number"  # currency | percent | number | integer
    definition: str = ""
    dependencies: list[str] = field(default_factory=list)
    roles_needed: list[str] = field(default_factory=list)


# Business measure library — resolved against semantic columns when possible
MEASURE_LIBRARY: list[MeasureDef] = [
    MeasureDef("revenue", "Revenue", aggregation="sum", format="currency", definition="Total sales revenue", roles_needed=["measure"]),
    MeasureDef("cost", "Cost", aggregation="sum", format="currency", definition="Total cost / COGS", roles_needed=["measure"]),
    MeasureDef("quantity", "Quantity", aggregation="sum", format="integer", definition="Units sold or stocked", roles_needed=["measure"]),
    MeasureDef("profit", "Profit", formula="revenue - cost", format="currency", definition="Revenue minus cost", dependencies=["revenue", "cost"]),
    MeasureDef("profit_margin", "Profit Margin", formula="profit / revenue", format="percent", definition="Profit as a share of revenue", dependencies=["profit", "revenue"]),
    MeasureDef("aov", "Average Order Value", formula="revenue / orders", format="currency", definition="Revenue per order", dependencies=["revenue", "orders"]),
    MeasureDef("orders", "Orders", aggregation="count", format="integer", definition="Number of order records"),
    MeasureDef("discount_pct", "Discount %", formula="discount / revenue", format="percent", definition="Discount as share of revenue", dependencies=["discount", "revenue"]),
]


class MeasureEngine:
    """Resolve and compute reusable business measures from semantic columns."""

    FIELD_ALIASES = {
        "revenue": ["revenue", "sales", "sales amount", "amount", "total", "net sales", "gross sales"],
        "cost": ["cost", "cogs", "cost of goods", "unit cost", "total cost"],
        "quantity": ["quantity", "qty", "units", "unit", "stock", "on hand"],
        "discount": ["discount", "discount amount", "markdown"],
        "orders": ["order", "orderid", "order id", "order_id"],
        "price": ["price", "unit price", "selling price", "asp"],
    }

    def resolve_sources(self, df: pd.DataFrame, semantic: dict[str, Any]) -> dict[str, str]:
        """Map measure ids → actual column names in the dataset."""
        cols = {str(c).lower(): str(c) for c in df.columns}
        names_from_sem = {
            m["name"].lower(): m["name"] for m in (semantic.get("measures") or [])
        }
        resolved: dict[str, str] = {}
        for mid, aliases in self.FIELD_ALIASES.items():
            for a in aliases:
                if a in cols:
                    resolved[mid] = cols[a]
                    break
                if a in names_from_sem:
                    resolved[mid] = names_from_sem[a]
                    break
        # any leftover numeric measures not mapped
        for m in semantic.get("measures") or []:
            n = m["name"]
            key = n.lower().replace(" ", "_")
            if key not in resolved and n in df.columns:
                resolved[key] = n
        return resolved

    def catalog(self, df: pd.DataFrame, semantic: dict[str, Any]) -> list[dict[str, Any]]:
        sources = self.resolve_sources(df, semantic)
        out = []
        for m in MEASURE_LIBRARY:
            src = sources.get(m.id) or m.source_field
            colset = set(str(c) for c in df.columns)
            available = False
            if m.formula:
                deps_ok = all(d in sources or d in colset for d in m.dependencies) if m.dependencies else False
                available = deps_ok or bool(src and src in colset)
            else:
                available = bool(src and src in colset) or m.id == "orders"
            resolved = src if src and src in colset else sources.get(m.id)
            out.append({**asdict(m), "resolved_source": resolved, "available": available})
        # also expose raw measures as catalog entries
        for m in semantic.get("measures") or []:
            if not any(x.get("resolved_source") == m["name"] for x in out):
                out.append(
                    {
                        "id": m["name"].lower().replace(" ", "_"),
                        "name": m["name"],
                        "source_field": m["name"],
                        "resolved_source": m["name"],
                        "aggregation": "sum",
                        "format": "currency" if m.get("data_type") == "currency" else "number",
                        "definition": f"Direct field {m['name']}",
                        "dependencies": [],
                        "available": True,
                    }
                )
        return out

    def series(self, df: pd.DataFrame, semantic: dict[str, Any], measure_id_or_col: str) -> pd.Series:
        """Return a numeric series for a measure id or column name."""
        sources = self.resolve_sources(df, semantic)
        mid = measure_id_or_col.lower().replace(" ", "_")

        # direct column
        if measure_id_or_col in df.columns:
            return pd.to_numeric(df[measure_id_or_col], errors="coerce")

        # library formulas
        if mid == "profit" and "revenue" in sources and "cost" in sources:
            return pd.to_numeric(df[sources["revenue"]], errors="coerce") - pd.to_numeric(
                df[sources["cost"]], errors="coerce"
            )
        if mid == "profit_margin" and "revenue" in sources and "cost" in sources:
            rev = pd.to_numeric(df[sources["revenue"]], errors="coerce")
            cost = pd.to_numeric(df[sources["cost"]], errors="coerce")
            profit = rev - cost
            return profit / rev.replace(0, pd.NA)
        if mid == "aov" and "revenue" in sources:
            rev = pd.to_numeric(df[sources["revenue"]], errors="coerce")
            # per-row AOV not meaningful; return revenue for aggregation path
            return rev
        if mid in sources:
            return pd.to_numeric(df[sources[mid]], errors="coerce")

        # fallback first measure
        for m in semantic.get("measures") or []:
            if m["name"] in df.columns:
                return pd.to_numeric(df[m["name"]], errors="coerce")
        return pd.Series([pd.NA] * len(df))

    def aggregate(
        self,
        df: pd.DataFrame,
        semantic: dict[str, Any],
        measure: str,
        aggregation: str = "sum",
        group_by: list[str] | None = None,
    ) -> dict[str, Any]:
        work = df.copy()
        work["_m"] = self.series(df, semantic, measure)
        agg = (aggregation or "sum").lower()
        group_by = group_by or []

        def _agg(s: pd.Series) -> float:
            s = s.dropna()
            if s.empty:
                return 0.0
            if agg in ("average", "avg", "mean"):
                return float(s.mean())
            if agg == "count":
                return float(len(s))
            if agg == "min":
                return float(s.min())
            if agg == "max":
                return float(s.max())
            if agg == "median":
                return float(s.median())
            if agg in ("distinct", "distinct_count", "nunique"):
                return float(s.nunique())
            return float(s.sum())

        if group_by:
            gcols = [g for g in group_by if g in work.columns]
            if not gcols:
                return {"ok": False, "error": "Group-by columns not found."}
            rows = []
            for keys, part in work.groupby(gcols, dropna=False):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                row = {gcols[i]: keys[i] for i in range(len(gcols))}
                row[agg] = _agg(part["_m"])
                rows.append(row)
            tdf = pd.DataFrame(rows)
            return json_safe({"ok": True, "table": tdf.to_dict(orient="records"), "metric_value": float(tdf[agg].sum()) if len(tdf) else 0})

        val = _agg(work["_m"])
        return json_safe(
            {
                "ok": True,
                "metric_value": val,
                "table": [{"measure": measure, "aggregation": agg, "value": val}],
            }
        )
