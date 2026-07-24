import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getRecommendations,
  submitResults,
  type RecommendRow,
} from "../api/client";
import styles from "./RecommendationsPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; rows: RecommendRow[] };

export default function RecommendationsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getRecommendations(name)
      .then((response) => {
        if (!cancelled) setState({ status: "loaded", rows: response.rows });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (state.status !== "loaded" || !name) return;

    const results = state.rows
      .filter((row) => labels[row.sample_id] !== undefined && labels[row.sample_id] !== "")
      .map((row) => ({
        sample_id: row.sample_id,
        label: Number(labels[row.sample_id]),
      }));

    if (results.length === 0) {
      setSubmitError("Enter at least one result before submitting.");
      return;
    }

    setSubmitError(null);
    setSubmitting(true);
    try {
      await submitResults(name, results);
      navigate(`/sessions/${name}`);
    } catch (err) {
      setSubmitError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <h2>Recommended experiments</h2>
      <form onSubmit={handleSubmit}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Sample ID</th>
              <th>Uncertainty</th>
              <th>P(positive)</th>
              <th>Predicted</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {state.rows.map((row) => (
              <tr key={row.sample_id}>
                <td>{row.rank}</td>
                <td>{row.sample_id}</td>
                <td>{row.uncertainty_score.toFixed(3)}</td>
                <td>{row.p_positive.toFixed(3)}</td>
                <td>{row.predicted_class}</td>
                <td>
                  <label htmlFor={`label-${row.sample_id}`} className={styles.srOnly}>
                    Result for {row.sample_id}
                  </label>
                  <select
                    id={`label-${row.sample_id}`}
                    value={labels[row.sample_id] ?? ""}
                    onChange={(e) =>
                      setLabels((prev) => ({ ...prev, [row.sample_id]: e.target.value }))
                    }
                  >
                    <option value="">—</option>
                    <option value="0">0</option>
                    <option value="1">1</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit results"}
        </button>

        {submitError && <p className={styles.submitError}>{submitError}</p>}
      </form>
    </div>
  );
}
