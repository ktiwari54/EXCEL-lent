"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { AlertTriangle, ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";
import type { Dataset, TaskSelection } from "@/lib/api";
import {
  generateAnalysis,
  getConfigSchema,
  listRecentConfigs,
  saveConfiguration,
  validateConfiguration,
} from "@/lib/api";

type FieldOpt = { value: string; label: string };
type SchemaField = {
  id: string;
  kind: string;
  label: string;
  help?: string;
  required?: boolean;
  allow_empty?: boolean;
  options?: FieldOpt[];
  default?: unknown;
  operators?: FieldOpt[];
  column_options?: FieldOpt[];
  recommended?: string;
  recommendation_reason?: string;
};

type Schema = {
  task: { id: string; name: string; category?: string; description?: string };
  title: string;
  subtitle: string;
  output_type: string;
  submit_label: string;
  fields: SchemaField[];
  advanced: SchemaField[];
  defaults: Record<string, unknown>;
  chart_recommendation?: { type: string; reason: string };
  preview_hint?: { note: string; columns: string[]; rows: Record<string, unknown>[] };
  dataset: { id: string; name: string; rows: number; columns: number; health?: number };
};

type FilterRow = { field: string; operator: string; value: string; join?: string };

export function ConfigureTaskView({
  selection,
  dataset,
  onChangeTask,
  onBackProfile,
  onGenerated,
}: {
  selection: TaskSelection;
  dataset: Dataset | null;
  onChangeTask: () => void;
  onBackProfile: () => void;
  onGenerated: (payload: Record<string, unknown>) => void;
}) {
  const [schema, setSchema] = useState<Schema | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState<Record<string, unknown>[]>([]);
  const [saveName, setSaveName] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErrors([]);
    try {
      const s = (await getConfigSchema(selection.dataset_id, selection.task_id)) as Schema;
      setSchema(s);
      setValues({ ...(s.defaults || {}) });
      setSaveName(`${selection.task_name} — ${selection.dataset_name || "dataset"}`);
      const rec = await listRecentConfigs(selection.dataset_id);
      setRecent(rec || []);
    } catch (e) {
      setErrors([e instanceof Error ? e.message : "Failed to load configuration"]);
    } finally {
      setLoading(false);
    }
  }, [selection.dataset_id, selection.task_id, selection.task_name, selection.dataset_name]);

  useEffect(() => {
    load();
  }, [load]);

  function setField(id: string, v: unknown) {
    setValues((prev) => ({ ...prev, [id]: v }));
    setErrors([]);
  }

  function filters(): FilterRow[] {
    return (values.filters as FilterRow[]) || [];
  }

  function setFilters(next: FilterRow[]) {
    setField("filters", next);
  }

  async function onValidate() {
    const r = await validateConfiguration({
      dataset_id: selection.dataset_id,
      task_id: selection.task_id,
      configuration: values,
    });
    setErrors(r.valid ? [] : r.errors);
    return r.valid;
  }

  async function onSave() {
    setLoading(true);
    setMsg(null);
    try {
      const ok = await onValidate();
      if (!ok) return;
      await saveConfiguration({
        dataset_id: selection.dataset_id,
        task_id: selection.task_id,
        configuration: values,
        name: saveName,
      });
      setMsg("Analysis configuration saved.");
      const rec = await listRecentConfigs(selection.dataset_id);
      setRecent(rec || []);
    } catch (e) {
      setErrors([e instanceof Error ? e.message : "Save failed"]);
    } finally {
      setLoading(false);
    }
  }

  async function onGenerate() {
    setLoading(true);
    setMsg(null);
    try {
      const ok = await onValidate();
      if (!ok) {
        setLoading(false);
        return;
      }
      const result = await generateAnalysis({
        dataset_id: selection.dataset_id,
        task_id: selection.task_id,
        configuration: values,
        name: saveName,
        save: true,
      });
      onGenerated(result as unknown as Record<string, unknown>);
    } catch (e) {
      setErrors([e instanceof Error ? e.message : "Generate failed"]);
    } finally {
      setLoading(false);
    }
  }

  function loadRecent(item: Record<string, unknown>) {
    const cfg = (item.configuration as Record<string, unknown>) || {};
    setValues(cfg);
    setSaveName(String(item.name || saveName));
    setMsg("Loaded saved configuration. Review and generate again.");
  }

  if (loading && !schema) {
    return <div className="card p-8 text-center text-sm text-slate-500">Loading configuration…</div>;
  }

  if (!schema) {
    return (
      <div className="card p-8 text-center">
        <p className="text-rose-700">{errors[0] || "Could not load configuration."}</p>
        <button className="btn-secondary mt-4" onClick={onChangeTask}>
          Change task
        </button>
      </div>
    );
  }

  const ds = schema.dataset;

  return (
    <div className="mx-auto grid max-w-[1100px] gap-5 lg:grid-cols-[1fr_300px]">
      <div className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Step 3 · Configure</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Configure Your Analysis</h1>
          <p className="mt-1 text-slate-500">Tell us what you want to analyze. We&apos;ll handle the technical work.</p>
        </div>

        <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <p className="text-[11px] font-semibold uppercase text-slate-400">Current dataset</p>
            <p className="font-semibold text-slate-900">{ds.name}</p>
            <p className="text-xs text-slate-500">
              {Number(ds.rows || 0).toLocaleString()} records · {ds.columns} fields · Health {ds.health ?? "—"}/100
            </p>
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={onBackProfile}>
              View data
            </button>
            <button className="btn-secondary" onClick={onChangeTask}>
              Change task
            </button>
          </div>
        </div>

        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase text-slate-400">Your task</p>
          <p className="text-lg font-bold text-slate-900">
            {schema.task.category} · {schema.task.name}
          </p>
          <p className="text-sm text-slate-500">{schema.task.description}</p>
        </div>

        <div className="card space-y-5 p-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900">{schema.title}</h2>
            <p className="text-sm text-slate-500">{schema.subtitle}</p>
          </div>

          {errors.length > 0 && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <div className="mb-1 flex items-center gap-2 font-semibold">
                <AlertTriangle className="h-4 w-4" /> Please fix
              </div>
              <ul className="list-disc pl-5">
                {errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          {msg && <div className="rounded-xl bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{msg}</div>}

          {schema.fields.map((f) => (
            <FieldRenderer key={f.id} field={f} value={values[f.id]} onChange={(v) => setField(f.id, v)} filters={filters()} setFilters={setFilters} />
          ))}

          {schema.advanced?.length > 0 && (
            <div className="border-t border-slate-100 pt-4">
              <button
                type="button"
                className="flex items-center gap-2 text-sm font-semibold text-slate-700"
                onClick={() => setAdvancedOpen((o) => !o)}
              >
                {advancedOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                Advanced options
              </button>
              {advancedOpen && (
                <div className="mt-4 space-y-4">
                  {schema.advanced.map((f) => (
                    <FieldRenderer key={f.id} field={f} value={values[f.id]} onChange={(v) => setField(f.id, v)} filters={filters()} setFilters={setFilters} />
                  ))}
                </div>
              )}
            </div>
          )}

          {schema.preview_hint && (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase text-slate-400">Result preview (layout)</p>
              <p className="mt-1 text-[11px] text-slate-500">{schema.preview_hint.note}</p>
              <table className="mt-3 w-full text-left text-xs">
                <thead>
                  <tr className="text-slate-500">
                    {(schema.preview_hint.columns || []).map((c) => (
                      <th key={c} className="pb-1 pr-3 font-semibold">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(schema.preview_hint.rows || []).map((row, i) => (
                    <tr key={i} className="border-t border-slate-200/80">
                      {(schema.preview_hint!.columns || []).map((c) => (
                        <td key={c} className="py-1.5 pr-3 text-slate-700">
                          {String(row[c] ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex flex-wrap items-end gap-3 border-t border-slate-100 pt-5">
            <div className="min-w-[200px] flex-1">
              <label className="label">Save as</label>
              <input className="input" value={saveName} onChange={(e) => setSaveName(e.target.value)} />
            </div>
            <button className="btn-secondary" disabled={loading} onClick={onSave}>
              Save analysis
            </button>
            <button className="btn-primary btn-lg" disabled={loading} onClick={onGenerate}>
              {loading ? "Working…" : schema.submit_label || "Generate Analysis"}
            </button>
          </div>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="card p-4">
          <p className="text-sm font-bold text-slate-900">Recent configurations</p>
          {recent.length === 0 ? (
            <p className="mt-2 text-xs text-slate-500">No saved analyses yet.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {recent.slice(0, 8).map((r) => (
                <li key={String(r.id)}>
                  <button
                    type="button"
                    className="w-full rounded-xl bg-slate-50 px-3 py-2 text-left hover:bg-blue-50"
                    onClick={() => loadRecent(r)}
                  >
                    <p className="text-xs font-semibold text-slate-800">{String(r.name)}</p>
                    <p className="text-[11px] text-slate-500">{r.task_name as string} · Run again</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card p-4 text-xs text-slate-500">
          <p className="font-semibold text-slate-700">Guided configuration</p>
          <p className="mt-1">Only fields needed for this task are shown. Calculations run in Step 4.</p>
        </div>
      </aside>
    </div>
  );
}

function FieldRenderer({
  field,
  value,
  onChange,
  filters,
  setFilters,
}: {
  field: SchemaField;
  value: unknown;
  onChange: (v: unknown) => void;
  filters: FilterRow[];
  setFilters: (f: FilterRow[]) => void;
}) {
  const opts = field.options || [];

  if (field.kind === "filter_builder") {
    return (
      <div>
        <label className="label">{field.label}</label>
        {field.help && <p className="mb-2 text-xs text-slate-500">{field.help}</p>}
        <div className="space-y-2">
          {filters.map((row, idx) => (
            <div key={idx} className="flex flex-wrap items-center gap-2">
              {idx > 0 && (
                <select
                  className="input w-20"
                  value={row.join || "AND"}
                  onChange={(e) => {
                    const next = [...filters];
                    next[idx] = { ...row, join: e.target.value };
                    setFilters(next);
                  }}
                >
                  <option value="AND">AND</option>
                  <option value="OR">OR</option>
                </select>
              )}
              <select
                className="input min-w-[120px] flex-1"
                value={row.field}
                onChange={(e) => {
                  const next = [...filters];
                  next[idx] = { ...row, field: e.target.value };
                  setFilters(next);
                }}
              >
                <option value="">Field</option>
                {(field.column_options || []).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <select
                className="input w-36"
                value={row.operator}
                onChange={(e) => {
                  const next = [...filters];
                  next[idx] = { ...row, operator: e.target.value };
                  setFilters(next);
                }}
              >
                {(field.operators || []).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <input
                className="input min-w-[100px] flex-1"
                value={row.value}
                onChange={(e) => {
                  const next = [...filters];
                  next[idx] = { ...row, value: e.target.value };
                  setFilters(next);
                }}
                placeholder="Value"
              />
              <button
                type="button"
                className="btn-ghost text-rose-600"
                onClick={() => setFilters(filters.filter((_, i) => i !== idx))}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn-secondary text-xs"
            onClick={() =>
              setFilters([
                ...filters,
                { field: "", operator: "eq", value: "", join: "AND" },
              ])
            }
          >
            <Plus className="h-3.5 w-3.5" /> Add filter
          </button>
        </div>
      </div>
    );
  }

  if (field.kind === "group_by_list" || field.kind === "multi_column" || field.kind === "multi_select") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div>
        <label className="label">{field.label}</label>
        {field.help && <p className="mb-2 text-xs text-slate-500">{field.help}</p>}
        <div className="flex flex-wrap gap-2">
          {opts.map((o) => {
            const on = selected.includes(o.value);
            return (
              <button
                key={o.value}
                type="button"
                className={clsx(
                  "rounded-full border px-3 py-1.5 text-xs font-medium",
                  on ? "border-blue-500 bg-blue-50 text-blue-800" : "border-slate-200 bg-white text-slate-600"
                )}
                onClick={() => {
                  if (on) onChange(selected.filter((x) => x !== o.value));
                  else onChange([...selected, o.value]);
                }}
              >
                {o.label}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (field.kind === "radio") {
    return (
      <div>
        <label className="label">{field.label}</label>
        {field.help && <p className="mb-2 text-xs text-slate-500">{field.help}</p>}
        <div className="flex flex-wrap gap-2">
          {opts.map((o) => (
            <button
              key={o.value}
              type="button"
              className={clsx(
                "rounded-xl border px-3 py-2 text-sm font-medium",
                value === o.value ? "border-blue-500 bg-blue-50 text-blue-800" : "border-slate-200"
              )}
              onClick={() => onChange(o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (field.kind === "boolean") {
    return (
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        {field.label}
      </label>
    );
  }

  if (field.kind === "text" || field.kind === "number") {
    return (
      <div>
        <label className="label">{field.label}</label>
        {field.help && <p className="mb-1 text-xs text-slate-500">{field.help}</p>}
        <input
          className="input"
          type={field.kind === "number" ? "number" : "text"}
          value={value == null ? "" : String(value)}
          onChange={(e) => onChange(field.kind === "number" ? Number(e.target.value) : e.target.value)}
        />
      </div>
    );
  }

  // select / measure / dimension / date / chart_type / dataset_select / any_column
  return (
    <div>
      <label className="label">{field.label}</label>
      {field.help && <p className="mb-1 text-xs text-slate-500">{field.help}</p>}
      {field.kind === "chart_type" && field.recommendation_reason && (
        <p className="mb-2 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-800">{field.recommendation_reason}</p>
      )}
      <select className="input" value={value == null ? "" : String(value)} onChange={(e) => onChange(e.target.value)}>
        {!field.required || field.allow_empty ? <option value="">— none —</option> : null}
        {opts.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function PreparingPlaceholder({
  payload,
  onBack,
  onConfigure,
}: {
  payload: Record<string, unknown>;
  onBack: () => void;
  onConfigure: () => void;
}) {
  const tr = (payload.task_request as Record<string, unknown>) || {};
  const ph = (payload.placeholder as Record<string, string>) || {};
  const result = payload.result as Record<string, unknown> | undefined;
  const meta = (result?.meta as Record<string, unknown>) || {};
  const engines = (meta.engines_used as string[]) || [];

  // If BI pipeline returned a result, show it
  if (result && payload.status === "completed") {
    return (
      <div className="mx-auto max-w-[1100px] space-y-4">
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={onConfigure}>
            Edit configuration
          </button>
          <button className="btn-secondary" onClick={onBack}>
            Choose another task
          </button>
        </div>
        {engines.length > 0 && (
          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="font-semibold text-slate-500">Pipeline:</span>
            {["semantic", ...engines, "insight", "result"].map((e) => (
              <span key={e} className="rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
                {e}
              </span>
            ))}
          </div>
        )}
        <AnalysisResultView result={result} />
      </div>
    );
  }

  return (
    <section className="card mx-auto max-w-2xl p-8">
      <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      <h1 className="text-center text-2xl font-bold text-slate-900">{ph.title || "Preparing your analysis…"}</h1>
      <p className="mt-2 text-center text-slate-500">{ph.body}</p>
      <div className="mt-6 rounded-2xl bg-slate-50 p-4 text-xs text-slate-600">
        <p className="font-semibold text-slate-800">Task request</p>
        <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-all">
          {JSON.stringify(tr.normalized || tr, null, 2)}
        </pre>
      </div>
      <div className="mt-6 flex justify-center gap-3">
        <button className="btn-primary" onClick={onConfigure}>
          Edit configuration
        </button>
        <button className="btn-secondary" onClick={onBack}>
          Choose another task
        </button>
      </div>
    </section>
  );
}

function AnalysisResultView({ result }: { result: Record<string, unknown> }) {
  const table = (result.table as Record<string, unknown>[]) || [];
  const insights = (result.insights as string[]) || [];
  const alerts = (result.alerts as string[]) || [];
  const recs = (result.recommendations as string[]) || [];
  const chart = result.chart as { type?: string; labels?: string[]; values?: number[]; label?: string } | null;
  const kpis = ((result.meta as Record<string, unknown>)?.kpis as Record<string, number>) || null;

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <h1 className="text-xl font-bold text-slate-900">{String(result.title || "Result")}</h1>
        {result.summary != null && <p className="mt-1 text-sm text-slate-600">{String(result.summary)}</p>}
        {result.metric_value != null && (
          <p className="mt-3 text-3xl font-bold text-blue-700">
            {Number(result.metric_value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </p>
        )}
      </div>

      {kpis && Object.keys(kpis).length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(kpis).map(([k, v]) => (
            <div key={k} className="kpi-card">
              <p className="text-[11px] font-semibold uppercase text-slate-400">{k}</p>
              <p className="text-lg font-bold text-slate-900">
                {typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v)}
              </p>
            </div>
          ))}
        </div>
      )}

      {alerts.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {alerts.map((a, i) => (
            <p key={i}>• {a}</p>
          ))}
        </div>
      )}
      {insights.length > 0 && (
        <div className="card p-4 text-sm text-slate-700">
          <p className="mb-2 font-semibold text-slate-900">Insights</p>
          {insights.map((a, i) => (
            <p key={i}>• {a}</p>
          ))}
        </div>
      )}
      {recs.length > 0 && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="mb-2 font-semibold">Recommendations</p>
          {recs.map((a, i) => (
            <p key={i}>• {a}</p>
          ))}
        </div>
      )}

      {chart?.labels && chart.values && (
        <div className="card p-4 text-xs text-slate-600">
          <p className="mb-2 text-sm font-semibold text-slate-800">{chart.label || "Chart"} ({chart.type})</p>
          <div className="space-y-1">
            {chart.labels.slice(0, 12).map((lab, i) => {
              const max = Math.max(...(chart.values || [1]), 1);
              const w = Math.round((100 * (chart.values![i] || 0)) / max);
              return (
                <div key={lab + i} className="flex items-center gap-2">
                  <span className="w-28 truncate text-slate-600">{lab}</span>
                  <div className="h-2 flex-1 rounded bg-slate-100">
                    <div className="h-2 rounded bg-blue-600" style={{ width: `${w}%` }} />
                  </div>
                  <span className="w-16 text-right font-medium">
                    {Number(chart.values![i] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {table.length > 0 && (
        <div className="card overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-[11px] uppercase text-slate-500">
              <tr>
                {Object.keys(table[0]).map((h) => (
                  <th key={h} className="px-3 py-2">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.slice(0, 50).map((row, i) => (
                <tr key={i} className="border-t border-slate-100">
                  {Object.keys(table[0]).map((h) => (
                    <td key={h} className="px-3 py-1.5 whitespace-nowrap text-slate-700">
                      {row[h] == null ? "—" : String(row[h])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
