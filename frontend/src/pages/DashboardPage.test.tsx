import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import DashboardPage from "./DashboardPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}`]}>
      <Routes>
        <Route path="/sessions/:name" element={<DashboardPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("DashboardPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows status stats and the chart once loaded", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
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
    });
    vi.spyOn(client, "getHistory").mockResolvedValue([
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.85,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ]);

    renderAtSession("azm-project");

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("93.0%")).toBeInTheDocument();
  });

  it("shows a stopping-recommended banner when should_stop is true", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project",
      current_round: 5,
      n_known: 60,
      n_pool: 10,
      n_pending: 0,
      latest_accuracy: 0.95,
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      total_cost: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
      should_stop: true,
      stop_reason: "Accuracy has not improved by >=0.005 for 3 rounds.",
      created_at: "2026-07-19T00:00:00Z",
    });
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("azm-project");

    expect(
      await screen.findByText(/accuracy has not improved/i)
    ).toBeInTheDocument();
  });

  it("shows an empty-history message instead of the chart when no rounds exist", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "new-project",
      current_round: 0,
      n_known: 20,
      n_pool: 30,
      n_pending: 0,
      latest_accuracy: null,
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
    });
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("new-project");

    expect(await screen.findByText(/no rounds completed yet/i)).toBeInTheDocument();
  });

  it("shows an error message when either request fails", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("No session named 'x'."));
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
