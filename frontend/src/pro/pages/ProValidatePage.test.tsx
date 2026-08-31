import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProValidatePage from "./ProValidatePage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/validate`]}>
      <Routes>
        <Route path="/pro/sessions/:name/validate" element={<ProValidatePage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleResult = {
  n_train: 32, n_holdout: 8, n_holdout_resistant: 3, n_holdout_sensitive: 5,
  balanced_accuracy: 0.9, precision: 0.85, recall: 0.95, f1: 0.88,
  roc_auc: 0.97, tn: 5, fp: 0, fn: 0, tp: 3,
};

describe("ProValidatePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the five headline metrics once loaded", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue(sampleResult);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("90.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("85.0%")).toBeInTheDocument();
    expect(screen.getByText("95.0%")).toBeInTheDocument();
    expect(screen.getByText("0.970")).toBeInTheDocument();
  });

  it("shows an em dash for roc-auc when it's null", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue({ ...sampleResult, roc_auc: null });

    renderAtSession("azm-project");

    expect(await screen.findByText("—")).toBeInTheDocument();
  });

  it("shows all four confusion matrix cells", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue(sampleResult);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText(/correctly caught resistant/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/correctly cleared sensitive/i)).toBeInTheDocument();
    expect(screen.getByText(/false alarms/i)).toBeInTheDocument();
    expect(screen.getByText(/missed resistant/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getValidation").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
