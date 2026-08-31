import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProSettingsPage from "./ProSettingsPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/settings`]}>
      <Routes>
        <Route path="/pro/sessions/:name/settings" element={<ProSettingsPage />} />
        <Route path="/pro" element={<div>Session list placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleStatus = {
  name: "azm-project", current_round: 2, n_known: 45, n_pool: 55, n_pending: 0,
  latest_accuracy: 0.93, patience: 3, min_delta: 0.005, cost_per_sample: 1.5,
  total_cost: 15, diversity_weight: 0, model: "rf", calibrate: false,
  calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
};

describe("ProSettingsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("pre-fills the form with the session's current settings", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByLabelText(/patience/i)).toHaveValue(3);
    });
    expect(screen.getByLabelText(/min delta/i)).toHaveValue(0.005);
    expect(screen.getByLabelText(/cost per sample/i)).toHaveValue(1.5);
  });

  it("saves changed settings and shows a confirmation", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const updateSpy = vi.spyOn(client, "updateSettings").mockResolvedValue({ ...sampleStatus, patience: 7 });
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByLabelText(/patience/i)).toHaveValue(3);
    });
    fireEvent.change(screen.getByLabelText(/patience/i), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalled();
    });
    expect(await screen.findByText(/settings saved/i)).toBeInTheDocument();
  });

  it("asks for confirmation before resetting, and does not reset if cancelled", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const resetSpy = vi.spyOn(client, "resetSession");
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reset session/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /reset session/i }));

    expect(window.confirm).toHaveBeenCalled();
    expect(resetSpy).not.toHaveBeenCalled();
  });

  it("resets when confirmed", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const resetSpy = vi.spyOn(client, "resetSession").mockResolvedValue({ n_known: 45, n_pool: 55, rounds_cleared: 2 });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reset session/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /reset session/i }));

    await waitFor(() => {
      expect(resetSpy).toHaveBeenCalledWith("azm-project");
    });
  });

  it("asks for confirmation before deleting, and navigates away when confirmed", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const deleteSpy = vi.spyOn(client, "deleteSession").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /delete session/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /delete session/i }));

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("azm-project");
    });
    expect(await screen.findByText("Session list placeholder")).toBeInTheDocument();
  });
});
