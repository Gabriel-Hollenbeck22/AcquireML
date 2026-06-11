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


class DiverseSampling(QueryStrategy):
    """Uncertainty sampling with a diversity term to avoid clustered batches.

    Pure uncertainty sampling can recommend N samples that are all very similar
    to each other — wasteful when the lab runs them in parallel. This strategy
    blends uncertainty with a greedy distance penalty so each pick is both
    informative AND as far as possible from the samples already selected in
    this batch.

    Algorithm (greedy):
        1. Score all pool samples by uncertainty.
        2. Pick the most uncertain sample first.
        3. For each subsequent pick, score candidates as:
               (1 - diversity_weight) * uncertainty
             + diversity_weight * min_distance_to_selected  (normalised to [0,1])
           and pick the highest scorer.

    Parameters
    ----------
    diversity_weight : float in [0, 1]
        0.0 = identical to UncertaintySampling.
        1.0 = greedy maximum-distance selection (ignores uncertainty).
        0.5 (default) balances both objectives.
    """

    def __init__(self, diversity_weight: float = 0.5) -> None:
        if not 0.0 <= diversity_weight <= 1.0:
            raise ValueError(
                f"diversity_weight must be in [0, 1], got {diversity_weight}"
            )
        self.diversity_weight = diversity_weight

    def select_batch(
        self,
        model: BaseEstimator,
        X_pool: np.ndarray,
        n: int,
    ) -> np.ndarray:
        n = min(n, len(X_pool))
        proba = model.predict_proba(X_pool)
        uncertainty = _binary_entropy(proba)

        # Normalise uncertainty to [0, 1]
        u_range = uncertainty.max() - uncertainty.min()
        if u_range > 0:
            uncertainty_norm = (uncertainty - uncertainty.min()) / u_range
        else:
            uncertainty_norm = uncertainty.copy()

        selected: list[int] = []
        # Min distances from each candidate to the selected set (start at inf)
        min_dist = np.full(len(X_pool), np.inf)

        for _ in range(n):
            if not selected:
                # First pick: highest uncertainty
                idx = int(np.argmax(uncertainty_norm))
            else:
                # Update min distances using the last selected point
                last = X_pool[selected[-1]]
                dists = np.linalg.norm(X_pool - last, axis=1)
                min_dist = np.minimum(min_dist, dists)

                # Normalise distances to [0, 1]
                d_max = min_dist.max()
                dist_norm = min_dist / d_max if d_max > 0 else min_dist.copy()

                score = (
                    (1.0 - self.diversity_weight) * uncertainty_norm
                    + self.diversity_weight * dist_norm
                )
                # Zero out already-selected indices
                score[selected] = -np.inf
                idx = int(np.argmax(score))

            selected.append(idx)

        return np.array(selected, dtype=int)
