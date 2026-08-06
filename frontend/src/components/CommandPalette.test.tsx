import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import CommandPalette from "./CommandPalette";

describe("CommandPalette", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <MemoryRouter>
        <CommandPalette open={false} onClose={vi.fn()} />
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
        <CommandPalette open={true} onClose={vi.fn()} />
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
        <CommandPalette open={true} onClose={vi.fn()} />
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
        <CommandPalette open={true} onClose={onClose} />
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
        <CommandPalette open={true} onClose={onClose} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/jump to/i)).toBeInTheDocument();
    });
    fireEvent.click(container.firstChild as Element);

    expect(onClose).toHaveBeenCalled();
  });
});
