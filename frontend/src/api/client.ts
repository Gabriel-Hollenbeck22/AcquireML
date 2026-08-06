export const API_BASE_URL = "http://localhost:8000";

export interface SessionSummary {
  name: string;
  current_round: number;
  n_known: number;
  n_pool: number;
  n_pending: number;
  latest_accuracy: number | null;
}

export interface SessionCreateResponse {
  name: string;
  n_known: number;
  n_pool: number;
  label_col: string;
  patience: number;
  min_delta: number;
  cost_per_sample: number | null;
  diversity_weight: number;
  model: string;
  calibrate: boolean;
  calibration_method: string;
}

export interface CreateSessionInput {
  name: string;
  labelCol: string;
  labeledFile: File;
  poolFile?: File;
  model?: string;
  patience?: number;
  minDelta?: number;
  costPerSample?: number;
  diversityWeight?: number;
  calibrate?: boolean;
  calibrationMethod?: string;
}

export interface StatusResponse {
  name: string | null;
  current_round: number;
  n_known: number;
  n_pool: number;
  n_pending: number;
  latest_accuracy: number | null;
  patience: number;
  min_delta: number;
  cost_per_sample: number | null;
  total_cost: number | null;
  diversity_weight: number;
  model: string;
  calibrate: boolean;
  calibration_method: string;
  should_stop: boolean;
  stop_reason: string;
  created_at: string | null;
}

export interface HistoryRow {
  round_number: number;
  n_known: number;
  accuracy: number | null;
  round_cost: number | null;
  cumulative_cost: number | null;
  created_at: string;
}

export interface RecommendRow {
  rank: number;
  sample_id: string;
  uncertainty_score: number;
  p_positive: number;
  predicted_class: string;
}

export interface RecommendResponse {
  rows: RecommendRow[];
  should_stop: boolean;
  stop_reason: string;
}

export interface ResultRow {
  sample_id: string;
  label: number;
}

export interface UpdateResponse {
  round: number;
  n_returned: number;
  n_known: number;
  n_pool: number;
  accuracy: number;
  round_cost: number | null;
  cumulative_cost: number | null;
  should_stop: boolean;
  stop_reason: string;
}

export interface ResetResponse {
  n_known: number;
  n_pool: number;
  rounds_cleared: number;
}

export interface UpdateSettingsInput {
  patience?: number;
  minDelta?: number;
  costPerSample?: number;
  diversityWeight?: number;
  model?: string;
  calibrate?: boolean;
  calibrationMethod?: string;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
  } catch {
    // response body wasn't JSON — fall through to the generic message
  }
  return `Request failed with status ${response.status}`;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const response = await fetch(`${API_BASE_URL}/sessions`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function createSession(
  input: CreateSessionInput
): Promise<SessionCreateResponse> {
  const form = new FormData();
  form.set("name", input.name);
  form.set("label_col", input.labelCol);
  form.set("labeled_file", input.labeledFile);
  if (input.poolFile) form.set("pool_file", input.poolFile);
  if (input.model) form.set("model", input.model);
  if (input.patience !== undefined) form.set("patience", String(input.patience));
  if (input.minDelta !== undefined) form.set("min_delta", String(input.minDelta));
  if (input.costPerSample !== undefined) form.set("cost_per_sample", String(input.costPerSample));
  if (input.diversityWeight !== undefined) form.set("diversity_weight", String(input.diversityWeight));
  if (input.calibrate !== undefined) form.set("calibrate", String(input.calibrate));
  if (input.calibrationMethod) form.set("calibration_method", input.calibrationMethod);

  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getStatus(name: string): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/status`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getHistory(name: string): Promise<HistoryRow[]> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/history`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getRecommendations(
  name: string,
  batchSize?: number
): Promise<RecommendResponse> {
  const url = new URL(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/recommend`);
  if (batchSize !== undefined) {
    url.searchParams.set("batch_size", String(batchSize));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function submitResults(
  name: string,
  results: ResultRow[]
): Promise<UpdateResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ results }),
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function exportHistory(name: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/export`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.blob();
}

export async function updateSettings(
  name: string,
  input: UpdateSettingsInput
): Promise<StatusResponse> {
  const body: Record<string, string | number | boolean> = {};
  if (input.patience !== undefined) body.patience = input.patience;
  if (input.minDelta !== undefined) body.min_delta = input.minDelta;
  if (input.costPerSample !== undefined) body.cost_per_sample = input.costPerSample;
  if (input.diversityWeight !== undefined) body.diversity_weight = input.diversityWeight;
  if (input.model !== undefined) body.model = input.model;
  if (input.calibrate !== undefined) body.calibrate = input.calibrate;
  if (input.calibrationMethod !== undefined) body.calibration_method = input.calibrationMethod;

  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function resetSession(name: string): Promise<ResetResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/reset`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function deleteSession(name: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
}
