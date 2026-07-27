import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import RecommendationsPage from "./RecommendationsPage";

function renderAtSession(name: string, { strict = false } = {}) {
  const tree = (
    <MemoryRouter initialEntries={[`/sessions/${name}/recommend`]}>
      <Routes>
        <Route path="/sessions/:name/recommend" element={<RecommendationsPage />} />
        <Route path="/sessions/:name" element={<div>Dashboard placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
  return render(strict ? <StrictMode>{tree}</StrictMode> : tree);
}

const sampleRows = [
  {
    rank: 1,
    sample_id: "pool_3",
    uncertainty_score: 0.98,
    p_positive: 0.51,
    predicted_class: "positive",
  },
  {
    rank: 2,
    sample_id: "pool_7",
    uncertainty_score: 0.95,
    p_positive: 0.49,
    predicted_class: "negative",
  },
];

describe("RecommendationsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the recommended batch once loaded", async () => {
    vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });

    renderAtSession("azm-project");

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });
    expect(screen.getByText("pool_7")).toBeInTheDocument();
  });

  it("submits only the rows with a selected result, then navigates to the dashboard", async () => {
    vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });
    const submitSpy = vi.spyOn(client, "submitResults").mockResolvedValue({
      round: 1,
      n_returned: 1,
      n_known: 21,
      n_pool: 1,
      accuracy: 0.9,
      round_cost: null,
      cumulative_cost: null,
      should_stop: false,
      stop_reason: "",
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/result for pool_3/i), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit results/i }));

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith("azm-project", [
        { sample_id: "pool_3", label: 1 },
      ]);
    });
    await waitFor(() => {
      expect(screen.getByText("Dashboard placeholder")).toBeInTheDocument();
    });
  });

  it("shows a validation message and does not submit when nothing is selected", async () => {
    vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });
    const submitSpy = vi.spyOn(client, "submitResults");

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /submit results/i }));

    expect(
      await screen.findByText(/enter at least one result/i)
    ).toBeInTheDocument();
    expect(submitSpy).not.toHaveBeenCalled();
  });

  it("fetches recommendations exactly once under StrictMode's double-invoked effects", async () => {
    const getSpy = vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });

    renderAtSession("azm-project", { strict: true });

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
  });
});
