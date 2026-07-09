"""Tests for Session — SQLite-backed prospective active learning loop."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from acquireml.session import Session


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def labeled_csv(tmp_path: Path) -> Path:
    """20 labeled samples with 10 binary features."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(20, 10)).astype(int),
        index=[f"known_{i}" for i in range(20)],
        columns=[f"f{j}" for j in range(10)],
    )
    df["outcome"] = (df["f0"] | df["f1"]).astype(int)
    p = tmp_path / "labeled.csv"
    df.to_csv(p)
    return p


@pytest.fixture()
def pool_csv(tmp_path: Path) -> Path:
    """30 unlabeled samples with the same 10 features."""
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(30, 10)).astype(int),
        index=[f"pool_{i}" for i in range(30)],
        columns=[f"f{j}" for j in range(10)],
    )
    p = tmp_path / "pool.csv"
    df.to_csv(p)
    return p


@pytest.fixture()
def session(tmp_path: Path, labeled_csv: Path, pool_csv: Path) -> Session:
    """Initialised session with 20 known + 30 pool samples."""
    db = tmp_path / "test.db"
    sess = Session(db)
    sess.init(
        data_path=labeled_csv,
        label_col="outcome",
        pool_path=pool_csv,
        name="test_session",
    )
    return sess


# ── init ──────────────────────────────────────────────────────────────────────

def test_init_creates_db(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome")
    assert db.exists()
    sess.close()


def test_init_populates_known_pool(session):
    s = session.status()
    assert s["n_known"] == 20
    session.close()


def test_init_populates_unlabeled_pool(session):
    s = session.status()
    assert s["n_pool"] == 30
    session.close()


def test_init_round_zero(session):
    s = session.status()
    assert s["current_round"] == 0
    session.close()


def test_init_duplicate_raises(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    Session(db).init(labeled_csv, label_col="outcome")
    with pytest.raises(FileExistsError):
        Session(db).init(labeled_csv, label_col="outcome")


def test_init_no_pool(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome")
    assert summary["n_pool"] == 0
    sess.close()


# ── recommend ─────────────────────────────────────────────────────────────────

def test_recommend_returns_dataframe(session):
    df = session.recommend(batch_size=5)
    assert len(df) == 5
    assert "sample_id" in df.columns
    assert "uncertainty_score" in df.columns
    assert "label" in df.columns
    session.close()


def test_recommend_increments_round(session):
    session.recommend(batch_size=5)
    s = session.status()
    assert s["current_round"] == 1
    session.close()


def test_recommend_marks_pending(session):
    session.recommend(batch_size=5)
    s = session.status()
    assert s["n_pending"] == 5
    assert s["n_pool"] == 25
    session.close()


def test_recommend_writes_csv(session, tmp_path):
    out = tmp_path / "recs.csv"
    session.recommend(batch_size=3, output_path=out)
    assert out.exists()
    df = pd.read_csv(out)
    assert len(df) == 3
    session.close()


def test_recommend_blocks_when_pending(session):
    session.recommend(batch_size=5)
    with pytest.raises(RuntimeError, match="pending"):
        session.recommend(batch_size=5)
    session.close()


def test_recommend_empty_pool_raises(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome")  # no pool
    with pytest.raises(RuntimeError, match="pool is empty"):
        sess.recommend(batch_size=5)
    sess.close()


# ── update ────────────────────────────────────────────────────────────────────

def _make_results(recommendations: pd.DataFrame, tmp_path: Path) -> Path:
    """Fill in labels for a recommendations DataFrame and save as CSV."""
    recs = recommendations.copy()
    recs["label"] = 0  # all negative for simplicity
    p = tmp_path / "results.csv"
    recs.to_csv(p, index=False)
    return p


def test_update_moves_pending_to_known(session, tmp_path):
    recs = session.recommend(batch_size=5)
    results_path = _make_results(recs, tmp_path)
    summary = session.update(results_path)
    assert summary["n_returned"] == 5
    s = session.status()
    assert s["n_known"] == 25
    assert s["n_pending"] == 0
    session.close()


def test_update_records_accuracy(session, tmp_path):
    recs = session.recommend(batch_size=5)
    results_path = _make_results(recs, tmp_path)
    summary = session.update(results_path)
    assert 0.0 <= summary["accuracy"] <= 1.0
    session.close()


def test_update_appears_in_history(session, tmp_path):
    recs = session.recommend(batch_size=5)
    results_path = _make_results(recs, tmp_path)
    session.update(results_path)
    hist = session.history()
    assert len(hist) == 1
    assert hist[0]["accuracy"] is not None
    session.close()


def test_update_unmatched_returns_to_pool(session, tmp_path):
    recs = session.recommend(batch_size=5)
    # Return only the first 3 of 5 recommended samples
    partial = recs.head(3).copy()
    partial["label"] = 0
    p = tmp_path / "partial.csv"
    partial.to_csv(p, index=False)
    summary = session.update(p)
    assert summary["n_returned"] == 3
    # The 2 unreturned should go back to pool
    s = session.status()
    assert s["n_pool"] == 27  # 25 remaining + 2 returned to pool
    session.close()


def test_update_bad_file_raises(session, tmp_path):
    session.recommend(batch_size=5)
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"wrong_col": [1, 2]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        session.update(bad)
    session.close()


def test_update_no_matches_raises(session, tmp_path):
    session.recommend(batch_size=5)
    bad = tmp_path / "nomatch.csv"
    pd.DataFrame({"sample_id": ["fake_1", "fake_2"], "label": [0, 1]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="No pending samples matched"):
        session.update(bad)
    session.close()


# ── Full round-trip ───────────────────────────────────────────────────────────

def test_two_full_rounds(session, tmp_path):
    for round_num in range(1, 3):
        recs = session.recommend(batch_size=5)
        round_dir = tmp_path / f"round_{round_num}"
        round_dir.mkdir()
        results_path = _make_results(recs, round_dir)
        summary = session.update(results_path)
        assert summary["round"] == round_num

    hist = session.history()
    assert len(hist) == 2
    s = session.status()
    assert s["current_round"] == 2
    assert s["n_known"] == 30
    session.close()


# ── status / history ──────────────────────────────────────────────────────────

def test_status_fields(session):
    s = session.status()
    for key in ("name", "current_round", "n_known", "n_pool", "n_pending",
                "latest_accuracy", "patience", "min_delta",
                "should_stop", "stop_reason", "created_at"):
        assert key in s
    session.close()


def test_history_empty_before_rounds(session):
    assert session.history() == []
    session.close()


# ── stopping criteria ─────────────────────────────────────────────────────────

def _run_n_rounds(session, tmp_path, n, batch_size=5):
    """Helper: run n full rounds, returns list of update summaries."""
    summaries = []
    for i in range(n):
        recs = session.recommend(batch_size=batch_size)
        d = tmp_path / f"r{i}"
        d.mkdir(exist_ok=True)
        results_path = _make_results(recs, d)
        summaries.append(session.update(results_path))
    return summaries


def test_no_stop_before_patience_rounds(tmp_path, labeled_csv, pool_csv):
    """Should not flag stopping until patience rounds have completed."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              patience=3, min_delta=0.005)
    summaries = _run_n_rounds(sess, tmp_path, n=2, batch_size=5)
    assert summaries[-1]["should_stop"] is False
    sess.close()


def test_stop_flagged_when_plateau(tmp_path, labeled_csv, pool_csv):
    """Should flag stopping when accuracy hasn't improved meaningfully."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              patience=3, min_delta=0.999)  # impossibly high threshold → always plateaued
    summaries = _run_n_rounds(sess, tmp_path, n=3, batch_size=5)
    assert summaries[-1]["should_stop"] is True
    assert summaries[-1]["stop_reason"] != ""
    sess.close()


def test_stop_reason_contains_round_count(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              patience=3, min_delta=0.999)
    summaries = _run_n_rounds(sess, tmp_path, n=3, batch_size=5)
    assert "3" in summaries[-1]["stop_reason"]
    sess.close()


def test_status_reflects_stopping(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              patience=3, min_delta=0.999)
    _run_n_rounds(sess, tmp_path, n=3, batch_size=5)
    s = sess.status()
    assert s["should_stop"] is True
    assert s["patience"] == 3
    assert s["min_delta"] == 0.999
    sess.close()


def test_custom_patience_and_min_delta_stored(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", patience=5, min_delta=0.02)
    s = sess.status()
    assert s["patience"] == 5
    assert s["min_delta"] == 0.02
    sess.close()


def test_recommend_attrs_carry_stopping(tmp_path, labeled_csv, pool_csv):
    """recommend() DataFrame attrs should carry should_stop and stop_reason."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              patience=3, min_delta=0.999)
    _run_n_rounds(sess, tmp_path, n=3, batch_size=5)
    recs = sess.recommend(batch_size=5)
    assert "should_stop" in recs.attrs
    assert "stop_reason" in recs.attrs
    assert recs.attrs["should_stop"] is True
    sess.close()


def test_update_returns_should_stop(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              patience=3, min_delta=0.999)
    summaries = _run_n_rounds(sess, tmp_path, n=3, batch_size=5)
    assert "should_stop" in summaries[-1]
    assert "stop_reason" in summaries[-1]
    sess.close()


# ── cost tracking ─────────────────────────────────────────────────────────────

def test_no_cost_when_not_configured(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    summaries = _run_n_rounds(sess, tmp_path, n=1, batch_size=5)
    assert summaries[0]["round_cost"] is None
    assert summaries[0]["cumulative_cost"] is None
    s = sess.status()
    assert s["cost_per_sample"] is None
    assert s["total_cost"] is None
    sess.close()


def test_round_cost_equals_n_returned_times_cost(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              cost_per_sample=200.0)
    summaries = _run_n_rounds(sess, tmp_path, n=1, batch_size=5)
    assert summaries[0]["round_cost"] == pytest.approx(200.0 * 5)
    sess.close()


def test_cumulative_cost_accumulates(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              cost_per_sample=100.0)
    summaries = _run_n_rounds(sess, tmp_path, n=2, batch_size=5)
    assert summaries[0]["cumulative_cost"] == pytest.approx(500.0)
    assert summaries[1]["cumulative_cost"] == pytest.approx(1000.0)
    sess.close()


def test_status_shows_total_cost(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              cost_per_sample=50.0)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)
    s = sess.status()
    assert s["cost_per_sample"] == pytest.approx(50.0)
    assert s["total_cost"] == pytest.approx(500.0)
    sess.close()


def test_history_includes_cost_columns(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              cost_per_sample=75.0)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)
    hist = sess.history()
    assert hist[0]["round_cost"] == pytest.approx(375.0)
    assert hist[1]["cumulative_cost"] == pytest.approx(750.0)
    sess.close()


def test_cost_stored_in_init_summary(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome", cost_per_sample=250.0)
    assert summary["cost_per_sample"] == pytest.approx(250.0)
    sess.close()


# ── batch diversity ───────────────────────────────────────────────────────────

def test_diversity_weight_stored(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome", diversity_weight=0.5)
    assert summary["diversity_weight"] == pytest.approx(0.5)
    sess.close()


def test_diversity_default_is_zero(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome")
    s = sess.status()
    assert s["diversity_weight"] == pytest.approx(0.0)
    sess.close()


def test_diversity_status_shows_weight(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              diversity_weight=0.7)
    s = sess.status()
    assert s["diversity_weight"] == pytest.approx(0.7)
    sess.close()


def test_diverse_session_recommend_returns_batch(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              diversity_weight=0.5)
    recs = sess.recommend(batch_size=5)
    assert len(recs) == 5
    assert len(recs["sample_id"].unique()) == 5
    sess.close()


def test_diverse_session_full_round(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              diversity_weight=0.5)
    summaries = _run_n_rounds(sess, tmp_path, n=2, batch_size=5)
    assert summaries[-1]["round"] == 2
    assert summaries[-1]["n_known"] == 30
    sess.close()


# ── round report ──────────────────────────────────────────────────────────────

def test_default_report_path_stored(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome")
    assert summary["report_path"] == str(tmp_path / "s_report.png")
    sess.close()


def test_custom_report_path_stored(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    custom = tmp_path / "charts" / "progress.png"
    custom.parent.mkdir()
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome", report_path=custom)
    assert summary["report_path"] == str(custom)
    sess.close()


def test_update_writes_report_png(session, tmp_path):
    recs = session.recommend(batch_size=5)
    results_path = _make_results(recs, tmp_path)
    summary = session.update(results_path)
    assert Path(summary["report_path"]).exists()
    session.close()


def test_status_includes_report_path(session):
    s = session.status()
    assert s["report_path"].endswith("_report.png")
    session.close()


def test_report_updates_across_rounds(session, tmp_path):
    summaries = _run_n_rounds(session, tmp_path, n=2, batch_size=5)
    report_path = Path(summaries[-1]["report_path"])
    assert report_path.exists()
    mtime_after_round_2 = report_path.stat().st_mtime
    assert mtime_after_round_2 > 0
    session.close()


# ── model selection ───────────────────────────────────────────────────────────

def test_model_defaults_to_rf(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome")
    assert summary["model"] == "rf"
    s = sess.status()
    assert s["model"] == "rf"
    sess.close()


@pytest.mark.parametrize("model_name", ["rf", "gbm", "lr", "svm"])
def test_each_model_choice_completes_a_round(tmp_path, labeled_csv, pool_csv, model_name):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv, model=model_name)
    summaries = _run_n_rounds(sess, tmp_path, n=1, batch_size=5)
    assert 0.0 <= summaries[0]["accuracy"] <= 1.0
    sess.close()


def test_invalid_model_name_raises(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    with pytest.raises(ValueError, match="Unknown model"):
        sess.init(labeled_csv, label_col="outcome", model="xgboost")
    sess.close()


# ── calibration ───────────────────────────────────────────────────────────────

def test_calibrate_defaults_to_false(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    summary = sess.init(labeled_csv, label_col="outcome")
    assert summary["calibrate"] is False
    s = sess.status()
    assert s["calibrate"] is False
    assert s["calibration_method"] == "sigmoid"
    sess.close()


def test_calibrate_true_completes_a_round(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv, calibrate=True)
    summaries = _run_n_rounds(sess, tmp_path, n=1, batch_size=5)
    assert 0.0 <= summaries[0]["accuracy"] <= 1.0
    sess.close()


def test_calibrate_isotonic_completes_a_round(tmp_path, labeled_csv, pool_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv,
              calibrate=True, calibration_method="isotonic")
    summaries = _run_n_rounds(sess, tmp_path, n=1, batch_size=5)
    assert 0.0 <= summaries[0]["accuracy"] <= 1.0
    sess.close()


def test_invalid_calibration_method_raises(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    with pytest.raises(ValueError, match="Unknown calibration method"):
        sess.init(labeled_csv, label_col="outcome", calibration_method="platt")
    sess.close()


# ── reset ─────────────────────────────────────────────────────────────────────

def test_reset_clears_history(tmp_path, labeled_csv, pool_csv):
    """After 2 rounds, reset should wipe all round history."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)
    assert len(sess.history()) == 2

    result = sess.reset()

    assert result["rounds_cleared"] == 2
    assert sess.history() == []
    sess.close()


def test_reset_restores_round_counter(tmp_path, labeled_csv, pool_csv):
    """current_round should return to 0 after reset."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)

    sess.reset()

    assert sess.status()["current_round"] == 0
    sess.close()


def test_reset_moves_pending_back_to_pool(tmp_path, labeled_csv, pool_csv):
    """Samples marked pending (recommended but not yet returned) go back to pool."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    sess.recommend(batch_size=5)  # marks 5 samples as pending

    before = sess.status()
    assert before["n_pending"] == 5

    sess.reset()

    after = sess.status()
    assert after["n_pending"] == 0
    assert after["n_pool"] == before["n_pool"] + 5
    sess.close()


def test_reset_preserves_known_pool(tmp_path, labeled_csv, pool_csv):
    """Known (labeled) samples are not affected by reset."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=1, batch_size=5)
    before_known = sess.status()["n_known"]

    sess.reset()

    # known pool still has same samples (we reset history, not labels)
    assert sess.status()["n_known"] == before_known
    sess.close()


def test_reset_allows_new_round_after(tmp_path, labeled_csv, pool_csv):
    """After a reset the session should accept a new recommend→update cycle."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)

    sess.reset()
    summaries = _run_n_rounds(sess, tmp_path, n=1, batch_size=5)

    assert summaries[0]["round"] == 1
    assert len(sess.history()) == 1
    sess.close()


def test_reset_zero_rounds_returns_zero_cleared(tmp_path, labeled_csv, pool_csv):
    """Resetting a fresh session reports 0 rounds cleared."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)

    result = sess.reset()

    assert result["rounds_cleared"] == 0
    sess.close()


# ── export ────────────────────────────────────────────────────────────────────

def test_export_writes_csv(tmp_path, labeled_csv, pool_csv):
    """export() should produce a readable CSV with one row per round."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)

    out = tmp_path / "history.csv"
    returned = sess.export(out)

    assert returned == out
    assert out.exists()
    df = pd.read_csv(out)
    assert len(df) == 2
    sess.close()


def test_export_csv_columns(tmp_path, labeled_csv, pool_csv):
    """Exported CSV must include the core history columns."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=1, batch_size=5)

    out = tmp_path / "hist.csv"
    sess.export(out)
    df = pd.read_csv(out)

    for col in ("round_number", "n_known", "accuracy", "created_at"):
        assert col in df.columns
    sess.close()


def test_export_accuracy_values_match_history(tmp_path, labeled_csv, pool_csv):
    """Accuracy values in the exported CSV must match session.history()."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)
    _run_n_rounds(sess, tmp_path, n=2, batch_size=5)

    hist = sess.history()
    out = tmp_path / "h.csv"
    sess.export(out)
    df = pd.read_csv(out)

    for i, row in enumerate(hist):
        assert df.iloc[i]["accuracy"] == pytest.approx(row["accuracy"])
    sess.close()


def test_export_empty_history_writes_header_only_csv(tmp_path, labeled_csv, pool_csv):
    """export() on a fresh session writes a header-only CSV (no round rows yet)."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", pool_path=pool_csv)

    out = tmp_path / "empty.csv"
    sess.export(out)
    df = pd.read_csv(out)

    assert len(df) == 0
    assert "round_number" in df.columns
    assert "accuracy" in df.columns
    sess.close()
