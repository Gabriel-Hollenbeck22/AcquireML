import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import HistoryPage from "./HistoryPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/history`]}>
      <Routes>
        <Route path="/sessions/:name/history" element={<HistoryPage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleHistory = [
  {
    round_number: 1,
    n_known: 25,
    accuracy: 0.85,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-19T00:00:00Z",
  },
  {
    round_number: 2,
    n_known: 30,
    accuracy: 0.9,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-20T00:00:00Z",
  },
];

describe("HistoryPage", () => {
  beforeEach(() => {
    // jsdom has no real implementation of createObjectURL/revokeObjectURL —
    // stub them so the export button's click handler doesn't throw.
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the round table once loaded", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue(sampleHistory);

    renderAtSession("azm-project");

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("90.0%")).toBeInTheDocument();
  });

  it("shows an empty-state message instead of the table when there's no history", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("new-project");

    expect(await screen.findByText(/no rounds completed yet/i)).toBeInTheDocument();
  });

  it("triggers a CSV download when Export is clicked", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue(sampleHistory);
    const mockBlob = new Blob(["round_number,accuracy\n1,0.85\n"], { type: "text/csv" });
    vi.spyOn(client, "exportHistory").mockResolvedValue(mockBlob);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    await waitFor(() => {
      expect(client.exportHistory).toHaveBeenCalledWith("azm-project");
    });
    expect(URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
  });

  it("shows an error message when the export fails", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue(sampleHistory);
    vi.spyOn(client, "exportHistory").mockRejectedValue(new Error("export failed"));

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(await screen.findByText(/export failed/i)).toBeInTheDocument();
  });
});
