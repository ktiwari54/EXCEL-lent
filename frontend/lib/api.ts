/**
 * Prefer same-origin paths so Next.js rewrites proxy to the FastAPI backend.
 * Override with NEXT_PUBLIC_API_URL only if you host API on another domain.
 */
const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

function url(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}`;
}

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
        title = "Couldn't process file";
      } else if (d && typeof d === "object") {
        title = d.title || "Couldn't process file";
        message = d.message || JSON.stringify(d);
      }
    } catch {
      /* ignore */
    }
    throw new Error(`${title}\n\n${message}`);
  }
  return res.json() as Promise<T>;
}

async function safeFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new Error(
      "Can't reach the Data Analyst Engine API.\n\n" +
        "The backend is not running. Start it with:\n" +
        "  cd backend\n" +
        "  .venv\\Scripts\\activate\n" +
        "  uvicorn app.main:app --host 127.0.0.1 --port 8000\n\n" +
        "Then refresh this page and try again."
    );
  }
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(url("/health"), { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function inspectFile(file: File): Promise<InspectResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await safeFetch(url("/api/datasets/inspect"), { method: "POST", body: form });
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
  const res = await safeFetch(url("/api/datasets/import"), { method: "POST", body: form });
  return handle(res);
}

export async function listDatasets(): Promise<DatasetListItem[]> {
  const res = await safeFetch(url("/api/datasets"));
  const data = await handle<{ datasets: DatasetListItem[] }>(res);
  return data.datasets;
}

export async function getDataset(id: string): Promise<Dataset> {
  const res = await safeFetch(url(`/api/datasets/${id}`));
  return handle(res);
}

export async function renameDataset(id: string, name: string): Promise<Dataset> {
  const res = await safeFetch(url(`/api/datasets/${id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return handle(res);
}

export async function deleteDataset(id: string): Promise<void> {
  const res = await safeFetch(url(`/api/datasets/${id}`), { method: "DELETE" });
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
  const res = await safeFetch(url(`/api/datasets/${id}/preview?${q}`));
  return handle(res);
}

export async function setRelationshipStatus(id: string, label: string, status: string): Promise<Dataset> {
  const res = await safeFetch(url(`/api/datasets/${id}/relationships`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, status }),
  });
  return handle(res);
}

export async function overrideRole(id: string, column: string, role: string): Promise<Dataset> {
  const res = await safeFetch(url(`/api/datasets/${id}/roles`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ column, role }),
  });
  return handle(res);
}

// ─── Step 2: Tasks ───────────────────────────────────────────

export type TaskItem = {
  id: string;
  name: string;
  category: string;
  description: string;
  examples?: string[];
  can_compare?: string[];
  keywords?: string[];
  availability?: "available" | "partial" | "unavailable";
  availability_reasons?: string[];
  can_start?: boolean;
  icon?: string;
  color?: string;
  facts_snapshot?: { measures?: string[]; dimensions?: string[]; dates?: string[] };
};

export type TaskRecommendation = {
  task_id: string;
  name: string;
  description: string;
  category: string;
  availability?: string;
  icon?: string;
  color?: string;
};

export type IntentResult = {
  intent?: string;
  task_id?: string;
  task_name?: string;
  confidence?: number;
  message?: string;
  availability?: string;
  can_start?: boolean;
  task?: TaskItem;
};

export type TaskSelection = {
  dataset_id: string;
  dataset_name?: string;
  task_id: string;
  task_name: string;
  task_category: string;
  objective?: string;
  secondary_dataset_ids?: string[];
  detected_fields?: Record<string, string[]>;
  history_id?: string;
  stage?: string;
};

export type HistoryItem = {
  id: string;
  dataset_id: string;
  dataset_name: string;
  task_id: string;
  task_name: string;
  category: string;
  timestamp: string;
};

export async function fetchTasks(datasetId: string): Promise<{
  tasks: TaskItem[];
  recommendations: TaskRecommendation[];
}> {
  const res = await safeFetch(url(`/api/tasks?dataset_id=${encodeURIComponent(datasetId)}`));
  return handle(res);
}

export async function searchTasksApi(q: string, datasetId?: string): Promise<TaskItem[]> {
  const params = new URLSearchParams({ q });
  if (datasetId) params.set("dataset_id", datasetId);
  const res = await safeFetch(url(`/api/tasks/search?${params}`));
  const data = await handle<{ results: TaskItem[] }>(res);
  return data.results;
}

export async function classifyIntentApi(query: string, datasetId?: string): Promise<IntentResult> {
  const res = await safeFetch(url("/api/tasks/intent"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, dataset_id: datasetId || null }),
  });
  return handle(res);
}

export async function startTaskApi(payload: {
  dataset_id: string;
  task_id: string;
  secondary_dataset_ids?: string[];
  objective?: string;
}): Promise<{ selection: TaskSelection; next: string }> {
  const res = await safeFetch(url("/api/tasks/start"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

export async function fetchTaskHistory(): Promise<HistoryItem[]> {
  const res = await safeFetch(url("/api/tasks/history"));
  const data = await handle<{ items: HistoryItem[] }>(res);
  return data.items;
}

// ─── Step 3: Configure ───────────────────────────────────────

export async function getConfigSchema(datasetId: string, taskId: string): Promise<Record<string, unknown>> {
  const res = await safeFetch(
    url(`/api/configure/schema?dataset_id=${encodeURIComponent(datasetId)}&task_id=${encodeURIComponent(taskId)}`)
  );
  return handle(res);
}

export async function validateConfiguration(body: {
  dataset_id: string;
  task_id: string;
  configuration: Record<string, unknown>;
}): Promise<{ valid: boolean; errors: string[] }> {
  const res = await safeFetch(url("/api/configure/validate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle(res);
}

export async function saveConfiguration(body: {
  dataset_id: string;
  task_id: string;
  configuration: Record<string, unknown>;
  name?: string;
}): Promise<{ saved: Record<string, unknown> }> {
  const res = await safeFetch(url("/api/configure/save"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle(res);
}

export async function listRecentConfigs(datasetId?: string): Promise<Record<string, unknown>[]> {
  const q = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
  const res = await safeFetch(url(`/api/configure/recent${q}`));
  const data = await handle<{ items: Record<string, unknown>[] }>(res);
  return data.items;
}

export async function generateAnalysis(body: {
  dataset_id: string;
  task_id: string;
  configuration: Record<string, unknown>;
  name?: string;
  save?: boolean;
}): Promise<Record<string, unknown>> {
  const res = await safeFetch(url("/api/configure/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle(res);
}

export { API_URL };
