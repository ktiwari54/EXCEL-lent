"use client";

import type { DatasetProfile } from "@/lib/api";
import { Table2 } from "lucide-react";

export function DataPreview({ profile }: { profile: DatasetProfile }) {
  const rows = profile.preview || [];
  if (!rows.length) return null;
  const headers = Object.keys(rows[0]);

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
            <Table2 className="h-4 w-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Your data</h3>
            <p className="text-xs text-slate-500">
              Preview · first {rows.length} of {profile.rows.toLocaleString()} rows
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="chip-blue">{profile.columns} columns</span>
          {profile.duplicate_rows > 0 && (
            <span className="chip-amber">{profile.duplicate_rows} duplicates</span>
          )}
          {profile.missing_cells > 0 && (
            <span className="chip-rose">{profile.missing_cells} missing cells</span>
          )}
          {profile.duplicate_rows === 0 && profile.missing_cells === 0 && (
            <span className="chip-green">Looks clean</span>
          )}
        </div>
      </div>
      <div className="scroll-thin max-h-64 overflow-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur">
            <tr>
              {headers.map((h) => {
                const meta = profile.column_profiles.find((c) => c.name === h);
                return (
                  <th key={h} className="whitespace-nowrap px-4 py-2.5 font-semibold text-slate-600">
                    <div>{h}</div>
                    {meta && (
                      <div className="mt-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                        {meta.inferred_type}
                      </div>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-slate-100 hover:bg-brand-50/30">
                {headers.map((h) => (
                  <td key={h} className="whitespace-nowrap px-4 py-2 text-slate-700">
                    {row[h] == null || row[h] === "" ? (
                      <span className="text-slate-300">—</span>
                    ) : (
                      String(row[h])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
