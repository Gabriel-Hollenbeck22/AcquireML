import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getFeatureImportance, type FeatureImportanceResponse } from "../api/client";
import styles from "./ExplainPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: FeatureImportanceResponse };

export default function ExplainPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getFeatureImportance(name)
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
  const maxImportance = Math.max(...data.features.map((f) => f.importance), 0.0001);

  return (
    <div>
      <h2>Feature importance</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.cv_accuracy_mean !== null
              ? `${(data.cv_accuracy_mean * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div className={styles.statLabel}>
            Cross-validated accuracy
            {data.cv_accuracy_std !== null && ` (± ${(data.cv_accuracy_std * 100).toFixed(1)}pp)`}
          </div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.total_features}</div>
          <div className={styles.statLabel}>Total features</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_known}</div>
          <div className={styles.statLabel}>Trained on</div>
        </div>
      </div>

      {data.features.length === 0 ? (
        <p className={styles.empty}>Not enough known samples yet to rank features.</p>
      ) : (
        <div className={styles.barCard}>
          <h4>Top predictive features</h4>
          <ul className={styles.barList}>
            {data.features.map((f) => (
              <li key={f.feature} className={styles.barRow}>
                <span className={styles.barRank}>#{f.rank}</span>
                <span className={styles.barLabel}>{f.feature}</span>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(f.importance / maxImportance) * 100}%` }}
                  />
                </div>
                <span className={styles.barValue}>{f.importance.toFixed(4)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
