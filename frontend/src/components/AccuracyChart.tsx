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

interface AccuracyChartProps {
  history: HistoryRow[];
}

export default function AccuracyChart({ history }: AccuracyChartProps) {
  const data = historyToChartData(history);
  const hasCost = historyHasCost(history);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
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
            stroke="var(--brass)"
            tick={{ fill: "var(--brass)", fontSize: 12 }}
            label={{ value: "Cumulative cost", angle: 90, position: "insideRight", fill: "var(--brass)" }}
          />
        )}
        <Tooltip
          contentStyle={{
            background: "var(--paper-raised)",
            border: "1px solid var(--line)",
            borderRadius: 4,
          }}
          labelStyle={{ color: "var(--ink)" }}
        />
        <Line
          yAxisId="accuracy"
          type="monotone"
          dataKey="accuracy"
          stroke="var(--accent-deep)"
          strokeWidth={2}
          dot={{ fill: "var(--accent-deep)" }}
          name="Accuracy %"
        />
        {hasCost && (
          <Line
            yAxisId="cost"
            type="monotone"
            dataKey="cost"
            stroke="var(--brass)"
            strokeWidth={2}
            dot={{ fill: "var(--brass)" }}
            name="Cumulative cost"
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
