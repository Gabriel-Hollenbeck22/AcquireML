"""
session.py — SQLite-backed prospective active learning session

Persists the state of a real-world active learning loop across multiple
lab rounds: which samples are labeled (known pool), which are waiting to
be tested (unlabeled pool), which are awaiting lab results (pending), and
the accuracy history across rounds.

Feature data is NOT stored in the DB — only sample IDs, labels, and status.
Features are reloaded from the original file on demand, keeping the .db
file small even for high-dimensional genomic datasets.

Workflow
--------
1. session.init(data, label_col, pool)   → seed known pool + unlabeled pool
2. session.recommend(batch_size, output) → get next experiments as CSV
3. <researcher runs experiments, fills in label column>
4. session.update(results.csv)           → feed results back, retrain
5. Repeat from step 2 until pool is exhausted or accuracy is sufficient.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

from acquireml.generic_loader import GenericLoader
from acquireml.strategies import UncertaintySampling, _binary_entropy
from acquireml.explain import train_full_model

DEFAULT_DB_NAME = "acquireml_session.db"


class Session:
    """Manages a prospective active learning session backed by SQLite.

    Parameters
    ----------
    db_path : str or Path
        Path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_NAME) -> None:
        self.db_path = Path(db_path)
        self._con: Optional[sqlite3.Connection] = None

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self.db_path)
            self._con.row_factory = sqlite3.Row
        return self._con

    def close(self) -> None:
        if self._con:
            self._con.close()
            self._con = None

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _create_schema(self) -> None:
        con = self._connect()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS samples (
                sample_id   TEXT PRIMARY KEY,
                label       INTEGER,
                status      TEXT NOT NULL CHECK(status IN ('known','pool','pending')),
                added_round INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS rounds (
                round_number    INTEGER PRIMARY KEY,
                recommended_ids TEXT NOT NULL,
                accuracy        REAL,
                n_known         INTEGER NOT NULL,
                created_at      TEXT NOT NULL
            );
        """)
        con.commit()

    # ── Meta helpers ──────────────────────────────────────────────────────────

    def _set_meta(self, key: str, value: str) -> None:
        con = self._connect()
        con.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
        )
        con.commit()

    def _get_meta(self, key: str) -> Optional[str]:
        con = self._connect()
        row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    # ── Feature loading ───────────────────────────────────────────────────────

    def _load_all_features(self) -> pd.DataFrame:
        """Reload all feature rows from the original data files."""
        data_path = self._get_meta("data_path")
        label_col = self._get_meta("label_col")
        X, _ = GenericLoader(data_path, label_col=label_col).load()

        pool_path = self._get_meta("pool_path")
        if pool_path:
            X_pool, _ = GenericLoader(pool_path).load()
            # Avoid duplicating samples already in X
            new_ids = X_pool.index.difference(X.index)
            X = pd.concat([X, X_pool.loc[new_ids]], axis=0)

        return X

    def _get_known_Xy(self) -> tuple[pd.DataFrame, pd.Series]:
        con = self._connect()
        rows = con.execute(
            "SELECT sample_id, label FROM samples WHERE status = 'known'"
        ).fetchall()
        if not rows:
            raise RuntimeError("No labeled samples in the known pool.")
        known_ids = [r["sample_id"] for r in rows]
        labels = {r["sample_id"]: r["label"] for r in rows}
        X_all = self._load_all_features()
        X_known = X_all.loc[X_all.index.isin(known_ids)]
        y_known = pd.Series(
            [labels[sid] for sid in X_known.index], index=X_known.index
        )
        return X_known, y_known

    def _get_pool_X(self) -> pd.DataFrame:
        con = self._connect()
        rows = con.execute(
            "SELECT sample_id FROM samples WHERE status = 'pool'"
        ).fetchall()
        pool_ids = {r["sample_id"] for r in rows}
        X_all = self._load_all_features()
        return X_all.loc[X_all.index.isin(pool_ids)]

    def _train(self) -> tuple:
        """Return (model, X_known, y_known, accuracy)."""
        X_known, y_known = self._get_known_Xy()
        model = train_full_model(X_known, y_known)
        acc = float(balanced_accuracy_score(y_known, model.predict(X_known)))
        return model, X_known, y_known, acc

    # ── Public API ────────────────────────────────────────────────────────────

    # ── Stopping criteria ────────────────────────────────────────────────────

    def _check_stopping(self) -> tuple[bool, str]:
        """Return (should_stop, reason) based on recent accuracy history.

        Compares the net accuracy improvement over the last `patience` completed
        rounds. If that improvement is below `min_delta`, the model has plateaued
        and further experiments are unlikely to help.
        """
        patience = int(self._get_meta("patience") or 3)
        min_delta = float(self._get_meta("min_delta") or 0.005)

        con = self._connect()
        rows = con.execute(
            "SELECT accuracy FROM rounds WHERE accuracy IS NOT NULL"
            " ORDER BY round_number DESC LIMIT ?",
            (patience,),
        ).fetchall()

        if len(rows) < patience:
            return False, ""

        accuracies = [r["accuracy"] for r in reversed(rows)]
        improvement = accuracies[-1] - accuracies[0]

        if improvement < min_delta:
            return True, (
                f"Accuracy improved by only {improvement:+.4f} over the last "
                f"{patience} rounds (threshold: {min_delta}). "
                "The model has likely plateaued — consider stopping."
            )
        return False, ""

    # ── Public API ────────────────────────────────────────────────────────────

    def init(
        self,
        data_path: str | Path,
        label_col: str,
        pool_path: Optional[str | Path] = None,
        name: str = "session",
        patience: int = 3,
        min_delta: float = 0.005,
    ) -> dict:
        """Create a new session from labeled data and an optional unlabeled pool.

        Parameters
        ----------
        data_path : path to labeled data file (CSV, TSV, Excel, or Rtab)
        label_col : column name containing binary labels (0/1)
        pool_path : optional path to unlabeled pool file (no label column)
        name      : human-readable session name

        Returns
        -------
        summary dict
        """
        if self.db_path.exists():
            raise FileExistsError(
                f"Session already exists at {self.db_path}. "
                "Delete it or specify a different --db path."
            )

        self._create_schema()
        self._set_meta("name", name)
        self._set_meta("data_path", str(Path(data_path).resolve()))
        self._set_meta("label_col", label_col)
        self._set_meta("current_round", "0")
        self._set_meta("patience", str(patience))
        self._set_meta("min_delta", str(min_delta))
        self._set_meta("created_at", datetime.now(timezone.utc).isoformat())
        if pool_path:
            self._set_meta("pool_path", str(Path(pool_path).resolve()))

        # Seed known pool from labeled data
        loader = GenericLoader(data_path, label_col=label_col)
        X, y = loader.load()

        con = self._connect()
        for sid in X.index:
            con.execute(
                "INSERT INTO samples (sample_id, label, status, added_round)"
                " VALUES (?, ?, 'known', 0)",
                (str(sid), int(y[sid])),
            )

        # Seed unlabeled pool
        n_pool = 0
        if pool_path:
            X_pool, _ = GenericLoader(pool_path).load()
            existing = {
                r[0]
                for r in con.execute("SELECT sample_id FROM samples").fetchall()
            }
            for sid in X_pool.index:
                if str(sid) not in existing:
                    con.execute(
                        "INSERT INTO samples (sample_id, label, status, added_round)"
                        " VALUES (?, NULL, 'pool', 0)",
                        (str(sid),),
                    )
                    n_pool += 1
        con.commit()

        return {
            "name": name,
            "n_known": len(X),
            "n_pool": n_pool,
            "label_col": label_col,
            "patience": patience,
            "min_delta": min_delta,
            "db_path": str(self.db_path),
        }

    def recommend(
        self,
        batch_size: int = 10,
        output_path: Optional[str | Path] = None,
    ) -> pd.DataFrame:
        """Rank the unlabeled pool and return the top batch_size to test next.

        Trains a model on the current known pool, scores unlabeled samples by
        uncertainty, marks the selected batch as 'pending', and writes an output
        CSV with an empty 'label' column for the researcher to fill in.

        Returns
        -------
        pd.DataFrame with columns: rank, sample_id, uncertainty_score,
            p_positive, predicted_class, label
        """
        con = self._connect()

        n_pool = con.execute(
            "SELECT COUNT(*) FROM samples WHERE status = 'pool'"
        ).fetchone()[0]
        if n_pool == 0:
            raise RuntimeError(
                "Unlabeled pool is empty — all samples have been labeled."
            )

        n_pending = con.execute(
            "SELECT COUNT(*) FROM samples WHERE status = 'pending'"
        ).fetchone()[0]
        if n_pending > 0:
            raise RuntimeError(
                f"{n_pending} samples are still pending lab results. "
                "Run 'session update' with those results before requesting more."
            )

        model, X_known, _, _ = self._train()
        X_pool = self._get_pool_X()

        n_select = min(batch_size, len(X_pool))
        strategy = UncertaintySampling()
        local_idx = strategy.select_batch(model, X_pool.values, n_select)

        proba = model.predict_proba(X_pool.values)
        uncertainty = _binary_entropy(proba)
        predictions = model.predict(X_pool.values)

        order = np.argsort(uncertainty)[::-1][:n_select]

        results = pd.DataFrame(
            {
                "rank": range(1, len(order) + 1),
                "sample_id": X_pool.index[order],
                "uncertainty_score": uncertainty[order].round(6),
                "p_positive": (
                    proba[order, 1].round(4)
                    if proba.shape[1] > 1
                    else np.zeros(len(order))
                ),
                "predicted_class": [
                    "positive" if p == 1 else "negative" for p in predictions[order]
                ],
                "label": "",  # researcher fills this in
            }
        ).reset_index(drop=True)

        current_round = int(self._get_meta("current_round")) + 1
        self._set_meta("current_round", str(current_round))

        for sid in results["sample_id"]:
            con.execute(
                "UPDATE samples SET status = 'pending', added_round = ?"
                " WHERE sample_id = ?",
                (current_round, str(sid)),
            )

        con.execute(
            "INSERT INTO rounds (round_number, recommended_ids, n_known, created_at)"
            " VALUES (?, ?, ?, ?)",
            (
                current_round,
                json.dumps(results["sample_id"].tolist()),
                len(X_known),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        con.commit()

        if output_path:
            results.to_csv(output_path, index=False)

        should_stop, stop_reason = self._check_stopping()
        results.attrs["should_stop"] = should_stop
        results.attrs["stop_reason"] = stop_reason

        return results

    def update(self, results_path: str | Path) -> dict:
        """Feed lab results back and retrain.

        Reads a CSV with 'sample_id' and 'label' columns (the filled-in
        recommendations file), moves matched samples to the known pool,
        retrains the model, and records accuracy for this round.

        Any pending samples NOT present in the results file are returned to
        the unlabeled pool (researcher can choose not to test some).

        Returns
        -------
        dict with round, n_returned, n_known, n_pool, accuracy
        """
        results_df = pd.read_csv(results_path)

        missing_cols = {"sample_id", "label"} - set(results_df.columns)
        if missing_cols:
            raise ValueError(
                f"Results file missing columns: {missing_cols}. "
                "Expected 'sample_id' and 'label'."
            )

        results_df = results_df.dropna(subset=["label"])
        results_df["label"] = results_df["label"].astype(int)

        con = self._connect()
        current_round = int(self._get_meta("current_round"))

        n_updated = 0
        for _, row in results_df.iterrows():
            cur = con.execute(
                "UPDATE samples SET status = 'known', label = ?"
                " WHERE sample_id = ? AND status = 'pending'",
                (int(row["label"]), str(row["sample_id"])),
            )
            n_updated += cur.rowcount

        # Return any unreported pending samples to the pool
        con.execute(
            "UPDATE samples SET status = 'pool', added_round = 0"
            " WHERE status = 'pending'"
        )
        con.commit()

        if n_updated == 0:
            raise ValueError(
                "No pending samples matched in the results file. "
                "Check that sample_id values match the recommendations."
            )

        _, _, _, accuracy = self._train()
        con.execute(
            "UPDATE rounds SET accuracy = ? WHERE round_number = ?",
            (accuracy, current_round),
        )
        con.commit()

        n_known = con.execute(
            "SELECT COUNT(*) FROM samples WHERE status = 'known'"
        ).fetchone()[0]
        n_pool = con.execute(
            "SELECT COUNT(*) FROM samples WHERE status = 'pool'"
        ).fetchone()[0]

        should_stop, stop_reason = self._check_stopping()
        return {
            "round": current_round,
            "n_returned": n_updated,
            "n_known": n_known,
            "n_pool": n_pool,
            "accuracy": accuracy,
            "should_stop": should_stop,
            "stop_reason": stop_reason,
        }

    def status(self) -> dict:
        """Return current session state as a dict."""
        con = self._connect()
        counts = {
            status: con.execute(
                "SELECT COUNT(*) FROM samples WHERE status = ?", (status,)
            ).fetchone()[0]
            for status in ("known", "pool", "pending")
        }
        latest = con.execute(
            "SELECT * FROM rounds ORDER BY round_number DESC LIMIT 1"
        ).fetchone()
        should_stop, stop_reason = self._check_stopping()
        return {
            "name": self._get_meta("name"),
            "current_round": int(self._get_meta("current_round") or 0),
            "n_known": counts["known"],
            "n_pool": counts["pool"],
            "n_pending": counts["pending"],
            "latest_accuracy": latest["accuracy"] if latest else None,
            "patience": int(self._get_meta("patience") or 3),
            "min_delta": float(self._get_meta("min_delta") or 0.005),
            "should_stop": should_stop,
            "stop_reason": stop_reason,
            "created_at": self._get_meta("created_at"),
        }

    def history(self) -> list[dict]:
        """Return all rounds as a list of dicts."""
        con = self._connect()
        rows = con.execute(
            "SELECT round_number, n_known, accuracy, created_at"
            " FROM rounds ORDER BY round_number"
        ).fetchall()
        return [dict(r) for r in rows]
