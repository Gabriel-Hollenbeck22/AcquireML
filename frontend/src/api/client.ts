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
