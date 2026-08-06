import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import SessionLayout from "./SessionLayout";
import styles from "./SessionLayout.module.css";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<div>dashboard content</div>} />
          <Route path="recommend" element={<div>recommend content</div>} />
          <Route path="history" element={<div>history content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("SessionLayout", () => {
  it("shows the session name as a mono SESSION:// label", () => {
    renderAt("/sessions/azm-project");
    expect(screen.getByText("SESSION://azm-project")).toBeInTheDocument();
  });

  it("marks only the Dashboard link active on the index route", () => {
    renderAt("/sessions/azm-project");
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "Recommendations" })).not.toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "History" })).not.toHaveClass(styles.active);
  });

  it("marks only the Recommendations link active on the recommend route", () => {
    renderAt("/sessions/azm-project/recommend");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "Recommendations" })).toHaveClass(styles.active);
  });
});

describe("SessionLayout settings/budget nav", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("always shows a Settings link", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });

    renderAt("/sessions/azm-project");

    expect(await screen.findByRole("link", { name: "Settings" })).toBeInTheDocument();
  });

  it("does not show a Budget link when cost_per_sample is null", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });

    renderAt("/sessions/azm-project");

    await screen.findByRole("link", { name: "Settings" }); // wait for the fetch to resolve
    expect(screen.queryByRole("link", { name: "Budget" })).not.toBeInTheDocument();
  });
});
