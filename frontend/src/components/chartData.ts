import type { HistoryRow } from "../api/client";

export interface ChartPoint {
  round: number;
  accuracy: number | null;
  cost: number | null;
}

export function historyToChartData(history: HistoryRow[]): ChartPoint[] {
  return history.map((row) => ({
    round: row.round_number,
    accuracy: row.accuracy !== null ? row.accuracy * 100 : null,
    cost: row.cumulative_cost,
  }));
}

export function historyHasCost(history: HistoryRow[]): boolean {
  return history.some((row) => row.cumulative_cost !== null);
}
