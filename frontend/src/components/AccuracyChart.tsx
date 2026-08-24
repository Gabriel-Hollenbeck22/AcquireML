import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryRow } from "../api/client";
import { historyHasCost, historyToChartData } from "./chartData";
import styles from "./AccuracyChart.module.css";

interface AccuracyChartProps {
  history: HistoryRow[];
}

function PulsingDot(props: { cx?: number; cy?: number; index?: number; totalPoints: number }) {
  const { cx, cy, index, totalPoints } = props;
  if (cx === undefined || cy === undefined || index === undefined) return null;
  const isLast = index === totalPoints - 1;
  return (
    <g>
      {isLast && (
        <circle
          className={styles.pulseRing}
          cx={cx}
          cy={cy}
          r={5}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={1.5}
        />
      )}
      <circle
        cx={cx}
        cy={cy}
        r={isLast ? 4.5 : 3.5}
        fill={isLast ? "var(--accent)" : "var(--paper-raised)"}
        stroke="var(--accent)"
        strokeWidth={2}
      />
    </g>
  );
}

export default function AccuracyChart({ history }: AccuracyChartProps) {
  const data = historyToChartData(history);
  const hasCost = historyHasCost(history);

  return (
    <div className={styles.card}>
      <span className="bracket bracket-tl" />
      <span className="bracket bracket-tr" />
      <span className="bracket bracket-bl" />
      <span className="bracket bracket-br" />
      <div className={styles.head}>
        <h4>Accuracy over rounds</h4>
        <span className={styles.legend}>● accuracy</span>
      </div>
      <div className={styles.chartWrap}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 8 }}>
            <defs>
              <filter id="chartGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
            <XAxis
              dataKey="round"
              stroke="var(--ink-faint)"
              tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
              label={{ value: "Round", position: "insideBottom", offset: -4, fill: "var(--ink-faint)" }}
            />
            <YAxis
              yAxisId="accuracy"
              domain={[0, 100]}
              stroke="var(--ink-faint)"
              tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
              label={{ value: "Accuracy %", angle: -90, position: "insideLeft", fill: "var(--ink-faint)" }}
            />
            {hasCost && (
              <YAxis
                yAxisId="cost"
                orientation="right"
                stroke="var(--accent-cool)"
                tick={{ fill: "var(--accent-cool)", fontSize: 12 }}
                label={{ value: "Cumulative cost", angle: 90, position: "insideRight", fill: "var(--accent-cool)" }}
              />
            )}
            <Tooltip
              contentStyle={{
                background: "var(--paper)",
                border: "1px solid var(--accent)",
                borderRadius: 6,
              }}
              labelStyle={{ color: "var(--ink)" }}
            />
            <Line
              yAxisId="accuracy"
              type="monotone"
              dataKey="accuracy"
              stroke="var(--accent)"
              strokeWidth={2.5}
              dot={<PulsingDot totalPoints={data.length} />}
              name="Accuracy %"
            />
            {hasCost && (
              <Line
                yAxisId="cost"
                type="monotone"
                dataKey="cost"
                stroke="var(--accent-cool)"
                strokeWidth={2}
                dot={{ fill: "var(--accent-cool)" }}
                name="Cumulative cost"
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
