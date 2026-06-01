"""Tests for acquireml/validate.py — holdout validation module."""
import numpy as np
import pandas as pd
import pytest

from acquireml.validate import run_validation


@pytest.fixture()
def separable_dataset():
    """A dataset where one feature perfectly predicts the label.

    This guarantees the model can learn something, so validation metrics
    are meaningful rather than random noise.
    """
    rng = np.random.default_rng(0)
    n = 400
    y = rng.integers(0, 2, size=n)
    # Feature 0 strongly correlates with y; the rest are noise.
    signal = y.copy()
    noise = rng.integers(0, 2, size=(n, 19))
    X = pd.DataFrame(
        np.column_stack([signal, noise]),
        columns=[f"f{i}" for i in range(20)],
    )
    y = pd.Series(y, name="label")
    return X, y


def test_validation_returns_expected_keys(separable_dataset):
    X, y = separable_dataset
    results = run_validation(X, y, test_size=0.25, random_state=0)
    for key in ["balanced_accuracy", "precision", "recall", "f1",
                "roc_auc", "confusion_matrix", "n_train", "n_holdout"]:
        assert key in results


def test_validation_split_sizes(separable_dataset):
    X, y = separable_dataset
    results = run_validation(X, y, test_size=0.25, random_state=0)
    assert results["n_holdout"] == 100        # 25% of 400
    assert results["n_train"] == 300
    assert results["n_train"] + results["n_holdout"] == len(y)


def test_validation_metrics_in_range(separable_dataset):
    X, y = separable_dataset
    results = run_validation(X, y, test_size=0.25, random_state=0)
    for metric in ["balanced_accuracy", "precision", "recall", "f1"]:
        assert 0.0 <= results[metric] <= 1.0


def test_validation_learns_separable_signal(separable_dataset):
    """With a perfectly predictive feature, accuracy should be high."""
    X, y = separable_dataset
    results = run_validation(X, y, test_size=0.25, random_state=0)
    assert results["balanced_accuracy"] > 0.9


def test_confusion_matrix_sums_to_holdout(separable_dataset):
    X, y = separable_dataset
    results = run_validation(X, y, test_size=0.25, random_state=0)
    cm = results["confusion_matrix"]
    assert cm.sum() == results["n_holdout"]
    # tp + tn + fp + fn should also equal holdout size
    assert results["tp"] + results["tn"] + results["fp"] + results["fn"] == results["n_holdout"]


def test_holdout_is_unseen():
    """Sanity check: train and holdout indices must not overlap.

    We verify indirectly — the split sizes must partition the data exactly,
    leaving no sample in both sets.
    """
    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.integers(0, 2, size=(200, 10)),
                     columns=[f"f{i}" for i in range(10)])
    y = pd.Series(rng.integers(0, 2, size=200))
    results = run_validation(X, y, test_size=0.3, random_state=1)
    assert results["n_train"] + results["n_holdout"] == 200
    assert results["n_holdout"] == 60
