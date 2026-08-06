import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import BudgetPage from "./BudgetPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/budget`]}>
      <Routes>
        <Route path="/sessions/:name/budget" element={<BudgetPage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleStatus = {
  name: "azm-project", current_round: 3, n_known: 45, n_pool: 55, n_pending: 0,
  latest_accuracy: 0.85, patience: 3, min_delta: 0.005, cost_per_sample: 1,
  total_cost: 30, diversity_weight: 0, model: "rf", calibrate: false,
  calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
};

describe("BudgetPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an insufficient-data message with fewer than 2 costed rounds", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    vi.spyOn(client, "getHistory").mockResolvedValue([
      { round_number: 1, n_known: 25, accuracy: 0.7, round_cost: 10, cumulative_cost: 10, created_at: "2026-01-01" },
    ]);

    renderAtSession("azm-project");

    expect(await screen.findByText(/not enough completed rounds/i)).toBeInTheDocument();
  });

  it("shows a projection with 2+ costed rounds and an upward trend", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    vi.spyOn(client, "getHistory").mockResolvedValue([
      { round_number: 1, n_known: 25, accuracy: 0.7, round_cost: 10, cumulative_cost: 10, created_at: "2026-01-01" },
      { round_number: 2, n_known: 35, accuracy: 0.8, round_cost: 10, cumulative_cost: 20, created_at: "2026-01-02" },
      { round_number: 3, n_known: 45, accuracy: 0.85, round_cost: 10, cumulative_cost: 30, created_at: "2026-01-03" },
    ]);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText(/spent so far/i)).toBeInTheDocument();
    });
    expect(await screen.findByText(/projected additional spend/i)).toBeInTheDocument();
  });

  it("shows an error message when a request fails", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("No session named 'x'."));
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
