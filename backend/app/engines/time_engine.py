from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.json_safe import json_safe


class TimeEngine:
    """Period grain, trends, MoM-style growth series."""

    def run(self, df: pd.DataFrame, normalized: dict[str, Any]) -> dict[str, Any]:
        date_field = normalized.get("date_field")
        measure = normalized.get("measure")
        grain = (normalized.get("date_grain") or "month").lower()

        if not date_field or date_field not in df.columns:
            return {"engine": "time", "ok": False, "error": "Date field required."}
        if not measure or measure not in df.columns:
            return {"engine": "time", "ok": False, "error": "Measure required."}

        work = df.copy()
        work["_dt"] = pd.to_datetime(work[date_field], errors="coerce")
        work["_m"] = pd.to_numeric(work[measure], errors="coerce")
        work = work.dropna(subset=["_dt"])

        if grain == "day":
            work["_p"] = work["_dt"].dt.date.astype(str)
        elif grain == "week":
            work["_p"] = work["_dt"].dt.to_period("W").astype(str)
        elif grain == "quarter":
            work["_p"] = work["_dt"].dt.to_period("Q").astype(str)
        elif grain == "year":
            work["_p"] = work["_dt"].dt.year.astype(str)
        else:
            work["_p"] = work["_dt"].dt.to_period("M").astype(str)

        series = work.groupby("_p")["_m"].sum().sort_index()
        tdf = series.reset_index()
        tdf.columns = ["Period", measure]
        tdf["prev"] = tdf[measure].shift(1)
        tdf["growth_pct"] = ((tdf[measure] - tdf["prev"]) / tdf["prev"].abs() * 100).round(2)
        latest = None
        if len(tdf) >= 2 and pd.notna(tdf["growth_pct"].iloc[-1]):
            latest = float(tdf["growth_pct"].iloc[-1])

        return json_safe(
            {
                "engine": "time",
                "ok": True,
                "metric_value": latest,
                "summary": f"{grain.title()} trend of {measure}"
                + (f" · latest change {latest:+.1f}%" if latest is not None else ""),
                "table": tdf.drop(columns=["prev"], errors="ignore").to_dict(orient="records"),
                "chart": {
                    "type": "line",
                    "labels": tdf["Period"].astype(str).tolist(),
                    "values": [float(x) for x in tdf[measure].tolist()],
                    "label": measure,
                },
            }
        )
