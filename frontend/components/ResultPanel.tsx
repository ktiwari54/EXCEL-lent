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
import type { AnalysisResult } from "@/lib/api";

const COLORS = ["#1f4e79", "#2676ba", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

export function ResultPanel({ result }: { result: AnalysisResult }) {
  const chartData =
    result.chart?.labels?.map((label, i) => ({
      name: label,
      value: result.chart!.values[i] ?? 0,
    })) || [];

  const chartType = result.chart?.type || "bar";
  const kpis = (result.meta?.kpis as Record<string, number> | undefined) || null;
  const extraCharts = (result.meta?.charts as Array<{
    title: string;
    type: string;
    labels: string[];
    values: number[];
  }>) || [];

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-brand-500">Result</p>
            <h2 className="mt-1 text-xl font-bold text-brand-800">{result.title}</h2>
            {result.summary && <p className="mt-2 text-sm text-slate-600">{result.summary}</p>}
          </div>
          {result.metric_value != null && (
            <div className="rounded-2xl bg-brand-50 px-5 py-3 text-right">
              <p className="text-xs font-semibold uppercase text-brand-500">Metric</p>
              <p className="text-2xl font-bold text-brand-700">
                {Number(result.metric_value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </p>
            </div>
          )}
        </div>
      </div>

      {kpis && Object.keys(kpis).length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(kpis).map(([k, v]) => (
            <div key={k} className="card p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{k}</p>
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
        <div className="card border-amber-200 bg-amber-50/80 p-5">
          <h3 className="font-semibold text-amber-900">Alerts</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-amber-900/90">
            {result.alerts.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </div>
      )}

      {result.insights?.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-brand-800">Insights</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
            {result.insights.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </div>
      )}

      {result.recommendations?.length > 0 && (
        <div className="card border-emerald-200 bg-emerald-50/60 p-5">
          <h3 className="font-semibold text-emerald-900">Recommendations</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-emerald-900/90">
            {result.recommendations.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="card p-5">
          <h3 className="mb-4 font-semibold text-brand-800">
            {result.chart?.label || "Chart"}
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {chartType === "line" || chartType === "area" ? (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#1f4e79" strokeWidth={2} dot />
                </LineChart>
              ) : chartType === "pie" || chartType === "donut" ? (
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={100}
                    innerRadius={chartType === "donut" ? 55 : 0}
                    label
                  >
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              ) : (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#1f4e79" radius={[6, 6, 0, 0]} />
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {extraCharts.map((c, idx) => {
        const data = c.labels.map((label, i) => ({ name: label, value: c.values[i] ?? 0 }));
        return (
          <div key={idx} className="card p-5">
            <h3 className="mb-4 font-semibold text-brand-800">{c.title}</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                {c.type === "line" ? (
                  <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} />
                  </LineChart>
                ) : (
                  <BarChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill={COLORS[idx % COLORS.length]} radius={[6, 6, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>
        );
      })}

      {result.table?.length > 0 && (
        <div className="card overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-3">
            <h3 className="font-semibold text-brand-800">Data table</h3>
          </div>
          <div className="max-h-96 overflow-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  {Object.keys(result.table[0]).map((h) => (
                    <th key={h} className="px-4 py-2 font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.table.slice(0, 100).map((row, i) => (
                  <tr key={i} className="border-t border-slate-100 hover:bg-slate-50/80">
                    {Object.keys(result.table[0]).map((h) => (
                      <td key={h} className="px-4 py-2 whitespace-nowrap text-slate-700">
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

function formatCell(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "number") return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return String(v);
}
