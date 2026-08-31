import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getValidation, type ValidateResponse } from "../../api/client";
import styles from "./ProValidatePage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: ValidateResponse };

export default function ProValidatePage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getValidation(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;

  return (
    <div>
      <h2 className={styles.title}>Holdout validation</h2>
      <p className={styles.intro}>
        Trained on {data.n_train} known samples, evaluated on {data.n_holdout} held-out
        samples the model never saw during training.
      </p>

      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.balanced_accuracy * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Balanced accuracy</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.precision * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Precision</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.recall * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Recall</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.f1 * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>F1</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.roc_auc !== null ? data.roc_auc.toFixed(3) : "—"}
          </div>
          <div className={styles.statLabel}>ROC-AUC</div>
        </div>
      </div>

      <div className={styles.matrixCard}>
        <h4>Confusion matrix</h4>
        <div className={styles.matrixGrid}>
          <div className={styles.matrixCell}>
            <div className={styles.matrixCount}>{data.tn}</div>
            <div className={styles.matrixLabel}>Correctly cleared sensitive strains</div>
          </div>
          <div className={`${styles.matrixCell} ${styles.matrixMiss}`}>
            <div className={styles.matrixCount}>{data.fp}</div>
            <div className={styles.matrixLabel}>False alarms (false positives)</div>
          </div>
          <div className={`${styles.matrixCell} ${styles.matrixMiss}`}>
            <div className={styles.matrixCount}>{data.fn}</div>
            <div className={styles.matrixLabel}>Missed resistant strains (false negatives)</div>
          </div>
          <div className={styles.matrixCell}>
            <div className={styles.matrixCount}>{data.tp}</div>
            <div className={styles.matrixLabel}>Correctly caught resistant strains</div>
          </div>
        </div>
      </div>
    </div>
  );
}
