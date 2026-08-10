from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.engines.arrays import filter_rows, sort_data, unique_values
from app.engines.cleaning import clean_dataframe, detect_issues
from app.engines.conditional import averageif, countif, countifs, math_expression, sumif, sumifs
from app.engines.dates import enrich_date_columns, period_growth, ytd_total
from app.engines.formula import calculate, compare, summarize
from app.engines.insight import analyze_dataset, build_dashboard, build_report, find_problems, top_bottom
from app.engines.lookup import multi_condition_lookup, xlookup
from app.engines.nl_parser import answer_question
from app.engines.pivot import chart_data, create_pivot
from app.engines.templates import list_templates as template_catalog
from app.engines.templates import run_template
from app.models.schemas import (
    AnalysisResult,
    AnalyzeRequest,
    AskRequest,
    CalculateRequest,
    ChartRequest,
    CleanRequest,
    CompareRequest,
    ConditionalRequest,
    DashboardRequest,
    EnrichDatesRequest,
    ExportRequest,
    FilterArrayRequest,
    FindRequest,
    GrowthRequest,
    LookupRequest,
    MathRequest,
    MultiLookupRequest,
    PivotRequest,
    ReportRequest,
    SortRequest,
    SummarizeRequest,
    TemplateRequest,
    UniqueRequest,
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
    if ft in ("top", "bottom", "highest", "lowest"):
        col = body.column
        if not col:
            raise HTTPException(400, "column is required for top/bottom")
        ascending = ft in ("bottom", "lowest")
        # Aggregate by first categorical-ish column if present
        label = None
        for c in df.columns:
            if c != col and not pd_is_numeric(df[c]):
                label = c
                break
        if label:
            work = df.copy()
            work["_v"] = pd.to_numeric(work[col], errors="coerce")
            agg = work.groupby(work[label].astype(str))["_v"].sum().reset_index()
            agg.columns = [label, col]
            out = top_bottom(agg, col, n=body.n, ascending=ascending, label_column=label)
        else:
            out = top_bottom(df, col, n=body.n, ascending=ascending)
        return _result(out)
    if ft in ("duplicates", "missing", "outliers", "problems"):
        out = find_problems(df, body.column, body.n)
        return _result(out)
    out = find_problems(df, body.column, body.n)
    return _result(out)


def pd_is_numeric(s) -> bool:
    return bool(pd.api.types.is_numeric_dtype(s))


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
    """Domain template library (runnable templates)."""
    return template_catalog()


@router.post("/templates/run", response_model=AnalysisResult)
def api_run_template(body: TemplateRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = run_template(df, body.template_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/lookup", response_model=AnalysisResult)
def api_lookup(body: LookupRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = xlookup(
            df,
            body.lookup_value,
            body.lookup_column,
            body.return_column,
            body.exact,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/lookup/multi", response_model=AnalysisResult)
def api_multi_lookup(body: MultiLookupRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = multi_condition_lookup(df, body.conditions, body.return_columns)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/growth", response_model=AnalysisResult)
def api_growth(body: GrowthRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = period_growth(df, body.date_column, body.value_column, body.freq)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/ytd", response_model=AnalysisResult)
def api_ytd(body: GrowthRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = ytd_total(df, body.date_column, body.value_column)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/enrich-dates", response_model=AnalysisResult)
def api_enrich_dates(body: EnrichDatesRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        enriched = enrich_date_columns(df, body.date_column)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    store.update(body.session_id, enriched, dates_enriched=True)
    new_cols = [c for c in enriched.columns if c not in df.columns]
    return AnalysisResult(
        title="Date columns enriched",
        summary=f"Added {len(new_cols)} helper columns from '{body.date_column}'.",
        insights=[f"New columns: {', '.join(new_cols)}"],
        table=table_to_records(enriched.head(30)),
        meta={"new_columns": new_cols, "rows": len(enriched)},
    )


@router.post("/conditional", response_model=AnalysisResult)
def api_conditional(body: ConditionalRequest) -> AnalysisResult:
    df = _df(body.session_id)
    fn = body.function.lower()
    try:
        if fn == "sumif":
            if not body.criteria_column or body.criteria_value is None or not body.value_column:
                raise ValueError("sumif requires criteria_column, criteria_value, value_column")
            out = sumif(df, body.criteria_column, body.criteria_value, body.value_column, body.op)
        elif fn == "sumifs":
            if not body.value_column:
                raise ValueError("sumifs requires value_column")
            out = sumifs(df, body.value_column, body.criteria)
        elif fn == "countif":
            if not body.criteria_column or body.criteria_value is None:
                raise ValueError("countif requires criteria_column and criteria_value")
            out = countif(df, body.criteria_column, body.criteria_value, body.op)
        elif fn == "countifs":
            out = countifs(df, body.criteria)
        elif fn == "averageif":
            if not body.criteria_column or body.criteria_value is None or not body.value_column:
                raise ValueError("averageif requires criteria_column, criteria_value, value_column")
            out = averageif(df, body.criteria_column, body.criteria_value, body.value_column, body.op)
        else:
            raise ValueError(f"Unknown function: {body.function}")
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/math", response_model=AnalysisResult)
def api_math(body: MathRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = math_expression(
            df,
            body.left_column,
            body.operator,
            body.right_column,
            body.right_value,
            body.result_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if body.persist and "dataframe" in out:
        store.update(body.session_id, out["dataframe"], math_column=body.result_name)
    return _result(out)


@router.post("/filter", response_model=AnalysisResult)
def api_filter(body: FilterArrayRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = filter_rows(df, body.column, body.op, body.value)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/unique", response_model=AnalysisResult)
def api_unique(body: UniqueRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = unique_values(df, body.column)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)


@router.post("/sort", response_model=AnalysisResult)
def api_sort(body: SortRequest) -> AnalysisResult:
    df = _df(body.session_id)
    try:
        out = sort_data(df, body.by, body.ascending)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _result(out)
