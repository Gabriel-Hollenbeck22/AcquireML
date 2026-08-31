import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProOverviewPage from "./ProOverviewPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/overview`]}>
      <Routes>
        <Route path="/pro/sessions/:name/overview" element={<ProOverviewPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProOverviewPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows class balance and feature counts once loaded", async () => {
    vi.spyOn(client, "getOverview").mockResolvedValue({
      n_known: 40, n_pool: 60, n_features: 30, n_positive: 11, n_negative: 29,
      positive_rate: 0.275, top_prevalent_features: [],
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("40")).toBeInTheDocument();
    });
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("27.5%")).toBeInTheDocument();
  });

  it("renders a bar per prevalent feature", async () => {
    vi.spyOn(client, "getOverview").mockResolvedValue({
      n_known: 40, n_pool: 60, n_features: 30, n_positive: 11, n_negative: 29,
      positive_rate: 0.275,
      top_prevalent_features: [
        { feature: "unitig_3", prevalence: 0.9 },
        { feature: "unitig_7", prevalence: 0.4 },
      ],
    });

    renderAtSession("azm-project");

    expect(await screen.findByText("unitig_3")).toBeInTheDocument();
    expect(screen.getByText("unitig_7")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getOverview").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
