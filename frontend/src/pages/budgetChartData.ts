import type { CostPoint } from "./costProjection";

export interface BudgetChartPoint {
  cost: number;
  actual: number | null;
  projected: number | null;
}

/**
 * Shapes cost/accuracy history plus an optional projected target point into
 * Recharts-friendly data. The last real point also carries a `projected`
 * value equal to its own `actual` value, so the dashed projection line
 * visually connects to the solid actual line instead of leaving a gap.
 */
export function toBudgetChartData(
  points: CostPoint[],
  projectedTargetCost: number | null,
  targetAccuracy: number
): BudgetChartPoint[] {
  const data: BudgetChartPoint[] = points.map((p, i) => ({
    cost: p.cost,
    actual: p.accuracy,
    projected:
      i === points.length - 1 && projectedTargetCost !== null ? p.accuracy : null,
  }));

  if (projectedTargetCost !== null) {
    data.push({ cost: projectedTargetCost, actual: null, projected: targetAccuracy });
  }

  return data;
}
