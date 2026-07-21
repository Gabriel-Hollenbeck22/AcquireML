import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import SessionListPage from "./SessionListPage";

describe("SessionListPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state, then the list of sessions", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      {
        name: "azm-project",
        current_round: 2,
        n_known: 45,
        n_pool: 55,
        n_pending: 0,
        latest_accuracy: 0.93,
      },
    ]);

    render(
      <MemoryRouter>
        <SessionListPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("azm-project")).toBeInTheDocument();
    });
    expect(screen.getByText(/round 2/i)).toBeInTheDocument();
    expect(screen.getByText(/93/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no sessions", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <SessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
    });
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "listSessions").mockRejectedValue(new Error("network down"));

    render(
      <MemoryRouter>
        <SessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/network down/i)).toBeInTheDocument();
    });
  });

  it("links to the new-session page", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <SessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /new session/i })).toHaveAttribute(
        "href",
        "/new"
      );
    });
  });
});
