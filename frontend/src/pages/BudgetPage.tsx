import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getHistory, getStatus, type HistoryRow, type StatusResponse } from "../api/client";
import { fitLinearTrend, projectCostForTarget, type CostPoint } from "./costProjection";
import { toBudgetChartData } from "./budgetChartData";
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
  const [targetPercent, setTargetPercent] = useState("95");

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
  const parsedTarget = Number(targetPercent) / 100;
  const projected =
    trend !== null && !Number.isNaN(parsedTarget)
      ? projectCostForTarget(trend, currentCost, parsedTarget)
      : null;
  const projectedTargetCost = projected !== null ? currentCost + projected : null;
  const chartData = toBudgetChartData(points, projectedTargetCost, parsedTarget);

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
          <div className={styles.chartCard}>
            <span className="bracket bracket-tl" />
            <span className="bracket bracket-tr" />
            <span className="bracket bracket-bl" />
            <span className="bracket bracket-br" />
            <div className={styles.chartHead}>
              <h4>Accuracy vs. cumulative cost</h4>
              <div className={styles.chartLegend}>
                <span className={styles.legendActual}>● actual</span>
                <span className={styles.legendProjected}>┄ projected</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="cost"
                  type="number"
                  domain={[0, "dataMax"]}
                  stroke="var(--ink-faint)"
                  tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
                  tickFormatter={(v: number) => `$${Math.round(v)}`}
                  label={{
                    value: "Cumulative cost",
                    position: "insideBottom",
                    offset: -6,
                    fill: "var(--ink-faint)",
                  }}
                />
                <YAxis
                  domain={[0, 1]}
                  stroke="var(--ink-faint)"
                  tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                  label={{
                    value: "Accuracy",
                    angle: -90,
                    position: "insideLeft",
                    fill: "var(--ink-faint)",
                  }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--paper)",
                    border: "1px solid var(--accent)",
                    borderRadius: 6,
                  }}
                  labelStyle={{ color: "var(--ink)" }}
                  labelFormatter={(v: number) => `$${v.toFixed(2)}`}
                  formatter={(value: number, dataKey: string) => [
                    `${(value * 100).toFixed(1)}%`,
                    dataKey === "actual" ? "Accuracy" : "Projected",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="var(--accent)"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "var(--accent)" }}
                  activeDot={{ r: 5 }}
                  name="actual"
                />
                <Line
                  type="monotone"
                  dataKey="projected"
                  stroke="var(--brass)"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={{ r: 4, fill: "var(--brass)" }}
                  activeDot={{ r: 5 }}
                  connectNulls
                  name="projected"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.projectionPanel}>
            <div className={styles.targetField}>
              <label htmlFor="targetAccuracy">Target accuracy</label>
              <div className={styles.targetInputWrap}>
                <input
                  id="targetAccuracy"
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  value={targetPercent}
                  onChange={(e) => setTargetPercent(e.target.value)}
                />
                <span className={styles.targetSuffix}>%</span>
              </div>
            </div>

            <div className={styles.projectionResult}>
              {trend !== null && trend.slope <= 0 ? (
                <p className={styles.empty}>
                  Accuracy isn't trending upward with cost yet — projection isn't
                  meaningful until it is.
                </p>
              ) : projected !== null ? (
                <>
                  <div className={styles.projectionValue}>${projected.toFixed(2)}</div>
                  <div className={styles.projectionLabel}>
                    Projected additional spend to reach {targetPercent}%
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
