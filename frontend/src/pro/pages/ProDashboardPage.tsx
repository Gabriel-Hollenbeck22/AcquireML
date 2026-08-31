import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getHistory,
  getStatus,
  type HistoryRow,
  type StatusResponse,
} from "../../api/client";
import ProAccuracyChart from "../components/ProAccuracyChart";
import { useCountUp } from "../../hooks/useCountUp";
import styles from "./ProDashboardPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessionStatus: StatusResponse; history: HistoryRow[] };

export default function ProDashboardPage() {
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

  const round = state.status === "loaded" ? state.sessionStatus.current_round : 0;
  const known = state.status === "loaded" ? state.sessionStatus.n_known : 0;
  const pool = state.status === "loaded" ? state.sessionStatus.n_pool : 0;
  const accuracyTarget =
    state.status === "loaded" && state.sessionStatus.latest_accuracy !== null
      ? state.sessionStatus.latest_accuracy * 100
      : 0;

  const animatedRound = Math.round(useCountUp(round));
  const animatedKnown = Math.round(useCountUp(known));
  const animatedPool = Math.round(useCountUp(pool));
  const animatedAccuracy = useCountUp(accuracyTarget);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { sessionStatus, history } = state;

  return (
    <div>
      <h2 className={styles.title}>Dashboard</h2>
      {sessionStatus.should_stop && (
        <div className={styles.stopBanner}>
          Stopping recommended: {sessionStatus.stop_reason}
        </div>
      )}

      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{animatedRound}</div>
          <div className={styles.statLabel}>Round</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{animatedKnown}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{animatedPool}</div>
          <div className={styles.statLabel}>In pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {sessionStatus.latest_accuracy !== null ? `${animatedAccuracy.toFixed(1)}%` : "—"}
          </div>
          <div className={styles.statLabel}>Accuracy</div>
        </div>
      </div>

      {history.length > 0 ? (
        <ProAccuracyChart history={history} />
      ) : (
        <p className={styles.empty}>No rounds completed yet.</p>
      )}
    </div>
  );
}
