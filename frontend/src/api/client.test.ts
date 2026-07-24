import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createSession,
  exportHistory,
  getHistory,
  getRecommendations,
  getStatus,
  listSessions,
  submitResults,
} from "./client";

describe("listSessions", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions and returns parsed JSON", async () => {
    const mockSessions = [
      {
        name: "azm-project",
        current_round: 2,
        n_known: 45,
        n_pool: 55,
        n_pending: 0,
        latest_accuracy: 0.93,
      },
    ];
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessions,
    });

    const result = await listSessions();

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions");
    expect(result).toEqual(mockSessions);
  });

  it("throws with the response detail when the request fails", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "something broke" }),
    });

    await expect(listSessions()).rejects.toThrow("something broke");
  });
});

describe("createSession", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts multipart form data to /sessions", async () => {
    const mockResponse = {
      name: "azm-project",
      n_known: 20,
      n_pool: 0,
      label_col: "outcome",
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const labeledFile = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
    const result = await createSession({
      name: "azm-project",
      labelCol: "outcome",
      labeledFile,
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("http://localhost:8000/sessions");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect(result).toEqual(mockResponse);
  });

  it("throws with the response detail on a 409 (duplicate name)", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Session already exists at ..." }),
    });

    const labeledFile = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
    await expect(
      createSession({ name: "azm-project", labelCol: "outcome", labeledFile })
    ).rejects.toThrow("Session already exists at ...");
  });
});

describe("getStatus", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions/{name}/status", async () => {
    const mockStatus = {
      name: "azm-project",
      current_round: 2,
      n_known: 45,
      n_pool: 55,
      n_pending: 0,
      latest_accuracy: 0.93,
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      total_cost: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
      should_stop: false,
      stop_reason: "",
      created_at: "2026-07-19T00:00:00Z",
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    });

    const result = await getStatus("azm-project");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/status");
    expect(result).toEqual(mockStatus);
  });

  it("throws with the response detail on a 404", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "No session named 'nope'." }),
    });

    await expect(getStatus("nope")).rejects.toThrow("No session named 'nope'.");
  });
});

describe("getHistory", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions/{name}/history", async () => {
    const mockHistory = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHistory,
    });

    const result = await getHistory("azm-project");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/history");
    expect(result).toEqual(mockHistory);
  });
});

describe("getRecommendations", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions/{name}/recommend with no batch_size by default", async () => {
    const mockResponse = { rows: [], should_stop: false, stop_reason: "" };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    await getRecommendations("azm-project");

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/sessions/azm-project/recommend");
  });

  it("includes batch_size in the query string when provided", async () => {
    const mockResponse = { rows: [], should_stop: false, stop_reason: "" };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    await getRecommendations("azm-project", 5);

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/sessions/azm-project/recommend?batch_size=5");
  });
});

describe("submitResults", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts JSON results to /sessions/{name}/update", async () => {
    const mockResponse = {
      round: 1,
      n_returned: 2,
      n_known: 22,
      n_pool: 18,
      accuracy: 0.9,
      round_cost: null,
      cumulative_cost: null,
      should_stop: false,
      stop_reason: "",
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const results = [
      { sample_id: "pool_1", label: 1 },
      { sample_id: "pool_2", label: 0 },
    ];
    const result = await submitResults("azm-project", results);

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results }),
    });
    expect(result).toEqual(mockResponse);
  });

  it("throws with the response detail on a 400 (no matching results)", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "No pending samples matched in the results file." }),
    });

    await expect(submitResults("azm-project", [])).rejects.toThrow(
      "No pending samples matched"
    );
  });
});

describe("exportHistory", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the CSV and returns it as a Blob", async () => {
    const mockBlob = new Blob(["round_number,accuracy\n1,0.9\n"], { type: "text/csv" });
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      blob: async () => mockBlob,
    });

    const result = await exportHistory("azm-project");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/export");
    expect(result).toBe(mockBlob);
  });
});
