from __future__ import annotations

from typing import Any

# Manager-friendly one-click templates. Each maps to a task_id + optional config overrides.
ONE_CLICK_PRESETS: list[dict[str, Any]] = [
    {
        "id": "one_click_dashboard",
        "name": "One-Click Dashboard",
        "description": "KPIs, trends, and top segments in one view — no setup.",
        "audience": "Managers",
        "task_id": "dashboard",
        "icon": "monitor",
        "color": "bg-teal-600",
        "one_click": True,
    },
    {
        "id": "one_click_report",
        "name": "One-Click Report",
        "description": "Executive-style summary with key findings and metrics.",
        "audience": "Managers",
        "task_id": "reports",
        "icon": "file",
        "color": "bg-indigo-600",
        "one_click": True,
    },
    {
        "id": "one_click_analyze",
        "name": "Analyze Everything",
        "description": "Full analyst pass: KPIs, rankings, outliers, and recommendations.",
        "audience": "Analysts & Managers",
        "task_id": "analyze",
        "icon": "sparkles",
        "color": "bg-blue-600",
        "one_click": True,
    },
    {
        "id": "sales_performance",
        "name": "Sales Performance",
        "description": "Revenue dashboard with products, regions, and growth.",
        "audience": "Sales leaders",
        "task_id": "sales_dashboard",
        "icon": "monitor",
        "color": "bg-emerald-600",
        "one_click": True,
    },
    {
        "id": "top_products",
        "name": "Top Products / Segments",
        "description": "Ranked top performers with contribution.",
        "audience": "Analysts",
        "task_id": "top_n",
        "icon": "clipboard",
        "color": "bg-amber-500",
        "one_click": True,
        "config_overrides": {"limit": "10", "sort_direction": "desc", "aggregation": "sum"},
    },
    {
        "id": "monthly_trend",
        "name": "Monthly Trend",
        "description": "Month-by-month movement of your main metric.",
        "audience": "Managers",
        "task_id": "monthly_trend",
        "icon": "chart",
        "color": "bg-sky-500",
        "one_click": True,
        "config_overrides": {"date_grain": "month", "date_range": "all"},
    },
    {
        "id": "summarize_category",
        "name": "Category Summary",
        "description": "Totals by product, region, or category — auto-detected.",
        "audience": "Analysts",
        "task_id": "summarize",
        "icon": "clipboard",
        "color": "bg-orange-500",
        "one_click": True,
        "config_overrides": {"aggregation": "sum", "limit": "20", "sort_direction": "desc"},
    },
    {
        "id": "data_health_check",
        "name": "Data Health Check",
        "description": "Find duplicates and quality issues before you present numbers.",
        "audience": "Analysts",
        "task_id": "clean",
        "icon": "wand",
        "color": "bg-teal-500",
        "one_click": True,
        "config_overrides": {"actions": ["find_duplicates", "trim_spaces", "fill_blanks"]},
    },
]


def list_presets() -> list[dict[str, Any]]:
    return list(ONE_CLICK_PRESETS)


def get_preset(preset_id: str) -> dict[str, Any] | None:
    return next((p for p in ONE_CLICK_PRESETS if p["id"] == preset_id), None)
