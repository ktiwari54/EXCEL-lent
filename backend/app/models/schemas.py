from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Objective(str, Enum):
    calculate = "calculate"
    compare = "compare"
    lookup = "lookup"
    clean = "clean"
    summarize = "summarize"
    pivot = "pivot"
    chart = "chart"
    dashboard = "dashboard"
    analyze = "analyze"
    find = "find"
    report = "report"
    ask = "ask"


class MetricOp(str, Enum):
    sum = "sum"
    average = "average"
    count = "count"
    counta = "counta"
    min = "min"
    max = "max"
    median = "median"
    percentage = "percentage"
    growth = "growth"
    difference = "difference"
    variance = "variance"
    contribution = "contribution"
    running_total = "running_total"


class ChartType(str, Enum):
    bar = "bar"
    column = "column"
    line = "line"
    pie = "pie"
    donut = "donut"
    area = "area"
    scatter = "scatter"


class CleanAction(str, Enum):
    drop_duplicates = "drop_duplicates"
    fill_blanks = "fill_blanks"
    drop_blanks = "drop_blanks"
    trim_spaces = "trim_spaces"
    normalize_case = "normalize_case"
    numbers_as_text = "numbers_as_text"
    fix_dates = "fix_dates"
    all = "all"


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    inferred_type: str
    non_null: int
    null_count: int
    null_pct: float
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    is_numeric: bool = False
    is_datetime: bool = False
    is_categorical: bool = False
    is_id_like: bool = False
    min: Any = None
    max: Any = None
    mean: float | None = None


class DatasetProfile(BaseModel):
    session_id: str
    filename: str
    rows: int
    columns: int
    column_profiles: list[ColumnProfile]
    duplicate_rows: int
    missing_cells: int
    sheet_names: list[str] = Field(default_factory=list)
    active_sheet: str | None = None
    preview: list[dict[str, Any]] = Field(default_factory=list)


class CalculateRequest(BaseModel):
    session_id: str
    column: str
    metric: MetricOp = MetricOp.sum
    group_by: str | None = None
    filter_column: str | None = None
    filter_value: str | None = None
    secondary_column: str | None = None


class CompareRequest(BaseModel):
    session_id: str
    value_column: str
    dimension_column: str
    metric: MetricOp = MetricOp.sum
    left_value: str | None = None
    right_value: str | None = None


class SummarizeRequest(BaseModel):
    session_id: str
    group_by: list[str]
    value_column: str
    metric: MetricOp = MetricOp.sum
    top_n: int | None = None


class PivotRequest(BaseModel):
    session_id: str
    rows: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    values: str
    aggregation: MetricOp = MetricOp.sum


class ChartRequest(BaseModel):
    session_id: str
    chart_type: ChartType = ChartType.bar
    category_column: str
    value_column: str
    metric: MetricOp = MetricOp.sum
    top_n: int = 10


class CleanRequest(BaseModel):
    session_id: str
    actions: list[CleanAction] = Field(default_factory=lambda: [CleanAction.all])
    fill_value: str | None = None
    case_mode: str = "title"  # lower | upper | title


class FindRequest(BaseModel):
    session_id: str
    find_type: str = "problems"  # problems | duplicates | missing | top | bottom | outliers
    column: str | None = None
    n: int = 10


class DashboardRequest(BaseModel):
    session_id: str
    dashboard_type: str = "sales"  # sales | inventory | finance | crm | marketing | hr | operations | custom
    date_column: str | None = None
    value_column: str | None = None
    category_column: str | None = None
    product_column: str | None = None
    region_column: str | None = None


class ReportRequest(BaseModel):
    session_id: str
    report_type: str = "monthly_sales"
    date_column: str | None = None
    value_column: str | None = None
    category_column: str | None = None


class AskRequest(BaseModel):
    session_id: str
    question: str


class AnalyzeRequest(BaseModel):
    session_id: str
    date_column: str | None = None
    value_column: str | None = None
    category_column: str | None = None


class LookupRequest(BaseModel):
    session_id: str
    lookup_value: str
    lookup_column: str
    return_column: str
    exact: bool = True


class MultiLookupRequest(BaseModel):
    session_id: str
    conditions: list[dict[str, str]] = Field(default_factory=list)
    return_columns: list[str] | None = None


class GrowthRequest(BaseModel):
    session_id: str
    date_column: str
    value_column: str
    freq: str = "M"  # M month, Q quarter, Y year


class TemplateRequest(BaseModel):
    session_id: str
    template_id: str


class EnrichDatesRequest(BaseModel):
    session_id: str
    date_column: str


class ConditionalRequest(BaseModel):
    session_id: str
    function: str = "sumif"  # sumif | sumifs | countif | countifs | averageif
    criteria_column: str | None = None
    criteria_value: str | None = None
    value_column: str | None = None  # sum/avg column
    op: str = "="
    criteria: list[dict[str, str]] = Field(default_factory=list)


class MathRequest(BaseModel):
    session_id: str
    left_column: str
    operator: str = "-"  # + - * / %
    right_column: str | None = None
    right_value: float | None = None
    result_name: str = "Result"
    persist: bool = False


class FilterArrayRequest(BaseModel):
    session_id: str
    column: str
    op: str = "="
    value: str


class UniqueRequest(BaseModel):
    session_id: str
    column: str


class SortRequest(BaseModel):
    session_id: str
    by: list[str]
    ascending: bool = True


class ExportRequest(BaseModel):
    session_id: str
    include_cleaned: bool = True
    include_insights: bool = True
    include_pivot: bool = False
    pivot: PivotRequest | None = None


class AnalysisResult(BaseModel):
    success: bool = True
    title: str
    summary: str | None = None
    metric_value: float | None = None
    table: list[dict[str, Any]] = Field(default_factory=list)
    chart: dict[str, Any] | None = None
    insights: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
