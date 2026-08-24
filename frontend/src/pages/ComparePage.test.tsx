import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import ComparePage from "./ComparePage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/compare`]}>
      <Routes>
        <Route path="/sessions/:name/compare" element={<ComparePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ComparePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch on mount", () => {
    const spy = vi.spyOn(client, "getComparison");

    renderAtSession("azm-project");

    expect(spy).not.toHaveBeenCalled();
  });

  it("fetches exactly once when the run button is clicked", async () => {
    const spy = vi.spyOn(client, "getComparison").mockResolvedValue({
      known_pool_sizes: [5, 7, 9],
      al_accuracy: [0.6, 0.75, 0.85],
      random_accuracy: [0.55, 0.6, 0.65],
      runs: 3,
      final_gap: 0.2,
    });

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledTimes(1);
    });
    expect(spy).toHaveBeenCalledWith("azm-project");
  });

  it("shows the final gap in plain language once loaded", async () => {
    vi.spyOn(client, "getComparison").mockResolvedValue({
      known_pool_sizes: [5, 7, 9],
      al_accuracy: [0.6, 0.75, 0.85],
      random_accuracy: [0.55, 0.6, 0.65],
      runs: 3,
      final_gap: 0.2,
    });

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    expect(await screen.findByText(/20\.0 percentage points/i)).toBeInTheDocument();
    expect(screen.getByText(/higher/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getComparison").mockRejectedValue(
      new Error("Need at least 20 known samples to compare strategies (have 10).")
    );

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    expect(await screen.findByText(/at least 20 known samples/i)).toBeInTheDocument();
  });
});
