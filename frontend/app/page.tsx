"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";
import {
  ArrowRight,
  BarChart3,
  Bell,
  Bot,
  Calculator,
  ChevronRight,
  ClipboardList,
  Database,
  FileSpreadsheet,
  FileText,
  Filter,
  HelpCircle,
  Home,
  LayoutDashboard,
  LineChart,
  MessageSquare,
  Monitor,
  RefreshCw,
  Scale,
  Search,
  Send,
  Settings,
  Sparkles,
  Table2,
  Upload,
  Wand2,
  Download,
  FolderOpen,
  Layers,
  Users,
  Package,
  Wallet,
  Megaphone,
  Contact,
} from "lucide-react";
import {
  AnalysisResult,
  DatasetProfile,
  exportWorkbook,
  getTemplates,
  healthCheck,
  postAnalysis,
  refreshSession,
  uploadFile,
  TemplateItem,
} from "@/lib/api";
import {
  HOME_ACTIONS,
  ObjectiveId,
  SIDEBAR_ANALYZE,
  SIDEBAR_SOLUTIONS,
  SUGGESTED_QUESTIONS,
} from "@/lib/objectives";
import { ResultPanel } from "@/components/ResultPanel";
import { DataPreview } from "@/components/DataPreview";
import { UploadZone } from "@/components/UploadZone";
import { FieldInput, FieldSelect, LoadingOverlay } from "@/components/ui";

type View = "home" | "upload" | "configure" | "result" | "explore";

const METRICS = ["sum", "average", "count", "min", "max", "median"];
const CHART_TYPES = ["bar", "column", "line", "pie", "donut", "area"];
const DASHBOARD_TYPES = ["sales", "inventory", "finance", "crm", "marketing", "hr", "operations", "custom"];

const ACTION_ICONS: Record<string, ReactNode> = {
  calculator: <Calculator className="h-5 w-5" />,
  scale: <Scale className="h-5 w-5" />,
  search: <Search className="h-5 w-5" />,
  broom: <Wand2 className="h-5 w-5" />,
  clipboard: <ClipboardList className="h-5 w-5" />,
  table: <Table2 className="h-5 w-5" />,
  chart: <BarChart3 className="h-5 w-5" />,
  monitor: <Monitor className="h-5 w-5" />,
  file: <FileText className="h-5 w-5" />,
  sparkles: <Sparkles className="h-5 w-5" />,
};

const SOLUTION_ICONS = [Users, Package, Wallet, Contact, Megaphone, LayoutDashboard];

export default function HomePage() {
  const [view, setView] = useState<View>("home");
  const [nav, setNav] = useState<string>("home");
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [objective, setObjective] = useState<ObjectiveId | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("Working…");
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [templates, setTemplates] = useState<Record<string, TemplateItem[]>>({});
  const [templateId, setTemplateId] = useState("sales_dashboard");
  const [askBox, setAskBox] = useState("");
  const [topAsk, setTopAsk] = useState("");

  // form fields
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

  const insightItems = useMemo(() => {
    if (!result) return [] as { text: string; tone: "green" | "amber" | "blue" | "violet" }[];
    const items: { text: string; tone: "green" | "amber" | "blue" | "violet" }[] = [];
    (result.alerts || []).slice(0, 2).forEach((t) => items.push({ text: t, tone: "amber" }));
    (result.insights || []).slice(0, 3).forEach((t, i) =>
      items.push({ text: t, tone: i % 2 === 0 ? "green" : "blue" })
    );
    return items.slice(0, 4);
  }, [result]);

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
    setLookupColumn(idCol?.name || p.column_profiles[0]?.name || "");
    setReturnColumn(money?.name || "");
    setCriteriaColumn(cat?.name || "");
    setMathLeft(money?.name || "");
    const cost = nums.find((c) => /cost|cogs|expense/i.test(c.name));
    setMathRight(cost?.name || nums[1]?.name || "");
  }

  function requireData(next: () => void) {
    if (!profile) {
      setError("Upload a data file first — then you can analyze it.");
      setView("upload");
      setNav("upload");
      return;
    }
    setError(null);
    next();
  }

  async function onUpload(file: File) {
    setLoading(true);
    setLoadingLabel("Reading your file…");
    setError(null);
    try {
      const p = await uploadFile(file);
      setProfile(p);
      seedDefaults(p);
      setResult(null);
      setView("home");
      setNav("home");
      // auto-analyze lightly for home KPIs
      setLoadingLabel("Preparing insights…");
      try {
        const res = await postAnalysis("analyze", { session_id: p.session_id });
        setResult(res);
      } catch {
        /* optional */
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  function openObjective(id: ObjectiveId) {
    if (id === "upload") {
      setView("upload");
      setNav("upload");
      return;
    }
    if (id === "home") {
      setView("home");
      setNav("home");
      return;
    }
    if (id === "ask") {
      requireData(() => {
        setObjective("ask");
        setView("configure");
        setNav("ask");
      });
      return;
    }
    requireData(() => {
      setObjective(id);
      setView("configure");
      setNav(id);
    });
  }

  async function runAsk(q: string) {
    requireData(async () => {
      setLoading(true);
      setLoadingLabel("Asking your data…");
      setError(null);
      try {
        const res = await postAnalysis("ask", {
          session_id: profile!.session_id,
          question: q,
        });
        setResult(res);
        setObjective("ask");
        setView("result");
        setNav("ask");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Ask failed");
      } finally {
        setLoading(false);
      }
    });
  }

  async function runTemplate(tid: string) {
    requireData(async () => {
      setLoading(true);
      setLoadingLabel("Running template…");
      setError(null);
      try {
        const res = await postAnalysis("templates/run", {
          session_id: profile!.session_id,
          template_id: tid,
        });
        setResult(res);
        setObjective("templates");
        setTemplateId(tid);
        setView("result");
        setNav("templates");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Template failed");
      } finally {
        setLoading(false);
      }
    });
  }

  async function runAnalysis() {
    if (!profile || !objective) return;
    setLoading(true);
    setLoadingLabel("Creating analysis…");
    setError(null);
    const sid = profile.session_id;
    try {
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
          res = await postAnalysis("clean", { session_id: sid, actions: ["all"], case_mode: "title" });
          setProfile(await refreshSession(sid));
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
          res = await postAnalysis("templates/run", { session_id: sid, template_id: templateId });
          break;
        case "growth":
          if (growthMode === "enrich") {
            res = await postAnalysis("enrich-dates", { session_id: sid, date_column: dateColumn });
            setProfile(await refreshSession(sid));
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
          setProfile(await refreshSession(sid));
          break;
        default:
          throw new Error("Unknown objective");
      }
      setResult(res!);
      setView("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function onExport() {
    if (!profile) return;
    setLoading(true);
    setLoadingLabel("Building Excel report…");
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

  async function refreshAnalyze() {
    if (!profile) return;
    setLoading(true);
    setLoadingLabel("Refreshing analysis…");
    try {
      const res = await postAnalysis("analyze", { session_id: profile.session_id });
      setResult(res);
      setView("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setLoading(false);
    }
  }

  const kpis = (result?.meta?.kpis as Record<string, number> | undefined) || null;

  return (
    <div className="app-shell">
      {loading && <LoadingOverlay label={loadingLabel} />}

      {/* ─── SIDEBAR ─── */}
      <aside className="sidebar">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-600 shadow-lg shadow-blue-900/40">
            <FileSpreadsheet className="h-5 w-5 text-white" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold leading-tight">Data Analyst Engine</p>
            <p className="truncate text-[11px] text-slate-400">Your Data. Our Intelligence.</p>
          </div>
        </div>

        <div className="sidebar-scroll">
          <button
            className={nav === "home" ? "nav-item-active" : "nav-item"}
            onClick={() => {
              setNav("home");
              setView("home");
            }}
          >
            <Home className="h-4 w-4" /> Home
          </button>
          <button
            className={nav === "upload" ? "nav-item-active" : "nav-item"}
            onClick={() => {
              setNav("upload");
              setView("upload");
            }}
          >
            <Upload className="h-4 w-4" /> Upload Data
          </button>
          <button
            className={nav === "explore" ? "nav-item-active" : "nav-item"}
            onClick={() => {
              setNav("explore");
              setView(profile ? "explore" : "upload");
            }}
          >
            <Database className="h-4 w-4" /> Explore Data
          </button>
          <button className={nav === "ask" ? "nav-item-active" : "nav-item"} onClick={() => openObjective("ask")}>
            <MessageSquare className="h-4 w-4" /> Ask & Analyze
          </button>

          <p className="nav-section">Analyze</p>
          {SIDEBAR_ANALYZE.map((item) => (
            <button
              key={item.id}
              className={nav === item.id ? "nav-item-active" : "nav-item"}
              onClick={() => openObjective(item.id)}
            >
              <ChevronRight className="h-3.5 w-3.5 opacity-50" />
              {item.label}
            </button>
          ))}

          <p className="nav-section">Solutions</p>
          {SIDEBAR_SOLUTIONS.map((s, i) => {
            const Icon = SOLUTION_ICONS[i % SOLUTION_ICONS.length];
            return (
              <button key={s.id} className="nav-item" onClick={() => runTemplate(s.id)}>
                <Icon className="h-4 w-4 opacity-80" />
                {s.label}
              </button>
            );
          })}

          <p className="nav-section">Settings</p>
          <button className="nav-item" onClick={() => openObjective("templates")}>
            <Layers className="h-4 w-4" /> Templates
          </button>
          <button className="nav-item" onClick={() => setView("upload")}>
            <FolderOpen className="h-4 w-4" /> Data Sources
          </button>
          <button className="nav-item opacity-60" title="Coming soon">
            <Settings className="h-4 w-4" /> My Workbooks
          </button>
        </div>

        <div className="border-t border-white/10 px-4 py-3">
          <div
            className={clsx(
              "flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium",
              apiOk ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"
            )}
          >
            <span className={clsx("h-2 w-2 rounded-full", apiOk ? "bg-emerald-400" : "bg-rose-400")} />
            {apiOk === null ? "Connecting…" : apiOk ? "Engine online" : "API offline :8000"}
          </div>
        </div>
      </aside>

      {/* ─── MAIN ─── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center gap-4 border-b border-slate-200/80 bg-white/90 px-6 py-3 backdrop-blur">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="w-full rounded-full border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
              placeholder="Ask your data anything…"
              value={topAsk}
              onChange={(e) => setTopAsk(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && topAsk.trim()) runAsk(topAsk.trim());
              }}
            />
          </div>
          <div className="hidden items-center gap-2 lg:flex">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button key={q} className="chip-soft" onClick={() => runAsk(q)}>
                {q}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1">
            <button className="btn-ghost h-10 w-10 rounded-full p-0" title="Notifications">
              <Bell className="h-4 w-4" />
            </button>
            <button className="btn-ghost h-10 w-10 rounded-full p-0" title="Help">
              <HelpCircle className="h-4 w-4" />
            </button>
            <div className="ml-1 flex items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                A
              </span>
              <span className="hidden text-sm font-medium text-slate-700 sm:inline">Admin User</span>
            </div>
          </div>
        </header>

        <main className="scroll-thin flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <span>{error}</span>
              <button className="font-semibold" onClick={() => setError(null)}>
                Dismiss
              </button>
            </div>
          )}

          <div className="mx-auto grid max-w-[1400px] gap-5 xl:grid-cols-[1fr_300px]">
            {/* CENTER */}
            <div className="min-w-0 space-y-5">
              {view === "upload" && (
                <section className="space-y-4">
                  <div>
                    <h1 className="text-2xl font-bold text-slate-900">Upload Data</h1>
                    <p className="muted mt-1">Import Excel or CSV — we profile it automatically.</p>
                  </div>
                  <UploadZone onFile={onUpload} loading={loading} />
                  {profile && (
                    <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{profile.filename}</p>
                        <p className="text-xs text-slate-500">
                          {profile.rows.toLocaleString()} rows · {profile.columns} columns loaded
                        </p>
                      </div>
                      <button className="btn-primary" onClick={() => setView("home")}>
                        Continue to Home <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </section>
              )}

              {view === "explore" && profile && (
                <section className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h1 className="text-2xl font-bold text-slate-900">Explore Data</h1>
                      <p className="muted mt-1">{profile.filename}</p>
                    </div>
                    <button className="btn-secondary" onClick={() => setView("upload")}>
                      Replace file
                    </button>
                  </div>
                  <DataPreview profile={profile} />
                  <div className="card p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-800">Detected columns</h3>
                    <div className="flex flex-wrap gap-2">
                      {profile.column_profiles.map((c) => (
                        <span key={c.name} className="chip-soft">
                          {c.name}
                          <span className="text-slate-400">· {c.inferred_type}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </section>
              )}

              {view === "configure" && objective && (
                <ConfigureView
                  objective={objective}
                  columns={columns}
                  numericCols={numericCols}
                  templates={templates}
                  values={{
                    column,
                    groupBy,
                    filterColumn,
                    filterValue,
                    metric,
                    valueColumn,
                    dimensionColumn,
                    leftValue,
                    rightValue,
                    categoryColumn,
                    chartType,
                    pivotRows,
                    pivotCols,
                    dashboardType,
                    question,
                    dateColumn,
                    lookupValue,
                    lookupColumn,
                    returnColumn,
                    growthMode,
                    findType,
                    condFn,
                    criteriaColumn,
                    criteriaValue,
                    mathLeft,
                    mathRight,
                    mathOp,
                    mathResult,
                    templateId,
                  }}
                  setters={{
                    setColumn,
                    setGroupBy,
                    setFilterColumn,
                    setFilterValue,
                    setMetric,
                    setValueColumn,
                    setDimensionColumn,
                    setLeftValue,
                    setRightValue,
                    setCategoryColumn,
                    setChartType,
                    setPivotRows,
                    setPivotCols,
                    setDashboardType,
                    setQuestion,
                    setDateColumn,
                    setLookupValue,
                    setLookupColumn,
                    setReturnColumn,
                    setGrowthMode,
                    setFindType,
                    setCondFn,
                    setCriteriaColumn,
                    setCriteriaValue,
                    setMathLeft,
                    setMathRight,
                    setMathOp,
                    setMathResult,
                    setTemplateId,
                  }}
                  onBack={() => setView("home")}
                  onRun={runAnalysis}
                  loading={loading}
                />
              )}

              {view === "result" && result && (
                <section className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h1 className="text-2xl font-bold text-slate-900">Analysis results</h1>
                      <p className="muted mt-1">{profile?.filename || "Your dataset"}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button className="btn-secondary" onClick={() => setView("configure")}>
                        Edit setup
                      </button>
                      <button className="btn-secondary" onClick={() => setView("home")}>
                        Home
                      </button>
                      <button className="btn-primary" onClick={onExport}>
                        <Download className="h-4 w-4" /> Export Report
                      </button>
                    </div>
                  </div>
                  <ResultPanel result={result} />
                </section>
              )}

              {view === "home" && (
                <>
                  {/* Steps */}
                  <section className="card p-5">
                    <h2 className="text-base font-bold text-slate-900">Get Started in 4 Simple Steps</h2>
                    <div className="mt-4 grid gap-3 md:grid-cols-4">
                      {[
                        {
                          n: "1",
                          title: "Upload Data",
                          desc: "Upload Excel/CSV file or connect data",
                          color: "bg-emerald-500",
                          icon: <Upload className="h-5 w-5" />,
                          action: () => {
                            setView("upload");
                            setNav("upload");
                          },
                        },
                        {
                          n: "2",
                          title: "Select Objective",
                          desc: "Choose what you want to do with your data",
                          color: "bg-violet-500",
                          icon: <Sparkles className="h-5 w-5" />,
                          action: () => {},
                        },
                        {
                          n: "3",
                          title: "Configure",
                          desc: "Select columns, filters and options",
                          color: "bg-blue-500",
                          icon: <Filter className="h-5 w-5" />,
                          action: () => {},
                        },
                        {
                          n: "4",
                          title: "Get Results",
                          desc: "Get analysis, charts and insights instantly",
                          color: "bg-orange-500",
                          icon: <LineChart className="h-5 w-5" />,
                          action: () => result && setView("result"),
                        },
                      ].map((s) => (
                        <button key={s.n} className="step-card text-left" onClick={s.action}>
                          <div className={clsx("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white", s.color)}>
                            {s.icon}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-900">
                              {s.n}. {s.title}
                            </p>
                            <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{s.desc}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </section>

                  {/* Actions */}
                  <section className="card p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <h2 className="text-base font-bold text-slate-900">What would you like to do?</h2>
                      {!profile && (
                        <button className="btn-primary" onClick={() => setView("upload")}>
                          <Upload className="h-4 w-4" /> Upload first
                        </button>
                      )}
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                      {HOME_ACTIONS.map((a) => (
                        <button key={a.id} className="action-tile" onClick={() => openObjective(a.id)}>
                          <div
                            className={clsx(
                              "mb-3 flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-sm",
                              a.color
                            )}
                          >
                            {ACTION_ICONS[a.icon]}
                          </div>
                          <p className="text-sm font-bold text-slate-900">{a.label}</p>
                          <p className="mt-1 text-xs leading-relaxed text-slate-500">{a.desc}</p>
                          {a.id === "analyze" && (
                            <span className="mt-2 inline-flex w-fit rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-blue-700">
                              New
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  </section>

                  {/* Recent analyses / KPIs */}
                  <section className="card p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <h2 className="text-base font-bold text-slate-900">
                        {profile ? "Recent Analyses" : "Sample dashboard preview"}
                      </h2>
                      {profile && (
                        <button className="text-xs font-semibold text-blue-600 hover:underline" onClick={refreshAnalyze}>
                          Refresh
                        </button>
                      )}
                    </div>

                    {!profile ? (
                      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-12 text-center">
                        <Upload className="mx-auto h-10 w-10 text-slate-300" />
                        <p className="mt-3 font-semibold text-slate-700">Upload data to unlock live KPIs</p>
                        <p className="mt-1 text-sm text-slate-500">
                          Revenue, orders, trends, and AI insights appear here automatically.
                        </p>
                        <button className="btn-primary mt-5" onClick={() => setView("upload")}>
                          Upload Excel / CSV
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
                          {(kpis
                            ? Object.entries(kpis).slice(0, 6)
                            : [
                                ["Rows", profile.rows],
                                ["Columns", profile.columns],
                                ["Duplicates", profile.duplicate_rows],
                                ["Missing cells", profile.missing_cells],
                              ]
                          ).map(([k, v]) => (
                            <div key={String(k)} className="kpi-card">
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                                {String(k)}
                              </p>
                              <p className="mt-1 text-xl font-bold text-slate-900">
                                {typeof v === "number"
                                  ? v.toLocaleString(undefined, { maximumFractionDigits: 2 })
                                  : String(v)}
                              </p>
                            </div>
                          ))}
                        </div>
                        {result && (
                          <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-3">
                            <ResultPanel result={result} />
                          </div>
                        )}
                      </>
                    )}
                  </section>

                  {/* Bottom ask + quick actions */}
                  <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
                    <div className="card p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
                          <Bot className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-900">Ask Anything About Your Data</p>
                          <p className="text-xs text-slate-500">Plain English — no Excel knowledge needed</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <input
                          className="input"
                          placeholder='Ask a question like: Show me top 10 customers by sales in Dubai'
                          value={askBox}
                          onChange={(e) => setAskBox(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && askBox.trim()) runAsk(askBox.trim());
                          }}
                        />
                        <button
                          className="btn-primary shrink-0 px-4"
                          onClick={() => askBox.trim() && runAsk(askBox.trim())}
                        >
                          <Send className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    <div className="card p-5">
                      <p className="mb-3 text-sm font-bold text-slate-900">Quick Actions</p>
                      <div className="grid grid-cols-2 gap-2">
                        <button className="btn-soft justify-start" onClick={refreshAnalyze}>
                          <RefreshCw className="h-4 w-4" /> Refresh Data
                        </button>
                        <button className="btn-soft justify-start" onClick={() => openObjective("dashboard")}>
                          <LayoutDashboard className="h-4 w-4" /> Create Dashboard
                        </button>
                        <button className="btn-soft justify-start" onClick={onExport} disabled={!profile}>
                          <Download className="h-4 w-4" /> Export Report
                        </button>
                        <button className="btn-soft justify-start" onClick={() => openObjective("analyze")}>
                          <Sparkles className="h-4 w-4" /> Analyze (AI)
                        </button>
                      </div>
                    </div>
                  </section>
                </>
              )}
            </div>

            {/* RIGHT RAIL */}
            <aside className="space-y-4 xl:sticky xl:top-0 xl:self-start">
              <div className="card p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm font-bold text-slate-900">AI Insights</p>
                  <button className="text-xs font-semibold text-blue-600" onClick={() => result && setView("result")}>
                    View all
                  </button>
                </div>
                {insightItems.length === 0 ? (
                  <p className="text-xs leading-relaxed text-slate-500">
                    Upload data and run <strong>Analyze (AI)</strong> to see smart insights here.
                  </p>
                ) : (
                  <ul className="space-y-2.5">
                    {insightItems.map((item, i) => (
                      <li
                        key={i}
                        className={clsx(
                          "rounded-xl px-3 py-2.5 text-xs leading-relaxed",
                          item.tone === "green" && "bg-emerald-50 text-emerald-900",
                          item.tone === "amber" && "bg-amber-50 text-amber-900",
                          item.tone === "blue" && "bg-blue-50 text-blue-900",
                          item.tone === "violet" && "bg-violet-50 text-violet-900"
                        )}
                      >
                        {item.text}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="card p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm font-bold text-slate-900">Recent Files</p>
                </div>
                {profile ? (
                  <div className="flex items-start gap-3 rounded-xl bg-slate-50 px-3 py-2.5">
                    <FileSpreadsheet className="mt-0.5 h-5 w-5 text-emerald-600" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-800">{profile.filename}</p>
                      <p className="text-[11px] text-slate-500">
                        {profile.rows.toLocaleString()} rows · active session
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No files yet. Upload Excel or CSV to begin.</p>
                )}
              </div>

              <div className="card p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm font-bold text-slate-900">Applied Filters</p>
                  <button
                    className="text-xs font-semibold text-blue-600"
                    onClick={() => {
                      setFilterColumn("");
                      setFilterValue("");
                    }}
                  >
                    Clear All
                  </button>
                </div>
                <div className="space-y-2">
                  <FilterChip label="Data source" value={profile?.filename || "None"} tone="blue" />
                  <FilterChip label="Value column" value={valueColumn || "Auto"} tone="green" />
                  <FilterChip label="Category" value={categoryColumn || "Auto"} tone="orange" />
                  <FilterChip label="Date" value={dateColumn || "Auto"} tone="violet" />
                </div>
              </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}

function FilterChip({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "blue" | "green" | "orange" | "violet";
}) {
  const tones = {
    blue: "bg-blue-50 text-blue-800",
    green: "bg-emerald-50 text-emerald-800",
    orange: "bg-orange-50 text-orange-800",
    violet: "bg-violet-50 text-violet-800",
  };
  return (
    <div className={clsx("rounded-xl px-3 py-2", tones[tone])}>
      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="truncate text-xs font-semibold">{value}</p>
    </div>
  );
}

function ConfigureView({
  objective,
  columns,
  numericCols,
  templates,
  values,
  setters,
  onBack,
  onRun,
  loading,
}: {
  objective: ObjectiveId;
  columns: string[];
  numericCols: string[];
  templates: Record<string, TemplateItem[]>;
  values: Record<string, string>;
  setters: Record<string, (v: any) => void>;
  onBack: () => void;
  onRun: () => void;
  loading: boolean;
}) {
  const title =
    HOME_ACTIONS.find((a) => a.id === objective)?.label ||
    SIDEBAR_ANALYZE.find((a) => a.id === objective)?.label ||
    objective;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Configure</p>
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          <p className="muted mt-1">Pick the fields — we handle the Excel formulas for you.</p>
        </div>
        <button className="btn-secondary" onClick={onBack}>
          Back to Home
        </button>
      </div>

      <div className="card p-6">
        {objective === "ask" && (
          <div>
            <label className="label">What do you want to know?</label>
            <textarea
              className="input min-h-[120px]"
              value={values.question}
              onChange={(e) => setters.setQuestion(e.target.value)}
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button key={q} type="button" className="chip-soft" onClick={() => setters.setQuestion(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {objective === "templates" && (
          <div className="space-y-4">
            {Object.entries(templates).map(([domain, items]) => (
              <div key={domain}>
                <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">{domain}</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {items.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setters.setTemplateId(t.id)}
                      className={clsx(
                        "rounded-xl border px-3 py-3 text-left text-sm transition",
                        values.templateId === t.id
                          ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                          : "border-slate-200 hover:border-blue-300"
                      )}
                    >
                      <p className="font-semibold text-slate-900">{t.name}</p>
                      <p className="mt-0.5 text-xs text-slate-500">{t.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {objective === "calculate" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Column" value={values.column} onChange={setters.setColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Metric" value={values.metric} onChange={setters.setMetric} options={METRICS} />
            <FieldSelect label="Group by" value={values.groupBy} onChange={setters.setGroupBy} options={columns} allowEmpty />
            <FieldSelect label="Filter column" value={values.filterColumn} onChange={setters.setFilterColumn} options={columns} allowEmpty />
            <FieldInput label="Filter value" value={values.filterValue} onChange={setters.setFilterValue} placeholder="e.g. UAE" />
          </div>
        )}

        {objective === "compare" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Value column" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Compare by" value={values.dimensionColumn} onChange={setters.setDimensionColumn} options={columns} />
            <FieldSelect label="Metric" value={values.metric} onChange={setters.setMetric} options={METRICS} />
            <FieldInput label="Left value" value={values.leftValue} onChange={setters.setLeftValue} placeholder="e.g. Dubai" />
            <FieldInput label="Right value" value={values.rightValue} onChange={setters.setRightValue} placeholder="e.g. Abu Dhabi" />
          </div>
        )}

        {objective === "lookup" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Lookup column" value={values.lookupColumn} onChange={setters.setLookupColumn} options={columns} />
            <FieldInput label="Lookup value" value={values.lookupValue} onChange={setters.setLookupValue} placeholder="e.g. ORD-1001" />
            <FieldSelect label="Return column" value={values.returnColumn} onChange={setters.setReturnColumn} options={columns} />
          </div>
        )}

        {objective === "clean" && (
          <p className="text-sm text-slate-600">
            We will trim spaces, fix numbers stored as text, parse dates, fill blanks, and remove duplicates.
          </p>
        )}

        {objective === "summarize" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Group by" value={values.groupBy} onChange={setters.setGroupBy} options={columns} />
            <FieldSelect label="Value" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Metric" value={values.metric} onChange={setters.setMetric} options={METRICS} />
          </div>
        )}

        {objective === "pivot" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Rows" value={values.pivotRows} onChange={setters.setPivotRows} options={columns} allowEmpty />
            <FieldSelect label="Columns" value={values.pivotCols} onChange={setters.setPivotCols} options={columns} allowEmpty />
            <FieldSelect label="Values" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Calculation" value={values.metric} onChange={setters.setMetric} options={METRICS} />
          </div>
        )}

        {objective === "chart" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Chart type" value={values.chartType} onChange={setters.setChartType} options={CHART_TYPES} />
            <FieldSelect label="Category" value={values.categoryColumn} onChange={setters.setCategoryColumn} options={columns} />
            <FieldSelect label="Value" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Metric" value={values.metric} onChange={setters.setMetric} options={METRICS} />
          </div>
        )}

        {objective === "dashboard" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Dashboard type" value={values.dashboardType} onChange={setters.setDashboardType} options={DASHBOARD_TYPES} />
            <FieldSelect label="Value / revenue" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Category / product" value={values.categoryColumn} onChange={setters.setCategoryColumn} options={columns} allowEmpty />
            <FieldSelect label="Region" value={values.dimensionColumn} onChange={setters.setDimensionColumn} options={columns} allowEmpty />
            <FieldSelect label="Date" value={values.dateColumn} onChange={setters.setDateColumn} options={columns} allowEmpty />
          </div>
        )}

        {(objective === "analyze" || objective === "report") && (
          <div className="grid gap-4 sm:grid-cols-3">
            <FieldSelect label="Value column" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Category" value={values.categoryColumn} onChange={setters.setCategoryColumn} options={columns} allowEmpty />
            <FieldSelect label="Date" value={values.dateColumn} onChange={setters.setDateColumn} options={columns} allowEmpty />
          </div>
        )}

        {objective === "find" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect
              label="Find type"
              value={values.findType}
              onChange={setters.setFindType}
              options={["problems", "duplicates", "top", "bottom", "outliers"]}
            />
            {(values.findType === "top" || values.findType === "bottom" || values.findType === "outliers") && (
              <FieldSelect
                label="Value column"
                value={values.valueColumn}
                onChange={setters.setValueColumn}
                options={numericCols.length ? numericCols : columns}
              />
            )}
          </div>
        )}

        {objective === "conditional" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Function" value={values.condFn} onChange={setters.setCondFn} options={["sumif", "countif", "averageif"]} />
            <FieldSelect label="Criteria column" value={values.criteriaColumn} onChange={setters.setCriteriaColumn} options={columns} />
            <FieldInput label="Criteria value" value={values.criteriaValue} onChange={setters.setCriteriaValue} placeholder="e.g. Dubai" />
            {values.condFn !== "countif" && (
              <FieldSelect label="Value column" value={values.valueColumn} onChange={setters.setValueColumn} options={numericCols.length ? numericCols : columns} />
            )}
          </div>
        )}

        {objective === "math" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldSelect label="Left column" value={values.mathLeft} onChange={setters.setMathLeft} options={numericCols.length ? numericCols : columns} />
            <FieldSelect label="Operator" value={values.mathOp} onChange={setters.setMathOp} options={["-", "+", "*", "/", "%"]} />
            <FieldSelect label="Right column" value={values.mathRight} onChange={setters.setMathRight} options={numericCols.length ? numericCols : columns} />
            <FieldInput label="Result name" value={values.mathResult} onChange={setters.setMathResult} />
          </div>
        )}

        {objective === "growth" && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ["mom", "Month-over-month"],
                  ["ytd", "Year-to-date"],
                  ["enrich", "Add date columns"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={clsx(
                    "rounded-full px-3 py-1.5 text-xs font-semibold",
                    values.growthMode === id ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"
                  )}
                  onClick={() => setters.setGrowthMode(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldSelect label="Date column" value={values.dateColumn} onChange={setters.setDateColumn} options={columns} />
              {values.growthMode !== "enrich" && (
                <FieldSelect
                  label="Value column"
                  value={values.valueColumn}
                  onChange={setters.setValueColumn}
                  options={numericCols.length ? numericCols : columns}
                />
              )}
            </div>
          </div>
        )}

        <div className="mt-8 flex flex-wrap gap-3">
          <button className="btn-primary btn-lg" disabled={loading} onClick={onRun}>
            <Sparkles className="h-4 w-4" />
            {loading ? "Working…" : "Create Analysis"}
          </button>
          <button className="btn-secondary" onClick={onBack}>
            Cancel
          </button>
        </div>
      </div>
    </section>
  );
}
