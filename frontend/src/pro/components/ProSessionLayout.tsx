import { useEffect, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { getStatus, type StatusResponse } from "../../api/client";
import styles from "./ProSessionLayout.module.css";

export default function ProSessionLayout() {
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
      <aside className={styles.sidebar}>
        <div className={styles.sessionName}>SESSION: {name}</div>
        <nav className={styles.nav}>
          <NavLink
            to={`/pro/sessions/${name}`}
            end
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Dashboard
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/recommend`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Recommendations
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/history`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            History
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/overview`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Overview
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/explain`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Explain
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/compare`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Compare
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/validate`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Validate
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/settings`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Settings
          </NavLink>
          {status?.cost_per_sample !== null && status?.cost_per_sample !== undefined && (
            <NavLink
              to={`/pro/sessions/${name}/budget`}
              className={({ isActive }) => (isActive ? styles.active : undefined)}
            >
              Budget
            </NavLink>
          )}
        </nav>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
