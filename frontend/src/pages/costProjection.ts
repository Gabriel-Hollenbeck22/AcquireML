export interface CostPoint {
  cost: number;
  accuracy: number;
}

export interface LinearTrend {
  slope: number;
  intercept: number;
}

/** Ordinary least-squares fit of accuracy as a function of cumulative cost. */
export function fitLinearTrend(points: CostPoint[]): LinearTrend | null {
  const n = points.length;
  if (n < 2) return null;

  const sumX = points.reduce((acc, p) => acc + p.cost, 0);
  const sumY = points.reduce((acc, p) => acc + p.accuracy, 0);
  const meanX = sumX / n;
  const meanY = sumY / n;

  let numerator = 0;
  let denominator = 0;
  for (const p of points) {
    numerator += (p.cost - meanX) * (p.accuracy - meanY);
    denominator += (p.cost - meanX) ** 2;
  }
  if (denominator === 0) return null; // all points at the same cost — no meaningful slope

  const slope = numerator / denominator;
  const intercept = meanY - slope * meanX;
  return { slope, intercept };
}

/**
 * Additional cost (beyond currentCost) needed to reach targetAccuracy,
 * based on a fitted linear trend. Returns null if the trend can't reach
 * the target (flat or declining slope) — never returns a negative
 * "additional cost beyond what's already met" value below 0.
 */
export function projectCostForTarget(
  trend: LinearTrend,
  currentCost: number,
  targetAccuracy: number
): number | null {
  if (trend.slope <= 0) return null;
  const totalCostForTarget = (targetAccuracy - trend.intercept) / trend.slope;
  const additional = totalCostForTarget - currentCost;
  return Math.max(0, additional);
}
