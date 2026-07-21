import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import NewSessionPage from "./NewSessionPage";

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/session name/i), {
    target: { value: "azm-project" },
  });
  fireEvent.change(screen.getByLabelText(/label column/i), {
    target: { value: "outcome" },
  });
  const file = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
  fireEvent.change(screen.getByLabelText(/labeled data file/i), {
    target: { files: [file] },
  });
}

describe("NewSessionPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits the form and calls createSession with the entered values", async () => {
    const createSpy = vi.spyOn(client, "createSession").mockResolvedValue({
      name: "azm-project",
      n_known: 20,
      n_pool: 0,
      label_col: "outcome",
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
    });

    render(
      <MemoryRouter>
        <NewSessionPage />
      </MemoryRouter>
    );

    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /create session/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledTimes(1);
    });
    const [input] = createSpy.mock.calls[0];
    expect(input.name).toBe("azm-project");
    expect(input.labelCol).toBe("outcome");
    expect(input.labeledFile.name).toBe("labeled.csv");
  });

  it("shows a validation message and does not submit when the name is blank", async () => {
    const createSpy = vi.spyOn(client, "createSession");

    render(
      <MemoryRouter>
        <NewSessionPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/label column/i), {
      target: { value: "outcome" },
    });
    const file = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText(/labeled data file/i), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: /create session/i }));

    expect(await screen.findByText(/session name is required/i)).toBeInTheDocument();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("shows the backend's error message on failure (e.g. duplicate name)", async () => {
    vi.spyOn(client, "createSession").mockRejectedValue(
      new Error("Session already exists at /path/to/azm-project.db.")
    );

    render(
      <MemoryRouter>
        <NewSessionPage />
      </MemoryRouter>
    );

    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /create session/i }));

    expect(
      await screen.findByText(/session already exists/i)
    ).toBeInTheDocument();
  });
});
