import type { SessionSummary } from "../api/client";

export type SortKey = "name" | "round" | "accuracy" | "known";

export function sortSessions(sessions: SessionSummary[], by: SortKey): SessionSummary[] {
  const copy = [...sessions];
  switch (by) {
    case "name":
      return copy.sort((a, b) => a.name.localeCompare(b.name));
    case "round":
      return copy.sort((a, b) => b.current_round - a.current_round);
    case "known":
      return copy.sort((a, b) => b.n_known - a.n_known);
    case "accuracy":
      return copy.sort((a, b) => {
        if (a.latest_accuracy === null && b.latest_accuracy === null) return 0;
        if (a.latest_accuracy === null) return 1;
        if (b.latest_accuracy === null) return -1;
        return b.latest_accuracy - a.latest_accuracy;
      });
  }
}
