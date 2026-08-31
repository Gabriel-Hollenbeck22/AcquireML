import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryRow } from "../../api/client";
import { historyHasCost, historyToChartData } from "../../components/chartData";
import styles from "./ProAccuracyChart.module.css";

interface ProAccuracyChartProps {
  history: HistoryRow[];
}

function ProDot(props: { cx?: number; cy?: number; index?: number; totalPoints: number }) {
  const { cx, cy, index, totalPoints } = props;
  if (cx === undefined || cy === undefined || index === undefined) return null;
  const isLast = index === totalPoints - 1;
  return (
    <g>
      {isLast && <circle cx={cx} cy={cy} r={9} fill="var(--pro-accent)" opacity={0.15} />}
      <circle
        cx={cx}
        cy={cy}
        r={isLast ? 4.5 : 3.5}
        fill={isLast ? "var(--pro-accent)" : "var(--pro-surface)"}
        stroke="var(--pro-accent)"
        strokeWidth={2}
      />
    </g>
  );
}

export default function ProAccuracyChart({ history }: ProAccuracyChartProps) {
  const data = historyToChartData(history);
  const hasCost = historyHasCost(history);

  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <h4>Accuracy over rounds</h4>
        <span className={styles.legend}>● accuracy</span>
      </div>
      <div className={styles.chartWrap}>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 8 }}>
            <defs>
              <linearGradient id="proAreaFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--pro-accent)" stopOpacity={0.16} />
                <stop offset="100%" stopColor="var(--pro-accent)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--pro-line-soft)" />
            <XAxis
              dataKey="round"
              stroke="var(--pro-ink-faint)"
              tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
              label={{ value: "Round", position: "insideBottom", offset: -4, fill: "var(--pro-ink-faint)" }}
            />
            <YAxis
              yAxisId="accuracy"
              domain={[0, 100]}
              stroke="var(--pro-ink-faint)"
              tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
              label={{ value: "Accuracy %", angle: -90, position: "insideLeft", fill: "var(--pro-ink-faint)" }}
            />
            {hasCost && (
              <YAxis
                yAxisId="cost"
                orientation="right"
                stroke="var(--pro-ink-soft)"
                tick={{ fill: "var(--pro-ink-soft)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
                label={{ value: "Cumulative cost", angle: 90, position: "insideRight", fill: "var(--pro-ink-soft)" }}
              />
            )}
            <Tooltip
              contentStyle={{
                background: "var(--pro-surface)",
                border: "1px solid var(--pro-line)",
                borderRadius: 6,
                boxShadow: "var(--pro-shadow-md)",
              }}
              labelStyle={{ color: "var(--pro-ink)" }}
            />
            <Area
              yAxisId="accuracy"
              type="monotone"
              dataKey="accuracy"
              stroke="var(--pro-accent)"
              strokeWidth={2.5}
              fill="url(#proAreaFill)"
              dot={<ProDot totalPoints={data.length} />}
              name="Accuracy %"
            />
            {hasCost && (
              <Line
                yAxisId="cost"
                type="monotone"
                dataKey="cost"
                stroke="var(--pro-ink-soft)"
                strokeWidth={2}
                strokeDasharray="4 3"
                dot={{ fill: "var(--pro-ink-soft)", r: 3 }}
                name="Cumulative cost"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
