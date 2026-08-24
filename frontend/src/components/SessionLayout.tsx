import { useEffect, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { getStatus, type StatusResponse } from "../api/client";
import styles from "./SessionLayout.module.css";

export default function SessionLayout() {
  const { name } = useParams<{ name: string }>();
  const [status, setStatus] = useState<StatusResponse | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getStatus(name)
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        // Nav still works without status — only the conditional Budget
        // link depends on it, and it simply won't appear on error.
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.sessionName}>SESSION://{name}</div>
        <nav className={styles.nav}>
          <NavLink
            to={`/sessions/${name}`}
            end
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Dashboard
          </NavLink>
          <NavLink
            to={`/sessions/${name}/recommend`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Recommendations
          </NavLink>
          <NavLink
            to={`/sessions/${name}/history`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            History
          </NavLink>
          <NavLink
            to={`/sessions/${name}/overview`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Overview
          </NavLink>
          <NavLink
            to={`/sessions/${name}/settings`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Settings
          </NavLink>
          {status?.cost_per_sample !== null && status?.cost_per_sample !== undefined && (
            <NavLink
              to={`/sessions/${name}/budget`}
              className={({ isActive }) => (isActive ? styles.active : undefined)}
            >
              Budget
            </NavLink>
          )}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
