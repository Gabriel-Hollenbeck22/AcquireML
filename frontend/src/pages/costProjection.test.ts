import { describe, expect, it } from "vitest";
import { fitLinearTrend, projectCostForTarget } from "./costProjection";

describe("fitLinearTrend", () => {
  it("returns null with fewer than 2 points", () => {
    expect(fitLinearTrend([])).toBeNull();
    expect(fitLinearTrend([{ cost: 10, accuracy: 0.8 }])).toBeNull();
  });

  it("fits an exact line through collinear points", () => {
    // accuracy = 0.5 + 0.01 * cost
    const points = [
      { cost: 0, accuracy: 0.5 },
      { cost: 10, accuracy: 0.6 },
      { cost: 20, accuracy: 0.7 },
    ];
    const trend = fitLinearTrend(points);
    expect(trend).not.toBeNull();
    expect(trend!.slope).toBeCloseTo(0.01, 5);
    expect(trend!.intercept).toBeCloseTo(0.5, 5);
  });
});

describe("projectCostForTarget", () => {
  it("projects additional cost needed to reach a target accuracy", () => {
    // accuracy = 0.5 + 0.01 * cost → to reach 0.9, need cost = 40
    const trend = { slope: 0.01, intercept: 0.5 };
    const result = projectCostForTarget(trend, 20, 0.9);
    expect(result).toBeCloseTo(20, 5); // 40 total - 20 already spent = 20 more
  });

  it("returns null when the trend is flat or declining", () => {
    expect(projectCostForTarget({ slope: 0, intercept: 0.8 }, 10, 0.9)).toBeNull();
    expect(projectCostForTarget({ slope: -0.01, intercept: 0.9 }, 10, 0.95)).toBeNull();
  });

  it("returns 0 (or negative-clamped-to-0) when the target is already met", () => {
    const trend = { slope: 0.01, intercept: 0.5 };
    // at cost=20, projected accuracy = 0.7, target 0.6 is already exceeded
    const result = projectCostForTarget(trend, 20, 0.6);
    expect(result).toBe(0);
  });
});
