import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProAccuracyChart from "./ProAccuracyChart";
import type { HistoryRow } from "../../api/client";

const sampleHistory: HistoryRow[] = [
  {
    round_number: 1,
    n_known: 25,
    accuracy: 0.85,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-19T00:00:00Z",
  },
  {
    round_number: 2,
    n_known: 30,
    accuracy: 0.9,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-20T00:00:00Z",
  },
];

describe("ProAccuracyChart", () => {
  it("renders without crashing given real history data", () => {
    const { container } = render(<ProAccuracyChart history={sampleHistory} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });

  it("renders without crashing given empty history", () => {
    const { container } = render(<ProAccuracyChart history={[]} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });
});
