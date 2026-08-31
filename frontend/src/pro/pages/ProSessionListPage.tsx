import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionSummary } from "../../api/client";
import { sortSessions, type SortKey } from "../../pages/sessionSort";
import styles from "./ProSessionListPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessions: SessionSummary[] };

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "name", label: "Name" },
  { value: "round", label: "Round" },
  { value: "accuracy", label: "Accuracy" },
  { value: "known", label: "Known" },
];

export default function ProSessionListPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [sortBy, setSortBy] = useState<SortKey>("name");

  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then((sessions) => {
        if (!cancelled) setState({ status: "loaded", sessions });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Sessions</h1>
        <Link to="/pro/new" className={styles.newLink}>
          New session
        </Link>
      </div>

      {state.status === "loaded" && state.sessions.length > 0 && (
        <div className={styles.sortRow}>
          <label htmlFor="sortBy">Sort by</label>
          <select id="sortBy" value={sortBy} onChange={(e) => setSortBy(e.target.value as SortKey)}>
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      )}

      {state.status === "loading" && <p className={styles.loading}>Loading…</p>}

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && state.sessions.length === 0 && (
        <p className={styles.empty}>No sessions yet — create one to get started.</p>
      )}

      {state.status === "loaded" && state.sessions.length > 0 && (
        <div className={styles.cardGrid}>
          {sortSessions(state.sessions, sortBy).map((session) => (
            <Link
              key={session.name}
              to={`/pro/sessions/${session.name}`}
              className={styles.sessionCard}
            >
              <div className={styles.sessionName}>{session.name}</div>
              <div className={styles.statRow}>
                <div className={styles.stat}>
                  <div className={styles.statValue}>{session.current_round}</div>
                  <div className={styles.statLabel}>Round</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles.statValue}>{session.n_known}</div>
                  <div className={styles.statLabel}>Known</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles.statValue}>{session.n_pool}</div>
                  <div className={styles.statLabel}>Pool</div>
                </div>
                <div className={styles.stat}>
                  <div
                    className={
                      session.latest_accuracy !== null && session.latest_accuracy >= 0.9
                        ? `${styles.statValue} ${styles.highAccuracy}`
                        : styles.statValue
                    }
                  >
                    {session.latest_accuracy !== null ? `${(session.latest_accuracy * 100).toFixed(1)}%` : "—"}
                  </div>
                  <div className={styles.statLabel}>Accuracy</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
