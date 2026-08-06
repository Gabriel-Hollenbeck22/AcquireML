import { describe, expect, it, vi } from "vitest";
import { filterCommands, type Command } from "./commandFilter";

function makeCommands(labels: string[]): Command[] {
  return labels.map((label, i) => ({ id: String(i), label, action: vi.fn() }));
}

describe("filterCommands", () => {
  it("returns all commands when the query is empty", () => {
    const commands = makeCommands(["Dashboard", "History", "Settings"]);
    expect(filterCommands(commands, "")).toHaveLength(3);
  });

  it("filters case-insensitively by substring", () => {
    const commands = makeCommands(["Dashboard", "History", "Settings"]);
    expect(filterCommands(commands, "hist").map((c) => c.label)).toEqual(["History"]);
    expect(filterCommands(commands, "DASH").map((c) => c.label)).toEqual(["Dashboard"]);
  });

  it("excludes commands with no match", () => {
    const commands = makeCommands(["Dashboard", "History"]);
    expect(filterCommands(commands, "budget")).toHaveLength(0);
  });

  it("sorts earlier substring matches before later ones", () => {
    const commands = makeCommands(["My Dashboard", "Dashboard Overview"]);
    // "Dashboard" appears at index 3 in "My Dashboard" but index 0 in "Dashboard Overview"
    expect(filterCommands(commands, "dashboard").map((c) => c.label)).toEqual([
      "Dashboard Overview",
      "My Dashboard",
    ]);
  });
});
