import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "./api/client";
import App from "./App";

describe("App", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the session list at the root route", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });
  });

  it("renders the Pro session list at the /pro route", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    window.history.pushState({}, "", "/pro");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });
  });
});
