from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engines.profiling import profile_dataframe, suggest_columns
from app.services.excel_io import table_to_records


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _category_cols(df: pd.DataFrame, max_unique: int = 50) -> list[str]:
    out = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        if df[c].nunique(dropna=True) <= max_unique:
            out.append(c)
    return out


def find_problems(df: pd.DataFrame, column: str | None = None, n: int = 10) -> dict[str, Any]:
    alerts: list[str] = []
    tables: dict[str, Any] = {}

    dups = df[df.duplicated(keep=False)]
    if len(dups):
        alerts.append(f"{df.duplicated().sum()} duplicate row(s) detected.")
        tables["duplicates"] = table_to_records(dups.head(n))

    missing_summary = []
    for col in df.columns:
        nulls = int(df[col].isna().sum())
        if nulls:
            pct = 100 * nulls / max(len(df), 1)
            alerts.append(f"Alert: {pct:.1f}% of '{col}' values are missing ({nulls} cells).")
            missing_summary.append({"column": col, "missing": nulls, "pct": round(pct, 2)})
    if missing_summary:
        tables["missing"] = missing_summary

    # Outliers on numeric column
    target = column
    nums = _numeric_cols(df)
    if target is None and nums:
        target = nums[0]
    if target and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
        s = pd.to_numeric(df[target], errors="coerce")
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if pd.notna(iqr) and iqr > 0:
            mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
            out_df = df.loc[mask]
            if len(out_df):
                alerts.append(f"Alert: {len(out_df)} outlier row(s) in '{target}' (IQR method).")
                tables["outliers"] = table_to_records(out_df.head(n))

    return {
        "title": "Data problems detected",
        "summary": f"{len(alerts)} issue(s) found." if alerts else "No major issues detected.",
        "alerts": alerts,
        "table": tables.get("missing") or tables.get("duplicates") or [],
        "meta": {"tables": {k: v for k, v in tables.items()}},
        "insights": alerts,
    }


def top_bottom(
    df: pd.DataFrame,
    column: str,
    n: int = 10,
    ascending: bool = False,
    label_column: str | None = None,
) -> dict[str, Any]:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
    work = df.copy()
    work["_v"] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=["_v"]).sort_values("_v", ascending=ascending).head(n)
    title = f"{'Bottom' if ascending else 'Top'} {n} by {column}"
    return {
        "title": title,
        "summary": title,
        "table": table_to_records(work.drop(columns=["_v"], errors="ignore")),
        "chart": {
            "type": "bar",
            "labels": (
                work[label_column].astype(str).tolist()
                if label_column and label_column in work.columns
                else [str(i) for i in range(len(work))]
            ),
            "values": [float(x) for x in work["_v"].tolist()],
            "label": column,
        },
        "meta": {"n": n, "ascending": ascending},
    }


def analyze_dataset(
    df: pd.DataFrame,
    session_id: str,
    filename: str = "dataset",
    date_column: str | None = None,
    value_column: str | None = None,
    category_column: str | None = None,
) -> dict[str, Any]:
    profile = profile_dataframe(df, session_id, filename)
    suggestions = suggest_columns(profile)
    value_column = value_column or suggestions.get("value_column")
    date_column = date_column or suggestions.get("date_column")
    category_column = category_column or suggestions.get("category_column")

    insights: list[str] = []
    alerts: list[str] = []
    recommendations: list[str] = []
    kpis: dict[str, Any] = {
        "rows": profile.rows,
        "columns": profile.columns,
        "duplicate_rows": profile.duplicate_rows,
        "missing_cells": profile.missing_cells,
    }

    insights.append(f"Dataset has {profile.rows:,} rows and {profile.columns} columns.")
    if profile.duplicate_rows:
        alerts.append(f"Alert: {profile.duplicate_rows} duplicate records detected.")
        recommendations.append("Run Clean Data → Remove duplicates before analysis.")
    if profile.missing_cells:
        pct = 100 * profile.missing_cells / max(profile.rows * profile.columns, 1)
        alerts.append(f"Alert: {profile.missing_cells:,} missing cells ({pct:.1f}% of all cells).")

    tables: list[dict[str, Any]] = []
    chart = None

    if value_column and value_column in df.columns:
        s = pd.to_numeric(df[value_column], errors="coerce").dropna()
        if len(s):
            kpis.update(
                {
                    "total": float(s.sum()),
                    "average": float(s.mean()),
                    "median": float(s.median()),
                    "min": float(s.min()),
                    "max": float(s.max()),
                }
            )
            insights.append(
                f"Key metric '{value_column}': total={s.sum():,.2f}, avg={s.mean():,.2f}, "
                f"min={s.min():,.2f}, max={s.max():,.2f}."
            )

    if category_column and value_column and category_column in df.columns and value_column in df.columns:
        work = df.copy()
        work["_v"] = pd.to_numeric(work[value_column], errors="coerce")
        top = work.groupby(work[category_column].astype(str))["_v"].sum().sort_values(ascending=False)
        if len(top):
            top_name, top_val = top.index[0], float(top.iloc[0])
            share = 100 * top_val / top.sum() if top.sum() else 0
            insights.append(
                f"Top performer in '{category_column}' is '{top_name}' "
                f"with {top_val:,.2f} ({share:.1f}% of total {value_column})."
            )
            if share > 30:
                recommendations.append(
                    f"'{top_name}' contributes {share:.0f}% of {value_column} — "
                    "consider concentration risk and growth diversification."
                )
            tdf = top.head(10).reset_index()
            tdf.columns = [category_column, value_column]
            tables = table_to_records(tdf)
            chart = {
                "type": "bar",
                "labels": tdf[category_column].astype(str).tolist(),
                "values": [float(x) for x in tdf[value_column].tolist()],
                "label": value_column,
            }

            # Decline detection if date available
            if date_column and date_column in df.columns:
                try:
                    tmp = work.copy()
                    tmp["_dt"] = pd.to_datetime(tmp[date_column], errors="coerce")
                    tmp = tmp.dropna(subset=["_dt"])
                    tmp["_period"] = tmp["_dt"].dt.to_period("M").astype(str)
                    monthly = tmp.groupby(["_period", category_column])["_v"].sum().reset_index()
                    # check top item mom decline
                    sub = monthly[monthly[category_column].astype(str) == str(top_name)].sort_values("_period")
                    if len(sub) >= 2:
                        prev, curr = float(sub["_v"].iloc[-2]), float(sub["_v"].iloc[-1])
                        if prev and curr < prev:
                            drop = 100 * (curr - prev) / abs(prev)
                            alerts.append(
                                f"Alert: '{top_name}' {value_column} changed {drop:+.1f}% "
                                f"vs previous month."
                            )
                except Exception:
                    pass

    # Numeric key metrics table
    key_metrics = []
    for col in _numeric_cols(df)[:8]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s):
            key_metrics.append(
                {
                    "column": col,
                    "total": float(s.sum()),
                    "average": float(s.mean()),
                    "median": float(s.median()),
                    "min": float(s.min()),
                    "max": float(s.max()),
                }
            )

    if not recommendations:
        recommendations.append("Create a Sales or Custom dashboard for a one-click visual overview.")
        recommendations.append("Use Ask the Data for natural-language questions (e.g. 'top 10 products').")

    return {
        "title": "Data Analyst Mode — Automatic Analysis",
        "summary": (
            f"Analyzed {profile.rows:,} rows. "
            f"{len(alerts)} alert(s), {len(insights)} insight(s)."
        ),
        "insights": insights,
        "alerts": alerts,
        "recommendations": recommendations,
        "table": tables or key_metrics,
        "chart": chart,
        "meta": {
            "kpis": kpis,
            "suggested_columns": suggestions,
            "key_metrics": key_metrics,
            "profile": profile.model_dump(),
        },
        "metric_value": kpis.get("total"),
    }


def build_dashboard(
    df: pd.DataFrame,
    dashboard_type: str = "sales",
    date_column: str | None = None,
    value_column: str | None = None,
    category_column: str | None = None,
    product_column: str | None = None,
    region_column: str | None = None,
) -> dict[str, Any]:
    profile = profile_dataframe(df, "tmp", "tmp")
    sug = suggest_columns(profile)
    value_column = value_column or sug.get("value_column")
    date_column = date_column or sug.get("date_column")
    category_column = category_column or sug.get("category_column")
    product_column = product_column or sug.get("product_column") or category_column
    region_column = region_column or sug.get("region_column")

    kpis: dict[str, Any] = {}
    charts: list[dict[str, Any]] = []
    insights: list[str] = []

    if value_column and value_column in df.columns:
        s = pd.to_numeric(df[value_column], errors="coerce")
        kpis["Revenue" if dashboard_type == "sales" else "Total"] = float(s.sum())
        kpis["Average"] = float(s.mean()) if s.notna().any() else 0
        kpis["Records"] = int(len(df))
        if "order" in " ".join(str(c).lower() for c in df.columns) or dashboard_type == "sales":
            kpis["Orders"] = int(len(df))
            if s.notna().any() and len(df):
                kpis["AOV"] = float(s.sum() / len(df))

    def add_breakdown(col: str | None, title: str) -> None:
        if not col or col not in df.columns or not value_column:
            return
        work = df.copy()
        work["_v"] = pd.to_numeric(work[value_column], errors="coerce")
        series = work.groupby(work[col].astype(str))["_v"].sum().sort_values(ascending=False).head(10)
        charts.append(
            {
                "title": title,
                "type": "bar",
                "labels": series.index.tolist(),
                "values": [float(x) for x in series.tolist()],
                "label": value_column,
            }
        )
        if len(series):
            insights.append(f"{title}: leader is '{series.index[0]}' ({series.iloc[0]:,.2f}).")

    add_breakdown(product_column, "Top products")
    add_breakdown(region_column, "By region / location")
    add_breakdown(category_column, f"By {category_column}" if category_column else "By category")

    if date_column and date_column in df.columns and value_column:
        tmp = df.copy()
        tmp["_dt"] = pd.to_datetime(tmp[date_column], errors="coerce")
        tmp["_v"] = pd.to_numeric(tmp[value_column], errors="coerce")
        tmp = tmp.dropna(subset=["_dt"])
        if len(tmp):
            tmp["_period"] = tmp["_dt"].dt.to_period("M").astype(str)
            monthly = tmp.groupby("_period")["_v"].sum().sort_index()
            charts.insert(
                0,
                {
                    "title": "Monthly trend",
                    "type": "line",
                    "labels": monthly.index.tolist(),
                    "values": [float(x) for x in monthly.tolist()],
                    "label": value_column,
                },
            )
            if len(monthly) >= 2:
                prev, curr = float(monthly.iloc[-2]), float(monthly.iloc[-1])
                if prev:
                    growth = 100 * (curr - prev) / abs(prev)
                    kpis["MoM Growth %"] = round(growth, 2)
                    insights.append(f"Month-over-month change: {growth:+.1f}%.")

    title = f"{dashboard_type.title()} Dashboard"
    return {
        "title": title,
        "summary": f"Auto-built {dashboard_type} dashboard with {len(kpis)} KPIs and {len(charts)} chart(s).",
        "insights": insights,
        "meta": {
            "dashboard_type": dashboard_type,
            "kpis": kpis,
            "charts": charts,
            "columns_used": {
                "value": value_column,
                "date": date_column,
                "category": category_column,
                "product": product_column,
                "region": region_column,
            },
        },
        "chart": charts[0] if charts else None,
        "table": [{"kpi": k, "value": v} for k, v in kpis.items()],
        "metric_value": kpis.get("Revenue") or kpis.get("Total"),
    }


def build_report(
    df: pd.DataFrame,
    report_type: str = "monthly_sales",
    date_column: str | None = None,
    value_column: str | None = None,
    category_column: str | None = None,
) -> dict[str, Any]:
    analysis = analyze_dataset(
        df,
        session_id="report",
        date_column=date_column,
        value_column=value_column,
        category_column=category_column,
    )
    findings = analysis.get("insights", [])[:5]
    exec_summary = findings[0] if findings else "Analysis complete."
    if analysis.get("alerts"):
        exec_summary = analysis["alerts"][0]

    sections = {
        "executive_summary": exec_summary,
        "key_findings": findings,
        "alerts": analysis.get("alerts", []),
        "recommendations": analysis.get("recommendations", []),
    }
    return {
        "title": f"Report: {report_type.replace('_', ' ').title()}",
        "summary": exec_summary,
        "insights": findings,
        "alerts": analysis.get("alerts", []),
        "recommendations": analysis.get("recommendations", []),
        "table": analysis.get("table", []),
        "chart": analysis.get("chart"),
        "meta": {"report_type": report_type, "sections": sections, **analysis.get("meta", {})},
        "metric_value": analysis.get("metric_value"),
    }
