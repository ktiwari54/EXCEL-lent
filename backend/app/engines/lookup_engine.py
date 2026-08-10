from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.json_safe import json_safe


class LookupEngine:
    """Match / lookup without exposing VLOOKUP/XLOOKUP to users."""

    def run(
        self,
        df: pd.DataFrame,
        normalized: dict[str, Any],
        secondary: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        mode = normalized.get("mode") or "lookup_value"
        col = normalized.get("lookup_column")
        if not col or col not in df.columns:
            return {"engine": "lookup", "ok": False, "error": "Match field is required."}

        if mode == "lookup_value" and normalized.get("lookup_value"):
            val = str(normalized["lookup_value"]).strip().lower()
            mask = df[col].astype(str).str.strip().str.lower() == val
            hits = df.loc[mask]
            ret = normalized.get("return_column")
            first = None
            if ret and ret in hits.columns and len(hits):
                first = hits.iloc[0][ret]
            return json_safe(
                {
                    "engine": "lookup",
                    "ok": True,
                    "summary": f"{len(hits)} match(es) for {col} = {normalized['lookup_value']}",
                    "metric_value": float(first) if isinstance(first, (int, float)) else None,
                    "table": hits.head(100).where(pd.notnull(hits), None).to_dict(orient="records"),
                }
            )

        if secondary is not None and not secondary.empty:
            # try same column name on secondary
            right_on = col if col in secondary.columns else None
            if not right_on:
                for c in secondary.columns:
                    if "id" in str(c).lower():
                        right_on = c
                        break
            if not right_on:
                return {"engine": "lookup", "ok": False, "error": "No common match field on second dataset."}
            merged = df.merge(secondary, left_on=col, right_on=right_on, how="outer", indicator=True, suffixes=("", "_right"))
            mode_out = normalized.get("output_mode") or "matching_only"
            if mode_out == "matching_only":
                merged = merged[merged["_merge"] == "both"]
            elif mode_out == "non_matching":
                merged = merged[merged["_merge"] != "both"]
            both = int((merged["_merge"] == "both").sum()) if "_merge" in merged.columns else len(merged)
            return json_safe(
                {
                    "engine": "lookup",
                    "ok": True,
                    "summary": f"Reconciliation complete. Matched rows in view: {len(merged)} (both-side matches tracked).",
                    "table": merged.drop(columns=["_merge"], errors="ignore").head(200).where(pd.notnull(merged), None).to_dict(orient="records"),
                    "meta": {"matched_indicator_available": True, "rows": len(merged)},
                }
            )

        # duplicates via keys
        keys = normalized.get("duplicate_keys") or [col]
        keys = [k for k in keys if k in df.columns]
        if not keys:
            keys = [col]
        dups = df[df.duplicated(subset=keys, keep=False)]
        return json_safe(
            {
                "engine": "lookup",
                "ok": True,
                "summary": f"{len(dups)} rows involved in duplicate key groups on {keys}.",
                "table": dups.head(200).where(pd.notnull(dups), None).to_dict(orient="records"),
            }
        )
