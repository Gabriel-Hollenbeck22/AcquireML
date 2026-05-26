from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.metrics import balanced_accuracy_score

from acquireml.strategies import QueryStrategy, UncertaintySampling


class ActiveLearningEngine:
    """Simulates a hindsight active learning loop on a fully-labelled genomic dataset.

    The engine partitions the dataset into two pools:

    - **Known Pool** — samples the lab has "already run" (initially seeded randomly).
    - **Unexplored Pool** — the genetic search space not yet tested.

    Each call to :meth:`step` asks the query strategy to rank the Unexplored
    Pool by informativeness, selects the top ``batch_size`` samples, reveals
    their true labels (the hindsight part), moves them to the Known Pool,
    and retrains the model.  Performance is evaluated against the *full*
    dataset so we can measure how quickly the engine learns to characterise
    resistance correctly.

    Parameters
    ----------
    X : pd.DataFrame or np.ndarray, shape (n_samples, n_features)
    y : pd.Series or np.ndarray, shape (n_samples,)
    estimator : scikit-learn estimator
        Must support ``predict_proba``.
    strategy : QueryStrategy, optional
        Defaults to :class:`~acquireml.strategies.UncertaintySampling`.
    initial_pool_size : int
        Number of randomly selected samples to seed the Known Pool.
    batch_size : int
        Samples recommended (and revealed) per iteration.
    random_state : int
        Seed for reproducible initial pool selection.
    """

    def __init__(
        self,
        X: pd.DataFrame | np.ndarray,
        y: pd.Series | np.ndarray,
        estimator: BaseEstimator,
        strategy: QueryStrategy | None = None,
        initial_pool_size: int = 10,
        batch_size: int = 10,
        random_state: int = 42,
    ) -> None:
        self.X = X.values if isinstance(X, pd.DataFrame) else np.asarray(X)
        self.y = y.values if isinstance(y, pd.Series) else np.asarray(y)
        self.estimator = estimator
        self.strategy = strategy if strategy is not None else UncertaintySampling()
        self.initial_pool_size = initial_pool_size
        self.batch_size = batch_size
        self.random_state = random_state

        self._known_idx: np.ndarray = np.array([], dtype=int)
        self._pool_idx: np.ndarray = np.arange(len(self.y))
        self._model: BaseEstimator = clone(self.estimator)
        self.history: List[Dict] = []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fit(self) -> None:
        self._model.fit(self.X[self._known_idx], self.y[self._known_idx])

    def _snapshot(self, iteration: int) -> Dict:
        y_pred = self._model.predict(self.X)
        return {
            "iteration": iteration,
            "known_pool_size": int(len(self._known_idx)),
            "pool_remaining": int(len(self._pool_idx)),
            "balanced_accuracy": float(balanced_accuracy_score(self.y, y_pred)),
            "exploration_rate": float(len(self._known_idx) / len(self.y)),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> Dict:
        """Seed the Known Pool with a random initial set and train a baseline model.

        Returns
        -------
        metrics : dict
            Baseline snapshot (iteration 0).
        """
        rng = np.random.default_rng(self.random_state)
        self._known_idx = rng.choice(len(self.y), size=self.initial_pool_size, replace=False)
        self._pool_idx = np.setdiff1d(np.arange(len(self.y)), self._known_idx)
        self._model = clone(self.estimator)
        self._fit()
        baseline = self._snapshot(iteration=0)
        self.history = [baseline]
        return baseline

    def step(self) -> Dict:
        """One active learning iteration: query → reveal → retrain → evaluate.

        Returns
        -------
        metrics : dict
            Performance snapshot after this iteration.
        """
        if len(self._pool_idx) == 0:
            raise RuntimeError("Unexplored pool is exhausted; nothing left to query.")

        n_query = min(self.batch_size, len(self._pool_idx))
        local_idx = self.strategy.select_batch(self._model, self.X[self._pool_idx], n_query)
        selected = self._pool_idx[local_idx]

        self._known_idx = np.concatenate([self._known_idx, selected])
        self._pool_idx = np.setdiff1d(self._pool_idx, selected)

        self._fit()

        metrics = self._snapshot(iteration=len(self.history))
        self.history.append(metrics)
        return metrics

    def run(self, n_iterations: int) -> List[Dict]:
        """Convenience method: initialise and run n_iterations steps.

        Returns
        -------
        history : list of dicts
            One entry per iteration, including the baseline at index 0.
        """
        self.initialize()
        for _ in range(n_iterations):
            self.step()
        return self.history
