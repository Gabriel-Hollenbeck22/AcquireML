"""Tests for demo.py — synthetic data generator."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from acquireml.demo import generate_synthetic_dataset, write_demo_files


def test_generate_returns_expected_shapes():
    X_known, y_known, X_pool = generate_synthetic_dataset(
        n_known=20, n_pool=30, n_features=10
    )
    assert X_known.shape == (20, 10)
    assert len(y_known) == 20
    assert X_pool.shape == (30, 10)


def test_generate_values_are_binary():
    X_known, _, X_pool = generate_synthetic_dataset(n_known=10, n_pool=10, n_features=5)
    assert set(X_known.values.flatten().tolist()) <= {0, 1}
    assert set(X_pool.values.flatten().tolist()) <= {0, 1}


def test_generate_labels_are_binary():
    _, y_known, _ = generate_synthetic_dataset(n_known=20, n_pool=10, n_features=8)
    assert set(y_known.unique().tolist()) <= {0, 1}


def test_generate_resistance_rate_approximately_respected():
    _, y_known, _ = generate_synthetic_dataset(
        n_known=500, n_pool=10, n_features=20, resistance_rate=0.25, random_state=1
    )
    assert 0.15 < y_known.mean() < 0.35


def test_generate_known_and_pool_disjoint_ids():
    X_known, _, X_pool = generate_synthetic_dataset(n_known=15, n_pool=15, n_features=5)
    assert set(X_known.index).isdisjoint(set(X_pool.index))


def test_generate_reproducible_with_same_seed():
    X1, y1, _ = generate_synthetic_dataset(n_known=10, n_pool=5, n_features=6, random_state=7)
    X2, y2, _ = generate_synthetic_dataset(n_known=10, n_pool=5, n_features=6, random_state=7)
    pd.testing.assert_frame_equal(X1, X2)
    pd.testing.assert_series_equal(y1, y2)


def test_generate_different_seeds_differ():
    X1, _, _ = generate_synthetic_dataset(n_known=10, n_pool=5, n_features=6, random_state=1)
    X2, _, _ = generate_synthetic_dataset(n_known=10, n_pool=5, n_features=6, random_state=2)
    assert not X1.equals(X2)


# ── write_demo_files ────────────────────────────────────────────────────────

def test_write_demo_files_creates_csvs(tmp_path: Path):
    summary = write_demo_files(tmp_path, n_known=10, n_pool=15, n_features=6)
    assert Path(summary["labeled_path"]).exists()
    assert Path(summary["pool_path"]).exists()


def test_write_demo_files_labeled_has_label_column(tmp_path: Path):
    summary = write_demo_files(tmp_path, n_known=10, n_pool=15, n_features=6)
    df = pd.read_csv(summary["labeled_path"], index_col=0)
    assert "resistant" in df.columns
    assert len(df) == 10


def test_write_demo_files_pool_has_no_label_column(tmp_path: Path):
    summary = write_demo_files(tmp_path, n_known=10, n_pool=15, n_features=6)
    df = pd.read_csv(summary["pool_path"], index_col=0)
    assert "resistant" not in df.columns
    assert len(df) == 15


def test_write_demo_files_summary_fields(tmp_path: Path):
    summary = write_demo_files(tmp_path, n_known=10, n_pool=15, n_features=6)
    for key in ("n_known", "n_pool", "n_features", "n_resistant", "resistance_rate"):
        assert key in summary


def test_write_demo_files_creates_output_dir(tmp_path: Path):
    nested = tmp_path / "a" / "b"
    write_demo_files(nested, n_known=5, n_pool=5, n_features=4)
    assert nested.exists()


# ── End-to-end: demo files feed straight into a real Session ──────────────────

def test_demo_files_work_with_session(tmp_path: Path):
    from acquireml.session import Session

    summary = write_demo_files(tmp_path, n_known=20, n_pool=20, n_features=8)
    db = tmp_path / "demo.db"
    sess = Session(db)
    init_summary = sess.init(
        data_path=summary["labeled_path"],
        label_col="resistant",
        pool_path=summary["pool_path"],
        name="demo",
    )
    assert init_summary["n_known"] == 20
    assert init_summary["n_pool"] == 20
    recs = sess.recommend(batch_size=5)
    assert len(recs) == 5
    sess.close()
