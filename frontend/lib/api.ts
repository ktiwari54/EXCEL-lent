const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type SheetInfo = {
  name: string;
  rows: number;
  columns: number;
  headers: string[];
  empty: boolean;
  error?: string;
  suggested_name: string;
};

export type InspectResult = {
  filename: string;
  kind: string;
  sheets: SheetInfo[];
  message: string;
};

export type ColumnProfile = {
  name: string;
  data_type: string;
  type_confidence: number;
  role: string;
  role_confidence: number;
  suggested_uses: string[];
  non_null: number;
  null_count: number;
  null_pct: number;
  unique_count: number;
  sample_values: unknown[];
  sum?: number;
  average?: number;
  median?: number;
  min?: number;
  max?: number;
  std?: number;
  min_date?: string;
  max_date?: string;
  top_values?: { value: string; count: number }[];
  role_overridden?: boolean;
};

export type HealthScore = {
  score: number;
  completeness: number;
  validity: number;
  uniqueness: number;
  consistency: number;
  type_confidence: number;
  explanation: string[];
};

export type QualityIssue = {
  severity: string;
  category: string;
  column: string | null;
  message: string;
  count: number;
};

export type Dataset = {
  id: string;
  name: string;
  original_filename?: string;
  sheet_name?: string;
  uploaded_at?: string;
  rows: number;
  columns: number;
  headers?: string[];
  column_profiles?: ColumnProfile[];
  quality?: { issues: QualityIssue[]; issue_count: number; missing_cells: number; duplicate_rows: number };
  health?: HealthScore;
  summary?: Record<string, number>;
  preview?: Record<string, unknown>[];
  relationships?: Relationship[];
  layers?: { raw: string; working: string };
};

export type Relationship = {
  left_dataset_id: string;
  left_dataset_name: string;
  left_column: string;
  right_dataset_id: string;
  right_dataset_name: string;
  right_column: string;
  confidence: number;
  status: string;
  label: string;
};

export type DatasetListItem = {
  id: string;
  name: string;
  original_filename?: string;
  sheet_name?: string;
  rows: number;
  columns: number;
  health?: number;
  uploaded_at?: string;
};

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let title = res.statusText;
    let message = res.statusText;
    try {
      const body = await res.json();
      const d = body.detail;
      if (typeof d === "string") {
        message = d;
        title = "Error";
      } else if (d && typeof d === "object") {
        title = d.title || "Error";
        message = d.message || JSON.stringify(d);
      }
    } catch {
      /* ignore */
    }
    throw new Error(`${title}: ${message}`);
  }
  return res.json() as Promise<T>;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function inspectFile(file: File): Promise<InspectResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/datasets/inspect`, { method: "POST", body: form });
  return handle(res);
}

export async function importFile(
  file: File,
  sheets: string[],
  names: Record<string, string>
): Promise<{ datasets: Dataset[]; relationships: Relationship[]; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("sheets", sheets.join(","));
  form.append("names", JSON.stringify(names));
  const res = await fetch(`${API_URL}/api/datasets/import`, { method: "POST", body: form });
  return handle(res);
}

export async function listDatasets(): Promise<DatasetListItem[]> {
  const res = await fetch(`${API_URL}/api/datasets`);
  const data = await handle<{ datasets: DatasetListItem[] }>(res);
  return data.datasets;
}

export async function getDataset(id: string): Promise<Dataset> {
  const res = await fetch(`${API_URL}/api/datasets/${id}`);
  return handle(res);
}

export async function renameDataset(id: string, name: string): Promise<Dataset> {
  const res = await fetch(`${API_URL}/api/datasets/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return handle(res);
}

export async function deleteDataset(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/datasets/${id}`, { method: "DELETE" });
  await handle(res);
}

export async function previewDataset(
  id: string,
  params: { page?: number; page_size?: number; search?: string; sort_by?: string; sort_dir?: string }
): Promise<{
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
  rows: Record<string, unknown>[];
}> {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.search) q.set("search", params.search);
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  const res = await fetch(`${API_URL}/api/datasets/${id}/preview?${q}`);
  return handle(res);
}

export async function setRelationshipStatus(id: string, label: string, status: string): Promise<Dataset> {
  const res = await fetch(`${API_URL}/api/datasets/${id}/relationships`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, status }),
  });
  return handle(res);
}

export async function overrideRole(id: string, column: string, role: string): Promise<Dataset> {
  const res = await fetch(`${API_URL}/api/datasets/${id}/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ column, role }),
  });
  return handle(res);
}

export { API_URL };
