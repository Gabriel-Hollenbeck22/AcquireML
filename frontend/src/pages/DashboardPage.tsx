import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getHistory,
  getStatus,
  type HistoryRow,
  type StatusResponse,
} from "../api/client";
import AccuracyChart from "../components/AccuracyChart";
import styles from "./DashboardPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessionStatus: StatusResponse; history: HistoryRow[] };

export default function DashboardPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    Promise.all([getStatus(name), getHistory(name)])
      .then(([sessionStatus, history]) => {
        if (!cancelled) setState({ status: "loaded", sessionStatus, history });
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

  const { sessionStatus, history } = state;

  return (
    <div>
      {sessionStatus.should_stop && (
        <div className={styles.stopBanner}>
          Stopping recommended: {sessionStatus.stop_reason}
        </div>
      )}

      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{sessionStatus.current_round}</div>
          <div className={styles.statLabel}>Round</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{sessionStatus.n_known}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{sessionStatus.n_pool}</div>
          <div className={styles.statLabel}>In pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {sessionStatus.latest_accuracy !== null
              ? `${(sessionStatus.latest_accuracy * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div className={styles.statLabel}>Accuracy</div>
        </div>
      </div>

      {history.length > 0 ? (
        <AccuracyChart history={history} />
      ) : (
        <p className={styles.empty}>No rounds completed yet.</p>
      )}
    </div>
  );
}
