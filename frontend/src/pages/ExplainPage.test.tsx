import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import ExplainPage from "./ExplainPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/explain`]}>
      <Routes>
        <Route path="/sessions/:name/explain" element={<ExplainPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ExplainPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows cv accuracy and ranked features once loaded", async () => {
    vi.spyOn(client, "getFeatureImportance").mockResolvedValue({
      features: [
        { rank: 1, feature: "unitig_9", importance: 0.21, cumulative_importance: 0.21 },
      ],
      cv_accuracy_mean: 0.93, cv_accuracy_std: 0.02, total_features: 500, n_known: 40,
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("93.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("unitig_9")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
  });

  it("shows an em dash for cv accuracy when it's null", async () => {
    vi.spyOn(client, "getFeatureImportance").mockResolvedValue({
      features: [{ rank: 1, feature: "unitig_1", importance: 0.5, cumulative_importance: 0.5 }],
      cv_accuracy_mean: null, cv_accuracy_std: null, total_features: 6, n_known: 5,
    });

    renderAtSession("azm-project");

    expect(await screen.findByText("—")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getFeatureImportance").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
