from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.engines.cleaning import clean_dataframe, detect_issues
from app.engines.formula import calculate, compare, summarize
from app.engines.insight import analyze_dataset, build_dashboard, build_report, find_problems, top_bottom
from app.engines.nl_parser import answer_question
from app.engines.pivot import chart_data, create_pivot
from app.models.schemas import (
    AnalysisResult,
    AnalyzeRequest,
    AskRequest,
    CalculateRequest,
    ChartRequest,
    CleanRequest,
    CompareRequest,
    DashboardRequest,
    ExportRequest,
    FindRequest,
    PivotRequest,
    ReportRequest,
    SummarizeRequest,
)
from app.services.excel_io import table_to_records, write_analysis_workbook
from app.services.session_store import store

router = APIRouter(prefix="/api", tags=["analysis"])


def _df(session_id: str):
    try:
        return store.get(session_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


def _result(payload: dict) -> AnalysisResult:
    # drop non-serializable helpers
    payload = {k: v for k, v in payload.items() if k != "dataframe"}
    return AnalysisResult(**{k: v for k, v in payload.items() if k in AnalysisResult.model_fields})


@router.post("/calculate", response_model=AnalysisResult)
def api_calculate(body: CalculateRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = calculate(
            df,
            body.column,
            body.metric,
            body.group_by,
            body.filter_column,
            body.filter_value,
            body.secondary_column,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/compare", response_model=AnalysisResult)
def api_compare(body: CompareRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = compare(
            df,
            body.value_column,
            body.dimension_column,
            body.metric,
            body.left_value,
            body.right_value,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/summarize", response_model=AnalysisResult)
def api_summarize(body: SummarizeRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = summarize(df, body.group_by, body.value_column, body.metric, body.top_n)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/pivot", response_model=AnalysisResult)
def api_pivot(body: PivotRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = create_pivot(df, body.rows, body.columns, body.values, body.aggregation)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/chart", response_model=AnalysisResult)
def api_chart(body: ChartRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = chart_data(
            df,
            body.category_column,
            body.value_column,
            body.metric,
            body.top_n,
            body.chart_type.value,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/clean", response_model=AnalysisResult)
def api_clean(body: CleanRequest) -> AnalysisResult:
    df = _df(body.session_id)
    before_issues = detect_issues(df)
    cleaned, log = clean_dataframe(df, body.actions, body.fill_value, body.case_mode)
    store.update(body.session_id, cleaned, cleaned=True)
    return AnalysisResult(
        title="Data cleaned",
        summary=f"Rows: {len(df)} → {len(cleaned)}. " + " ".join(log),
        insights=log,
        alerts=before_issues[:10],
        table=table_to_records(cleaned, limit=50),
        meta={"rows_before": len(df), "rows_after": len(cleaned), "actions": [a.value for a in body.actions]},
    )


@router.post("/find", response_model=AnalysisResult)
def api_find(body: FindRequest) -> AnalysisResult:
    df = _df(body.session_id)
    ft = body.find_type.lower()
    if ft in ("top", "bottom"):
        col = body.column
        if not col:
            raise HTTPException(400, "column is required for top/bottom")
        out = top_bottom(df, col, n=body.n, ascending=(ft == "bottom"))
        return _result(out)
    out = find_problems(df, body.column, body.n)
    return _result(out)


@router.post("/analyze", response_model=AnalysisResult)
def api_analyze(body: AnalyzeRequest) -> AnalysisResult:
    df = _df(body.session_id)
    meta = store.get_meta(body.session_id)
    out = analyze_dataset(
        df,
        body.session_id,
        meta.get("filename", "dataset"),
        body.date_column,
        body.value_column,
        body.category_column,
    )
    return _result(out)


@router.post("/dashboard", response_model=AnalysisResult)
def api_dashboard(body: DashboardRequest) -> AnalysisResult:
    df = _df(body.session_id)
    out = build_dashboard(
        df,
        body.dashboard_type,
        body.date_column,
        body.value_column,
        body.category_column,
        body.product_column,
        body.region_column,
    )
    return _result(out)


@router.post("/report", response_model=AnalysisResult)
def api_report(body: ReportRequest) -> AnalysisResult:
    df = _df(body.session_id)
    out = build_report(
        df,
        body.report_type,
        body.date_column,
        body.value_column,
        body.category_column,
    )
    return _result(out)


@router.post("/ask", response_model=AnalysisResult)
def api_ask(body: AskRequest) -> AnalysisResult:
    df = _df(body.session_id)
    if not body.question.strip():
        raise HTTPException(400, "Question is empty")
    out = answer_question(df, body.question, body.session_id)
    return _result(out)


@router.post("/export")
def api_export(body: ExportRequest) -> FileResponse:
    df = _df(body.session_id)
    meta = store.get_meta(body.session_id)
    settings = get_settings()

    tables = {}
    insights: list[str] = []
    if body.include_insights:
        analysis = analyze_dataset(df, body.session_id, meta.get("filename", "dataset"))
        insights = (
            analysis.get("insights", [])
            + analysis.get("alerts", [])
            + analysis.get("recommendations", [])
        )
        if analysis.get("table"):
            import pandas as pd

            tables["Analysis"] = pd.DataFrame(analysis["table"])

    if body.include_pivot and body.pivot:
        piv = create_pivot(
            df,
            body.pivot.rows,
            body.pivot.columns,
            body.pivot.values,
            body.pivot.aggregation,
        )
        if "dataframe" in piv:
            tables["Pivot"] = piv["dataframe"]

    path = settings.exports_dir / f"{body.session_id}_analysis.xlsx"
    write_analysis_workbook(
        path,
        data=df,
        cleaned=df if body.include_cleaned else None,
        tables=tables,
        insights=insights,
        title="EXCEL-lent Analysis Export",
    )
    return FileResponse(
        path,
        filename=f"excellent_analysis_{body.session_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/templates")
def list_templates() -> dict:
    """Template library scaffold for domain analytics."""
    return {
        "templates": {
            "sales": [
                "Sales Dashboard",
                "Sales Forecast",
                "Salesperson Performance",
                "Product Performance",
                "Customer Analysis",
            ],
            "inventory": [
                "Stock Dashboard",
                "Stock Aging",
                "Inventory Turnover",
                "Low Stock Report",
                "Dead Stock Analysis",
            ],
            "finance": [
                "P&L Analysis",
                "Expense Analysis",
                "Budget vs Actual",
                "Cash Flow",
                "Variance Analysis",
            ],
            "hr": [
                "Attendance",
                "Employee Performance",
                "Attrition",
                "Payroll Analysis",
            ],
            "crm": [
                "Lead Analysis",
                "Conversion Rate",
                "Pipeline Analysis",
                "Win/Loss Analysis",
            ],
            "ecommerce": [
                "Order Analysis",
                "SKU Performance",
                "Returns",
                "Marketplace Performance",
                "Customer Cohort Analysis",
            ],
        }
    }
