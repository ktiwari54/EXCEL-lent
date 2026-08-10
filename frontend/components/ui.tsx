"use client";

import { ReactNode } from "react";
import clsx from "clsx";

export function FieldSelect({
  label,
  value,
  onChange,
  options,
  allowEmpty,
  help,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  allowEmpty?: boolean;
  help?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {allowEmpty && <option value="">Any / none</option>}
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      {help && <p className="mt-1 text-xs text-slate-400">{help}</p>}
    </div>
  );
}

export function FieldInput({
  label,
  value,
  onChange,
  placeholder,
  help,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  help?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        className="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {help && <p className="mt-1 text-xs text-slate-400">{help}</p>}
    </div>
  );
}

export function EmptyHint({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
      {children}
    </div>
  );
}

export function StatPill({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: string | number;
  tone?: "slate" | "blue" | "green" | "amber" | "rose";
}) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    blue: "bg-brand-50 text-brand-700",
    green: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-800",
    rose: "bg-rose-50 text-rose-700",
  };
  return (
    <div className={clsx("rounded-xl px-3 py-2", tones[tone])}>
      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-sm font-bold">{value}</p>
    </div>
  );
}

export function LoadingOverlay({ label = "Working…" }: { label?: string }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 backdrop-blur-[2px]">
      <div className="card flex items-center gap-3 px-6 py-4 shadow-xl">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        <span className="text-sm font-semibold text-slate-800">{label}</span>
      </div>
    </div>
  );
}
