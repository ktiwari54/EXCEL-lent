"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bell,
  Calculator,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Database,
  FileSpreadsheet,
  FileText,
  Filter,
  HelpCircle,
  Home,
  Layers,
  LayoutDashboard,
  MessageSquare,
  Monitor,
  Scale,
  Search,
  Settings,
  Sparkles,
  Table2,
  Trash2,
  Upload,
  Wand2,
  X,
} from "lucide-react";
import {
  ColumnProfile,
  Dataset,
  DatasetListItem,
  InspectResult,
  TaskSelection,
  deleteDataset,
  getDataset,
  healthCheck,
  importFile,
  inspectFile,
  listDatasets,
  previewDataset,
  renameDataset,
  setRelationshipStatus,
} from "@/lib/api";
import { UploadZone } from "@/components/UploadZone";
import { LoadingOverlay } from "@/components/ui";
import { TaskSelectionView } from "@/components/TaskSelection";
import { ConfigureTaskView, PreparingPlaceholder } from "@/components/ConfigureTask";

type View = "home" | "upload" | "sheets" | "profile" | "library" | "soon" | "tasks" | "configure" | "preparing";

export default function HomePage() {
  const [view, setView] = useState<View>("home");
  const [nav, setNav] = useState("home");
  const [soonLabel, setSoonLabel] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("Working…");
  const [error, setError] = useState<string | null>(null);

  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [inspect, setInspect] = useState<InspectResult | null>(null);
  const [selectedSheets, setSelectedSheets] = useState<string[]>([]);
  const [sheetNames, setSheetNames] = useState<Record<string, string>>({});

  const [library, setLibrary] = useState<DatasetListItem[]>([]);
  const [active, setActive] = useState<Dataset | null>(null);
  const [selectedColumn, setSelectedColumn] = useState<ColumnProfile | null>(null);

  // preview controls
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const [renameValue, setRenameValue] = useState("");
  const [preselectTaskId, setPreselectTaskId] = useState<string | null>(null);
  const [taskSelection, setTaskSelection] = useState<TaskSelection | null>(null);
  const [generatePayload, setGeneratePayload] = useState<Record<string, unknown> | null>(null);

  const refreshLibrary = useCallback(async () => {
    try {
      setLibrary(await listDatasets());
    } catch {
      /* ignore offline */
    }
  }, []);

  useEffect(() => {
    healthCheck().then(setApiOk);
    refreshLibrary();
    // restore last dataset for Task step after refresh
    const lastId = typeof window !== "undefined" ? sessionStorage.getItem("excellent_active_id") : null;
    if (lastId) {
      getDataset(lastId)
        .then((ds) => {
          setActive(ds);
          setRenameValue(ds.name);
        })
        .catch(() => sessionStorage.removeItem("excellent_active_id"));
    }
  }, [refreshLibrary]);

  async function goToTasks(dataset?: Dataset | null, taskId?: string | null) {
    let ds = dataset || active;
    if (!ds && library[0]) {
      ds = (await openDataset(library[0].id, false)) || null;
    }
    if (!ds) {
      setError("Upload and profile a dataset first, then choose a task.");
      go("upload", "upload");
      return;
    }
    setError(null);
    setPreselectTaskId(taskId || null);
    setView("tasks");
    setNav("tasks");
  }

  async function loadPreview(id: string, p = page, q = search) {
    const data = await previewDataset(id, {
      page: p,
      page_size: 50,
      search: q || undefined,
      sort_by: sortBy || undefined,
      sort_dir: sortDir,
    });
    setPreviewRows(data.rows);
    setTotalPages(data.total_pages);
    setTotalRows(data.total_rows);
    setPage(data.page);
  }

  async function openDataset(id: string, goProfile = true) {
    setLoading(true);
    setLoadingLabel("Loading dataset…");
    setError(null);
    try {
      const ds = await getDataset(id);
      setActive(ds);
      setRenameValue(ds.name);
      setSelectedColumn(null);
      setSearch("");
      setSortBy(null);
      setPage(1);
      sessionStorage.setItem("excellent_active_id", id);
      try {
        await loadPreview(id, 1, "");
      } catch (previewErr) {
        // profile can still show without preview
        console.warn(previewErr);
        setPreviewRows(ds.preview || []);
        setTotalRows(ds.rows || 0);
        setTotalPages(1);
      }
      if (goProfile) {
        setView("profile");
        setNav("explore");
      }
      return ds;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dataset");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function onFileChosen(file: File) {
    setLoading(true);
    setLoadingLabel("Reading workbook structure…");
    setError(null);
    try {
      const info = await inspectFile(file);
      setPendingFile(file);
      setInspect(info);
      const nonEmpty = info.sheets.filter((s) => !s.empty).map((s) => s.name);
      setSelectedSheets(nonEmpty.length ? [nonEmpty[0]] : info.sheets.map((s) => s.name));
      const names: Record<string, string> = {};
      info.sheets.forEach((s) => {
        names[s.name] = s.suggested_name;
      });
      setSheetNames(names);
      setView("sheets");
      setNav("upload");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function confirmImport() {
    if (!pendingFile || !selectedSheets.length) {
      setError("Select at least one sheet that contains data.");
      return;
    }
    setLoading(true);
    setLoadingLabel("Profiling your data…");
    setError(null);
    try {
      const names: Record<string, string> = {};
      selectedSheets.forEach((s) => {
        names[s] = sheetNames[s] || s;
      });
      const result = await importFile(pendingFile, selectedSheets, names);
      await refreshLibrary();
      const first = result.datasets[0];
      if (!first) {
        setError("Import finished but no dataset was created. Try another sheet.");
        return;
      }
      const ds = await openDataset(first.id, true);
      if (!ds) {
        setError("Dataset was saved but the profile screen failed to load. Open it from My Data.");
        go("library", "sources");
      }
      setPendingFile(null);
      setInspect(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  }

  async function onRename() {
    if (!active) return;
    setLoading(true);
    try {
      const ds = await renameDataset(active.id, renameValue);
      setActive(ds);
      await refreshLibrary();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rename failed");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this dataset from the library? Original file is not deleted from your computer.")) return;
    setLoading(true);
    try {
      await deleteDataset(id);
      if (active?.id === id) {
        setActive(null);
        setView("library");
      }
      await refreshLibrary();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setLoading(false);
    }
  }

  function goSoon(label: string, key: string) {
    setSoonLabel(label);
    setNav(key);
    setView("soon");
  }

  function go(viewName: View, navKey: string) {
    setView(viewName);
    setNav(navKey);
  }

  function openTaskFromNav(taskId: string) {
    goToTasks(active, taskId);
  }

  const headers = useMemo(() => {
    if (previewRows[0]) return Object.keys(previewRows[0]);
    return active?.headers || [];
  }, [previewRows, active]);

  return (
    <div className="app-shell">
      {loading && <LoadingOverlay label={loadingLabel} />}

      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-600 shadow-lg">
            <FileSpreadsheet className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight">Data Analyst Engine</p>
            <p className="text-[11px] text-slate-400">Your Data. Our Intelligence.</p>
          </div>
        </div>

        <div className="sidebar-scroll">
          <NavBtn active={nav === "home"} onClick={() => go("home", "home")} icon={<Home className="h-4 w-4" />} label="Home" />
          <NavBtn active={nav === "upload"} onClick={() => go("upload", "upload")} icon={<Upload className="h-4 w-4" />} label="Upload Data" />
          <NavBtn
            active={nav === "explore"}
            onClick={() => (active ? go("profile", "explore") : go("library", "explore"))}
            icon={<Database className="h-4 w-4" />}
            label="Explore Data"
          />
          <NavBtn
            active={nav === "ask" || nav === "tasks"}
            onClick={() => goToTasks(active)}
            icon={<MessageSquare className="h-4 w-4" />}
            label="Ask & Analyze"
          />

          <p className="nav-section">Analyze</p>
          {[
            ["Calculate", "calculate"],
            ["Compare", "compare"],
            ["Lookup / Match", "lookup"],
            ["Clean Data", "clean"],
            ["Summarize", "summarize"],
            ["Pivot Table", "pivot"],
            ["Charts", "charts"],
            ["Dashboard", "dashboard"],
            ["Reports", "reports"],
          ].map(([label, key]) => (
            <NavBtn
              key={key}
              active={nav === key}
              onClick={() => openTaskFromNav(key)}
              icon={<ChevronRight className="h-3.5 w-3.5 opacity-50" />}
              label={label}
            />
          ))}

          <p className="nav-section">Solutions</p>
          {[
            ["Sales Analysis", "sales"],
            ["Inventory Analysis", "inventory"],
            ["Finance Analysis", "finance"],
            ["HR Analysis", "hr"],
            ["Marketing Analysis", "marketing"],
            ["CRM Analysis", "crm"],
          ].map(([label, key]) => (
            <NavBtn key={key} active={nav === key} onClick={() => goSoon(label, key)} icon={<LayoutDashboard className="h-4 w-4 opacity-70" />} label={label} soon />
          ))}

          <p className="nav-section">Settings</p>
          <NavBtn active={nav === "sources"} onClick={() => go("library", "sources")} icon={<FolderIcon />} label="Data Sources" />
          <NavBtn active={nav === "templates"} onClick={() => goSoon("Templates", "templates")} icon={<Layers className="h-4 w-4" />} label="Templates" soon />
          <NavBtn active={nav === "workbooks"} onClick={() => goSoon("My Workbooks", "workbooks")} icon={<Settings className="h-4 w-4" />} label="My Workbooks" soon />
        </div>

        <div className="border-t border-white/10 px-4 py-3">
          <div className={clsx("flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium", apiOk ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300")}>
            <span className={clsx("h-2 w-2 rounded-full", apiOk ? "bg-emerald-400" : "bg-rose-400")} />
            {apiOk ? "Engine online · Steps 1–3" : "API offline"}
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-slate-200/80 bg-white px-6 py-3">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="w-full rounded-full border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm text-slate-500"
              placeholder="Ask your data anything… (coming in Step 2)"
              disabled
            />
          </div>
          <div className="flex items-center gap-1">
            <button className="btn-ghost h-10 w-10 rounded-full p-0"><Bell className="h-4 w-4" /></button>
            <button className="btn-ghost h-10 w-10 rounded-full p-0"><HelpCircle className="h-4 w-4" /></button>
            <div className="ml-1 flex items-center gap-2 rounded-full border border-slate-200 py-1 pl-1 pr-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">A</span>
              <span className="text-sm font-medium text-slate-700">Admin User</span>
            </div>
          </div>
        </header>

        <main className="scroll-thin flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <div className="flex gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span className="whitespace-pre-wrap">{error}</span>
              </div>
              <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
            </div>
          )}

          {/* Stage indicator */}
          <div className="mb-5 flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-500">
            <button
              type="button"
              onClick={() => (active ? go("profile", "explore") : go("upload", "upload"))}
              className={clsx(
                "rounded-full px-3 py-1",
                ["preparing", "configure", "tasks"].includes(view)
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-blue-600 text-white"
              )}
            >
              1. Upload
              {["profile", "tasks", "configure", "preparing"].includes(view) && " ✓"}
            </button>
            <span className="text-slate-300">↓</span>
            <button
              type="button"
              onClick={() => goToTasks()}
              className={clsx(
                "rounded-full px-3 py-1",
                view === "tasks"
                  ? "bg-blue-600 text-white"
                  : ["configure", "preparing"].includes(view)
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-slate-200 text-slate-500"
              )}
            >
              2. Choose Task
              {["configure", "preparing"].includes(view) && " ✓"}
            </button>
            <span className="text-slate-300">↓</span>
            <span
              className={clsx(
                "rounded-full px-3 py-1",
                view === "configure"
                  ? "bg-blue-600 text-white"
                  : view === "preparing"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-slate-200 text-slate-500"
              )}
            >
              3. Configure
              {view === "preparing" && " ✓"}
            </span>
            <span className="text-slate-300">↓</span>
            <span
              className={clsx(
                "rounded-full px-3 py-1",
                view === "preparing" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-500"
              )}
            >
              4–5. Generate / Result
            </span>
          </div>

          {view === "home" && (
            <HomeView
              libraryCount={library.length}
              onUpload={() => go("upload", "upload")}
              onLibrary={() => go("library", "sources")}
              onTasks={() => goToTasks()}
              recent={library.slice(0, 3)}
              onOpen={openDataset}
            />
          )}

          {view === "upload" && (
            <section className="mx-auto max-w-3xl space-y-5">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Upload your data</h1>
                <p className="mt-1 text-slate-500">
                  Upload an Excel or CSV file and we&apos;ll automatically understand your data.
                </p>
              </div>
              <UploadZone onFile={onFileChosen} loading={loading} />
              <p className="text-center text-xs text-slate-400">
                Supported: XLSX · XLS · CSV · Max {50} MB · Original file is never modified
              </p>
            </section>
          )}

          {view === "sheets" && inspect && (
            <SheetSelectView
              inspect={inspect}
              selectedSheets={selectedSheets}
              sheetNames={sheetNames}
              onToggle={(name) =>
                setSelectedSheets((prev) =>
                  prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]
                )
              }
              onNameChange={(sheet, name) => setSheetNames((p) => ({ ...p, [sheet]: name }))}
              onBack={() => go("upload", "upload")}
              onContinue={confirmImport}
            />
          )}

          {view === "library" && (
            <LibraryView
              items={library}
              onOpen={openDataset}
              onDelete={onDelete}
              onUpload={() => go("upload", "upload")}
            />
          )}

          {view === "profile" && active && (
            <ProfileView
              dataset={active}
              renameValue={renameValue}
              setRenameValue={setRenameValue}
              onRename={onRename}
              onDelete={() => onDelete(active.id)}
              selectedColumn={selectedColumn}
              setSelectedColumn={setSelectedColumn}
              headers={headers}
              previewRows={previewRows}
              page={page}
              totalPages={totalPages}
              totalRows={totalRows}
              search={search}
              setSearch={setSearch}
              sortBy={sortBy}
              sortDir={sortDir}
              onSort={(col) => {
                if (sortBy === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                else {
                  setSortBy(col);
                  setSortDir("asc");
                }
              }}
              onSearch={async () => {
                setLoading(true);
                try {
                  await loadPreview(active.id, 1, search);
                } finally {
                  setLoading(false);
                }
              }}
              onPage={async (p) => {
                setLoading(true);
                try {
                  await loadPreview(active.id, p, search);
                } finally {
                  setLoading(false);
                }
              }}
              onRelStatus={async (label, status) => {
                const ds = await setRelationshipStatus(active.id, label, status);
                setActive(ds);
              }}
              onContinue={() => goToTasks(active)}
              reloadSort={async () => {
                setLoading(true);
                try {
                  await loadPreview(active.id, page, search);
                } finally {
                  setLoading(false);
                }
              }}
            />
          )}

          {view === "tasks" && (
            <TaskSelectionView
              dataset={active}
              library={library}
              preselectTaskId={preselectTaskId}
              onBack={() => (active ? go("profile", "explore") : go("home", "home"))}
              onChangeDataset={() => go("library", "sources")}
              onStarted={(selection) => {
                setTaskSelection(selection);
                setView("configure");
                setNav(selection.task_id);
              }}
            />
          )}

          {view === "configure" && taskSelection && (
            <ConfigureTaskView
              selection={taskSelection}
              dataset={active}
              onChangeTask={() => goToTasks(active)}
              onBackProfile={() => active && openDataset(active.id, true)}
              onGenerated={(payload) => {
                setGeneratePayload(payload);
                setView("preparing");
              }}
            />
          )}

          {view === "preparing" && generatePayload && (
            <PreparingPlaceholder
              payload={generatePayload}
              onBack={() => goToTasks(active)}
              onConfigure={() => setView("configure")}
            />
          )}

          {view === "soon" && (
            <ComingSoon label={soonLabel} onBack={() => go("home", "home")} onUpload={() => go("upload", "upload")} />
          )}
        </main>
      </div>
    </div>
  );
}

function FolderIcon() {
  return <Database className="h-4 w-4" />;
}

function NavBtn({
  active,
  onClick,
  icon,
  label,
  soon,
}: {
  active?: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
  soon?: boolean;
}) {
  return (
    <button className={active ? "nav-item-active" : "nav-item"} onClick={onClick}>
      {icon}
      <span className="flex-1 text-left">{label}</span>
      {soon && <span className="rounded bg-white/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-400">Soon</span>}
    </button>
  );
}

function HomeView({
  libraryCount,
  onUpload,
  onLibrary,
  onTasks,
  recent,
  onOpen,
}: {
  libraryCount: number;
  onUpload: () => void;
  onLibrary: () => void;
  onTasks: () => void;
  recent: DatasetListItem[];
  onOpen: (id: string) => void;
}) {
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Welcome to Data Analyst Engine</h1>
        <p className="mt-1 text-slate-500">Upload data once. We profile it. Analysis comes next — no Excel skills required.</p>
      </div>

      <section className="card p-5">
        <h2 className="text-base font-bold text-slate-900">Get Started in 4 Simple Steps</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          {[
            { n: "1", title: "Upload Data", desc: "Upload Excel or CSV", active: true, onClick: onUpload, color: "bg-emerald-500" },
            { n: "2", title: "Choose Task", desc: "What do you want to do?", active: libraryCount > 0, onClick: onTasks, color: "bg-violet-500" },
            { n: "3", title: "Configure", desc: "Select columns, filters and options", active: false, onClick: () => {}, color: "bg-blue-500" },
            { n: "4", title: "Get Results", desc: "Analysis, charts and insights", active: false, onClick: () => {}, color: "bg-orange-500" },
          ].map((s) => (
            <button
              key={s.n}
              disabled={!s.active}
              onClick={s.onClick}
              className={clsx(
                "step-card text-left",
                s.active ? "hover:border-blue-300" : "cursor-not-allowed opacity-60"
              )}
            >
              <div className={clsx("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white", s.color)}>
                {s.n}
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">
                  {s.n}. {s.title}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">{s.desc}</p>
                {!s.active && <p className="mt-1 text-[10px] font-bold uppercase text-slate-400">Coming soon</p>}
              </div>
            </button>
          ))}
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <button className="card p-6 text-left transition hover:border-blue-300 hover:shadow-md" onClick={onUpload}>
          <Upload className="h-8 w-8 text-blue-600" />
          <p className="mt-3 text-lg font-bold text-slate-900">Upload Data</p>
          <p className="mt-1 text-sm text-slate-500">Excel or CSV — we detect sheets, types, roles, and data health.</p>
        </button>
        <button className="card p-6 text-left transition hover:border-blue-300 hover:shadow-md" onClick={onLibrary}>
          <Table2 className="h-8 w-8 text-emerald-600" />
          <p className="mt-3 text-lg font-bold text-slate-900">My Data</p>
          <p className="mt-1 text-sm text-slate-500">
            {libraryCount === 0 ? "No datasets yet" : `${libraryCount} dataset(s) in your library`}
          </p>
        </button>
      </div>

      {recent.length > 0 && (
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-slate-900">Recent datasets</h2>
          <div className="space-y-2">
            {recent.map((d) => (
              <button
                key={d.id}
                className="flex w-full items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-left hover:bg-blue-50"
                onClick={() => onOpen(d.id)}
              >
                <div>
                  <p className="text-sm font-semibold text-slate-800">{d.name}</p>
                  <p className="text-xs text-slate-500">
                    {d.rows?.toLocaleString()} rows · {d.columns} columns · Health {d.health ?? "—"}
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 text-slate-400" />
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function SheetSelectView({
  inspect,
  selectedSheets,
  sheetNames,
  onToggle,
  onNameChange,
  onBack,
  onContinue,
}: {
  inspect: InspectResult;
  selectedSheets: string[];
  sheetNames: Record<string, string>;
  onToggle: (name: string) => void;
  onNameChange: (sheet: string, name: string) => void;
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <section className="mx-auto max-w-2xl space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          {inspect.kind === "excel" ? "Workbook detected" : "CSV detected"}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Select the data you want to analyze</h1>
        <p className="mt-1 text-sm text-slate-500">{inspect.filename}</p>
      </div>

      <div className="card divide-y divide-slate-100">
        {inspect.sheets.map((s) => (
          <div key={s.name} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
            <label className="flex flex-1 cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600"
                checked={selectedSheets.includes(s.name)}
                disabled={s.empty}
                onChange={() => onToggle(s.name)}
              />
              <div>
                <p className="font-semibold text-slate-900">{s.name}</p>
                <p className="text-xs text-slate-500">
                  {s.empty
                    ? s.error || "Empty sheet"
                    : `${s.rows.toLocaleString()} rows · ${s.columns} columns`}
                </p>
              </div>
            </label>
            {selectedSheets.includes(s.name) && !s.empty && (
              <div className="sm:w-64">
                <label className="label">Dataset name</label>
                <input
                  className="input"
                  value={sheetNames[s.name] || ""}
                  onChange={(e) => onNameChange(s.name, e.target.value)}
                  placeholder="e.g. Sales – August 2026"
                />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        <button className="btn-primary btn-lg" onClick={onContinue}>
          Profile selected data
        </button>
        <button className="btn-secondary" onClick={onBack}>
          Choose another file
        </button>
      </div>
      <p className="text-xs text-slate-400">
        Each sheet becomes its own dataset. Original data is stored as <strong>RAW</strong> and never modified.
      </p>
    </section>
  );
}

function LibraryView({
  items,
  onOpen,
  onDelete,
  onUpload,
}: {
  items: DatasetListItem[];
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onUpload: () => void;
}) {
  return (
    <section className="mx-auto max-w-4xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Data</h1>
          <p className="text-sm text-slate-500">Datasets you have uploaded and profiled</p>
        </div>
        <button className="btn-primary" onClick={onUpload}>
          <Upload className="h-4 w-4" /> Upload
        </button>
      </div>
      <div className="card overflow-hidden">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Dataset</th>
              <th className="px-4 py-3">Rows</th>
              <th className="px-4 py-3">Columns</th>
              <th className="px-4 py-3">Health</th>
              <th className="px-4 py-3">Uploaded</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                  No datasets yet. Upload Excel or CSV to begin.
                </td>
              </tr>
            )}
            {items.map((d) => (
              <tr key={d.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                <td className="px-4 py-3">
                  <button className="font-semibold text-blue-700 hover:underline" onClick={() => onOpen(d.id)}>
                    {d.name}
                  </button>
                  <p className="text-xs text-slate-400">{d.original_filename}</p>
                </td>
                <td className="px-4 py-3">{d.rows?.toLocaleString()}</td>
                <td className="px-4 py-3">{d.columns}</td>
                <td className="px-4 py-3">
                  <HealthBadge score={d.health ?? 0} />
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {d.uploaded_at ? new Date(d.uploaded_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <button className="btn-ghost text-rose-600" onClick={() => onDelete(d.id)}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function HealthBadge({ score }: { score: number }) {
  const color = score >= 90 ? "bg-emerald-100 text-emerald-800" : score >= 75 ? "bg-amber-100 text-amber-900" : "bg-rose-100 text-rose-800";
  return <span className={clsx("rounded-full px-2.5 py-1 text-xs font-bold", color)}>{score}/100</span>;
}

function ProfileView(props: {
  dataset: Dataset;
  renameValue: string;
  setRenameValue: (v: string) => void;
  onRename: () => void;
  onDelete: () => void;
  selectedColumn: ColumnProfile | null;
  setSelectedColumn: (c: ColumnProfile | null) => void;
  headers: string[];
  previewRows: Record<string, unknown>[];
  page: number;
  totalPages: number;
  totalRows: number;
  search: string;
  setSearch: (v: string) => void;
  sortBy: string | null;
  sortDir: string;
  onSort: (col: string) => void;
  onSearch: () => void;
  onPage: (p: number) => void;
  onRelStatus: (label: string, status: string) => void;
  onContinue: () => void;
  reloadSort: () => void;
}) {
  const { dataset: d } = props;
  const s = d.summary || {};
  const health = d.health;

  useEffect(() => {
    if (props.sortBy) props.reloadSort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.sortBy, props.sortDir]);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Dataset profile</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <input
              className="input max-w-md text-lg font-bold"
              value={props.renameValue}
              onChange={(e) => props.setRenameValue(e.target.value)}
            />
            <button className="btn-secondary" onClick={props.onRename}>
              Rename
            </button>
            <button className="btn-ghost text-rose-600" onClick={props.onDelete}>
              <Trash2 className="h-4 w-4" /> Delete
            </button>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {d.original_filename}
            {d.sheet_name ? ` · Sheet: ${d.sheet_name}` : ""} · RAW data preserved
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-semibold uppercase text-slate-400">Data Health</p>
          <p className="text-4xl font-bold text-slate-900">{health?.score ?? "—"}<span className="text-lg text-slate-400">/100</span></p>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {[
          ["Rows", s.rows ?? d.rows],
          ["Columns", s.columns ?? d.columns],
          ["Numeric", s.numeric_fields],
          ["Dates", s.date_fields],
          ["Categories", s.category_fields],
          ["Missing", s.missing_values],
          ["Duplicates", s.duplicate_records],
          ["Health", s.data_health ?? health?.score],
        ].map(([label, val]) => (
          <div key={String(label)} className="kpi-card">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {typeof val === "number" ? val.toLocaleString() : val ?? "—"}
            </p>
          </div>
        ))}
      </div>

      {/* Health breakdown */}
      {health && (
        <div className="card p-5">
          <h3 className="text-sm font-bold text-slate-900">Data Health breakdown</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-5">
            {(
              [
                ["Completeness", health.completeness],
                ["Validity", health.validity],
                ["Uniqueness", health.uniqueness],
                ["Consistency", health.consistency],
                ["Type confidence", health.type_confidence],
              ] as const
            ).map(([label, val]) => (
              <div key={label}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-slate-500">{label}</span>
                  <span className="font-semibold">{val}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-blue-600" style={{ width: `${val}%` }} />
                </div>
              </div>
            ))}
          </div>
          <ul className="mt-3 space-y-1 text-xs text-slate-500">
            {health.explanation?.map((e, i) => (
              <li key={i}>• {e}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          {/* Columns table */}
          <div className="card overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-3">
              <h3 className="text-sm font-bold text-slate-900">Columns</h3>
              <p className="text-xs text-slate-500">Click a column for details</p>
            </div>
            <div className="scroll-thin max-h-72 overflow-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-2">Name</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Role</th>
                    <th className="px-4 py-2">Missing</th>
                    <th className="px-4 py-2">Unique</th>
                  </tr>
                </thead>
                <tbody>
                  {(d.column_profiles || []).map((c) => (
                    <tr
                      key={c.name}
                      className={clsx(
                        "cursor-pointer border-t border-slate-100 hover:bg-blue-50/50",
                        props.selectedColumn?.name === c.name && "bg-blue-50"
                      )}
                      onClick={() => props.setSelectedColumn(c)}
                    >
                      <td className="px-4 py-2 font-medium text-slate-800">{c.name}</td>
                      <td className="px-4 py-2 capitalize text-slate-600">{c.data_type}</td>
                      <td className="px-4 py-2">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-700">
                          {c.role.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{c.null_pct}%</td>
                      <td className="px-4 py-2 text-slate-600">{c.unique_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Quality issues */}
          {(d.quality?.issues?.length || 0) > 0 && (
            <div className="card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Data quality flags
              </h3>
              <ul className="space-y-2">
                {d.quality!.issues.slice(0, 20).map((issue, i) => (
                  <li
                    key={i}
                    className={clsx(
                      "rounded-xl px-3 py-2 text-xs",
                      issue.severity === "high" && "bg-rose-50 text-rose-900",
                      issue.severity === "warning" && "bg-amber-50 text-amber-900",
                      issue.severity === "info" && "bg-slate-50 text-slate-700"
                    )}
                  >
                    {issue.message}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-slate-400">Issues are flagged only — nothing is deleted or changed.</p>
            </div>
          )}

          {/* Relationships */}
          {(d.relationships?.length || 0) > 0 && (
            <div className="card p-5">
              <h3 className="mb-3 text-sm font-bold text-slate-900">Possible relationships</h3>
              <div className="space-y-3">
                {d.relationships!.map((r) => (
                  <div key={r.label} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <p className="text-sm font-semibold text-slate-800">{r.label}</p>
                    <p className="text-xs text-slate-500">Confidence: {r.confidence}% · Status: {r.status}</p>
                    <div className="mt-2 flex gap-2">
                      <button className="btn-secondary text-xs" onClick={() => props.onRelStatus(r.label, "accepted")}>
                        Accept
                      </button>
                      <button className="btn-ghost text-xs" onClick={() => props.onRelStatus(r.label, "ignored")}>
                        Ignore
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Preview */}
          <div className="card overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Data preview</h3>
                <p className="text-xs text-slate-500">
                  Showing page {props.page} · {props.totalRows.toLocaleString()} filtered rows · first 50 per page
                </p>
              </div>
              <div className="flex gap-2">
                <input
                  className="input w-48"
                  placeholder="Search…"
                  value={props.search}
                  onChange={(e) => props.setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && props.onSearch()}
                />
                <button className="btn-secondary" onClick={props.onSearch}>
                  <Search className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="scroll-thin max-h-96 overflow-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="sticky top-0 z-10 bg-slate-50">
                  <tr>
                    {props.headers.map((h) => (
                      <th
                        key={h}
                        className="cursor-pointer whitespace-nowrap px-3 py-2 font-semibold text-slate-600 hover:text-blue-700"
                        onClick={() => props.onSort(h)}
                      >
                        {h}
                        {props.sortBy === h ? (props.sortDir === "asc" ? " ↑" : " ↓") : ""}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {props.previewRows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-100 hover:bg-slate-50/80">
                      {props.headers.map((h) => (
                        <td key={h} className="whitespace-nowrap px-3 py-1.5 text-slate-700">
                          {row[h] == null || row[h] === "" ? <span className="text-slate-300">—</span> : String(row[h])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
              <button className="btn-secondary text-xs" disabled={props.page <= 1} onClick={() => props.onPage(props.page - 1)}>
                Previous
              </button>
              <span className="text-xs text-slate-500">
                Page {props.page} of {props.totalPages}
              </span>
              <button
                className="btn-secondary text-xs"
                disabled={props.page >= props.totalPages}
                onClick={() => props.onPage(props.page + 1)}
              >
                Next
              </button>
            </div>
          </div>

          <div className="card flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-blue-50 to-white p-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Your data is ready.</h2>
              <p className="text-sm text-slate-500">Continue when you&apos;re ready to choose what to do next.</p>
            </div>
            <button className="btn-primary btn-lg" onClick={props.onContinue}>
              Continue to What Do You Want To Do?
            </button>
          </div>
        </div>

        {/* Column panel */}
        <aside className="space-y-4 xl:sticky xl:top-0 xl:self-start">
          {props.selectedColumn ? (
            <ColumnPanel col={props.selectedColumn} onClose={() => props.setSelectedColumn(null)} />
          ) : (
            <div className="card p-5 text-sm text-slate-500">
              <Filter className="mb-2 h-5 w-5 text-slate-300" />
              Select a column to inspect type, role, statistics, and suggested uses.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function ColumnPanel({ col, onClose }: { col: ColumnProfile; onClose: () => void }) {
  return (
    <div className="card p-5">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-blue-600">Column</p>
          <h3 className="text-lg font-bold text-slate-900">{col.name}</h3>
        </div>
        <button className="btn-ghost h-8 w-8 p-0" onClick={onClose}>
          <X className="h-4 w-4" />
        </button>
      </div>
      <dl className="space-y-2 text-sm">
        <Row k="Role" v={col.role.replace("_", " ")} />
        <Row k="Type" v={col.data_type} />
        <Row k="Type confidence" v={`${Math.round(col.type_confidence * 100)}%`} />
        <Row k="Records" v={String(col.non_null + col.null_count)} />
        <Row k="Unique" v={String(col.unique_count)} />
        <Row k="Missing" v={`${col.null_count} (${col.null_pct}%)`} />
        {col.min != null && <Row k="Minimum" v={fmt(col.min)} />}
        {col.max != null && <Row k="Maximum" v={fmt(col.max)} />}
        {col.average != null && <Row k="Average" v={fmt(col.average)} />}
        {col.sum != null && <Row k="Total" v={fmt(col.sum)} />}
        {col.median != null && <Row k="Median" v={fmt(col.median)} />}
        {col.min_date && <Row k="Min date" v={col.min_date.slice(0, 10)} />}
        {col.max_date && <Row k="Max date" v={col.max_date.slice(0, 10)} />}
      </dl>
      {col.top_values && col.top_values.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase text-slate-400">Most frequent</p>
          <ul className="mt-1 space-y-1 text-xs text-slate-600">
            {col.top_values.map((t) => (
              <li key={t.value} className="flex justify-between">
                <span className="truncate">{t.value}</span>
                <span className="font-semibold">{t.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-5">
        <p className="text-xs font-semibold uppercase text-slate-400">Suggested uses</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {(col.suggested_uses || []).map((u) => (
            <span key={u} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-500" title="Coming soon">
              {u} · soon
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-slate-50 py-1.5">
      <dt className="text-slate-500">{k}</dt>
      <dd className="text-right font-semibold capitalize text-slate-800">{v}</dd>
    </div>
  );
}

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function ComingSoon({ label, onBack, onUpload }: { label: string; onBack: () => void; onUpload: () => void }) {
  return (
    <section className="card mx-auto max-w-lg p-10 text-center">
      <Sparkles className="mx-auto h-10 w-10 text-slate-300" />
      <h1 className="mt-4 text-xl font-bold text-slate-900">{label}</h1>
      <p className="mt-2 text-sm text-slate-500">
        Coming soon. This stage will unlock after Upload & Profiling (Step 1).
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <button className="btn-primary" onClick={onUpload}>
          Upload Data
        </button>
        <button className="btn-secondary" onClick={onBack}>
          Home
        </button>
      </div>
    </section>
  );
}
