"""Tests for GenericLoader — format auto-detection and loading."""
from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from acquireml.generic_loader import GenericLoader


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Small 6-sample binary feature matrix with a label column."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(6, 8)).astype(int),
        index=[f"S{i}" for i in range(6)],
        columns=[f"feat_{j}" for j in range(8)],
    )
    df["resistance"] = [1, 0, 1, 0, 1, 0]
    return df


@pytest.fixture()
def csv_file(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    p = tmp_path / "data.csv"
    sample_df.to_csv(p)
    return p


@pytest.fixture()
def tsv_file(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    p = tmp_path / "data.tsv"
    sample_df.to_csv(p, sep="\t")
    return p


@pytest.fixture()
def excel_file(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    p = tmp_path / "data.xlsx"
    sample_df.to_excel(p)
    return p


@pytest.fixture()
def unlabeled_csv(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    p = tmp_path / "pool.csv"
    sample_df.drop(columns=["resistance"]).to_csv(p)
    return p


@pytest.fixture()
def rtab_file(tmp_path: Path) -> Path:
    """Minimal Rtab file: 4 unitigs × 3 samples."""
    content = textwrap.dedent("""\
        pattern_id S0 S1 S2
        unitig_1 1 0 1
        unitig_2 0 1 0
        unitig_3 1 1 0
        unitig_4 0 0 1
    """)
    p = tmp_path / "test.Rtab"
    p.write_text(content)
    return p


# ── Format detection ──────────────────────────────────────────────────────────

def test_detect_csv(csv_file):
    assert GenericLoader(csv_file)._detect_format() == "csv"


def test_detect_tsv(tsv_file):
    assert GenericLoader(tsv_file)._detect_format() == "tsv"


def test_detect_excel(excel_file):
    assert GenericLoader(excel_file)._detect_format() == "excel"


def test_detect_rtab(rtab_file):
    assert GenericLoader(rtab_file)._detect_format() == "rtab"


def test_sniff_tab_delimited(tmp_path):
    p = tmp_path / "data.dat"
    p.write_text("id\ta\tb\nS0\t1\t0\n")
    assert GenericLoader(p)._detect_format() == "tsv"


def test_sniff_comma_delimited(tmp_path):
    p = tmp_path / "data.dat"
    p.write_text("id,a,b\nS0,1,0\n")
    assert GenericLoader(p)._detect_format() == "csv"


# ── Loading with label column ─────────────────────────────────────────────────

def test_csv_load_with_label(csv_file, sample_df):
    X, y = GenericLoader(csv_file, label_col="resistance").load()
    assert list(X.columns) == [f"feat_{j}" for j in range(8)]
    assert len(y) == 6
    assert "resistance" not in X.columns
    assert y.sum() == 3


def test_tsv_load_with_label(tsv_file, sample_df):
    X, y = GenericLoader(tsv_file, label_col="resistance").load()
    assert len(X) == 6
    assert y is not None


def test_excel_load_with_label(excel_file, sample_df):
    X, y = GenericLoader(excel_file, label_col="resistance").load()
    assert len(X) == 6
    assert y is not None


# ── Loading without label column ──────────────────────────────────────────────

def test_csv_load_no_label(unlabeled_csv):
    X, y = GenericLoader(unlabeled_csv).load()
    assert y is None
    assert len(X) == 6


def test_csv_load_label_col_none_explicitly(csv_file):
    X, y = GenericLoader(csv_file, label_col=None).load()
    assert y is None


# ── Rtab loading ──────────────────────────────────────────────────────────────

def test_rtab_load_transposes(rtab_file):
    X, y = GenericLoader(rtab_file).load()
    # 3 samples × 4 unitigs after transpose
    assert X.shape == (3, 4)
    assert y is None
    assert list(X.index) == ["S0", "S1", "S2"]


def test_rtab_values_are_uint8(rtab_file):
    X, _ = GenericLoader(rtab_file).load()
    assert X.dtypes.unique()[0] == np.uint8


# ── Error handling ────────────────────────────────────────────────────────────

def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        GenericLoader("/nonexistent/path.csv")


def test_missing_label_col_raises(csv_file):
    with pytest.raises(ValueError, match="Label column"):
        GenericLoader(csv_file, label_col="nonexistent").load()


# ── Summary ───────────────────────────────────────────────────────────────────

def test_summary_with_label(csv_file):
    s = GenericLoader(csv_file, label_col="resistance").summary()
    assert "Positive" in s
    assert "6" in s


def test_summary_without_label(unlabeled_csv):
    s = GenericLoader(unlabeled_csv).summary()
    assert "Positive" not in s
