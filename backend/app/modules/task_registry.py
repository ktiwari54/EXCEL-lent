from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass
class TaskDef:
    id: str
    name: str
    category: str
    description: str
    examples: list[str] = field(default_factory=list)
    can_compare: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)  # measure, date_dimension, dimension, identifier
    optional_roles: list[str] = field(default_factory=list)
    min_datasets: int = 1
    max_datasets: int = 1
    keywords: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)
    recommend_if: str | None = None  # rule key
    icon: str = "sparkles"
    color: str = "bg-blue-500"


# Central registry — UI and availability rules consume this; no hard-coded UI-only logic
TASK_REGISTRY: list[TaskDef] = [
    # Categories (primary)
    TaskDef(
        id="calculate",
        name="Calculate",
        category="Calculate",
        description="Perform calculations and create new metrics from your numbers.",
        examples=["Sum of revenue", "Average order value", "Growth %", "Profit = Revenue − Cost", "Running total"],
        required_roles=["measure"],
        keywords=["calculate", "sum", "average", "total", "count", "min", "max", "percentage", "growth", "variance", "ratio", "profit", "margin"],
        output_types=["metric", "table"],
        recommend_if="has_measure",
        icon="calculator",
        color="bg-emerald-500",
    ),
    TaskDef(
        id="compare",
        name="Compare",
        category="Compare",
        description="Compare values between groups, products, regions, or time periods.",
        examples=["Month vs month", "Product A vs Product B", "Actual vs target", "Region comparison"],
        can_compare=["Products", "Regions", "Customers", "Employees", "Periods", "Categories"],
        required_roles=["measure"],
        optional_roles=["dimension", "date_dimension"],
        keywords=["compare", "vs", "versus", "difference", "against", "higher", "lower"],
        output_types=["table", "chart"],
        recommend_if="has_measure_and_dimension",
        icon="scale",
        color="bg-blue-500",
    ),
    TaskDef(
        id="lookup",
        name="Lookup / Match",
        category="Lookup",
        description="Match records between columns, sheets, or datasets — without writing formulas.",
        examples=["Match two datasets", "Find missing IDs", "Bring customer names into sales", "Find unmatched records"],
        required_roles=["identifier"],
        optional_roles=["dimension"],
        min_datasets=1,
        max_datasets=2,
        keywords=["lookup", "match", "vlookup", "xlookup", "join", "merge", "cross", "missing records", "unmatched"],
        output_types=["table"],
        recommend_if="multi_dataset_or_id",
        icon="search",
        color="bg-violet-500",
    ),
    TaskDef(
        id="clean",
        name="Clean Data",
        category="Clean",
        description="Find and fix data-quality issues before analysis.",
        examples=["Find duplicates", "Remove blanks", "Fix spaces", "Standardize categories", "Numbers stored as text"],
        required_roles=[],
        keywords=["clean", "duplicate", "missing", "blank", "fix", "standardize", "spaces", "invalid"],
        output_types=["table", "quality_report"],
        recommend_if="has_quality_issues",
        icon="wand",
        color="bg-teal-500",
    ),
    TaskDef(
        id="summarize",
        name="Summarize",
        category="Summarize",
        description="Turn detailed rows into clear summaries by group.",
        examples=["Sales by month", "Revenue by product", "Orders by status", "Top 10 customers"],
        required_roles=["measure"],
        optional_roles=["dimension", "date_dimension"],
        keywords=["summarize", "group", "by", "top", "bottom", "ranking", "breakdown"],
        output_types=["table", "chart"],
        recommend_if="has_measure_and_dimension",
        icon="clipboard",
        color="bg-orange-500",
    ),
    TaskDef(
        id="pivot",
        name="Pivot Table",
        category="Pivot",
        description="Build a pivot-style summary without configuring Excel pivots yourself.",
        examples=["Rows = Product, Columns = Month, Values = Revenue", "Count of orders by region"],
        required_roles=["measure"],
        optional_roles=["dimension", "date_dimension"],
        keywords=["pivot", "crosstab", "matrix"],
        output_types=["pivot"],
        recommend_if="has_measure_and_dimension",
        icon="table",
        color="bg-green-500",
    ),
    TaskDef(
        id="charts",
        name="Charts",
        category="Charts",
        description="Create charts and visual insights from your data.",
        examples=["Column chart", "Line trend", "Pie of categories", "Bar ranking"],
        required_roles=["measure"],
        optional_roles=["dimension", "date_dimension"],
        keywords=["chart", "graph", "plot", "visual", "line", "bar", "pie"],
        output_types=["chart"],
        recommend_if="has_measure",
        icon="chart",
        color="bg-pink-500",
    ),
    TaskDef(
        id="dashboard",
        name="Dashboard",
        category="Dashboard",
        description="Build an interactive board with KPIs, charts, and filters.",
        examples=["Sales dashboard", "Inventory dashboard", "Finance dashboard", "Custom dashboard"],
        required_roles=["measure"],
        optional_roles=["dimension", "date_dimension"],
        keywords=["dashboard", "kpi", "board", "overview"],
        output_types=["dashboard"],
        recommend_if="has_measure",
        icon="monitor",
        color="bg-teal-600",
    ),
    TaskDef(
        id="reports",
        name="Reports",
        category="Reports",
        description="Generate a structured management-style report from your data.",
        examples=["Monthly sales report", "Exception report", "Performance report"],
        required_roles=["measure"],
        optional_roles=["dimension", "date_dimension"],
        keywords=["report", "summary report", "management"],
        output_types=["report"],
        recommend_if="has_measure",
        icon="file",
        color="bg-indigo-600",
    ),
    TaskDef(
        id="analyze",
        name="Analyze My Data",
        category="Analyze",
        description="Let the engine examine your dataset and surface important findings.",
        examples=["Trends", "Top/bottom performers", "Outliers", "Anomalies", "Business problems"],
        required_roles=[],
        keywords=["analyze", "analysis", "insights", "findings", "examine", "what is interesting"],
        output_types=["insights", "alerts", "recommendations"],
        recommend_if="always",
        icon="sparkles",
        color="bg-blue-600",
    ),
    # Specific recommendation-style tasks (also selectable)
    TaskDef(
        id="monthly_trend",
        name="Monthly Trends",
        category="Summarize",
        description="See how a key number moves month by month.",
        examples=["Monthly revenue", "Orders over time"],
        required_roles=["date_dimension", "measure"],
        keywords=["monthly", "trend", "over time", "time series"],
        output_types=["chart", "table"],
        recommend_if="has_date_and_measure",
        icon="chart",
        color="bg-sky-500",
    ),
    TaskDef(
        id="top_n",
        name="Top Performers",
        category="Summarize",
        description="Identify the highest-performing products, customers, or regions.",
        examples=["Top 10 customers", "Top products by revenue"],
        required_roles=["measure", "dimension"],
        keywords=["top", "highest", "best", "leading"],
        output_types=["table", "chart"],
        recommend_if="has_measure_and_dimension",
        icon="clipboard",
        color="bg-amber-500",
    ),
    TaskDef(
        id="find_duplicates",
        name="Find Duplicates",
        category="Clean",
        description="Detect duplicate rows or repeated IDs in your dataset.",
        examples=["Duplicate customers", "Duplicate order IDs"],
        required_roles=[],
        keywords=["duplicate", "duplicates", "repeated"],
        output_types=["table", "quality_report"],
        recommend_if="has_quality_issues",
        icon="wand",
        color="bg-rose-500",
    ),
    TaskDef(
        id="match_datasets",
        name="Match Datasets",
        category="Lookup",
        description="Connect two datasets using shared IDs or keys.",
        examples=["Sales ↔ Customers", "Orders ↔ Products"],
        required_roles=["identifier"],
        min_datasets=2,
        max_datasets=2,
        keywords=["match datasets", "join tables", "link"],
        output_types=["table"],
        recommend_if="multi_dataset",
        icon="search",
        color="bg-violet-600",
    ),
    TaskDef(
        id="sales_dashboard",
        name="Sales Dashboard",
        category="Dashboard",
        description="Sales-focused KPIs: revenue, trends, products, regions.",
        examples=["Revenue KPI", "Top products", "Regional split"],
        required_roles=["measure"],
        optional_roles=["date_dimension", "dimension"],
        keywords=["sales dashboard", "revenue dashboard"],
        output_types=["dashboard"],
        recommend_if="looks_like_sales",
        icon="monitor",
        color="bg-emerald-600",
    ),
    TaskDef(
        id="inventory_analysis",
        name="Inventory Analysis",
        category="Analyze",
        description="Stock, quantity, and warehouse-oriented analysis.",
        examples=["Low stock", "Warehouse comparison", "SKU performance"],
        required_roles=["measure"],
        keywords=["inventory", "stock", "sku", "warehouse"],
        output_types=["insights", "table"],
        recommend_if="looks_like_inventory",
        icon="package",
        color="bg-slate-600",
    ),
]


def _profile_facts(dataset: dict[str, Any], dataset_count: int = 1) -> dict[str, Any]:
    profiles = dataset.get("column_profiles") or []
    roles = {p.get("role") for p in profiles}
    types = {p.get("data_type") for p in profiles}
    names = " ".join(str(p.get("name", "")).lower() for p in profiles)
    quality = dataset.get("quality") or {}
    issues = quality.get("issues") or []
    has_measure = "measure" in roles or any(
        t in types for t in ("currency", "number", "integer", "decimal", "percentage")
    )
    has_date = "date_dimension" in roles or any(t in types for t in ("date", "datetime"))
    has_dim = "dimension" in roles or "category" in types
    has_id = "identifier" in roles or "identifier" in types
    looks_sales = any(k in names for k in ("revenue", "sales", "order", "customer", "product"))
    looks_inv = any(k in names for k in ("sku", "stock", "warehouse", "qty", "quantity", "inventory"))
    return {
        "has_measure": has_measure,
        "has_date": has_date,
        "has_dimension": has_dim,
        "has_identifier": has_id,
        "has_quality_issues": len(issues) > 0 or (quality.get("duplicate_rows") or 0) > 0,
        "dataset_count": dataset_count,
        "looks_like_sales": looks_sales,
        "looks_like_inventory": looks_inv,
        "measure_names": [p["name"] for p in profiles if p.get("role") == "measure"][:8],
        "dimension_names": [p["name"] for p in profiles if p.get("role") == "dimension"][:8],
        "date_names": [p["name"] for p in profiles if p.get("role") == "date_dimension" or p.get("data_type") in ("date", "datetime")][:4],
    }


def _rule(facts: dict[str, Any], key: str | None) -> bool:
    if not key or key == "always":
        return True
    if key == "has_measure":
        return facts["has_measure"]
    if key == "has_measure_and_dimension":
        return facts["has_measure"] and facts["has_dimension"]
    if key == "has_date_and_measure":
        return facts["has_date"] and facts["has_measure"]
    if key == "has_quality_issues":
        return facts["has_quality_issues"]
    if key == "multi_dataset":
        return facts["dataset_count"] >= 2
    if key == "multi_dataset_or_id":
        return facts["dataset_count"] >= 2 or facts["has_identifier"]
    if key == "looks_like_sales":
        return facts["looks_like_sales"] and facts["has_measure"]
    if key == "looks_like_inventory":
        return facts["looks_like_inventory"] and facts["has_measure"]
    return True


def evaluate_availability(task: TaskDef, facts: dict[str, Any]) -> dict[str, Any]:
    """Return available | partial | unavailable with reasons."""
    reasons: list[str] = []
    missing: list[str] = []

    if facts["dataset_count"] < task.min_datasets:
        missing.append(f"Needs at least {task.min_datasets} dataset(s). You have {facts['dataset_count']}.")
    if facts["dataset_count"] > task.max_datasets and task.max_datasets == 1 and task.min_datasets == 1:
        # single-dataset tasks still ok with multiple available — user selects one
        pass

    for role in task.required_roles:
        if role == "measure" and not facts["has_measure"]:
            missing.append("A numeric measure is required (e.g. Revenue, Quantity, Amount).")
        if role == "date_dimension" and not facts["has_date"]:
            missing.append("A date field is required for this analysis.")
        if role == "dimension" and not facts["has_dimension"]:
            missing.append("A category/dimension field is required (e.g. Product, Region).")
        if role == "identifier" and not facts["has_identifier"] and task.id != "lookup":
            missing.append("An ID field is recommended for reliable matching.")

    if task.id == "match_datasets" and facts["dataset_count"] < 2:
        missing.append("Upload at least two datasets to match them together.")

    if missing:
        # partial if only optional-ish gaps
        if task.required_roles and any("required" in m.lower() or "is required" in m for m in missing):
            status = "unavailable" if len(missing) >= 1 and (
                ("date field is required" in " ".join(missing).lower() and "date" in task.required_roles)
                or ("numeric measure is required" in " ".join(missing).lower())
                or ("at least two datasets" in " ".join(missing).lower())
            ) else "partial"
            # simplify: if any hard required missing → unavailable for critical ones
            hard = any(
                x in " ".join(missing).lower()
                for x in ("numeric measure is required", "date field is required", "at least two datasets", "at least 2 dataset")
            )
            status = "unavailable" if hard else "partial"
        else:
            status = "partial" if missing else "available"
        # refine: no measure for calculate etc
        if "numeric measure is required" in " ".join(missing).lower():
            status = "unavailable"
        if "date field is required" in " ".join(missing).lower() and "date_dimension" in task.required_roles:
            status = "unavailable"
        if "at least two datasets" in " ".join(missing).lower():
            status = "unavailable"
        reasons = missing
    else:
        status = "available"
        reasons = ["Your dataset has the fields needed for this task."]

    # partial cases: measure without cost for profit-like keywords is handled in NL, not here
    if status == "available" and task.id == "calculate" and facts["has_measure"] and not any(
        "cost" in n.lower() for n in facts.get("measure_names", [])
    ):
        # still available for sum/avg
        pass

    return {
        "status": status,
        "reasons": reasons,
        "can_start": status in ("available", "partial"),
    }


def list_tasks_for_dataset(dataset: dict[str, Any], dataset_count: int = 1) -> list[dict[str, Any]]:
    facts = _profile_facts(dataset, dataset_count)
    out = []
    for t in TASK_REGISTRY:
        # Hide multi-dataset-only tasks when only one dataset — show as unavailable instead of hide
        avail = evaluate_availability(t, facts)
        item = {
            **{k: v for k, v in asdict(t).items()},
            "availability": avail["status"],
            "availability_reasons": avail["reasons"],
            "can_start": avail["can_start"],
            "facts_snapshot": {
                "measures": facts["measure_names"],
                "dimensions": facts["dimension_names"],
                "dates": facts["date_names"],
            },
        }
        out.append(item)
    return out


def recommend_tasks(dataset: dict[str, Any], dataset_count: int = 1, limit: int = 5) -> list[dict[str, Any]]:
    facts = _profile_facts(dataset, dataset_count)
    scored: list[tuple[int, dict[str, Any]]] = []
    for t in TASK_REGISTRY:
        if not _rule(facts, t.recommend_if):
            continue
        avail = evaluate_availability(t, facts)
        if avail["status"] == "unavailable":
            continue
        score = 10
        if t.id == "analyze":
            score = 20
        if t.recommend_if == "looks_like_sales" and facts["looks_like_sales"]:
            score = 18
        if t.recommend_if == "has_date_and_measure" and facts["has_date"]:
            score = 16
        if t.recommend_if == "has_quality_issues" and facts["has_quality_issues"]:
            score = 17
        if t.recommend_if == "multi_dataset" and facts["dataset_count"] >= 2:
            score = 15
        title = t.name
        blurb = t.description
        # contextual blurbs
        if t.id == "monthly_trend" and facts["date_names"] and facts["measure_names"]:
            blurb = f"Track {facts['measure_names'][0]} over {facts['date_names'][0]}."
        if t.id == "top_n" and facts["dimension_names"] and facts["measure_names"]:
            blurb = f"Rank {facts['dimension_names'][0]} by {facts['measure_names'][0]}."
        if t.id == "sales_dashboard":
            blurb = "Build a sales dashboard using your revenue and category fields."
        scored.append(
            (
                score,
                {
                    "task_id": t.id,
                    "name": title,
                    "description": blurb,
                    "category": t.category,
                    "availability": avail["status"],
                    "icon": t.icon,
                    "color": t.color,
                },
            )
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    # unique by task_id
    seen = set()
    recs = []
    for _, r in scored:
        if r["task_id"] in seen:
            continue
        seen.add(r["task_id"])
        recs.append(r)
        if len(recs) >= limit:
            break
    return recs


def search_tasks(query: str, dataset: dict[str, Any] | None = None, dataset_count: int = 1) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return list_tasks_for_dataset(dataset or {}, dataset_count) if dataset else [asdict(t) for t in TASK_REGISTRY]

    facts = _profile_facts(dataset, dataset_count) if dataset else None
    hits = []
    for t in TASK_REGISTRY:
        blob = " ".join([t.id, t.name, t.category, t.description, " ".join(t.examples), " ".join(t.keywords)]).lower()
        if q in blob or any(k in q or q in k for k in t.keywords):
            item = asdict(t)
            if facts:
                avail = evaluate_availability(t, facts)
                item["availability"] = avail["status"]
                item["availability_reasons"] = avail["reasons"]
                item["can_start"] = avail["can_start"]
            hits.append(item)
    return hits


def classify_intent(text: str) -> dict[str, Any]:
    """Basic modular intent layer — replaceable by AI later."""
    q = (text or "").strip().lower()
    if not q:
        return {"intent": None, "task_id": None, "confidence": 0, "message": "Enter a request."}

    rules: list[tuple[list[str], str, float]] = [
        (["duplicate", "duplicates"], "find_duplicates", 0.9),
        (["clean", "missing", "blank", "spaces"], "clean", 0.85),
        (["dashboard"], "dashboard", 0.9),
        (["sales dashboard", "revenue dashboard"], "sales_dashboard", 0.92),
        (["chart", "graph", "plot", "visual"], "charts", 0.88),
        (["pivot"], "pivot", 0.9),
        (["report"], "reports", 0.85),
        (["compare", " vs ", "versus", "difference between"], "compare", 0.88),
        (["match", "lookup", "join", "vlookup", "xlookup"], "lookup", 0.87),
        (["top ", "highest", "best", "bottom "], "top_n", 0.86),
        (["monthly", "trend", "over time"], "monthly_trend", 0.86),
        (["sum", "average", "total", "calculate", "growth", "profit", "margin", "percentage"], "calculate", 0.84),
        (["summarize", "by region", "by product", "group"], "summarize", 0.84),
        (["analyze", "insights", "what is interesting"], "analyze", 0.8),
    ]
    for keys, task_id, conf in rules:
        if any(k in q for k in keys):
            task = next((t for t in TASK_REGISTRY if t.id == task_id), None)
            return {
                "intent": task.category if task else task_id,
                "task_id": task_id,
                "task_name": task.name if task else task_id,
                "confidence": conf,
                "message": f"Mapped to “{task.name if task else task_id}”.",
                "query": text,
            }
    return {
        "intent": "analyze",
        "task_id": "analyze",
        "task_name": "Analyze My Data",
        "confidence": 0.45,
        "message": "Could not match a specific task — defaulting to Analyze My Data.",
        "query": text,
    }


def get_task(task_id: str) -> dict[str, Any] | None:
    t = next((x for x in TASK_REGISTRY if x.id == task_id), None)
    return asdict(t) if t else None
