import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProSessionListPage from "./ProSessionListPage";

describe("ProSessionListPage", () => {
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
        <ProSessionListPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("azm-project")).toBeInTheDocument();
    });
    const card = screen.getByRole("link", { name: /azm-project/i });
    expect(card).toHaveTextContent("Round 2");
    expect(card).toHaveTextContent("45");
    expect(card).toHaveTextContent("55");
    expect(card).toHaveTextContent("93.0%");
  });

  it("shows an empty state when there are no sessions", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <ProSessionListPage />
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
        <ProSessionListPage />
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
        <ProSessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /new session/i })).toHaveAttribute(
        "href",
        "/pro/new"
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
        <ProSessionListPage />
      </MemoryRouter>
    );

    const links = await screen.findAllByRole("link", { name: /zeta|alpha/ });
    expect(links[0]).toHaveTextContent("alpha");
  });
});
