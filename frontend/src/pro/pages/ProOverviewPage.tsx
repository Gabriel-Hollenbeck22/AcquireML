import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getOverview, type OverviewResponse } from "../../api/client";
import styles from "./ProOverviewPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: OverviewResponse };

export default function ProOverviewPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getOverview(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
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

  const { data } = state;
  const maxPrevalence = Math.max(...data.top_prevalent_features.map((f) => f.prevalence), 0.0001);

  return (
    <div>
      <h2 className={styles.title}>Session overview</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_known}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_pool}</div>
          <div className={styles.statLabel}>Pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_features}</div>
          <div className={styles.statLabel}>Features</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.positive_rate !== null ? `${(data.positive_rate * 100).toFixed(1)}%` : "—"}
          </div>
          <div className={styles.statLabel}>
            Positive ({data.n_positive} / {data.n_positive + data.n_negative})
          </div>
        </div>
      </div>

      {data.top_prevalent_features.length > 0 && (
        <div className={styles.barCard}>
          <h4>Most prevalent features</h4>
          <ul className={styles.barList}>
            {data.top_prevalent_features.map((f) => (
              <li key={f.feature} className={styles.barRow}>
                <span className={styles.barLabel}>{f.feature}</span>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(f.prevalence / maxPrevalence) * 100}%` }}
                  />
                </div>
                <span className={styles.barValue}>{(f.prevalence * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
