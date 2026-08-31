import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { exportHistory, getHistory, type HistoryRow } from "../../api/client";
import ProAccuracyChart from "../components/ProAccuracyChart";
import styles from "./ProHistoryPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; history: HistoryRow[] };

export default function ProHistoryPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getHistory(name)
      .then((history) => {
        if (!cancelled) setState({ status: "loaded", history });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  async function handleExport() {
    if (!name) return;
    setExportError(null);
    try {
      const blob = await exportHistory(name);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name}_history.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError((err as Error).message);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <div className={styles.headerRow}>
        <h2 className={styles.title}>Round history</h2>
        <button onClick={handleExport} className={styles.exportButton}>
          Export CSV
        </button>
      </div>

      {exportError && <p className={styles.error}>{exportError}</p>}

      {state.history.length === 0 ? (
        <p className={styles.empty}>No rounds completed yet.</p>
      ) : (
        <>
          <ProAccuracyChart history={state.history} />
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Round</th>
                <th>Known</th>
                <th>Accuracy</th>
                <th>Round cost</th>
                <th>Cumulative cost</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {state.history.map((row) => (
                <tr key={row.round_number}>
                  <td>{row.round_number}</td>
                  <td>{row.n_known}</td>
                  <td>{row.accuracy !== null ? `${(row.accuracy * 100).toFixed(1)}%` : "—"}</td>
                  <td>{row.round_cost !== null ? row.round_cost.toFixed(2) : "—"}</td>
                  <td>{row.cumulative_cost !== null ? row.cumulative_cost.toFixed(2) : "—"}</td>
                  <td>{row.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
