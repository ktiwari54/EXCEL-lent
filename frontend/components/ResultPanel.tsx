"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  Lightbulb,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { AnalysisResult } from "@/lib/api";

const COLORS = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"];

export function ResultPanel({ result }: { result: AnalysisResult }) {
  const chartData =
    result.chart?.labels?.map((label, i) => ({
      name: label.length > 14 ? label.slice(0, 12) + "…" : label,
      full: label,
      value: result.chart!.values[i] ?? 0,
    })) || [];

  const chartType = result.chart?.type || "bar";
  const kpis = (result.meta?.kpis as Record<string, number> | undefined) || null;
  const extraCharts =
    (result.meta?.charts as Array<{
      title: string;
      type: string;
      labels: string[];
      values: number[];
    }>) || [];

  return (
    <div className="space-y-5">
      <div className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-1 inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700">
              <Sparkles className="h-3.5 w-3.5" />
              Result
            </div>
            <h2 className="text-xl font-bold text-slate-900">{result.title}</h2>
            {result.summary && <p className="mt-1.5 max-w-3xl text-sm text-slate-500">{result.summary}</p>}
          </div>
          {result.metric_value != null && (
            <div className="rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 px-5 py-3 text-right text-white shadow-lg shadow-blue-600/20">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-100">Key metric</p>
              <p className="text-2xl font-bold">
                {Number(result.metric_value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </p>
            </div>
          )}
        </div>
      </div>

      {kpis && Object.keys(kpis).length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          {Object.entries(kpis).map(([k, v]) => (
            <div key={k} className="kpi-card">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{k}</p>
              <p className="mt-1 text-xl font-bold text-slate-900">
                {typeof v === "number"
                  ? v.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : String(v)}
              </p>
            </div>
          ))}
        </div>
      )}

      {result.alerts?.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <div className="mb-2 flex items-center gap-2 font-semibold text-amber-900">
            <AlertTriangle className="h-4 w-4" />
            Alerts
          </div>
          <ul className="space-y-1.5 text-sm text-amber-900/90">
            {result.alerts.map((a, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.insights?.length > 0 && (
        <div className="card p-4">
          <div className="mb-2 flex items-center gap-2 font-semibold text-slate-900">
            <TrendingUp className="h-4 w-4 text-blue-600" />
            Insights
          </div>
          <ul className="space-y-1.5 text-sm text-slate-600">
            {result.insights.map((a, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.recommendations?.length > 0 && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="mb-2 flex items-center gap-2 font-semibold text-emerald-900">
            <Lightbulb className="h-4 w-4" />
            Recommendations
          </div>
          <ul className="space-y-1.5 text-sm text-emerald-900/90">
            {result.recommendations.map((a, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="card p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">{result.chart?.label || "Chart"}</h3>
          <div className="h-72 w-full">
            <ChartBlock type={chartType} data={chartData} color={COLORS[0]} />
          </div>
        </div>
      )}

      {extraCharts.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {extraCharts.map((c, idx) => {
            const data = c.labels.map((label, i) => ({
              name: label.length > 12 ? label.slice(0, 10) + "…" : label,
              value: c.values[i] ?? 0,
            }));
            return (
              <div key={idx} className="card p-5">
                <h3 className="mb-4 text-sm font-semibold text-slate-800">{c.title}</h3>
                <div className="h-56 w-full">
                  <ChartBlock type={c.type} data={data} color={COLORS[idx % COLORS.length]} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {result.table?.length > 0 && (
        <div className="card overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-3">
            <h3 className="text-sm font-semibold text-slate-800">Data table</h3>
          </div>
          <div className="scroll-thin max-h-96 overflow-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
                <tr>
                  {Object.keys(result.table[0]).map((h) => (
                    <th key={h} className="px-4 py-2.5 font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.table.slice(0, 100).map((row, i) => (
                  <tr key={i} className="border-t border-slate-100 hover:bg-slate-50/80">
                    {Object.keys(result.table[0]).map((h) => (
                      <td key={h} className="whitespace-nowrap px-4 py-2 text-slate-700">
                        {formatCell(row[h])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function ChartBlock({
  type,
  data,
  color,
}: {
  type: string;
  data: { name: string; value: number }[];
  color: string;
}) {
  if (type === "line" || type === "area") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (type === "pie" || type === "donut") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            outerRadius={100}
            innerRadius={type === "donut" ? 55 : 0}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Bar dataKey="value" fill={color} radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function formatCell(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "number") return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return String(v);
}
