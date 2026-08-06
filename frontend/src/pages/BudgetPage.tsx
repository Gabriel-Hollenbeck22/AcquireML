import { useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { getHistory, getStatus, type HistoryRow, type StatusResponse } from "../api/client";
import { fitLinearTrend, projectCostForTarget, type CostPoint } from "./costProjection";
import styles from "./BudgetPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; history: HistoryRow[]; sessionStatus: StatusResponse };

function historyToCostPoints(history: HistoryRow[]): CostPoint[] {
  return history
    .filter((row): row is HistoryRow & { accuracy: number; cumulative_cost: number } =>
      row.accuracy !== null && row.cumulative_cost !== null
    )
    .map((row) => ({ cost: row.cumulative_cost, accuracy: row.accuracy }));
}

export default function BudgetPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [targetAccuracy, setTargetAccuracy] = useState("0.95");

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    Promise.all([getHistory(name), getStatus(name)])
      .then(([history, sessionStatus]) => {
        if (!cancelled) setState({ status: "loaded", history, sessionStatus });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const points = historyToCostPoints(state.history);
  const trend = fitLinearTrend(points);
  const currentCost = state.sessionStatus.total_cost ?? 0;
  const parsedTarget = Number(targetAccuracy);
  const projected =
    trend !== null && !Number.isNaN(parsedTarget)
      ? projectCostForTarget(trend, currentCost, parsedTarget)
      : null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    // state derives targetAccuracy reactively — nothing to do beyond
    // preventing the native form submit/page reload.
  }

  return (
    <div>
      <h2>Cost &amp; budget projection</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>${currentCost.toFixed(2)}</div>
          <div className={styles.statLabel}>Spent so far</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {state.sessionStatus.latest_accuracy !== null
              ? `${(state.sessionStatus.latest_accuracy * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div className={styles.statLabel}>Current accuracy</div>
        </div>
      </div>

      {points.length < 2 ? (
        <p className={styles.empty}>
          Not enough completed rounds yet to project a trend — at least 2 rounds with
          both accuracy and cost recorded are needed.
        </p>
      ) : (
        <>
          <svg viewBox="0 0 400 200" width="100%" height="200" className={styles.chart}>
            <BudgetChartBody points={points} trend={trend} currentCost={currentCost} projectedCost={projected} targetAccuracy={parsedTarget} />
          </svg>

          <form onSubmit={handleSubmit} className={styles.form}>
            <label htmlFor="targetAccuracy">Target accuracy</label>
            <input
              id="targetAccuracy"
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={targetAccuracy}
              onChange={(e) => setTargetAccuracy(e.target.value)}
            />
          </form>

          {trend !== null && trend.slope <= 0 && (
            <p className={styles.empty}>
              Accuracy isn't trending upward with cost yet — projection isn't meaningful
              until it is.
            </p>
          )}
          {projected !== null && (
            <p className={styles.projection}>
              Projected additional spend to reach {(parsedTarget * 100).toFixed(0)}%:{" "}
              <strong>${projected.toFixed(2)}</strong>
            </p>
          )}
        </>
      )}
    </div>
  );
}

function BudgetChartBody({
  points,
  trend,
  currentCost,
  projectedCost,
  targetAccuracy,
}: {
  points: CostPoint[];
  trend: ReturnType<typeof fitLinearTrend>;
  currentCost: number;
  projectedCost: number | null;
  targetAccuracy: number;
}) {
  const maxCost = Math.max(...points.map((p) => p.cost), currentCost + (projectedCost ?? 0));
  const xScale = (cost: number) => 20 + (cost / (maxCost || 1)) * 360;
  const yScale = (accuracy: number) => 180 - accuracy * 160;

  const realPath = points.map((p) => `${xScale(p.cost)},${yScale(p.accuracy)}`).join(" ");

  const projectedTargetCost =
    projectedCost !== null ? currentCost + projectedCost : null;

  return (
    <>
      <polyline points={realPath} fill="none" stroke="var(--accent)" strokeWidth={2} />
      {points.map((p, i) => (
        <circle key={i} cx={xScale(p.cost)} cy={yScale(p.accuracy)} r={3} fill="var(--accent)" />
      ))}
      {trend !== null && projectedTargetCost !== null && (
        <>
          <line
            x1={xScale(currentCost)}
            y1={yScale(trend.slope * currentCost + trend.intercept)}
            x2={xScale(projectedTargetCost)}
            y2={yScale(targetAccuracy)}
            stroke="var(--brass)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
          <circle cx={xScale(projectedTargetCost)} cy={yScale(targetAccuracy)} r={4} fill="var(--brass)" />
        </>
      )}
    </>
  );
}
