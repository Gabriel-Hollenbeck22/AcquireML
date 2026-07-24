import { describe, expect, it } from "vitest";
import { historyHasCost, historyToChartData } from "./chartData";
import type { HistoryRow } from "../api/client";

describe("historyToChartData", () => {
  it("maps round_number to round and scales accuracy to a percentage", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];

    expect(historyToChartData(history)).toEqual([
      { round: 1, accuracy: 90, cost: null },
    ]);
  });

  it("passes through a null accuracy as null rather than scaling it", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 10,
        accuracy: null,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];

    expect(historyToChartData(history)[0].accuracy).toBeNull();
  });

  it("carries cumulative_cost through as cost", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: 150,
        cumulative_cost: 150,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];

    expect(historyToChartData(history)[0].cost).toBe(150);
  });

  it("returns an empty array for empty history", () => {
    expect(historyToChartData([])).toEqual([]);
  });
});

describe("historyHasCost", () => {
  it("returns false when no round has a cumulative_cost", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];
    expect(historyHasCost(history)).toBe(false);
  });

  it("returns true when at least one round has a cumulative_cost", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
      {
        round_number: 2,
        n_known: 30,
        accuracy: 0.92,
        round_cost: 150,
        cumulative_cost: 300,
        created_at: "2026-07-20T00:00:00Z",
      },
    ];
    expect(historyHasCost(history)).toBe(true);
  });

  it("returns false for empty history", () => {
    expect(historyHasCost([])).toBe(false);
  });
});
