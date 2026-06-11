import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from acquireml.engine import ActiveLearningEngine
from acquireml.strategies import UncertaintySampling, DiverseSampling, _binary_entropy


@pytest.fixture()
def tiny_dataset():
    rng = np.random.default_rng(0)
    X = rng.integers(0, 2, size=(100, 50), dtype=np.uint8)
    y = rng.integers(0, 2, size=100)
    return X, y


@pytest.fixture()
def engine(tiny_dataset):
    X, y = tiny_dataset
    return ActiveLearningEngine(
        X=X,
        y=y,
        estimator=RandomForestClassifier(n_estimators=10, random_state=0),
        strategy=UncertaintySampling(),
        initial_pool_size=10,
        batch_size=5,
        random_state=0,
    )


# ── Initialisation ──────────────────────────────────────────────────────

def test_initialize_known_pool_size(engine):
    baseline = engine.initialize()
    assert baseline["known_pool_size"] == 10


def test_initialize_pool_remaining(engine, tiny_dataset):
    _, y = tiny_dataset
    baseline = engine.initialize()
    assert baseline["pool_remaining"] == len(y) - 10


def test_initialize_resets_history(engine):
    engine.initialize()
    engine.initialize()
    assert len(engine.history) == 1  # only the fresh baseline


# ── Step behaviour ──────────────────────────────────────────────────────

def test_step_grows_known_pool(engine):
    engine.initialize()
    pre_known = engine._known_idx.copy()
    m = engine.step()
    assert m["known_pool_size"] == len(pre_known) + 5


def test_step_shrinks_pool(engine, tiny_dataset):
    _, y = tiny_dataset
    engine.initialize()
    m = engine.step()
    assert m["pool_remaining"] == len(y) - m["known_pool_size"]


def test_step_appends_to_history(engine):
    engine.initialize()
    engine.step()
    engine.step()
    assert len(engine.history) == 3  # baseline + 2 steps


# ── Run behaviour ───────────────────────────────────────────────────────

def test_run_history_length(engine):
    history = engine.run(n_iterations=5)
    assert len(history) == 6  # baseline + 5 steps


def test_exploration_rate_monotone(engine):
    history = engine.run(n_iterations=5)
    rates = [m["exploration_rate"] for m in history]
    assert all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1))


def test_balanced_accuracy_in_range(engine):
    history = engine.run(n_iterations=5)
    for m in history:
        assert 0.0 <= m["balanced_accuracy"] <= 1.0


def test_exhausted_pool_raises(engine, tiny_dataset):
    _, y = tiny_dataset
    engine = ActiveLearningEngine(
        X=tiny_dataset[0],
        y=y,
        estimator=RandomForestClassifier(n_estimators=5, random_state=0),
        initial_pool_size=len(y) - 1,  # leave only 1 sample in pool
        batch_size=5,
        random_state=0,
    )
    engine.initialize()
    engine.step()  # drains the pool
    with pytest.raises(RuntimeError, match="Unexplored pool is exhausted"):
        engine.step()


# ── Strategy internals ──────────────────────────────────────────────────

def test_binary_entropy_at_maximum_uncertainty():
    proba = np.array([[0.5, 0.5]])
    h = _binary_entropy(proba)
    assert abs(h[0] - 1.0) < 1e-6, "Binary entropy must equal 1.0 bit at p = 0.5"


def test_binary_entropy_near_zero_at_certainty():
    proba = np.array([[1.0, 0.0], [0.0, 1.0]])
    h = _binary_entropy(proba)
    assert all(h < 0.01), "Binary entropy must be near 0 at p ≈ 0 or p ≈ 1"


def test_uncertainty_sampling_selects_closest_to_half():
    strategy = UncertaintySampling()
    clf = _DummyClassifier(probas=np.array([[0.5, 0.5], [0.9, 0.1], [0.55, 0.45]]))
    X_pool = np.zeros((3, 1))
    selected = strategy.select_batch(clf, X_pool, n=1)
    assert selected[0] == 0, "Most uncertain sample (p=0.5) should be selected first"


# Helper for above test — avoids fitting a real model
class _DummyClassifier:
    def __init__(self, probas: np.ndarray):
        self._probas = probas

    def predict_proba(self, X):
        return self._probas


# ── DiverseSampling ──────────────────────────────────────────────────────────

def test_diverse_sampling_returns_correct_count():
    strategy = DiverseSampling(diversity_weight=0.5)
    clf = _DummyClassifier(np.tile([0.5, 0.5], (20, 1)))
    X_pool = np.random.default_rng(0).random((20, 5))
    selected = strategy.select_batch(clf, X_pool, n=5)
    assert len(selected) == 5


def test_diverse_sampling_no_duplicates():
    strategy = DiverseSampling(diversity_weight=0.5)
    clf = _DummyClassifier(np.tile([0.5, 0.5], (20, 1)))
    X_pool = np.random.default_rng(0).random((20, 5))
    selected = strategy.select_batch(clf, X_pool, n=10)
    assert len(set(selected)) == len(selected)


def test_diverse_sampling_indices_in_range():
    strategy = DiverseSampling(diversity_weight=0.5)
    clf = _DummyClassifier(np.tile([0.5, 0.5], (15, 1)))
    X_pool = np.random.default_rng(1).random((15, 4))
    selected = strategy.select_batch(clf, X_pool, n=5)
    assert all(0 <= i < 15 for i in selected)


def test_diverse_weight_zero_picks_highest_uncertainty():
    """diversity_weight=0 should pick only from the most uncertain samples."""
    probas = np.column_stack([
        np.linspace(0.1, 0.9, 10),
        np.linspace(0.9, 0.1, 10),
    ])
    clf = _DummyClassifier(probas)
    X_pool = np.random.default_rng(2).random((10, 3))

    from acquireml.strategies import _binary_entropy
    entropy = _binary_entropy(probas)
    top3_threshold = np.sort(entropy)[::-1][2]  # 3rd highest entropy value

    d_idx = DiverseSampling(diversity_weight=0.0).select_batch(clf, X_pool, n=3)
    for i in d_idx:
        assert entropy[i] >= top3_threshold - 1e-9, (
            "diversity_weight=0 should only pick high-entropy samples"
        )


def test_diverse_sampling_spreads_across_space():
    """With high diversity weight, selected points should be further apart
    than pure uncertainty sampling on a dataset where uncertainty is clustered."""
    rng = np.random.default_rng(42)
    # Two tight clusters far apart — uncertain samples all in cluster A
    cluster_a = rng.normal(loc=[0, 0], scale=0.1, size=(10, 2))
    cluster_b = rng.normal(loc=[10, 10], scale=0.1, size=(10, 2))
    X_pool = np.vstack([cluster_a, cluster_b])

    # All samples equally uncertain
    probas = np.tile([0.5, 0.5], (20, 1))
    clf = _DummyClassifier(probas)

    diverse = DiverseSampling(diversity_weight=0.9).select_batch(clf, X_pool, n=4)
    # Should pick from both clusters, not all from one
    from_a = sum(1 for i in diverse if i < 10)
    from_b = sum(1 for i in diverse if i >= 10)
    assert from_a >= 1 and from_b >= 1, "Diverse sampling should span both clusters"


def test_diverse_sampling_invalid_weight_raises():
    with pytest.raises(ValueError, match="diversity_weight"):
        DiverseSampling(diversity_weight=1.5)
