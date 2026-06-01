"""Tests for acquireml/recommend.py — Phase 3 live recommendation module."""
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from acquireml.loader import ANTIBIOTIC_MAP
from acquireml.recommend import (
    load_new_strains,
    align_to_training,
    rank_strains,
)
from acquireml.explain import train_full_model


# ── Shared fixtures ────────────────────────────────────────────────────────────

TRAINING_COLUMNS = ["UNITIG_AAA", "UNITIG_GGG", "UNITIG_CCC", "UNITIG_TTT"]


def _write_training_data(tmp_path: Path, antibiotic: str = "azm") -> Path:
    """Write a minimal synthetic .Rtab + metadata.csv to tmp_path."""
    rtab_file = ANTIBIOTIC_MAP[antibiotic][0]
    rtab_content = (
        "pattern_id ERR001 ERR002 ERR003 ERR004 ERR005 ERR006\n"
        "UNITIG_AAA 1 0 1 0 1 0\n"
        "UNITIG_GGG 0 1 0 1 0 1\n"
        "UNITIG_CCC 1 1 0 0 1 1\n"
        "UNITIG_TTT 0 0 1 1 0 0\n"
    )
    (tmp_path / rtab_file).write_text(rtab_content)
    meta = (
        "Sample_ID,azm_sr,cip_sr,cfx_sr\n"
        "ERR001,1,0,0\n"
        "ERR002,0,1,0\n"
        "ERR003,1,0,0\n"
        "ERR004,0,1,0\n"
        "ERR005,1,0,0\n"
        "ERR006,0,1,0\n"
    )
    (tmp_path / "metadata.csv").write_text(meta)
    return tmp_path


def _write_new_strains_csv(tmp_path: Path, columns=None, n_strains: int = 4) -> Path:
    """Write a synthetic CSV of unlabelled new strains."""
    cols = columns if columns is not None else TRAINING_COLUMNS
    rng = np.random.default_rng(0)
    data = rng.integers(0, 2, size=(n_strains, len(cols)))
    ids = [f"NEW_{i:03d}" for i in range(n_strains)]
    df = pd.DataFrame(data, index=ids, columns=cols)
    out = tmp_path / "new_strains.csv"
    df.to_csv(out)
    return out


@pytest.fixture()
def trained_model(tmp_path):
    """Return a model trained on synthetic data."""
    from acquireml.loader import DataLoader
    _write_training_data(tmp_path, antibiotic="azm")
    loader = DataLoader(data_dir=tmp_path, antibiotic="azm")
    X_train, y_train = loader.load()
    model = train_full_model(X_train, y_train, random_state=0)
    return model, list(X_train.columns)


# ── load_new_strains ────────────────────────────────────────────────────────────

def test_load_new_strains_basic(tmp_path):
    csv_path = _write_new_strains_csv(tmp_path, n_strains=5)
    df = load_new_strains(csv_path)
    assert df.shape == (5, len(TRAINING_COLUMNS))
    assert list(df.index) == [f"NEW_{i:03d}" for i in range(5)]


def test_load_new_strains_bad_file_raises(tmp_path):
    bad = tmp_path / "nonexistent.csv"
    with pytest.raises(ValueError, match="Could not read"):
        load_new_strains(bad)


def test_load_new_strains_empty_raises(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("strain_id\n")   # only index column, no feature columns
    with pytest.raises(ValueError, match="appears empty"):
        load_new_strains(empty)


# ── align_to_training ───────────────────────────────────────────────────────────

def test_align_exact_match():
    X = pd.DataFrame({"UNITIG_AAA": [1], "UNITIG_GGG": [0]})
    aligned, cov = align_to_training(X, ["UNITIG_AAA", "UNITIG_GGG"])
    assert list(aligned.columns) == ["UNITIG_AAA", "UNITIG_GGG"]
    assert cov == 1.0


def test_align_handles_missing_columns():
    """Columns missing from new data are filled with 0."""
    X = pd.DataFrame({"UNITIG_AAA": [1]})  # missing UNITIG_GGG
    aligned, cov = align_to_training(X, ["UNITIG_AAA", "UNITIG_GGG"])
    assert aligned.shape[1] == 2
    assert aligned["UNITIG_GGG"].iloc[0] == 0   # filled with 0
    assert cov == 0.5


def test_align_handles_extra_columns():
    """Columns not in training data are silently dropped."""
    X = pd.DataFrame({"UNITIG_AAA": [1], "UNITIG_UNKNOWN": [1]})
    aligned, cov = align_to_training(X, ["UNITIG_AAA"])
    assert list(aligned.columns) == ["UNITIG_AAA"]
    assert "UNITIG_UNKNOWN" not in aligned.columns


def test_align_reorders_columns():
    """Output column order matches training, regardless of input order."""
    X = pd.DataFrame({"UNITIG_GGG": [1], "UNITIG_AAA": [0]})
    training_order = ["UNITIG_AAA", "UNITIG_GGG"]
    aligned, _ = align_to_training(X, training_order)
    assert list(aligned.columns) == training_order


# ── rank_strains ────────────────────────────────────────────────────────────────

def test_recommend_returns_all_strains(tmp_path, trained_model):
    model, training_cols = trained_model
    csv_path = _write_new_strains_csv(tmp_path, columns=training_cols, n_strains=6)
    X_new = load_new_strains(csv_path)
    X_aligned, _ = align_to_training(X_new, training_cols)
    results = rank_strains(model, X_aligned, top_n=None)
    assert len(results) == 6


def test_recommend_ranking_is_permutation(tmp_path, trained_model):
    """Every input strain appears in the output exactly once."""
    model, training_cols = trained_model
    csv_path = _write_new_strains_csv(tmp_path, columns=training_cols, n_strains=4)
    X_new = load_new_strains(csv_path)
    X_aligned, _ = align_to_training(X_new, training_cols)
    results = rank_strains(model, X_aligned, top_n=None)
    assert set(results["strain_id"].tolist()) == set(X_new.index.tolist())


def test_recommend_top_n_limits_output(tmp_path, trained_model):
    """--top-n returns exactly N rows."""
    model, training_cols = trained_model
    csv_path = _write_new_strains_csv(tmp_path, columns=training_cols, n_strains=6)
    X_new = load_new_strains(csv_path)
    X_aligned, _ = align_to_training(X_new, training_cols)
    results = rank_strains(model, X_aligned, top_n=2)
    assert len(results) == 2
    assert list(results["rank"]) == [1, 2]


def test_recommend_csv_output(tmp_path, trained_model):
    """Passing an output path writes a readable CSV."""
    model, training_cols = trained_model
    csv_path = _write_new_strains_csv(tmp_path, columns=training_cols, n_strains=4)
    X_new = load_new_strains(csv_path)
    X_aligned, _ = align_to_training(X_new, training_cols)
    results = rank_strains(model, X_aligned, top_n=None)
    out_path = tmp_path / "recommendations.csv"
    results.to_csv(out_path, index=False)
    loaded = pd.read_csv(out_path)
    assert list(loaded.columns) == ["rank", "strain_id", "uncertainty_score",
                                    "p_resistant", "predicted_class"]
    assert len(loaded) == 4


def test_recommend_handles_missing_columns_end_to_end(tmp_path, trained_model):
    """A CSV with only half the training columns should not raise."""
    model, training_cols = trained_model
    subset_cols = training_cols[:2]   # only provide half the unitigs
    csv_path = _write_new_strains_csv(tmp_path, columns=subset_cols, n_strains=3)
    X_new = load_new_strains(csv_path)
    X_aligned, coverage = align_to_training(X_new, training_cols)
    assert coverage == pytest.approx(0.5)
    results = rank_strains(model, X_aligned, top_n=None)
    assert len(results) == 3   # should complete without error
