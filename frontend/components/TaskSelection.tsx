"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";
import {
  ArrowRight,
  BarChart3,
  Calculator,
  CheckCircle2,
  ClipboardList,
  FileText,
  Monitor,
  Package,
  Scale,
  Search,
  Sparkles,
  Table2,
  Wand2,
} from "lucide-react";
import type {
  Dataset,
  DatasetListItem,
  HistoryItem,
  TaskItem,
  TaskRecommendation,
  TaskSelection,
} from "@/lib/api";
import {
  classifyIntentApi,
  fetchTaskHistory,
  fetchTasks,
  searchTasksApi,
  startTaskApi,
} from "@/lib/api";

const ICONS: Record<string, ReactNode> = {
  calculator: <Calculator className="h-5 w-5" />,
  scale: <Scale className="h-5 w-5" />,
  search: <Search className="h-5 w-5" />,
  wand: <Wand2 className="h-5 w-5" />,
  clipboard: <ClipboardList className="h-5 w-5" />,
  table: <Table2 className="h-5 w-5" />,
  chart: <BarChart3 className="h-5 w-5" />,
  monitor: <Monitor className="h-5 w-5" />,
  file: <FileText className="h-5 w-5" />,
  sparkles: <Sparkles className="h-5 w-5" />,
  package: <Package className="h-5 w-5" />,
};

const PRIMARY_IDS = [
  "calculate",
  "compare",
  "lookup",
  "clean",
  "summarize",
  "pivot",
  "charts",
  "dashboard",
  "reports",
  "analyze",
];

export function TaskSelectionView({
  dataset,
  library,
  onBack,
  onChangeDataset,
  onStarted,
  preselectTaskId,
}: {
  dataset: Dataset | null;
  library: DatasetListItem[];
  onBack: () => void;
  onChangeDataset: () => void;
  onStarted: (selection: TaskSelection) => void;
  preselectTaskId?: string | null;
}) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [recs, setRecs] = useState<TaskRecommendation[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selected, setSelected] = useState<TaskItem | null>(null);
  const [search, setSearch] = useState("");
  const [nl, setNl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intentMsg, setIntentMsg] = useState<string | null>(null);
  const [secondaryIds, setSecondaryIds] = useState<string[]>([]);

  useEffect(() => {
    if (!dataset?.id) return;
    setLoading(true);
    setError(null);
    Promise.all([fetchTasks(dataset.id), fetchTaskHistory()])
      .then(([t, h]) => {
        setTasks(t.tasks || []);
        setRecs(t.recommendations || []);
        setHistory(h || []);
        if (preselectTaskId) {
          const found = (t.tasks || []).find((x) => x.id === preselectTaskId);
          if (found) setSelected(found);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load tasks"))
      .finally(() => setLoading(false));
  }, [dataset?.id, preselectTaskId]);

  const primary = useMemo(() => {
    const map = new Map(tasks.map((t) => [t.id, t]));
    return PRIMARY_IDS.map((id) => map.get(id)).filter(Boolean) as TaskItem[];
  }, [tasks]);

  const filtered = useMemo(() => {
    if (!search.trim()) return primary.length ? primary : tasks;
    const q = search.toLowerCase();
    return tasks.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        (t.keywords || []).some((k) => k.includes(q)) ||
        (t.examples || []).some((e) => e.toLowerCase().includes(q))
    );
  }, [tasks, primary, search]);

  async function onSearchSubmit() {
    if (!dataset || !search.trim()) return;
    setLoading(true);
    try {
      const results = await searchTasksApi(search, dataset.id);
      // merge into view by setting search filter only; results already in tasks
      if (results.length) {
        setSelected(results[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function onAnalyzeNl() {
    if (!dataset || !nl.trim()) return;
    setLoading(true);
    setIntentMsg(null);
    try {
      const result = await classifyIntentApi(nl, dataset.id);
      setIntentMsg(`${result.message} (confidence ${Math.round((result.confidence || 0) * 100)}%)`);
      if (result.task) setSelected(result.task);
      else if (result.task_id) {
        const t = tasks.find((x) => x.id === result.task_id);
        if (t) setSelected(t);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not understand request");
    } finally {
      setLoading(false);
    }
  }

  async function onStart() {
    if (!dataset || !selected) return;
    if (selected.can_start === false) {
      setError((selected.availability_reasons || []).join(" ") || "Task not available.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await startTaskApi({
        dataset_id: dataset.id,
        task_id: selected.id,
        secondary_dataset_ids: secondaryIds,
        objective: selected.name,
      });
      onStarted(res.selection);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start task");
    } finally {
      setLoading(false);
    }
  }

  if (!dataset) {
    return (
      <div className="card mx-auto max-w-lg p-10 text-center">
        <p className="font-semibold text-slate-900">Select a dataset first</p>
        <p className="mt-2 text-sm text-slate-500">Upload or open a profiled dataset, then choose a task.</p>
        <button className="btn-primary mt-4" onClick={onChangeDataset}>
          My Data
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-[1400px] gap-5 xl:grid-cols-[1fr_320px]">
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Step 2 · Choose Task</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">What would you like to do?</h1>
            <p className="mt-1 text-slate-500">Choose a task and we&apos;ll guide you through the analysis.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" onClick={onBack}>
              Back to profile
            </button>
            <button className="btn-secondary" onClick={onChangeDataset}>
              Change dataset
            </button>
          </div>
        </div>

        <div className="card flex flex-wrap items-center gap-3 p-4">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase text-slate-400">Current dataset</p>
            <p className="truncate font-semibold text-slate-900">{dataset.name}</p>
            <p className="text-xs text-slate-500">
              {dataset.rows?.toLocaleString()} rows · {dataset.columns} columns · Health{" "}
              {dataset.health?.score ?? "—"}/100
            </p>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
        )}

        {/* NL ask */}
        <div className="card p-5">
          <p className="text-sm font-bold text-slate-900">What do you want to do with your data?</p>
          <div className="mt-3 flex gap-2">
            <input
              className="input"
              placeholder='e.g. Show me my top 10 customers · Find duplicates · Create a monthly sales chart'
              value={nl}
              onChange={(e) => setNl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onAnalyzeNl()}
            />
            <button className="btn-primary shrink-0" disabled={loading} onClick={onAnalyzeNl}>
              Analyze
            </button>
          </div>
          {intentMsg && <p className="mt-2 text-xs text-blue-700">{intentMsg}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              "Show me my top 10 customers",
              "Compare sales by region",
              "Find duplicate records",
              "Create a monthly sales chart",
              "Build a sales dashboard",
            ].map((q) => (
              <button key={q} type="button" className="chip-soft" onClick={() => setNl(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Manager tip */}
        <div className="rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          <strong>Tip for managers:</strong> Prefer <em>Home → One-click</em> for Dashboard / Report with zero setup.
          Use this screen when you want guided dropdowns and filters.
        </div>

        {/* Recommendations */}
        {recs.length > 0 && (
          <section className="card p-5">
            <h2 className="text-base font-bold text-slate-900">Recommended for this dataset</h2>
            <p className="mt-1 text-xs text-slate-500">Based on detected measures, dimensions, and dates — not the filename.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {recs.map((r) => (
                <button
                  key={r.task_id}
                  className="action-tile text-left"
                  onClick={() => {
                    const t = tasks.find((x) => x.id === r.task_id);
                    if (t) setSelected(t);
                  }}
                >
                  <div className={clsx("mb-2 flex h-9 w-9 items-center justify-center rounded-xl text-white", r.color || "bg-blue-500")}>
                    {ICONS[r.icon || "sparkles"] || <Sparkles className="h-5 w-5" />}
                  </div>
                  <p className="text-sm font-bold text-slate-900">{r.name}</p>
                  <p className="mt-1 text-xs text-slate-500">{r.description}</p>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Search tasks */}
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="Search tasks (e.g. duplicate, profit, chart)…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSearchSubmit()}
          />
          <button className="btn-secondary" onClick={onSearchSubmit}>
            <Search className="h-4 w-4" />
          </button>
        </div>

        {/* Task cards */}
        <section>
          <h2 className="mb-3 text-base font-bold text-slate-900">All tasks</h2>
          {loading && tasks.length === 0 ? (
            <p className="text-sm text-slate-500">Loading tasks…</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filtered.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelected(t)}
                  className={clsx(
                    "action-tile relative text-left",
                    selected?.id === t.id && "ring-2 ring-blue-500 border-blue-300"
                  )}
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div className={clsx("flex h-10 w-10 items-center justify-center rounded-xl text-white", t.color || "bg-blue-500")}>
                      {ICONS[t.icon || "sparkles"] || <Sparkles className="h-5 w-5" />}
                    </div>
                    <AvailBadge status={t.availability || "available"} />
                  </div>
                  <p className="text-sm font-bold text-slate-900">{t.name}</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500 line-clamp-2">{t.description}</p>
                  {t.examples?.[0] && (
                    <p className="mt-2 text-[11px] text-slate-400 line-clamp-1">e.g. {t.examples[0]}</p>
                  )}
                  <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-blue-600">
                    View <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Right rail: detail + history */}
      <aside className="space-y-4 xl:sticky xl:top-0 xl:self-start">
        {selected ? (
          <div className="card p-5">
            <div className={clsx("mb-3 flex h-11 w-11 items-center justify-center rounded-xl text-white", selected.color || "bg-blue-600")}>
              {ICONS[selected.icon || "sparkles"]}
            </div>
            <h3 className="text-lg font-bold text-slate-900">{selected.name}</h3>
            <p className="mt-1 text-sm text-slate-600">{selected.description}</p>
            <div className="mt-3">
              <AvailBadge status={selected.availability || "available"} large />
            </div>
            {(selected.availability_reasons || []).length > 0 && (
              <ul className="mt-3 space-y-1.5 text-xs text-slate-600">
                {selected.availability_reasons!.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
                    {r}
                  </li>
                ))}
              </ul>
            )}
            {selected.examples && selected.examples.length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] font-semibold uppercase text-slate-400">Example questions</p>
                <ul className="mt-1 space-y-1 text-xs text-slate-600">
                  {selected.examples.map((e) => (
                    <li key={e}>“{e}”</li>
                  ))}
                </ul>
              </div>
            )}
            {selected.can_compare && selected.can_compare.length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] font-semibold uppercase text-slate-400">You can compare</p>
                <p className="mt-1 text-xs text-slate-600">{selected.can_compare.join(" · ")}</p>
              </div>
            )}
            {selected.id === "match_datasets" || selected.id === "lookup" ? (
              <div className="mt-4">
                <p className="text-[11px] font-semibold uppercase text-slate-400">Optional second dataset</p>
                <div className="mt-2 max-h-32 space-y-1 overflow-auto">
                  {library
                    .filter((d) => d.id !== dataset.id)
                    .map((d) => (
                      <label key={d.id} className="flex items-center gap-2 text-xs text-slate-700">
                        <input
                          type="checkbox"
                          checked={secondaryIds.includes(d.id)}
                          onChange={() =>
                            setSecondaryIds((prev) =>
                              prev.includes(d.id) ? prev.filter((x) => x !== d.id) : [...prev, d.id]
                            )
                          }
                        />
                        {d.name}
                      </label>
                    ))}
                  {library.filter((d) => d.id !== dataset.id).length === 0 && (
                    <p className="text-xs text-slate-400">Upload another dataset to enable matching.</p>
                  )}
                </div>
              </div>
            ) : null}
            <button
              className="btn-primary mt-5 w-full"
              disabled={loading || selected.can_start === false}
              onClick={onStart}
            >
              Start {selected.name}
            </button>
            {selected.can_start === false && (
              <p className="mt-2 text-center text-[11px] text-rose-600">Not available for this dataset yet.</p>
            )}
          </div>
        ) : (
          <div className="card p-5 text-sm text-slate-500">Select a task card to see details and start.</div>
        )}

        <div className="card p-4">
          <p className="text-sm font-bold text-slate-900">Recent tasks</p>
          {history.length === 0 ? (
            <p className="mt-2 text-xs text-slate-500">No tasks started yet.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {history.slice(0, 8).map((h) => (
                <li key={h.id} className="rounded-xl bg-slate-50 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-800">{h.task_name}</p>
                  <p className="text-[11px] text-slate-500">
                    {h.dataset_name} · {h.timestamp ? new Date(h.timestamp).toLocaleString() : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}

function AvailBadge({ status, large }: { status: string; large?: boolean }) {
  const map: Record<string, string> = {
    available: "bg-emerald-100 text-emerald-800",
    partial: "bg-amber-100 text-amber-900",
    unavailable: "bg-slate-200 text-slate-600",
  };
  const label =
    status === "available" ? "Available" : status === "partial" ? "Partially available" : "Not available";
  return (
    <span className={clsx("rounded-full px-2 py-0.5 font-semibold", large ? "text-xs" : "text-[10px]", map[status] || map.available)}>
      {label}
    </span>
  );
}

export function TaskConfigurePlaceholder({
  selection,
  onBack,
  onProfile,
}: {
  selection: TaskSelection;
  onBack: () => void;
  onProfile: () => void;
}) {
  return (
    <section className="card mx-auto max-w-2xl p-8">
      <div className="flex items-center gap-2 text-emerald-600">
        <CheckCircle2 className="h-5 w-5" />
        <p className="text-xs font-semibold uppercase tracking-wide">Step 3 · Configure (placeholder)</p>
      </div>
      <h1 className="mt-3 text-2xl font-bold text-slate-900">You selected: {selection.task_name}</h1>
      <p className="mt-2 text-slate-500">
        Dataset: <strong>{selection.dataset_name}</strong>
      </p>
      <div className="mt-6 rounded-2xl border border-slate-100 bg-slate-50 p-5 text-sm text-slate-700">
        <p className="font-semibold text-slate-900">What would you like to configure?</p>
        <p className="mt-2 text-slate-500">
          The Task Configuration Engine (Step 3) will let you pick columns, filters, and options for{" "}
          <strong>{selection.task_name}</strong>. That engine is not implemented yet — your selection is saved.
        </p>
        {selection.detected_fields && (
          <div className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
            <div>
              <p className="font-semibold text-slate-500">Measures</p>
              <p>{(selection.detected_fields.measures || []).join(", ") || "—"}</p>
            </div>
            <div>
              <p className="font-semibold text-slate-500">Dimensions</p>
              <p>{(selection.detected_fields.dimensions || []).join(", ") || "—"}</p>
            </div>
            <div>
              <p className="font-semibold text-slate-500">Dates</p>
              <p>{(selection.detected_fields.dates || []).join(", ") || "—"}</p>
            </div>
          </div>
        )}
      </div>
      <div className="mt-6 flex flex-wrap gap-3">
        <button className="btn-primary" onClick={onBack}>
          Choose another task
        </button>
        <button className="btn-secondary" onClick={onProfile}>
          Back to data profile
        </button>
      </div>
    </section>
  );
}
