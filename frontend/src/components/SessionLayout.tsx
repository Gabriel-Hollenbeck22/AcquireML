import { NavLink, Outlet, useParams } from "react-router-dom";
import styles from "./SessionLayout.module.css";

export default function SessionLayout() {
  const { name } = useParams<{ name: string }>();

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
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
