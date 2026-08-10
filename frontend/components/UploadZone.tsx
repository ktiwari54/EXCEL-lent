"use client";

import { useCallback, useState } from "react";
import { FileSpreadsheet, UploadCloud } from "lucide-react";
import clsx from "clsx";

export function UploadZone({
  onFile,
  loading,
}: {
  onFile: (file: File) => void;
  loading?: boolean;
}) {
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    (list: FileList | null) => {
      const file = list?.[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  return (
    <label
      onDragEnter={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={clsx(
        "group relative flex cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed px-6 py-16 transition",
        dragOver
          ? "border-brand-500 bg-brand-50 scale-[1.01]"
          : "border-brand-200/80 bg-gradient-to-b from-white to-brand-50/40 hover:border-brand-400 hover:shadow-lg hover:shadow-brand-600/5",
        loading && "pointer-events-none opacity-70"
      )}
    >
      <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-brand-100/50 blur-2xl" />
      <div className="absolute -bottom-12 -left-8 h-36 w-36 rounded-full bg-emerald-100/40 blur-2xl" />

      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/30">
        {loading ? (
          <span className="h-7 w-7 animate-spin rounded-full border-2 border-white border-t-transparent" />
        ) : (
          <UploadCloud className="h-8 w-8" />
        )}
      </div>

      <h3 className="relative mt-5 text-xl font-bold text-slate-900">
        {loading ? "Reading your data…" : "Drop your file here"}
      </h3>
      <p className="relative mt-2 max-w-md text-center text-sm text-slate-500">
        Excel or CSV — we detect columns, types, and issues automatically.
        <br />
        No formulas required.
      </p>

      <div className="relative mt-6 flex flex-wrap items-center justify-center gap-2">
        <span className="chip-blue">
          <FileSpreadsheet className="h-3.5 w-3.5" /> .xlsx
        </span>
        <span className="chip-blue">.xls</span>
        <span className="chip-blue">.csv</span>
        <span className="chip-slate">up to 50 MB</span>
      </div>

      <span className="relative mt-8 btn-primary btn-lg pointer-events-none">
        Choose file
      </span>

      <input
        type="file"
        accept=".xlsx,.xls,.xlsm,.csv,.txt"
        className="hidden"
        disabled={loading}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </label>
  );
}
