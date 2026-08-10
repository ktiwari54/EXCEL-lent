from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.excel_io import table_to_records


def enrich_date_columns(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    if date_column not in df.columns:
        raise ValueError(f"Date column '{date_column}' not found.")

    out = df.copy()
    dt = pd.to_datetime(out[date_column], errors="coerce")
    out[f"{date_column}_Day"] = dt.dt.day
    out[f"{date_column}_Week"] = dt.dt.isocalendar().week.astype("Int64")
    out[f"{date_column}_Month"] = dt.dt.month
    out[f"{date_column}_MonthName"] = dt.dt.month_name()
    out[f"{date_column}_Quarter"] = dt.dt.quarter
    out[f"{date_column}_Year"] = dt.dt.year
    # Financial year: April start (common in many regions including UAE/India style FY)
    out[f"{date_column}_FY"] = dt.apply(
        lambda x: int(x.year + 1) if pd.notna(x) and x.month >= 4 else (int(x.year) if pd.notna(x) else pd.NA)
    )
    out[f"{date_column}_Period"] = dt.dt.to_period("M").astype(str)
    return out


def period_growth(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
    freq: str = "M",
) -> dict[str, Any]:
    if date_column not in df.columns or value_column not in df.columns:
        raise ValueError("Date or value column not found.")

    work = df.copy()
    work["_dt"] = pd.to_datetime(work[date_column], errors="coerce")
    work["_v"] = pd.to_numeric(work[value_column], errors="coerce")
    work = work.dropna(subset=["_dt"])
    work["_period"] = work["_dt"].dt.to_period(freq).astype(str)
    series = work.groupby("_period")["_v"].sum().sort_index()
    tdf = series.reset_index()
    tdf.columns = ["Period", value_column]
    tdf["prev"] = tdf[value_column].shift(1)
    tdf["growth_pct"] = ((tdf[value_column] - tdf["prev"]) / tdf["prev"].abs() * 100).round(2)

    latest_growth = None
    if len(tdf) >= 2 and pd.notna(tdf["growth_pct"].iloc[-1]):
        latest_growth = float(tdf["growth_pct"].iloc[-1])

    label = "Month-over-month" if freq == "M" else "Period-over-period"
    return {
        "title": f"{label} growth — {value_column}",
        "summary": (
            f"Latest growth: {latest_growth:+.1f}%"
            if latest_growth is not None
            else "Not enough periods for growth."
        ),
        "metric_value": latest_growth,
        "table": table_to_records(tdf.drop(columns=["prev"], errors="ignore")),
        "chart": {
            "type": "line",
            "labels": tdf["Period"].tolist(),
            "values": [float(x) for x in tdf[value_column].tolist()],
            "label": value_column,
        },
        "insights": [
            f"{label} series over {len(tdf)} period(s).",
            *(
                [f"Most recent change: {latest_growth:+.1f}%."]
                if latest_growth is not None
                else []
            ),
        ],
        "meta": {"freq": freq, "periods": len(tdf)},
    }


def ytd_total(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
    as_of: str | None = None,
) -> dict[str, Any]:
    work = df.copy()
    work["_dt"] = pd.to_datetime(work[date_column], errors="coerce")
    work["_v"] = pd.to_numeric(work[value_column], errors="coerce")
    work = work.dropna(subset=["_dt"])
    if work.empty:
        return {
            "title": f"YTD {value_column}",
            "summary": "No valid dates.",
            "metric_value": 0,
            "table": [],
        }

    ref = pd.to_datetime(as_of) if as_of else work["_dt"].max()
    year = ref.year
    mask = (work["_dt"].dt.year == year) & (work["_dt"] <= ref)
    total = float(work.loc[mask, "_v"].sum())
    return {
        "title": f"YTD {value_column} ({year})",
        "summary": f"Year-to-date total as of {ref.date()}: {total:,.2f}",
        "metric_value": total,
        "table": [{"year": year, "as_of": str(ref.date()), "ytd_total": total}],
        "insights": [f"YTD {value_column} for {year} = {total:,.2f}"],
        "meta": {"year": year, "as_of": str(ref.date())},
    }
