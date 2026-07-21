import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as client from "./api/client";
import App from "./App";

describe("App", () => {
  it("renders the session list at the root route", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });
  });
});
