import { useState } from "react";
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
import { getComparison, type CompareResponse } from "../api/client";
import styles from "./ComparePage.module.css";

type RunState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: CompareResponse };

interface ComparePoint {
  size: number;
  al: number;
  random: number;
}

function toChartData(data: CompareResponse): ComparePoint[] {
  return data.known_pool_sizes.map((size, i) => ({
    size,
    al: data.al_accuracy[i] * 100,
    random: data.random_accuracy[i] * 100,
  }));
}

export default function ComparePage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<RunState>({ status: "idle" });

  async function handleRun() {
    if (!name) return;
    setState({ status: "loading" });
    try {
      const data = await getComparison(name);
      setState({ status: "loaded", data });
    } catch (err) {
      setState({ status: "error", message: (err as Error).message });
    }
  }

  return (
    <div>
      <h2>Active learning vs. random sampling</h2>
      <p className={styles.intro}>
        Simulates both strategies on this session's own known data to show how much
        faster active learning reaches a given accuracy compared to random sampling.
        This trains several models and can take a few seconds.
      </p>

      <button type="button" onClick={handleRun} disabled={state.status === "loading"} className={styles.runButton}>
        {state.status === "loading" ? "Running…" : "Run comparison"}
      </button>

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && (
        <>
          <div className={styles.chartCard}>
            <span className="bracket bracket-tl" />
            <span className="bracket bracket-tr" />
            <span className="bracket bracket-bl" />
            <span className="bracket bracket-br" />
            <div className={styles.chartHead}>
              <h4>Accuracy vs. known pool size</h4>
              <div className={styles.chartLegend}>
                <span className={styles.legendActual}>● active learning</span>
                <span className={styles.legendProjected}>┄ random</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={toChartData(state.data)} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="size"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  stroke="var(--ink-faint)"
                  tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
                  label={{
                    value: "Known pool size",
                    position: "insideBottom",
                    offset: -6,
                    fill: "var(--ink-faint)",
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="var(--ink-faint)"
                  tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
                  tickFormatter={(v: number) => `${Math.round(v)}%`}
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
                  labelFormatter={(v: number) => `${v} known`}
                  formatter={(value: number, dataKey: string) => [
                    `${value.toFixed(1)}%`,
                    dataKey === "al" ? "Active learning" : "Random",
                  ]}
                />
                <Line type="monotone" dataKey="al" stroke="var(--accent)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--accent)" }} name="al" />
                <Line type="monotone" dataKey="random" stroke="var(--accent-cool)" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3, fill: "var(--accent-cool)" }} name="random" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className={styles.summary}>
            Active learning reached{" "}
            <strong className={styles.summaryValue}>
              {Math.abs(state.data.final_gap * 100).toFixed(1)} percentage points
            </strong>{" "}
            {state.data.final_gap >= 0 ? "higher" : "lower"} accuracy than random sampling at
            the same number of experiments, averaged over {state.data.runs} run
            {state.data.runs === 1 ? "" : "s"}.
          </p>
        </>
      )}
    </div>
  );
}
