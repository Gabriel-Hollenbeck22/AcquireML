import { describe, expect, it } from "vitest";
import { toBudgetChartData } from "./budgetChartData";

describe("toBudgetChartData", () => {
  it("maps each history point to cost/actual, with projected null", () => {
    const points = [
      { cost: 100, accuracy: 0.72 },
      { cost: 200, accuracy: 0.81 },
    ];
    const data = toBudgetChartData(points, null, 0.95);
    expect(data).toEqual([
      { cost: 100, actual: 0.72, projected: null },
      { cost: 200, actual: 0.81, projected: null },
    ]);
  });

  it("connects the dashed projection to the last real point and appends the target", () => {
    const points = [
      { cost: 100, accuracy: 0.72 },
      { cost: 300, accuracy: 0.87 },
    ];
    const data = toBudgetChartData(points, 400, 0.95);
    expect(data).toEqual([
      { cost: 100, actual: 0.72, projected: null },
      { cost: 300, actual: 0.87, projected: 0.87 },
      { cost: 400, actual: null, projected: 0.95 },
    ]);
  });

  it("returns just the real points when there is no projection", () => {
    const points = [
      { cost: 50, accuracy: 0.6 },
      { cost: 150, accuracy: 0.6 },
    ];
    expect(toBudgetChartData(points, null, 0.95)).toHaveLength(2);
  });
});
