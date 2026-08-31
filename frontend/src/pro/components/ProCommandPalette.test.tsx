import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProCommandPalette from "./ProCommandPalette";

describe("ProCommandPalette", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <MemoryRouter>
        <ProCommandPalette open={false} onClose={vi.fn()} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("lists sessions as commands when open", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      { name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.9 },
    ]);
    render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    expect(await screen.findByText(/go to session: azm-project/i)).toBeInTheDocument();
  });

  it("filters commands as the query changes", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      { name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.9 },
    ]);
    render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    await screen.findByText(/go to session: azm-project/i);
    fireEvent.change(screen.getByPlaceholderText(/jump to/i), { target: { value: "new session" } });

    expect(screen.getByText("New session")).toBeInTheDocument();
    expect(screen.queryByText(/go to session: azm-project/i)).not.toBeInTheDocument();
  });

  it("calls onClose when Escape is pressed", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={onClose} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/jump to/i)).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when clicking the backdrop", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    const onClose = vi.fn();
    const { container } = render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={onClose} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/jump to/i)).toBeInTheDocument();
    });
    fireEvent.click(container.firstChild as Element);

    expect(onClose).toHaveBeenCalled();
  });

  it("does not show a Budget command for a session without cost tracking", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });
    render(
      <MemoryRouter initialEntries={["/pro/sessions/azm-project"]}>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    expect(await screen.findByText("Dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Budget")).not.toBeInTheDocument();
  });

  it("shows a Budget command for a session with cost tracking", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: 12.5,
      total_cost: 125, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });
    render(
      <MemoryRouter initialEntries={["/pro/sessions/azm-project"]}>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    expect(await screen.findByText("Budget")).toBeInTheDocument();
  });
});
