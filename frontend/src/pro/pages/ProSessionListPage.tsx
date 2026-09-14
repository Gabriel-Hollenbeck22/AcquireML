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

  const sessions = state.status === "loaded" ? state.sessions : [];
  const accuracies = sessions
    .map((s) => s.latest_accuracy)
    .filter((a): a is number => a !== null);
  const avgAccuracy = accuracies.length > 0
    ? accuracies.reduce((sum, a) => sum + a, 0) / accuracies.length
    : null;
  const totalKnown = sessions.reduce((sum, s) => sum + s.n_known, 0);
  const totalPool = sessions.reduce((sum, s) => sum + s.n_pool, 0);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Portfolio</div>
          <h1>Sessions</h1>
          <p className={styles.subtitle}>Track active learning progress across every experiment.</p>
        </div>
        <Link to="/pro/new" className={styles.newLink}>
          New session
        </Link>
      </div>

      {state.status === "loaded" && state.sessions.length > 0 && (
        <div className={styles.summaryRow}>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>{sessions.length}</div>
            <div className={styles.summaryLabel}>Sessions</div>
          </div>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>{totalKnown}</div>
            <div className={styles.summaryLabel}>Known samples</div>
          </div>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>{totalPool}</div>
            <div className={styles.summaryLabel}>In pool</div>
          </div>
          <div className={styles.summaryStat}>
            <div className={styles.summaryValue}>
              {avgAccuracy !== null ? `${(avgAccuracy * 100).toFixed(1)}%` : "—"}
            </div>
            <div className={styles.summaryLabel}>Avg. accuracy</div>
          </div>
        </div>
      )}

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
        <div className={styles.emptyState}>
          <div className={styles.emptyTitle}>No sessions yet</div>
          <p className={styles.emptyBody}>
            Create a session to start recommending experiments from your data.
          </p>
          <Link to="/pro/new" className={styles.newLink}>
            New session
          </Link>
        </div>
      )}

      {state.status === "loaded" && state.sessions.length > 0 && (
        <div className={styles.cardGrid}>
          {sortSessions(state.sessions, sortBy).map((session) => (
            <Link
              key={session.name}
              to={`/pro/sessions/${session.name}`}
              className={styles.sessionCard}
            >
              <div className={styles.cardTop}>
                <div className={styles.sessionName}>{session.name}</div>
                <div className={styles.roundBadge}>Round {session.current_round}</div>
              </div>
              <div className={styles.statRow}>
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
