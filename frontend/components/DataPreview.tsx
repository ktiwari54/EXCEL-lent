"use client";

import type { DatasetProfile } from "@/lib/api";

export function DataPreview({ profile }: { profile: DatasetProfile }) {
  const rows = profile.preview || [];
  if (!rows.length) {
    return (
      <div className="card p-5 text-sm text-slate-500">No preview rows available.</div>
    );
  }
  const headers = Object.keys(rows[0]);

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
        <div>
          <h3 className="font-semibold text-brand-800">Data preview</h3>
          <p className="text-xs text-slate-500">
            First {rows.length} of {profile.rows.toLocaleString()} rows
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-brand-50 px-2.5 py-1 font-medium text-brand-700">
            {profile.columns} columns
          </span>
          {profile.duplicate_rows > 0 && (
            <span className="rounded-full bg-amber-50 px-2.5 py-1 font-medium text-amber-800">
              {profile.duplicate_rows} duplicates
            </span>
          )}
          {profile.missing_cells > 0 && (
            <span className="rounded-full bg-rose-50 px-2.5 py-1 font-medium text-rose-800">
              {profile.missing_cells} missing
            </span>
          )}
        </div>
      </div>
      <div className="max-h-72 overflow-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              {headers.map((h) => (
                <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-slate-100 hover:bg-slate-50/80">
                {headers.map((h) => (
                  <td key={h} className="whitespace-nowrap px-3 py-1.5 text-slate-700">
                    {row[h] == null ? "—" : String(row[h])}
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
