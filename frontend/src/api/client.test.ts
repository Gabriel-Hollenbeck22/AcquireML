import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createSession, listSessions } from "./client";

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
