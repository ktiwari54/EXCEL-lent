"""Smoke tests for core analytics engines."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.engines.cleaning import clean_dataframe, detect_issues
from app.engines.dates import period_growth, ytd_total
from app.engines.formula import calculate, compare, summarize
from app.engines.insight import analyze_dataset, build_dashboard, find_problems
from app.engines.lookup import xlookup
from app.engines.nl_parser import answer_question
from app.engines.pivot import chart_data, create_pivot
from app.engines.profiling import profile_dataframe
from app.engines.templates import run_template
from app.models.schemas import CleanAction, MetricOp

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sales_sample.csv"


@pytest.fixture
def sales_df() -> pd.DataFrame:
    return pd.read_csv(SAMPLE)


def test_profile(sales_df: pd.DataFrame) -> None:
    p = profile_dataframe(sales_df, "s1", "sales.csv")
    assert p.rows == 30
    assert p.columns >= 10
    assert any(c.name == "Revenue" for c in p.column_profiles)


def test_calculate_group(sales_df: pd.DataFrame) -> None:
    r = calculate(sales_df, "Revenue", MetricOp.sum, group_by="Region")
    assert r["metric_value"] is not None
    assert len(r["table"]) >= 1
    assert r["chart"] is not None


def test_compare(sales_df: pd.DataFrame) -> None:
    r = compare(sales_df, "Revenue", "Region", MetricOp.sum, "Dubai", "Abu Dhabi")
    assert "table" in r
    assert r["meta"]["growth_pct"] is not None or r["meta"]["left_value"] is not None


def test_summarize(sales_df: pd.DataFrame) -> None:
    r = summarize(sales_df, ["Product"], "Revenue", MetricOp.sum, top_n=5)
    assert len(r["table"]) <= 5


def test_pivot(sales_df: pd.DataFrame) -> None:
    r = create_pivot(sales_df, ["Region"], ["Category"], "Revenue", MetricOp.sum)
    assert len(r["table"]) >= 1


def test_chart(sales_df: pd.DataFrame) -> None:
    r = chart_data(sales_df, "Product", "Revenue", MetricOp.sum, top_n=5, chart_type="bar")
    assert len(r["chart"]["labels"]) <= 5


def test_clean(sales_df: pd.DataFrame) -> None:
    issues = detect_issues(sales_df)
    cleaned, log = clean_dataframe(sales_df, [CleanAction.all])
    assert len(cleaned) <= len(sales_df)
    assert log


def test_analyze(sales_df: pd.DataFrame) -> None:
    r = analyze_dataset(sales_df, "s1", "sales.csv")
    assert r["insights"]
    assert "kpis" in r["meta"]


def test_dashboard(sales_df: pd.DataFrame) -> None:
    r = build_dashboard(sales_df, "sales")
    assert r["meta"]["kpis"]
    assert r["meta"]["charts"] is not None


def test_find_problems(sales_df: pd.DataFrame) -> None:
    r = find_problems(sales_df)
    assert "title" in r


def test_lookup(sales_df: pd.DataFrame) -> None:
    r = xlookup(sales_df, "ORD-1001", "OrderID", "Revenue")
    assert r["meta"]["matches"] == 1


def test_growth(sales_df: pd.DataFrame) -> None:
    r = period_growth(sales_df, "OrderDate", "Revenue", "M")
    assert len(r["table"]) >= 2


def test_ytd(sales_df: pd.DataFrame) -> None:
    r = ytd_total(sales_df, "OrderDate", "Revenue")
    assert r["metric_value"] and r["metric_value"] > 0


def test_ask_top_customers(sales_df: pd.DataFrame) -> None:
    r = answer_question(sales_df, "Who are my top 10 customers?")
    assert r["table"] or r["chart"]


def test_template_sales_dashboard(sales_df: pd.DataFrame) -> None:
    r = run_template(sales_df, "sales_dashboard")
    assert r["meta"]["template_id"] == "sales_dashboard"


def test_sumif(sales_df: pd.DataFrame) -> None:
    from app.engines.conditional import sumif, math_expression

    r = sumif(sales_df, "Region", "Dubai", "Revenue")
    assert r["metric_value"] and r["metric_value"] > 0
    m = math_expression(sales_df, "Revenue", "-", "Cost", result_name="Profit")
    assert m["metric_value"] is not None


def test_filter_unique(sales_df: pd.DataFrame) -> None:
    from app.engines.arrays import filter_rows, unique_values

    f = filter_rows(sales_df, "Region", "=", "Dubai")
    assert f["meta"]["rows_matched"] > 0
    u = unique_values(sales_df, "Product")
    assert u["meta"]["unique_count"] >= 1
