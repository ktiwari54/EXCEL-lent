from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from app.engines.dates import period_growth
from app.engines.formula import summarize
from app.engines.insight import analyze_dataset, build_dashboard, find_problems
from app.engines.pivot import chart_data
from app.engines.profiling import profile_dataframe, suggest_columns
from app.models.schemas import MetricOp


TEMPLATE_CATALOG: dict[str, list[dict[str, str]]] = {
    "sales": [
        {"id": "sales_dashboard", "name": "Sales Dashboard", "desc": "KPIs, trend, top products & regions"},
        {"id": "salesperson_performance", "name": "Salesperson Performance", "desc": "Revenue by salesperson"},
        {"id": "product_performance", "name": "Product Performance", "desc": "Top products by revenue"},
        {"id": "customer_analysis", "name": "Customer Analysis", "desc": "Top customers & contribution"},
        {"id": "monthly_trend", "name": "Monthly Sales Trend", "desc": "Month-over-month revenue"},
    ],
    "inventory": [
        {"id": "stock_dashboard", "name": "Stock Dashboard", "desc": "Inventory overview KPIs"},
        {"id": "low_stock", "name": "Low Stock Report", "desc": "Items near bottom of stock distribution"},
        {"id": "dead_stock", "name": "Dead Stock Analysis", "desc": "Lowest movers / zero activity"},
    ],
    "finance": [
        {"id": "expense_analysis", "name": "Expense Analysis", "desc": "Spend by category"},
        {"id": "variance_analysis", "name": "Variance Analysis", "desc": "Actual vs comparison columns"},
        {"id": "pnl_summary", "name": "P&L Summary", "desc": "Revenue / cost / margin if present"},
    ],
    "hr": [
        {"id": "employee_performance", "name": "Employee Performance", "desc": "Metrics by employee"},
        {"id": "attendance_summary", "name": "Attendance Summary", "desc": "Group attendance fields"},
    ],
    "crm": [
        {"id": "lead_analysis", "name": "Lead Analysis", "desc": "Leads by status/source"},
        {"id": "pipeline_analysis", "name": "Pipeline Analysis", "desc": "Pipeline stage breakdown"},
    ],
    "ecommerce": [
        {"id": "order_analysis", "name": "Order Analysis", "desc": "Orders, AOV, trends"},
        {"id": "sku_performance", "name": "SKU Performance", "desc": "Top SKUs by revenue/units"},
        {"id": "returns_overview", "name": "Returns Overview", "desc": "Find return-related issues"},
    ],
}


def _cols(df: pd.DataFrame) -> dict[str, str | None]:
    p = profile_dataframe(df, "t", "t")
    return suggest_columns(p)


def _find(df: pd.DataFrame, *keywords: str) -> str | None:
    for kw in keywords:
        for c in df.columns:
            if kw in str(c).lower():
                return str(c)
    return None


def run_template(df: pd.DataFrame, template_id: str) -> dict[str, Any]:
    sug = _cols(df)
    value = sug.get("value_column") or _find(df, "revenue", "sales", "amount", "total")
    date = sug.get("date_column") or _find(df, "date")
    category = sug.get("category_column") or _find(df, "product", "category", "sku")
    region = sug.get("region_column") or _find(df, "region", "country", "city")
    person = _find(df, "salesperson", "employee", "rep", "agent", "owner")
    customer = _find(df, "customer", "client", "account")

    runners: dict[str, Callable[[], dict[str, Any]]] = {
        "sales_dashboard": lambda: build_dashboard(
            df, "sales", date, value, category, category, region
        ),
        "salesperson_performance": lambda: (
            summarize(df, [person], value, MetricOp.sum, 20)
            if person and value
            else analyze_dataset(df, "t", value_column=value, category_column=person)
        ),
        "product_performance": lambda: (
            chart_data(df, category, value, MetricOp.sum, 15, "bar")
            if category and value
            else analyze_dataset(df, "t")
        ),
        "customer_analysis": lambda: (
            summarize(df, [customer], value, MetricOp.sum, 20)
            if customer and value
            else analyze_dataset(df, "t", value_column=value, category_column=customer)
        ),
        "monthly_trend": lambda: (
            period_growth(df, date, value, "M")
            if date and value
            else analyze_dataset(df, "t", date_column=date, value_column=value)
        ),
        "stock_dashboard": lambda: build_dashboard(df, "inventory", date, value, category, category, region),
        "low_stock": lambda: _bottom_numeric(df, value or _first_numeric(df), 15),
        "dead_stock": lambda: _bottom_numeric(df, value or _first_numeric(df), 15, title="Dead / low activity stock"),
        "expense_analysis": lambda: (
            summarize(df, [category], value, MetricOp.sum, 20)
            if category and value
            else analyze_dataset(df, "t")
        ),
        "variance_analysis": lambda: _variance(df),
        "pnl_summary": lambda: _pnl(df),
        "employee_performance": lambda: (
            summarize(df, [person], value, MetricOp.sum, 20)
            if person and value
            else analyze_dataset(df, "t")
        ),
        "attendance_summary": lambda: analyze_dataset(
            df, "t", category_column=person or category, value_column=value
        ),
        "lead_analysis": lambda: analyze_dataset(
            df, "t", category_column=_find(df, "status", "source", "stage") or category
        ),
        "pipeline_analysis": lambda: (
            chart_data(df, _find(df, "stage", "status", "pipeline") or category or list(df.columns)[0], value or _first_numeric(df), MetricOp.sum, 20, "bar")
            if df is not None
            else analyze_dataset(df, "t")
        ),
        "order_analysis": lambda: build_dashboard(df, "sales", date, value, category, category, region),
        "sku_performance": lambda: (
            chart_data(df, _find(df, "sku", "product", "item") or category, value, MetricOp.sum, 20, "bar")
            if value
            else analyze_dataset(df, "t")
        ),
        "returns_overview": lambda: find_problems(df),
    }

    if template_id not in runners:
        raise ValueError(f"Unknown template: {template_id}")

    result = runners[template_id]()
    result["meta"] = {**(result.get("meta") or {}), "template_id": template_id}
    result["title"] = result.get("title") or template_id
    return result


def _first_numeric(df: pd.DataFrame) -> str:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            return str(c)
    return str(df.columns[0])


def _bottom_numeric(df: pd.DataFrame, column: str, n: int = 15, title: str | None = None) -> dict[str, Any]:
    from app.engines.insight import top_bottom

    label = _find(df, "product", "sku", "item", "name")
    work = df.copy()
    if label and label in work.columns and column in work.columns:
        work["_v"] = pd.to_numeric(work[column], errors="coerce")
        agg = work.groupby(work[label].astype(str))["_v"].sum().reset_index()
        agg.columns = [label, column]
        out = top_bottom(agg, column, n=n, ascending=True, label_column=label)
    else:
        out = top_bottom(df, column, n=n, ascending=True)
    if title:
        out["title"] = title
    return out


def _variance(df: pd.DataFrame) -> dict[str, Any]:
    actual = _find(df, "actual", "revenue", "sales", "amount")
    budget = _find(df, "budget", "target", "plan", "forecast")
    if actual and budget and actual in df.columns and budget in df.columns:
        work = df.copy()
        work["_actual"] = pd.to_numeric(work[actual], errors="coerce")
        work["_budget"] = pd.to_numeric(work[budget], errors="coerce")
        work["variance"] = work["_actual"] - work["_budget"]
        work["variance_pct"] = (work["variance"] / work["_budget"].abs() * 100).round(2)
        total_var = float(work["variance"].sum())
        from app.services.excel_io import table_to_records

        return {
            "title": f"Variance: {actual} vs {budget}",
            "summary": f"Total variance = {total_var:,.2f}",
            "metric_value": total_var,
            "table": table_to_records(work.head(100)),
            "insights": [f"Sum({actual}) − Sum({budget}) = {total_var:,.2f}"],
            "meta": {"actual": actual, "budget": budget},
        }
    return analyze_dataset(df, "t")


def _pnl(df: pd.DataFrame) -> dict[str, Any]:
    revenue = _find(df, "revenue", "sales", "income")
    cost = _find(df, "cost", "cogs", "expense")
    insights = []
    table = []
    if revenue:
        r = float(pd.to_numeric(df[revenue], errors="coerce").sum())
        table.append({"metric": "Revenue", "value": r})
        insights.append(f"Revenue total: {r:,.2f}")
    if cost:
        c = float(pd.to_numeric(df[cost], errors="coerce").sum())
        table.append({"metric": "Cost", "value": c})
        insights.append(f"Cost total: {c:,.2f}")
    if revenue and cost:
        r = float(pd.to_numeric(df[revenue], errors="coerce").sum())
        c = float(pd.to_numeric(df[cost], errors="coerce").sum())
        profit = r - c
        margin = 100 * profit / r if r else 0
        table.append({"metric": "Gross Profit", "value": profit})
        table.append({"metric": "Gross Margin %", "value": round(margin, 2)})
        insights.append(f"Gross profit: {profit:,.2f} ({margin:.1f}% margin)")
        return {
            "title": "P&L Summary",
            "summary": f"Profit {profit:,.2f} · Margin {margin:.1f}%",
            "metric_value": profit,
            "table": table,
            "insights": insights,
            "meta": {"revenue_col": revenue, "cost_col": cost},
        }
    return analyze_dataset(df, "t")


def list_templates() -> dict[str, Any]:
    return {"templates": TEMPLATE_CATALOG}
