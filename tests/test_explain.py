"""Tests for explain.py model selection — build_estimator / train_full_model."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from acquireml.explain import MODEL_CHOICES, build_estimator, train_full_model


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
