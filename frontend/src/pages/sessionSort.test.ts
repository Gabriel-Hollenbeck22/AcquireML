import { describe, expect, it } from "vitest";
import { sortSessions } from "./sessionSort";
import type { SessionSummary } from "../api/client";

const sessions: SessionSummary[] = [
  { name: "beta", current_round: 3, n_known: 20, n_pool: 5, n_pending: 0, latest_accuracy: 0.8 },
  { name: "alpha", current_round: 1, n_known: 50, n_pool: 5, n_pending: 0, latest_accuracy: null },
  { name: "gamma", current_round: 5, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.95 },
];

describe("sortSessions", () => {
  it("sorts by name alphabetically", () => {
    expect(sortSessions(sessions, "name").map((s) => s.name)).toEqual(["alpha", "beta", "gamma"]);
  });

  it("sorts by round descending", () => {
    expect(sortSessions(sessions, "round").map((s) => s.name)).toEqual(["gamma", "beta", "alpha"]);
  });

  it("sorts by known count descending", () => {
    expect(sortSessions(sessions, "known").map((s) => s.name)).toEqual(["alpha", "beta", "gamma"]);
  });

  it("sorts by accuracy descending, with null accuracy sorted last regardless of direction", () => {
    expect(sortSessions(sessions, "accuracy").map((s) => s.name)).toEqual(["gamma", "beta", "alpha"]);
  });

  it("does not mutate the input array", () => {
    const original = [...sessions];
    sortSessions(sessions, "name");
    expect(sessions).toEqual(original);
  });
});
