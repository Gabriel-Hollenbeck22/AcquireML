"""Tests for explain.py model selection — build_estimator / train_full_model."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from sklearn.calibration import CalibratedClassifierCV

from acquireml.explain import (
    CALIBRATION_METHODS,
    MODEL_CHOICES,
    build_estimator,
    find_best_threshold,
    predict_at_threshold,
    train_full_model,
)


@pytest.fixture()
def tiny_Xy():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.integers(0, 2, size=(40, 6)).astype(int),
                      columns=[f"f{j}" for j in range(6)])
    y = pd.Series((X["f0"] | X["f1"]).astype(int))
    return X, y


def test_model_choices_contains_expected():
    assert set(MODEL_CHOICES) == {"rf", "gbm", "lr", "svm"}


@pytest.mark.parametrize("name,expected_type", [
    ("rf", RandomForestClassifier),
    ("gbm", GradientBoostingClassifier),
    ("lr", LogisticRegression),
    ("svm", SVC),
])
def test_build_estimator_returns_correct_type(name, expected_type):
    assert isinstance(build_estimator(name), expected_type)


def test_build_estimator_invalid_name_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        build_estimator("nope")


@pytest.mark.parametrize("name", MODEL_CHOICES)
def test_train_full_model_fits_and_predicts_proba(tiny_Xy, name):
    X, y = tiny_Xy
    model = train_full_model(X, y, model_name=name)
    proba = model.predict_proba(X.values)
    assert proba.shape == (len(X), 2)


def test_train_full_model_defaults_to_rf(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y)
    assert isinstance(model, RandomForestClassifier)


# ── calibration ───────────────────────────────────────────────────────────────

def test_calibration_methods_contains_expected():
    assert set(CALIBRATION_METHODS) == {"sigmoid", "isotonic"}


def test_calibrate_true_wraps_in_calibrated_classifier(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y, calibrate=True)
    assert isinstance(model, CalibratedClassifierCV)


def test_calibrate_false_returns_plain_model(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y, calibrate=False)
    assert isinstance(model, RandomForestClassifier)


@pytest.mark.parametrize("method", CALIBRATION_METHODS)
def test_calibrated_model_predicts_proba(tiny_Xy, method):
    X, y = tiny_Xy
    model = train_full_model(X, y, calibrate=True, calibration_method=method)
    proba = model.predict_proba(X.values)
    assert proba.shape == (len(X), 2)


def test_calibration_skipped_when_class_too_small(tiny_Xy):
    """With only 1 sample in the minority class, CV calibration is impossible —
    should silently fall back to the uncalibrated model rather than raising."""
    X, y = tiny_Xy
    X_small = X.iloc[:21].copy()
    y_small = pd.concat([pd.Series([0] * 20), pd.Series([1])]).reset_index(drop=True)
    model = train_full_model(X_small, y_small, calibrate=True)
    assert isinstance(model, RandomForestClassifier)  # fell back, not wrapped


def test_calibrate_with_other_model_names(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y, model_name="lr", calibrate=True)
    assert isinstance(model, CalibratedClassifierCV)


# ── threshold tuning ─────────────────────────────────────────────────────────

def test_find_best_threshold_returns_value_in_range():
    rng = np.random.default_rng(0)
    n = 200
    y = rng.integers(0, 2, size=n)
    signal = y.copy()
    noise = rng.integers(0, 2, size=(n, 5))
    X = np.column_stack([signal, noise]).astype(float)
    estimator = build_estimator("rf")
    threshold = find_best_threshold(estimator, X, y, cv=5)
    assert 0.05 <= threshold <= 0.95


def test_find_best_threshold_improves_recall_on_imbalanced_data():
    """With a rare positive class, the sklearn-default 0.5 cutoff under-
    calls the positive class. The tuned threshold should be lower, and
    should improve balanced accuracy over what 0.5 would give on the same
    out-of-fold probabilities."""
    rng = np.random.default_rng(1)
    n = 500
    # ~12% positive, mirroring AZM's real-world imbalance.
    y = (rng.random(n) < 0.12).astype(int)
    signal = y + rng.normal(0, 0.3, size=n)  # noisy but informative
    noise = rng.integers(0, 2, size=(n, 5))
    X = np.column_stack([signal, noise])

    estimator = build_estimator("rf")
    threshold = find_best_threshold(estimator, X, y, cv=5)

    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import balanced_accuracy_score
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    proba = cross_val_predict(estimator, X, y, cv=skf, method="predict_proba")[:, 1]

    acc_at_threshold = balanced_accuracy_score(y, proba >= threshold)
    acc_at_half = balanced_accuracy_score(y, proba >= 0.5)
    assert acc_at_threshold >= acc_at_half


def test_predict_at_threshold_uses_model_threshold(tiny_Xy):
    X, y = tiny_Xy
    model = build_estimator("rf")
    model.fit(X.values, y.values)
    model.threshold_ = 0.9  # deliberately extreme — almost nothing clears it
    proba = model.predict_proba(X.values)[:, 1]
    expected = (proba >= 0.9).astype(int)
    result = predict_at_threshold(model, X.values)
    np.testing.assert_array_equal(result, expected)


def test_predict_at_threshold_defaults_to_half_when_absent(tiny_Xy):
    X, y = tiny_Xy
    model = build_estimator("rf")
    model.fit(X.values, y.values)
    assert not hasattr(model, "threshold_")
    proba = model.predict_proba(X.values)[:, 1]
    expected = (proba >= 0.5).astype(int)
    result = predict_at_threshold(model, X.values)
    np.testing.assert_array_equal(result, expected)


def test_train_full_model_sets_threshold_attribute(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y)
    assert hasattr(model, "threshold_")
    assert 0.05 <= model.threshold_ <= 0.95


def test_train_full_model_threshold_falls_back_when_class_too_small(tiny_Xy):
    """With only 1 sample in the minority class, no CV fold count >= 2 is
    possible — threshold search should be skipped, not raise."""
    X, y = tiny_Xy
    X_small = X.iloc[:21].copy()
    y_small = pd.concat([pd.Series([0] * 20), pd.Series([1])]).reset_index(drop=True)
    model = train_full_model(X_small, y_small)
    assert model.threshold_ == 0.5


def test_train_full_model_tune_threshold_false_keeps_half(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y, tune_threshold=False)
    assert model.threshold_ == 0.5


def test_train_full_model_calibrated_still_gets_threshold(tiny_Xy):
    X, y = tiny_Xy
    model = train_full_model(X, y, calibrate=True)
    assert isinstance(model, CalibratedClassifierCV)
    assert hasattr(model, "threshold_")
