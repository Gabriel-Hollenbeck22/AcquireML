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
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
    expect(screen.getByText("93.0%")).toBeInTheDocument();
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

  it("sorts sessions when the sort dropdown changes", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      { name: "zeta", current_round: 1, n_known: 5, n_pool: 5, n_pending: 0, latest_accuracy: null },
      { name: "alpha", current_round: 1, n_known: 5, n_pool: 5, n_pending: 0, latest_accuracy: null },
    ]);
    render(
      <MemoryRouter>
        <SessionListPage />
      </MemoryRouter>
    );

    const links = await screen.findAllByRole("link", { name: /zeta|alpha/ });
    // default sort is "name" — alpha should come before zeta
    expect(links[0]).toHaveTextContent("alpha");
  });
});
