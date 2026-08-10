"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AnalysisResult,
  DatasetProfile,
  TemplateItem,
  exportWorkbook,
  getTemplates,
  healthCheck,
  postAnalysis,
  refreshSession,
  uploadFile,
} from "@/lib/api";
import { ResultPanel } from "@/components/ResultPanel";
import { DataPreview } from "@/components/DataPreview";

type Objective =
  | "calculate"
  | "compare"
  | "lookup"
  | "clean"
  | "summarize"
  | "pivot"
  | "chart"
  | "dashboard"
  | "analyze"
  | "find"
  | "report"
  | "ask"
  | "templates"
  | "growth"
  | "conditional"
  | "math";

const OBJECTIVES: { id: Objective; label: string; desc: string; icon: string }[] = [
  { id: "analyze", label: "Analyze Data", desc: "Auto insights like an analyst", icon: "◎" },
  { id: "ask", label: "Ask the Data", desc: "Natural language questions", icon: "?" },
  { id: "templates", label: "Templates", desc: "Sales, finance, CRM playbooks", icon: "▣" },
  { id: "calculate", label: "Calculate", desc: "Totals, averages, growth %", icon: "Σ" },
  { id: "conditional", label: "SUMIF / COUNTIF", desc: "Conditional Excel-style metrics", icon: "ƒ" },
  { id: "math", label: "Row Math", desc: "Revenue − Cost, ratios, flags", icon: "±" },
  { id: "compare", label: "Compare", desc: "Region, product, period vs period", icon: "↔" },
  { id: "lookup", label: "Lookup / Match", desc: "XLOOKUP-style value search", icon: "⌕" },
  { id: "clean", label: "Clean Data", desc: "Duplicates, blanks, text fixes", icon: "✦" },
  { id: "summarize", label: "Summarize", desc: "Group-by summaries", icon: "▤" },
  { id: "pivot", label: "Create Pivot", desc: "Rows × columns × values", icon: "⬚" },
  { id: "chart", label: "Create Chart", desc: "Bar, line, pie visualizations", icon: "▤" },
  { id: "dashboard", label: "Build Dashboard", desc: "KPIs + multi-chart boards", icon: "◈" },
  { id: "growth", label: "Growth / YTD", desc: "MoM trends and year-to-date", icon: "%" },
  { id: "find", label: "Find", desc: "Problems, top 10, bottom 10", icon: "!" },
  { id: "report", label: "Create Report", desc: "Executive summary & findings", icon: "☰" },
];

const METRICS = ["sum", "average", "count", "min", "max", "median"];
const CHART_TYPES = ["bar", "column", "line", "pie", "donut", "area"];
const DASHBOARD_TYPES = ["sales", "inventory", "finance", "crm", "marketing", "hr", "operations", "custom"];

export default function HomePage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [objective, setObjective] = useState<Objective | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [templates, setTemplates] = useState<Record<string, TemplateItem[]>>({});
  const [templateId, setTemplateId] = useState("sales_dashboard");

  const [column, setColumn] = useState("");
  const [groupBy, setGroupBy] = useState("");
  const [filterColumn, setFilterColumn] = useState("");
  const [filterValue, setFilterValue] = useState("");
  const [metric, setMetric] = useState("sum");
  const [valueColumn, setValueColumn] = useState("");
  const [dimensionColumn, setDimensionColumn] = useState("");
  const [leftValue, setLeftValue] = useState("");
  const [rightValue, setRightValue] = useState("");
  const [categoryColumn, setCategoryColumn] = useState("");
  const [chartType, setChartType] = useState("bar");
  const [pivotRows, setPivotRows] = useState("");
  const [pivotCols, setPivotCols] = useState("");
  const [dashboardType, setDashboardType] = useState("sales");
  const [question, setQuestion] = useState("Who are my top 10 customers?");
  const [dateColumn, setDateColumn] = useState("");
  const [lookupValue, setLookupValue] = useState("");
  const [lookupColumn, setLookupColumn] = useState("");
  const [returnColumn, setReturnColumn] = useState("");
  const [growthMode, setGrowthMode] = useState<"mom" | "ytd" | "enrich">("mom");
  const [findType, setFindType] = useState("problems");
  const [condFn, setCondFn] = useState("sumif");
  const [criteriaColumn, setCriteriaColumn] = useState("");
  const [criteriaValue, setCriteriaValue] = useState("");
  const [mathLeft, setMathLeft] = useState("");
  const [mathRight, setMathRight] = useState("");
  const [mathOp, setMathOp] = useState("-");
  const [mathResult, setMathResult] = useState("Profit");

  useEffect(() => {
    healthCheck().then(setApiOk);
    getTemplates()
      .then((t) => setTemplates(t.templates || {}))
      .catch(() => setTemplates({}));
  }, []);

  const columns = useMemo(() => profile?.column_profiles.map((c) => c.name) || [], [profile]);
  const numericCols = useMemo(
    () => profile?.column_profiles.filter((c) => c.is_numeric).map((c) => c.name) || [],
    [profile]
  );

  function seedDefaults(p: DatasetProfile) {
    const nums = p.column_profiles.filter((c) => c.is_numeric);
    const cats = p.column_profiles.filter((c) => c.is_categorical || c.inferred_type === "text");
    const dates = p.column_profiles.filter((c) => c.is_datetime);
    const money = nums.find((c) => /revenue|sales|amount|total/i.test(c.name)) || nums[0];
    const cat = cats.find((c) => /product|customer|region|category/i.test(c.name)) || cats[0];
    const idCol = p.column_profiles.find((c) => c.is_id_like || /order|id/i.test(c.name));
    setColumn(money?.name || "");
    setValueColumn(money?.name || "");
    setCategoryColumn(cat?.name || "");
    setGroupBy(cat?.name || "");
    setDimensionColumn(cat?.name || "");
    setPivotRows(cat?.name || "");
    setDateColumn(dates[0]?.name || "");
    setLookupColumn(idCol?.name || columns[0] || "");
    setReturnColumn(money?.name || "");
    setCriteriaColumn(cat?.name || "");
    setMathLeft(money?.name || "");
    const cost = nums.find((c) => /cost|cogs|expense/i.test(c.name));
    setMathRight(cost?.name || nums[1]?.name || "");
  }

  async function onUpload(file: File | null) {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const p = await uploadFile(file);
      setProfile(p);
      seedDefaults(p);
      setStep(2);
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function runAnalysis() {
    if (!profile || !objective) return;
    setLoading(true);
    setError(null);
    try {
      const sid = profile.session_id;
      let res: AnalysisResult;

      switch (objective) {
        case "calculate":
          res = await postAnalysis("calculate", {
            session_id: sid,
            column,
            metric,
            group_by: groupBy || null,
            filter_column: filterColumn || null,
            filter_value: filterValue || null,
          });
          break;
        case "compare":
          res = await postAnalysis("compare", {
            session_id: sid,
            value_column: valueColumn,
            dimension_column: dimensionColumn,
            metric,
            left_value: leftValue || null,
            right_value: rightValue || null,
          });
          break;
        case "lookup":
          res = await postAnalysis("lookup", {
            session_id: sid,
            lookup_value: lookupValue,
            lookup_column: lookupColumn,
            return_column: returnColumn,
            exact: true,
          });
          break;
        case "clean":
          res = await postAnalysis("clean", {
            session_id: sid,
            actions: ["all"],
            case_mode: "title",
          });
          {
            const refreshed = await refreshSession(sid);
            setProfile(refreshed);
          }
          break;
        case "summarize":
          res = await postAnalysis("summarize", {
            session_id: sid,
            group_by: groupBy ? [groupBy] : [],
            value_column: valueColumn,
            metric,
            top_n: 20,
          });
          break;
        case "pivot":
          res = await postAnalysis("pivot", {
            session_id: sid,
            rows: pivotRows ? [pivotRows] : [],
            columns: pivotCols ? [pivotCols] : [],
            values: valueColumn,
            aggregation: metric,
          });
          break;
        case "chart":
          res = await postAnalysis("chart", {
            session_id: sid,
            chart_type: chartType,
            category_column: categoryColumn,
            value_column: valueColumn,
            metric,
            top_n: 10,
          });
          break;
        case "dashboard":
          res = await postAnalysis("dashboard", {
            session_id: sid,
            dashboard_type: dashboardType,
            date_column: dateColumn || null,
            value_column: valueColumn || null,
            category_column: categoryColumn || null,
            product_column: categoryColumn || null,
            region_column: dimensionColumn || null,
          });
          break;
        case "analyze":
          res = await postAnalysis("analyze", {
            session_id: sid,
            date_column: dateColumn || null,
            value_column: valueColumn || null,
            category_column: categoryColumn || null,
          });
          break;
        case "find":
          res = await postAnalysis("find", {
            session_id: sid,
            find_type: findType,
            column: valueColumn || null,
            n: 10,
          });
          break;
        case "conditional":
          res = await postAnalysis("conditional", {
            session_id: sid,
            function: condFn,
            criteria_column: criteriaColumn,
            criteria_value: criteriaValue,
            value_column: valueColumn,
            op: "=",
          });
          break;
        case "math":
          res = await postAnalysis("math", {
            session_id: sid,
            left_column: mathLeft,
            operator: mathOp,
            right_column: mathRight || null,
            result_name: mathResult,
            persist: true,
          });
          {
            const refreshed = await refreshSession(sid);
            setProfile(refreshed);
          }
          break;
        case "report":
          res = await postAnalysis("report", {
            session_id: sid,
            report_type: "monthly_sales",
            date_column: dateColumn || null,
            value_column: valueColumn || null,
            category_column: categoryColumn || null,
          });
          break;
        case "ask":
          res = await postAnalysis("ask", { session_id: sid, question });
          break;
        case "templates":
          res = await postAnalysis("templates/run", {
            session_id: sid,
            template_id: templateId,
          });
          break;
        case "growth":
          if (growthMode === "enrich") {
            res = await postAnalysis("enrich-dates", {
              session_id: sid,
              date_column: dateColumn,
            });
            const refreshed = await refreshSession(sid);
            setProfile(refreshed);
          } else if (growthMode === "ytd") {
            res = await postAnalysis("ytd", {
              session_id: sid,
              date_column: dateColumn,
              value_column: valueColumn,
              freq: "M",
            });
          } else {
            res = await postAnalysis("growth", {
              session_id: sid,
              date_column: dateColumn,
              value_column: valueColumn,
              freq: "M",
            });
          }
          break;
        default:
          throw new Error("Unknown objective");
      }

      setResult(res);
      setStep(4);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function onExport() {
    if (!profile) return;
    setLoading(true);
    try {
      const blob = await exportWorkbook(profile.session_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `excellent_${profile.filename.replace(/\.\w+$/, "")}_analysis.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-500">
            EXCEL-lent
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-brand-800 sm:text-4xl">
            Data Analyst Engine
          </h1>
          <p className="mt-2 max-w-xl text-slate-600">
            Your data analyst, built into Excel.{" "}
            <span className="font-medium text-brand-700">Upload. Ask. Analyze.</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-full ${
                    step >= s ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {s}
                </span>
                {s < 4 && <span className="hidden h-px w-6 bg-slate-200 sm:block" />}
              </div>
            ))}
          </div>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
              apiOk === null
                ? "bg-slate-100 text-slate-500"
                : apiOk
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-rose-50 text-rose-700"
            }`}
          >
            API {apiOk === null ? "checking…" : apiOk ? "online" : "offline — start backend :8000"}
          </span>
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {step === 1 && (
        <section className="card p-8 sm:p-12">
          <h2 className="text-center text-2xl font-bold text-brand-800">
            Welcome to Data Analyst Engine
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-center text-slate-600">
            Upload Excel or CSV — no formulas, pivots, or charts knowledge required.
          </p>

          <label className="group mx-auto mt-10 flex max-w-2xl cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-brand-200 bg-brand-50/50 px-6 py-14 transition hover:border-brand-500 hover:bg-brand-50">
            <span className="text-4xl text-brand-600">↑</span>
            <span className="mt-3 text-lg font-semibold text-brand-800">Upload Excel or CSV</span>
            <span className="mt-1 text-sm text-slate-500">.xlsx · .xls · .xlsm · .csv (max 50 MB)</span>
            <input
              type="file"
              accept=".xlsx,.xls,.xlsm,.csv,.txt"
              className="hidden"
              disabled={loading}
              onChange={(e) => onUpload(e.target.files?.[0] || null)}
            />
          </label>

          {loading && (
            <p className="mt-6 text-center text-sm font-medium text-brand-600">Profiling your data…</p>
          )}

          <div className="mx-auto mt-10 grid max-w-2xl gap-3 sm:grid-cols-3">
            {["Calculate without formulas", "One-click dashboards", "Ask questions in plain English"].map(
              (t) => (
                <div key={t} className="rounded-xl bg-slate-50 px-3 py-3 text-center text-xs font-medium text-slate-600">
                  {t}
                </div>
              )
            )}
          </div>
        </section>
      )}

      {step === 2 && profile && (
        <section className="space-y-6">
          <div className="card flex flex-wrap items-center justify-between gap-3 p-5">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Loaded</p>
              <p className="font-semibold text-brand-800">{profile.filename}</p>
              <p className="text-sm text-slate-500">
                {profile.rows.toLocaleString()} rows · {profile.columns} columns
                {profile.active_sheet ? ` · sheet: ${profile.active_sheet}` : ""}
              </p>
            </div>
            <button className="btn-secondary" onClick={() => setStep(1)}>
              Upload different file
            </button>
          </div>

          <DataPreview profile={profile} />

          <h2 className="text-xl font-bold text-brand-800">I want to…</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {OBJECTIVES.map((o) => (
              <button
                key={o.id}
                className={`card p-5 text-left transition hover:-translate-y-0.5 hover:border-brand-300 ${
                  objective === o.id ? "ring-2 ring-brand-500" : ""
                }`}
                onClick={() => {
                  setObjective(o.id);
                  setStep(3);
                }}
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-lg font-bold text-brand-700">
                  {o.icon}
                </span>
                <p className="mt-3 font-semibold text-slate-900">{o.label}</p>
                <p className="mt-1 text-sm text-slate-500">{o.desc}</p>
              </button>
            ))}
          </div>
        </section>
      )}

      {step === 3 && profile && objective && (
        <section className="grid gap-6 lg:grid-cols-5">
          <div className="card p-6 lg:col-span-3">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase text-brand-500">Configure</p>
                <h2 className="text-xl font-bold text-brand-800">
                  {OBJECTIVES.find((o) => o.id === objective)?.label}
                </h2>
              </div>
              <button className="btn-secondary" onClick={() => setStep(2)}>
                Change objective
              </button>
            </div>

            {objective === "ask" && (
              <div>
                <label className="label">What do you want to know?</label>
                <textarea
                  className="input min-h-[120px]"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  {[
                    "Who are my top 10 customers?",
                    "Show me monthly revenue",
                    "Find duplicate records",
                    "Create a sales dashboard",
                    "Compare Dubai and Abu Dhabi",
                    "Analyze my data",
                  ].map((q) => (
                    <button
                      key={q}
                      type="button"
                      className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 hover:border-brand-300"
                      onClick={() => setQuestion(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {objective === "templates" && (
              <div className="space-y-4">
                <p className="text-sm text-slate-600">
                  Pick a ready-made analytical template. Columns are auto-detected.
                </p>
                <div className="space-y-4">
                  {Object.entries(templates).map(([domain, items]) => (
                    <div key={domain}>
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                        {domain}
                      </p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {items.map((t) => (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => setTemplateId(t.id)}
                            className={`rounded-xl border px-3 py-3 text-left text-sm transition ${
                              templateId === t.id
                                ? "border-brand-500 bg-brand-50 ring-1 ring-brand-500"
                                : "border-slate-200 hover:border-brand-300"
                            }`}
                          >
                            <p className="font-semibold text-slate-900">{t.name}</p>
                            <p className="mt-0.5 text-xs text-slate-500">{t.desc}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {!Object.keys(templates).length && (
                    <p className="text-sm text-amber-700">
                      Templates API offline — start the backend, then refresh.
                    </p>
                  )}
                </div>
              </div>
            )}

            {objective === "lookup" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Lookup column" value={lookupColumn} onChange={setLookupColumn} options={columns} />
                <div>
                  <label className="label">Lookup value</label>
                  <input className="input" value={lookupValue} onChange={(e) => setLookupValue(e.target.value)} placeholder="e.g. ORD-1001" />
                </div>
                <FieldSelect label="Return column" value={returnColumn} onChange={setReturnColumn} options={columns} />
              </div>
            )}

            {objective === "growth" && (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {(
                    [
                      ["mom", "Month-over-month growth"],
                      ["ytd", "Year-to-date total"],
                      ["enrich", "Add day/month/quarter/FY columns"],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                        growthMode === id ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                      }`}
                      onClick={() => setGrowthMode(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <FieldSelect label="Date column" value={dateColumn} onChange={setDateColumn} options={columns} />
                  {growthMode !== "enrich" && (
                    <FieldSelect
                      label="Value column"
                      value={valueColumn}
                      onChange={setValueColumn}
                      options={numericCols.length ? numericCols : columns}
                    />
                  )}
                </div>
              </div>
            )}

            {objective === "clean" && (
              <p className="text-sm text-slate-600">
                Trim spaces, fix numbers-as-text, parse dates, fill blanks, remove duplicates.
              </p>
            )}

            {objective === "find" && (
              <div className="space-y-4">
                <FieldSelect
                  label="Find type"
                  value={findType}
                  onChange={setFindType}
                  options={["problems", "duplicates", "top", "bottom", "outliers"]}
                />
                {(findType === "top" || findType === "bottom" || findType === "outliers") && (
                  <FieldSelect
                    label="Value column"
                    value={valueColumn}
                    onChange={setValueColumn}
                    options={numericCols.length ? numericCols : columns}
                  />
                )}
              </div>
            )}

            {objective === "conditional" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect
                  label="Function"
                  value={condFn}
                  onChange={setCondFn}
                  options={["sumif", "countif", "averageif"]}
                />
                <FieldSelect label="Criteria column" value={criteriaColumn} onChange={setCriteriaColumn} options={columns} />
                <div>
                  <label className="label">Criteria value</label>
                  <input
                    className="input"
                    value={criteriaValue}
                    onChange={(e) => setCriteriaValue(e.target.value)}
                    placeholder="e.g. Dubai"
                  />
                </div>
                {condFn !== "countif" && (
                  <FieldSelect
                    label="Value column"
                    value={valueColumn}
                    onChange={setValueColumn}
                    options={numericCols.length ? numericCols : columns}
                  />
                )}
              </div>
            )}

            {objective === "math" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Left column" value={mathLeft} onChange={setMathLeft} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Operator" value={mathOp} onChange={setMathOp} options={["-", "+", "*", "/", "%"]} />
                <FieldSelect label="Right column" value={mathRight} onChange={setMathRight} options={numericCols.length ? numericCols : columns} />
                <div>
                  <label className="label">Result column name</label>
                  <input className="input" value={mathResult} onChange={(e) => setMathResult(e.target.value)} />
                </div>
                <p className="sm:col-span-2 text-sm text-slate-600">
                  Example: Revenue − Cost = Profit (saved back into your session for further analysis).
                </p>
              </div>
            )}

            {(objective === "analyze" || objective === "report") && (
              <div className="grid gap-4 sm:grid-cols-3">
                <FieldSelect label="Value column" value={valueColumn} onChange={setValueColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Category" value={categoryColumn} onChange={setCategoryColumn} options={columns} allowEmpty />
                <FieldSelect label="Date" value={dateColumn} onChange={setDateColumn} options={columns} allowEmpty />
              </div>
            )}

            {objective === "dashboard" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Dashboard type" value={dashboardType} onChange={setDashboardType} options={DASHBOARD_TYPES} />
                <FieldSelect label="Value / revenue" value={valueColumn} onChange={setValueColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Category / product" value={categoryColumn} onChange={setCategoryColumn} options={columns} allowEmpty />
                <FieldSelect label="Region / dimension" value={dimensionColumn} onChange={setDimensionColumn} options={columns} allowEmpty />
                <FieldSelect label="Date" value={dateColumn} onChange={setDateColumn} options={columns} allowEmpty />
              </div>
            )}

            {objective === "pivot" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Rows" value={pivotRows} onChange={setPivotRows} options={columns} allowEmpty />
                <FieldSelect label="Columns" value={pivotCols} onChange={setPivotCols} options={columns} allowEmpty />
                <FieldSelect label="Values" value={valueColumn} onChange={setValueColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Calculation" value={metric} onChange={setMetric} options={METRICS} />
              </div>
            )}

            {objective === "chart" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Chart type" value={chartType} onChange={setChartType} options={CHART_TYPES} />
                <FieldSelect label="Category" value={categoryColumn} onChange={setCategoryColumn} options={columns} />
                <FieldSelect label="Value" value={valueColumn} onChange={setValueColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Metric" value={metric} onChange={setMetric} options={METRICS} />
              </div>
            )}

            {objective === "compare" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Value column" value={valueColumn} onChange={setValueColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Compare by" value={dimensionColumn} onChange={setDimensionColumn} options={columns} />
                <FieldSelect label="Metric" value={metric} onChange={setMetric} options={METRICS} />
                <div>
                  <label className="label">Left value (optional)</label>
                  <input className="input" value={leftValue} onChange={(e) => setLeftValue(e.target.value)} placeholder="e.g. Dubai" />
                </div>
                <div>
                  <label className="label">Right value (optional)</label>
                  <input className="input" value={rightValue} onChange={(e) => setRightValue(e.target.value)} placeholder="e.g. Abu Dhabi" />
                </div>
              </div>
            )}

            {objective === "summarize" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Group by" value={groupBy} onChange={setGroupBy} options={columns} />
                <FieldSelect label="Value" value={valueColumn} onChange={setValueColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Metric" value={metric} onChange={setMetric} options={METRICS} />
              </div>
            )}

            {objective === "calculate" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldSelect label="Column" value={column} onChange={setColumn} options={numericCols.length ? numericCols : columns} />
                <FieldSelect label="Metric" value={metric} onChange={setMetric} options={METRICS} />
                <FieldSelect label="Group by" value={groupBy} onChange={setGroupBy} options={columns} allowEmpty />
                <FieldSelect label="Filter column" value={filterColumn} onChange={setFilterColumn} options={columns} allowEmpty />
                <div>
                  <label className="label">Filter value</label>
                  <input className="input" value={filterValue} onChange={(e) => setFilterValue(e.target.value)} placeholder="e.g. UAE" />
                </div>
              </div>
            )}

            <div className="mt-8 flex flex-wrap gap-3">
              <button className="btn-primary" disabled={loading} onClick={runAnalysis}>
                {loading ? "Working…" : "Create analysis"}
              </button>
              <button className="btn-secondary" onClick={() => setStep(2)}>
                Back
              </button>
            </div>
          </div>

          <aside className="space-y-4 lg:col-span-2">
            <div className="card p-5">
              <h3 className="font-semibold text-brand-800">Detected columns</h3>
              <ul className="mt-3 max-h-96 space-y-2 overflow-auto text-sm">
                {profile.column_profiles.map((c) => (
                  <li
                    key={c.name}
                    className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"
                  >
                    <span className="font-medium text-slate-800">{c.name}</span>
                    <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500 ring-1 ring-slate-200">
                      {c.inferred_type}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        </section>
      )}

      {step === 4 && result && profile && (
        <section>
          <div className="mb-6 flex flex-wrap gap-3">
            <button className="btn-primary" onClick={onExport} disabled={loading}>
              Download Excel report
            </button>
            <button className="btn-secondary" onClick={() => setStep(3)}>
              Reconfigure
            </button>
            <button className="btn-secondary" onClick={() => setStep(2)}>
              New objective
            </button>
            <button
              className="btn-accent"
              onClick={() => {
                setStep(1);
                setProfile(null);
                setResult(null);
                setObjective(null);
              }}
            >
              Start over
            </button>
          </div>
          <ResultPanel result={result} />
        </section>
      )}

      <footer className="mt-16 border-t border-slate-200/80 pt-6 text-center text-xs text-slate-400">
        EXCEL-lent · Unlock Excel for everyone ·{" "}
        <a
          className="text-brand-600 hover:underline"
          href="https://github.com/ktiwari54/EXCEL-lent"
          target="_blank"
          rel="noreferrer"
        >
          github.com/ktiwari54/EXCEL-lent
        </a>
      </footer>
    </div>
  );
}

function FieldSelect({
  label,
  value,
  onChange,
  options,
  allowEmpty,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  allowEmpty?: boolean;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">— none —</option>}
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
