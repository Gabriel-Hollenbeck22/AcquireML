import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionSummary } from "../api/client";
import styles from "./SessionListPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessions: SessionSummary[] };

export default function SessionListPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

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
        <Link to="/new" className={styles.newLink}>
          New session
        </Link>
      </div>

      {state.status === "loading" && <p className={styles.loading}>Loading…</p>}

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && state.sessions.length === 0 && (
        <p className={styles.empty}>No sessions yet — create one to get started.</p>
      )}

      {state.status === "loaded" &&
        state.sessions.map((session) => (
          <div key={session.name} className={styles.sessionCard}>
            <div className={styles.sessionName}>{session.name}</div>
            <div className={styles.sessionMeta}>
              Round {session.current_round} · {session.n_known} known ·{" "}
              {session.n_pool} in pool
              {session.latest_accuracy !== null &&
                ` · ${(session.latest_accuracy * 100).toFixed(1)}% accuracy`}
            </div>
          </div>
        ))}
    </div>
  );
}
