const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ColumnProfile = {
  name: string;
  dtype: string;
  inferred_type: string;
  non_null: number;
  null_count: number;
  null_pct: number;
  unique_count: number;
  sample_values: unknown[];
  is_numeric: boolean;
  is_datetime: boolean;
  is_categorical: boolean;
  is_id_like: boolean;
  min?: unknown;
  max?: unknown;
  mean?: number | null;
};

export type DatasetProfile = {
  session_id: string;
  filename: string;
  rows: number;
  columns: number;
  column_profiles: ColumnProfile[];
  duplicate_rows: number;
  missing_cells: number;
  sheet_names: string[];
  active_sheet?: string | null;
  preview: Record<string, unknown>[];
};

export type AnalysisResult = {
  success: boolean;
  title: string;
  summary?: string | null;
  metric_value?: number | null;
  table: Record<string, unknown>[];
  chart?: {
    type: string;
    labels: string[];
    values: number[];
    label?: string;
    title?: string;
  } | null;
  insights: string[];
  alerts: string[];
  recommendations: string[];
  meta: Record<string, unknown>;
};

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export async function uploadFile(file: File): Promise<DatasetProfile> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/upload`, { method: "POST", body: form });
  return handle(res);
}

export async function postAnalysis<T extends object>(
  path: string,
  body: T
): Promise<AnalysisResult> {
  const res = await fetch(`${API_URL}/api/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle(res);
}

export async function getTemplates(): Promise<{
  templates: Record<string, string[]>;
}> {
  const res = await fetch(`${API_URL}/api/templates`);
  return handle(res);
}

export function exportUrl(sessionId: string): string {
  return `${API_URL}/api/export`;
}

export async function exportWorkbook(sessionId: string): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      include_cleaned: true,
      include_insights: true,
    }),
  });
  if (!res.ok) throw new Error("Export failed");
  return res.blob();
}

export { API_URL };
