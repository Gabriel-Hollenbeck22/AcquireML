from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from sklearn.base import BaseEstimator


class QueryStrategy(ABC):
    """Abstract base class for active learning query strategies.

    Subclass this to implement alternative selection policies
    (e.g. Query by Committee, Expected Model Change, GP-UCB).
    """

    @abstractmethod
    def select_batch(
        self,
        model: BaseEstimator,
        X_pool: np.ndarray,
        n: int,
    ) -> np.ndarray:
        """Return indices (into X_pool rows) of the n most informative samples."""


def _binary_entropy(proba: np.ndarray) -> np.ndarray:
    """Shannon entropy for binary class probabilities (maximised at p = 0.5).

    Parameters
    ----------
    proba : array of shape (n_samples, 2)
        Output of model.predict_proba — columns are [P(class=0), P(class=1)].

    Returns
    -------
    entropy : array of shape (n_samples,)  in the range [0, 1] bits.
    """
    # If the model has only seen one class it returns a single-column proba.
    # In that case every pool sample looks equally uncertain, so return zeros
    # and let the caller fall back to whatever tie-breaking it uses.
    if proba.shape[1] < 2:
        return np.zeros(len(proba))
    p = np.clip(proba[:, 1], 1e-10, 1.0 - 1e-10)
    return -(p * np.log2(p) + (1.0 - p) * np.log2(1.0 - p))


class RandomSampling(QueryStrategy):
    """Baseline strategy: pick the next experiments completely at random.

    This is the control group.  It ignores everything the model has learned
    and just grabs n random samples from the unexplored pool.  If
    UncertaintySampling can't beat this, AcquireML has no value.
    """

    def __init__(self, random_state: int = 0) -> None:
        self._rng = np.random.default_rng(random_state)

    def select_batch(
        self,
        model: BaseEstimator,
        X_pool: np.ndarray,
        n: int,
    ) -> np.ndarray:
        return self._rng.choice(len(X_pool), size=n, replace=False)


class UncertaintySampling(QueryStrategy):
    """Select the samples where the model is most uncertain (closest to p = 0.5).

    This is AcquireML's core Phase-1 query strategy.  Each call finds the
    genetic configurations the model is maximally confused about — the ones
    a single lab run would teach it the most.  Uncertainty is measured via
    Shannon entropy so that the selection is sensitive to the full shape of
    the predictive distribution, not just the margin.
    """

    def select_batch(
        self,
        model: BaseEstimator,
        X_pool: np.ndarray,
        n: int,
    ) -> np.ndarray:
        proba = model.predict_proba(X_pool)
        entropy = _binary_entropy(proba)
        return np.argsort(entropy)[::-1][:n]
