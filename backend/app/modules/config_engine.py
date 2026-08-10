from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.modules.task_registry import TASK_REGISTRY, get_task


# Field kinds the UI knows how to render
# measure | dimension | date | aggregation | select | multi_select | compare_values
# filter_builder | group_by_list | chart_type | boolean | number | text | radio | match_fields


def _cols(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return list(dataset.get("column_profiles") or [])


def _by_role(dataset: dict[str, Any], *roles: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for c in _cols(dataset):
        role = c.get("role") or ""
        dtype = c.get("data_type") or ""
        name = c["name"]
        match = False
        if "any" in roles:
            match = True
        if "measure" in roles and (
            role == "measure" or dtype in ("currency", "number", "integer", "decimal", "percentage")
        ):
            match = True
        if "dimension" in roles and (
            role in ("dimension", "status", "text_attribute") or dtype == "category"
        ):
            match = True
        if "date_dimension" in roles and (role == "date_dimension" or dtype in ("date", "datetime")):
            match = True
        if "identifier" in roles and (role == "identifier" or dtype == "identifier"):
            match = True
        if match:
            out.append({"value": name, "label": name, "role": role, "data_type": dtype})
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for o in out:
        if o["value"] not in seen:
            seen.add(o["value"])
            uniq.append(o)
    return uniq


def _pick_default(options: list[dict[str, str]], prefer: list[str] | None = None) -> str | None:
    if not options:
        return None
    if prefer:
        for p in prefer:
            for o in options:
                if p.lower() in o["value"].lower():
                    return o["value"]
    return options[0]["value"]


# Declarative config templates per task (engine expands options from dataset)
CONFIG_TEMPLATES: dict[str, dict[str, Any]] = {
    "calculate": {
        "title": "What would you like to calculate?",
        "subtitle": "Pick a number and how we should calculate it.",
        "output_type": "value",
        "fields": [
            {
                "id": "aggregation",
                "kind": "radio",
                "label": "How would you like us to calculate this?",
                "help": "Choose how values should be combined.",
                "required": True,
                "options": [
                    {"value": "sum", "label": "Total (Sum)"},
                    {"value": "average", "label": "Average"},
                    {"value": "count", "label": "Count"},
                    {"value": "min", "label": "Minimum"},
                    {"value": "max", "label": "Maximum"},
                    {"value": "median", "label": "Median"},
                ],
                "default": "sum",
            },
            {
                "id": "measure",
                "kind": "measure",
                "label": "What number would you like to analyze?",
                "help": "Only numeric fields are shown.",
                "required": True,
                "role": "measure",
            },
            {
                "id": "group_by",
                "kind": "dimension",
                "label": "Break down by (optional)",
                "help": "Optional — group results by a category.",
                "required": False,
                "role": "dimension",
                "allow_empty": True,
            },
            {"id": "filters", "kind": "filter_builder", "label": "Do you want to narrow down the data?", "required": False},
        ],
        "advanced": [
            {"id": "ignore_blanks", "kind": "boolean", "label": "Ignore blank values", "default": True},
            {"id": "decimals", "kind": "number", "label": "Decimal places", "default": 2},
        ],
        "submit_label": "Generate Analysis",
    },
    "compare": {
        "title": "What would you like to compare?",
        "subtitle": "Compare groups, regions, products, or periods.",
        "output_type": "comparison",
        "fields": [
            {"id": "measure", "kind": "measure", "label": "What number would you like to compare?", "required": True, "role": "measure"},
            {"id": "compare_by", "kind": "dimension", "label": "Compare by", "help": "The field that defines the groups.", "required": True, "role": "dimension"},
            {
                "id": "left_value",
                "kind": "text",
                "label": "First value (optional)",
                "help": "e.g. Dubai — leave blank to compare all groups.",
                "required": False,
            },
            {
                "id": "right_value",
                "kind": "text",
                "label": "Second value (optional)",
                "help": "e.g. Abu Dhabi",
                "required": False,
            },
            {
                "id": "comparison_method",
                "kind": "select",
                "label": "How should we compare?",
                "required": True,
                "options": [
                    {"value": "absolute", "label": "Absolute difference"},
                    {"value": "percentage", "label": "Percentage difference"},
                    {"value": "growth", "label": "Growth %"},
                    {"value": "ratio", "label": "Ratio"},
                ],
                "default": "percentage",
            },
            {
                "id": "aggregation",
                "kind": "select",
                "label": "How should values be calculated?",
                "required": True,
                "options": [
                    {"value": "sum", "label": "Total"},
                    {"value": "average", "label": "Average"},
                    {"value": "count", "label": "Count"},
                ],
                "default": "sum",
            },
            {"id": "filters", "kind": "filter_builder", "label": "Do you want to narrow down the data?", "required": False},
        ],
        "submit_label": "Compare",
    },
    "lookup": {
        "title": "Match information",
        "subtitle": "Connect tables or find matching records — without formulas.",
        "output_type": "table",
        "fields": [
            {
                "id": "mode",
                "kind": "radio",
                "label": "What do you want to do?",
                "required": True,
                "options": [
                    {"value": "lookup_value", "label": "Look up a value in this dataset"},
                    {"value": "match_datasets", "label": "Match two datasets"},
                    {"value": "find_unmatched", "label": "Find unmatched / missing records"},
                ],
                "default": "lookup_value",
            },
            {"id": "lookup_column", "kind": "any_column", "label": "Match field (this dataset)", "required": True},
            {"id": "lookup_value", "kind": "text", "label": "Value to find (optional for full match)", "required": False},
            {"id": "return_column", "kind": "any_column", "label": "What would you like to retrieve?", "required": False},
            {
                "id": "secondary_dataset_id",
                "kind": "dataset_select",
                "label": "Second dataset (for matching tables)",
                "required": False,
            },
            {
                "id": "match_type",
                "kind": "select",
                "label": "Match type",
                "options": [
                    {"value": "exact", "label": "Exact match"},
                    {"value": "approximate", "label": "Approximate match"},
                ],
                "default": "exact",
            },
            {
                "id": "output_mode",
                "kind": "select",
                "label": "Output",
                "options": [
                    {"value": "add_columns", "label": "Add columns"},
                    {"value": "matching_only", "label": "Matching records only"},
                    {"value": "non_matching", "label": "Non-matching records"},
                    {"value": "full", "label": "Full reconciliation"},
                ],
                "default": "matching_only",
            },
        ],
        "submit_label": "Run Match",
    },
    "clean": {
        "title": "Clean your data",
        "subtitle": "Tell us which quality issues to address. We won't change your original data.",
        "output_type": "table",
        "fields": [
            {
                "id": "actions",
                "kind": "multi_select",
                "label": "What would you like to clean?",
                "required": True,
                "options": [
                    {"value": "find_duplicates", "label": "Find duplicates"},
                    {"value": "drop_duplicates", "label": "Remove duplicates"},
                    {"value": "fill_blanks", "label": "Handle missing values"},
                    {"value": "trim_spaces", "label": "Fix extra spaces"},
                    {"value": "normalize_case", "label": "Standardize text case"},
                    {"value": "numbers_as_text", "label": "Convert numbers stored as text"},
                    {"value": "fix_dates", "label": "Fix dates"},
                ],
                "default": ["find_duplicates", "trim_spaces"],
            },
            {
                "id": "duplicate_keys",
                "kind": "multi_column",
                "label": "Which fields identify a duplicate?",
                "help": "Leave empty to check entire rows.",
                "required": False,
                "role": "any",
            },
            {
                "id": "duplicate_mode",
                "kind": "select",
                "label": "Matching rule",
                "options": [
                    {"value": "all", "label": "Match all selected fields"},
                    {"value": "any", "label": "Match any selected field"},
                ],
                "default": "all",
            },
        ],
        "advanced": [
            {
                "id": "match_method",
                "kind": "select",
                "label": "Matching method",
                "options": [
                    {"value": "exact", "label": "Exact"},
                    {"value": "normalized", "label": "Normalized"},
                    {"value": "fuzzy", "label": "Fuzzy (later)"},
                ],
                "default": "exact",
            },
        ],
        "submit_label": "Prepare Cleaning",
    },
    "find_duplicates": {
        "title": "Find duplicates",
        "subtitle": "Choose fields that identify the same record.",
        "output_type": "table",
        "fields": [
            {
                "id": "duplicate_keys",
                "kind": "multi_column",
                "label": "Which fields should identify a duplicate?",
                "required": False,
                "role": "any",
            },
            {
                "id": "duplicate_mode",
                "kind": "select",
                "label": "Match rule",
                "options": [
                    {"value": "all", "label": "Match all selected fields"},
                    {"value": "any", "label": "Match any selected field"},
                ],
                "default": "all",
            },
        ],
        "submit_label": "Find Duplicates",
    },
    "summarize": {
        "title": "Create a summary",
        "subtitle": "Turn detailed rows into a clear summary.",
        "output_type": "table",
        "fields": [
            {
                "id": "group_by",
                "kind": "group_by_list",
                "label": "How would you like to group the data?",
                "help": "e.g. Product, Region, Month",
                "required": True,
                "role": "dimension",
            },
            {"id": "measure", "kind": "measure", "label": "What number would you like to analyze?", "required": True, "role": "measure"},
            {
                "id": "aggregation",
                "kind": "select",
                "label": "How should we calculate this?",
                "required": True,
                "options": [
                    {"value": "sum", "label": "Total"},
                    {"value": "average", "label": "Average"},
                    {"value": "count", "label": "Count"},
                    {"value": "min", "label": "Minimum"},
                    {"value": "max", "label": "Maximum"},
                ],
                "default": "sum",
            },
            {
                "id": "sort_direction",
                "kind": "select",
                "label": "Sort order",
                "options": [
                    {"value": "desc", "label": "Highest to lowest"},
                    {"value": "asc", "label": "Lowest to highest"},
                ],
                "default": "desc",
            },
            {
                "id": "limit",
                "kind": "select",
                "label": "How many results?",
                "options": [
                    {"value": "10", "label": "Top 10"},
                    {"value": "20", "label": "Top 20"},
                    {"value": "50", "label": "Top 50"},
                    {"value": "0", "label": "All"},
                ],
                "default": "10",
            },
            {"id": "filters", "kind": "filter_builder", "label": "Do you want to narrow down the data?", "required": False},
        ],
        "submit_label": "Create Summary",
    },
    "top_n": {
        "title": "Top performers",
        "subtitle": "Find the highest or lowest values.",
        "output_type": "table",
        "fields": [
            {"id": "group_by", "kind": "dimension", "label": "Rank by category", "required": True, "role": "dimension"},
            {"id": "measure", "kind": "measure", "label": "Using which number?", "required": True, "role": "measure"},
            {
                "id": "sort_direction",
                "kind": "select",
                "label": "Show",
                "options": [
                    {"value": "desc", "label": "Top (highest first)"},
                    {"value": "asc", "label": "Bottom (lowest first)"},
                ],
                "default": "desc",
            },
            {
                "id": "limit",
                "kind": "select",
                "label": "How many?",
                "options": [
                    {"value": "5", "label": "5"},
                    {"value": "10", "label": "10"},
                    {"value": "20", "label": "20"},
                ],
                "default": "10",
            },
            {"id": "filters", "kind": "filter_builder", "label": "Filters (optional)", "required": False},
        ],
        "submit_label": "Create Ranking",
    },
    "pivot": {
        "title": "Build a pivot-style summary",
        "subtitle": "Choose rows, columns, and values — no Excel pivot skills needed.",
        "output_type": "pivot",
        "fields": [
            {"id": "rows", "kind": "group_by_list", "label": "Rows", "help": "How to organize rows.", "required": False, "role": "dimension"},
            {"id": "columns", "kind": "dimension", "label": "Columns (optional)", "required": False, "role": "dimension", "allow_empty": True},
            {"id": "measure", "kind": "measure", "label": "Values", "required": True, "role": "measure"},
            {
                "id": "aggregation",
                "kind": "select",
                "label": "Calculation",
                "options": [
                    {"value": "sum", "label": "Sum"},
                    {"value": "average", "label": "Average"},
                    {"value": "count", "label": "Count"},
                    {"value": "min", "label": "Min"},
                    {"value": "max", "label": "Max"},
                ],
                "default": "sum",
            },
            {"id": "filters", "kind": "filter_builder", "label": "Filters", "required": False},
        ],
        "submit_label": "Create Pivot",
    },
    "charts": {
        "title": "Create a chart",
        "subtitle": "Pick what to visualize — we'll recommend a chart type.",
        "output_type": "chart",
        "fields": [
            {"id": "measure", "kind": "measure", "label": "What number do you want to visualize?", "required": True, "role": "measure"},
            {"id": "category", "kind": "dimension", "label": "Category / dimension", "required": True, "role": "dimension"},
            {
                "id": "chart_type",
                "kind": "chart_type",
                "label": "Chart type",
                "help": "We recommend a bar chart for comparing categories.",
                "required": True,
                "options": [
                    {"value": "bar", "label": "Bar"},
                    {"value": "column", "label": "Column"},
                    {"value": "line", "label": "Line"},
                    {"value": "area", "label": "Area"},
                    {"value": "pie", "label": "Pie"},
                    {"value": "donut", "label": "Donut"},
                ],
                "default": "bar",
                "recommended": "bar",
                "recommendation_reason": "A bar chart works well when comparing values across categories.",
            },
            {
                "id": "aggregation",
                "kind": "select",
                "label": "How should we calculate values?",
                "options": [
                    {"value": "sum", "label": "Total"},
                    {"value": "average", "label": "Average"},
                    {"value": "count", "label": "Count"},
                ],
                "default": "sum",
            },
            {
                "id": "limit",
                "kind": "select",
                "label": "How many categories?",
                "options": [
                    {"value": "10", "label": "Top 10"},
                    {"value": "15", "label": "Top 15"},
                    {"value": "25", "label": "Top 25"},
                ],
                "default": "10",
            },
            {"id": "filters", "kind": "filter_builder", "label": "Filters (optional)", "required": False},
        ],
        "submit_label": "Create Chart",
    },
    "monthly_trend": {
        "title": "Monthly trend",
        "subtitle": "See how a number moves over time.",
        "output_type": "chart",
        "fields": [
            {"id": "measure", "kind": "measure", "label": "What number?", "required": True, "role": "measure"},
            {"id": "date_field", "kind": "date", "label": "Which date field?", "required": True, "role": "date_dimension"},
            {
                "id": "date_grain",
                "kind": "select",
                "label": "Group dates by",
                "options": [
                    {"value": "day", "label": "Day"},
                    {"value": "week", "label": "Week"},
                    {"value": "month", "label": "Month"},
                    {"value": "quarter", "label": "Quarter"},
                    {"value": "year", "label": "Year"},
                ],
                "default": "month",
            },
            {
                "id": "date_range",
                "kind": "select",
                "label": "Date range",
                "options": [
                    {"value": "all", "label": "All data"},
                    {"value": "last_30", "label": "Last 30 days"},
                    {"value": "this_month", "label": "This month"},
                    {"value": "this_year", "label": "This year"},
                    {"value": "custom", "label": "Custom (later)"},
                ],
                "default": "all",
            },
            {"id": "filters", "kind": "filter_builder", "label": "Filters (optional)", "required": False},
        ],
        "submit_label": "Show Trend",
    },
    "dashboard": {
        "title": "Build a dashboard",
        "subtitle": "Choose the focus — detailed layout comes in a later step.",
        "output_type": "dashboard",
        "fields": [
            {
                "id": "dashboard_type",
                "kind": "select",
                "label": "Dashboard type",
                "options": [
                    {"value": "sales", "label": "Sales"},
                    {"value": "inventory", "label": "Inventory"},
                    {"value": "finance", "label": "Finance"},
                    {"value": "crm", "label": "CRM"},
                    {"value": "hr", "label": "HR"},
                    {"value": "marketing", "label": "Marketing"},
                    {"value": "custom", "label": "Custom"},
                ],
                "default": "sales",
            },
            {"id": "measure", "kind": "measure", "label": "Primary number (KPI)", "required": True, "role": "measure"},
            {"id": "date_field", "kind": "date", "label": "Date field (optional)", "required": False, "role": "date_dimension", "allow_empty": True},
            {"id": "category", "kind": "dimension", "label": "Main category (optional)", "required": False, "role": "dimension", "allow_empty": True},
            {"id": "region", "kind": "dimension", "label": "Region / location (optional)", "required": False, "role": "dimension", "allow_empty": True},
        ],
        "submit_label": "Prepare Dashboard",
    },
    "sales_dashboard": {
        "title": "Sales dashboard",
        "subtitle": "We'll use your sales-related fields as defaults.",
        "output_type": "dashboard",
        "fields": [
            {"id": "measure", "kind": "measure", "label": "Revenue / sales field", "required": True, "role": "measure"},
            {"id": "date_field", "kind": "date", "label": "Order / sales date", "required": False, "role": "date_dimension", "allow_empty": True},
            {"id": "category", "kind": "dimension", "label": "Product / category", "required": False, "role": "dimension", "allow_empty": True},
            {"id": "region", "kind": "dimension", "label": "Region", "required": False, "role": "dimension", "allow_empty": True},
        ],
        "submit_label": "Prepare Sales Dashboard",
    },
    "reports": {
        "title": "Create a report",
        "subtitle": "We'll structure findings from your data.",
        "output_type": "report",
        "fields": [
            {
                "id": "report_type",
                "kind": "select",
                "label": "Report type",
                "options": [
                    {"value": "management", "label": "Management report"},
                    {"value": "sales", "label": "Sales report"},
                    {"value": "monthly", "label": "Monthly report"},
                    {"value": "exception", "label": "Exception report"},
                    {"value": "performance", "label": "Performance report"},
                ],
                "default": "sales",
            },
            {"id": "measure", "kind": "measure", "label": "Key number", "required": True, "role": "measure"},
            {"id": "date_field", "kind": "date", "label": "Date field (optional)", "required": False, "role": "date_dimension", "allow_empty": True},
            {"id": "category", "kind": "dimension", "label": "Focus category (optional)", "required": False, "role": "dimension", "allow_empty": True},
        ],
        "submit_label": "Prepare Report",
    },
    "analyze": {
        "title": "Analyze my data",
        "subtitle": "We'll examine your dataset for findings. Optional focus fields improve results.",
        "output_type": "insight",
        "fields": [
            {"id": "measure", "kind": "measure", "label": "Primary number to focus on (optional)", "required": False, "role": "measure", "allow_empty": True},
            {"id": "category", "kind": "dimension", "label": "Category to rank (optional)", "required": False, "role": "dimension", "allow_empty": True},
            {"id": "date_field", "kind": "date", "label": "Date for trends (optional)", "required": False, "role": "date_dimension", "allow_empty": True},
        ],
        "submit_label": "Generate Analysis",
    },
    "match_datasets": {
        "title": "Match two datasets",
        "subtitle": "Connect records using shared IDs.",
        "output_type": "table",
        "fields": [
            {"id": "lookup_column", "kind": "any_column", "label": "Match field — this dataset", "required": True},
            {"id": "secondary_dataset_id", "kind": "dataset_select", "label": "Second dataset", "required": True},
            {
                "id": "match_type",
                "kind": "select",
                "label": "Match type",
                "options": [
                    {"value": "exact", "label": "Exact"},
                    {"value": "approximate", "label": "Approximate"},
                ],
                "default": "exact",
            },
            {
                "id": "output_mode",
                "kind": "select",
                "label": "Output",
                "options": [
                    {"value": "matching_only", "label": "Matching only"},
                    {"value": "non_matching", "label": "Non-matching"},
                    {"value": "full", "label": "Full reconciliation"},
                ],
                "default": "full",
            },
        ],
        "submit_label": "Run Match",
    },
    "inventory_analysis": {
        "title": "Inventory analysis",
        "subtitle": "Focus on stock and quantity fields.",
        "output_type": "insight",
        "fields": [
            {"id": "measure", "kind": "measure", "label": "Quantity / stock field", "required": True, "role": "measure"},
            {"id": "category", "kind": "dimension", "label": "SKU / product", "required": False, "role": "dimension", "allow_empty": True},
        ],
        "submit_label": "Prepare Analysis",
    },
}


def build_config_schema(
    task_id: str,
    dataset: dict[str, Any],
    datasets_list: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    task = get_task(task_id) or {"id": task_id, "name": task_id, "category": "General", "description": ""}
    template = deepcopy(CONFIG_TEMPLATES.get(task_id) or CONFIG_TEMPLATES.get("analyze"))
    assert template is not None

    measures = _by_role(dataset, "measure")
    dimensions = _by_role(dataset, "dimension")
    dates = _by_role(dataset, "date_dimension")
    any_cols = [{"value": c["name"], "label": c["name"]} for c in _cols(dataset)]
    ds_options = [
        {"value": d["id"], "label": d.get("name") or d["id"]}
        for d in (datasets_list or [])
        if d.get("id") != dataset.get("id")
    ]

    defaults: dict[str, Any] = {}
    fields_out = []

    for f in template["fields"]:
        field = deepcopy(f)
        kind = field["kind"]
        if kind == "measure":
            field["options"] = measures
            field["default"] = _pick_default(measures, ["revenue", "sales", "amount", "total", "qty", "quantity"])
            defaults[field["id"]] = field["default"]
        elif kind == "dimension":
            field["options"] = ([{"value": "", "label": "— none —"}] if field.get("allow_empty") else []) + dimensions
            field["default"] = "" if field.get("allow_empty") else _pick_default(dimensions, ["product", "region", "category", "customer"])
            defaults[field["id"]] = field["default"]
        elif kind == "date":
            field["options"] = ([{"value": "", "label": "— none —"}] if field.get("allow_empty") else []) + dates
            field["default"] = "" if field.get("allow_empty") and not dates else _pick_default(dates, ["date", "order"])
            defaults[field["id"]] = field.get("default")
        elif kind == "any_column":
            field["options"] = any_cols
            field["default"] = _pick_default(any_cols, ["id", "code", "sku", "customer"])
            defaults[field["id"]] = field["default"]
        elif kind == "multi_column":
            field["options"] = any_cols
            # suggest id-like
            ids = [c for c in any_cols if any(k in c["value"].lower() for k in ("id", "email", "phone", "code", "sku"))]
            defaults[field["id"]] = [c["value"] for c in (ids[:3] or any_cols[:2])]
            field["default"] = defaults[field["id"]]
        elif kind == "group_by_list":
            field["options"] = dimensions
            d0 = _pick_default(dimensions, ["product", "region", "category"])
            defaults[field["id"]] = [d0] if d0 else []
            field["default"] = defaults[field["id"]]
        elif kind == "dataset_select":
            field["options"] = ds_options
            field["default"] = ds_options[0]["value"] if ds_options else None
            defaults[field["id"]] = field["default"]
        elif kind == "filter_builder":
            field["column_options"] = any_cols
            field["operators"] = [
                {"value": "eq", "label": "is"},
                {"value": "ne", "label": "is not"},
                {"value": "gt", "label": "greater than"},
                {"value": "gte", "label": "at least"},
                {"value": "lt", "label": "less than"},
                {"value": "lte", "label": "at most"},
                {"value": "contains", "label": "contains"},
            ]
            defaults[field["id"]] = []
        elif kind in ("select", "radio", "chart_type"):
            defaults[field["id"]] = field.get("default")
        elif kind == "multi_select":
            defaults[field["id"]] = field.get("default") or []
        elif kind in ("text", "number", "boolean"):
            defaults[field["id"]] = field.get("default")
        else:
            defaults[field["id"]] = field.get("default")
        fields_out.append(field)

    advanced_out = []
    for f in template.get("advanced") or []:
        field = deepcopy(f)
        defaults.setdefault(field["id"], field.get("default"))
        advanced_out.append(field)

    # chart recommendation
    chart_rec = None
    if task_id == "charts":
        chart_rec = {
            "type": "bar",
            "reason": "A bar chart is recommended because you're comparing values across categories.",
        }
        if dates and not dimensions:
            chart_rec = {"type": "line", "reason": "A line chart is recommended for trends over time."}

    preview_hint = _preview_hint(task_id, defaults, dataset)

    return {
        "task": task,
        "title": template.get("title"),
        "subtitle": template.get("subtitle"),
        "output_type": template.get("output_type", "table"),
        "submit_label": template.get("submit_label", "Generate Analysis"),
        "fields": fields_out,
        "advanced": advanced_out,
        "defaults": defaults,
        "chart_recommendation": chart_rec,
        "preview_hint": preview_hint,
        "dataset": {
            "id": dataset.get("id"),
            "name": dataset.get("name"),
            "rows": dataset.get("rows"),
            "columns": dataset.get("columns"),
            "health": (dataset.get("health") or {}).get("score") or dataset.get("health_score"),
        },
    }


def _preview_hint(task_id: str, defaults: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    """Lightweight structural preview — not a real calculation."""
    measure = defaults.get("measure") or "Value"
    group = defaults.get("group_by") or defaults.get("category") or defaults.get("compare_by")
    if isinstance(group, list):
        group = group[0] if group else "Category"
    rows = [
        {str(group or "Item"): "Sample A", str(measure): "…"},
        {str(group or "Item"): "Sample B", str(measure): "…"},
        {str(group or "Item"): "Sample C", str(measure): "…"},
    ]
    return {
        "note": "Preview of layout only — calculations run in Step 4.",
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "task_id": task_id,
    }


def validate_config(task_id: str, config: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    schema = build_config_schema(task_id, dataset)
    errors: list[str] = []
    values = config or {}

    for f in schema["fields"]:
        fid = f["id"]
        val = values.get(fid, f.get("default"))
        required = f.get("required", False)
        allow_empty = f.get("allow_empty", False)
        if required and not allow_empty:
            if val is None or val == "" or val == []:
                errors.append(f"Please complete: {f.get('label') or fid}")
                continue
        # type checks for columns
        if f["kind"] in ("measure", "dimension", "date", "any_column") and val:
            names = {c["name"] for c in _cols(dataset)}
            if val not in names and val != "":
                errors.append(f"“{val}” is not a column in this dataset.")
        if f["kind"] == "group_by_list" and required:
            if not val or (isinstance(val, list) and not any(val)):
                errors.append("Please choose how to group the data.")
        if f["kind"] == "multi_select" and required and not val:
            errors.append(f"Please select at least one option for: {f.get('label')}")

    # compare both values if one set
    if task_id == "compare":
        left, right = values.get("left_value"), values.get("right_value")
        if (left and not right) or (right and not left):
            errors.append("Select two values to compare, or leave both blank to compare all groups.")

    return {"valid": len(errors) == 0, "errors": errors}


def build_task_request(
    *,
    dataset_id: str,
    dataset_name: str,
    task_id: str,
    config: dict[str, Any],
    name: str | None = None,
) -> dict[str, Any]:
    task = get_task(task_id) or {"id": task_id, "name": task_id, "category": "General"}
    schema_output = CONFIG_TEMPLATES.get(task_id, {}).get("output_type", "table")
    req = {
        "name": name or f"{task.get('name')} — {dataset_name}",
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "task_id": task_id,
        "task_name": task.get("name"),
        "task_category": task.get("category"),
        "configuration": config,
        "output_type": schema_output,
        "status": "ready_for_processing",
        "engine": "step4_pending",
    }
    # normalize common keys for Step 4
    c = config or {}
    req["normalized"] = {
        "measure": c.get("measure"),
        "aggregation": c.get("aggregation", "sum"),
        "group_by": c.get("group_by") if isinstance(c.get("group_by"), list) else ([c["group_by"]] if c.get("group_by") else []),
        "filters": c.get("filters") or [],
        "date_field": c.get("date_field"),
        "date_grain": c.get("date_grain"),
        "date_range": c.get("date_range"),
        "chart_type": c.get("chart_type"),
        "category": c.get("category") or c.get("compare_by"),
        "limit": int(c["limit"]) if str(c.get("limit", "")).isdigit() else c.get("limit"),
        "sort_direction": c.get("sort_direction", "desc"),
        "compare_by": c.get("compare_by"),
        "left_value": c.get("left_value"),
        "right_value": c.get("right_value"),
        "comparison_method": c.get("comparison_method"),
        "rows": c.get("rows") if isinstance(c.get("rows"), list) else ([c["rows"]] if c.get("rows") else []),
        "columns": c.get("columns"),
        "actions": c.get("actions"),
        "duplicate_keys": c.get("duplicate_keys"),
        "secondary_dataset_id": c.get("secondary_dataset_id"),
        "lookup_column": c.get("lookup_column"),
        "return_column": c.get("return_column"),
        "dashboard_type": c.get("dashboard_type"),
        "report_type": c.get("report_type"),
    }
    return req
