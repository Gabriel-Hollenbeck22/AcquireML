import { Link, Outlet, useParams } from "react-router-dom";
import styles from "./SessionLayout.module.css";

export default function SessionLayout() {
  const { name } = useParams<{ name: string }>();

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.sessionName}>{name}</div>
        <nav className={styles.nav}>
          <Link to={`/sessions/${name}`}>Dashboard</Link>
          <Link to={`/sessions/${name}/recommend`}>Recommendations</Link>
          <Link to={`/sessions/${name}/history`}>History</Link>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
