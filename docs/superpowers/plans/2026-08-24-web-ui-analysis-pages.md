# Web UI Analysis Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four session-scoped analysis pages — Session Overview, Feature Importance, AL vs Random Comparison, and Holdout Validation — completing Phase 5+6 of the web UI by wrapping the dataset-agnostic cores of `explain.py`, `compare.py`, and `validate.py`, plus new session-generic overview logic (not a wrapper around `explore.py` — see the design spec's "Scope Correction").

**Architecture:** Four new `Session` methods in `acquireml/session.py`, four new FastAPI endpoints, four new Pydantic schemas — all reusing existing dataset-agnostic functions from `explain.py`/`validate.py`, and `ActiveLearningEngine` from `engine.py` directly for the comparison. Four new frontend pages under the existing `SessionLayout`, four new unconditional nav links, four new API client functions. `ComparePage` is the one page in the app that doesn't fetch on mount — it's the most compute-heavy endpoint, gated behind an explicit "Run comparison" button.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest, scikit-learn (backend). React 18, TypeScript 5 (strict), Vite 5, Vitest 2 + React Testing Library 16, React Router 6, Recharts 2 (frontend) — matching every prior phase.

## Global Constraints

- Backend test suite (`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q` from repo root) must report 236 passed before this plan's backend work starts, and grow by exactly the new tests each backend task adds.
- Frontend test suite (`npm test -- --run` from `frontend/`) must report 88 passed before this plan's frontend work starts, and grow by exactly the new tests each frontend task adds.
- `npx tsc --noEmit` (from `frontend/`) must stay clean throughout.
- New backend response fields follow the exact snake_case-in-Python / camelCase-in-TypeScript mirroring discipline already established: Pydantic schema field names match `Session` dict keys exactly; `client.ts` interfaces mirror the schema field names verbatim (all-lowercase-with-underscores fields like `n_known`, `cv_accuracy_mean` are kept as-is in the TypeScript interfaces too, matching how `StatusResponse`/`HistoryRow` already do this — this app's established convention only camelCases *input* parameters a function takes, e.g. `topN` vs the wire param `top_n`, never response field names).
- `explain.py`, `explore.py`, `compare.py`, `validate.py`, and their existing CLI `main()` functions are NOT modified anywhere in this plan — every new backend method only *imports and calls* their already-dataset-agnostic functions. `explore.py` is not imported by any new code in this plan at all.
- No new endpoint blocks session-scoped pages from rendering while it fetches — `ComparePage` is the sole exception, and it's exempt by design (see Task 8), not by omission.
- Every task's `git add` must be scoped to the exact files that task changed — never `git add -A` / `git add .`.
- Per `CLAUDE.md`: before the final task reports done, the dev server must be run and every new/changed page clicked through in a real browser.

---

### Task 1: Backend — Feature Importance

**Files:**
- Modify: `acquireml/session.py`
- Modify: `acquireml/api/schemas.py`
- Modify: `acquireml/api/app.py`
- Test: `tests/test_session.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Produces: `Session.feature_importance(top_n: int = 20) -> dict` returning `{"features": [{"rank", "feature", "importance", "cumulative_importance"}], "cv_accuracy_mean": float | None, "cv_accuracy_std": float | None, "total_features": int, "n_known": int}`. `GET /sessions/{name}/explain?top_n=N` returning `FeatureImportanceResponse`.

- [ ] **Step 1: Write the failing `Session` tests**

Add to `tests/test_session.py`, in a new `# ── feature_importance ──` section after the existing `# ── update_settings ──` section (end of file, following the file's established section-comment convention):

```python
# ── feature_importance ───────────────────────────────────────────────────────

def test_feature_importance_ranks_features(session):
    result = session.feature_importance(top_n=5)

    assert len(result["features"]) == 5
    assert result["total_features"] == 10
    assert result["n_known"] == 20
    # ranks are 1-indexed and strictly increasing
    assert [f["rank"] for f in result["features"]] == [1, 2, 3, 4, 5]
    # importances are sorted descending
    importances = [f["importance"] for f in result["features"]]
    assert importances == sorted(importances, reverse=True)


def test_feature_importance_cumulative_importance_increases(session):
    result = session.feature_importance(top_n=5)

    cumulative = [f["cumulative_importance"] for f in result["features"]]
    assert cumulative == sorted(cumulative)


def test_feature_importance_reports_cv_accuracy_with_enough_data(session):
    result = session.feature_importance(top_n=5)

    # the `session` fixture's 20 labeled samples have enough of both
    # classes for a >=2-fold CV (outcome = f0 | f1, not degenerate)
    assert result["cv_accuracy_mean"] is not None
    assert result["cv_accuracy_std"] is not None
    assert 0.0 <= result["cv_accuracy_mean"] <= 1.0


def test_feature_importance_skips_cv_when_pool_too_small(tmp_path):
    """A known pool with only 1 sample of a class can't support any
    cross-validation split — cv_accuracy_mean/std should be None rather
    than raising."""
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(3)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(5, 6)).astype(int),
        index=[f"s_{i}" for i in range(5)],
        columns=[f"f{j}" for j in range(6)],
    )
    df["outcome"] = [1, 0, 0, 0, 0]  # only 1 positive sample
    p = tmp_path / "tiny.csv"
    df.to_csv(p)

    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(p, label_col="outcome")

    result = sess.feature_importance(top_n=3)

    assert result["cv_accuracy_mean"] is None
    assert result["cv_accuracy_std"] is None
    # feature importances are still computed — only CV is skipped
    assert len(result["features"]) == 3
    sess.close()


def test_feature_importance_caps_top_n_to_total_features(session):
    result = session.feature_importance(top_n=999)

    assert len(result["features"]) == 10  # session fixture has 10 features
    assert result["total_features"] == 10
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k feature_importance -v`
Expected: FAIL — `AttributeError: 'Session' object has no attribute 'feature_importance'` on every test.

- [ ] **Step 3: Add the required imports to `session.py`**

In `acquireml/session.py`, extend the existing `from acquireml.explain import (...)` multi-line import to add `build_estimator`, `extract_importances`, `get_cross_val_score`:

```python
from acquireml.explain import (
    CALIBRATION_METHODS,
    MODEL_CHOICES,
    build_estimator,
    extract_importances,
    get_cross_val_score,
    predict_at_threshold,
    train_full_model,
)
```

- [ ] **Step 4: Implement `Session.feature_importance`**

Add this method to `acquireml/session.py` immediately after `update_settings()` (the last method added in the previous phase), before `def recommend(`:

```python
def feature_importance(self, top_n: int = 20) -> dict:
    """Rank the session's features by predictive importance.

    Trains a fresh Random Forest on the full known pool — independent of
    whichever model the session's own recommend/update cycle is
    configured to use, since feature_importances_ is only exposed by
    RandomForestClassifier among this app's model choices. When the
    known pool has at least 2 samples in every class, also reports a
    cross-validated balanced accuracy (up to 5-fold, fewer if a class
    has fewer than 5 members) as a sanity check — skipped (None) when
    the pool is too small/imbalanced for CV, the same
    graceful-degradation pattern init()'s calibration/threshold tuning
    already uses.
    """
    X, y = self._get_known_Xy()
    min_class_count = int(y.value_counts().min())

    cv_mean, cv_std = None, None
    if min_class_count >= 2:
        cv_mean, cv_std = get_cross_val_score(X, y, n_splits=min(5, min_class_count))

    model = train_full_model(X, y, model_name="rf", tune_threshold=False)
    imp_df = extract_importances(model, list(X.columns), top_n=min(top_n, X.shape[1]))

    return {
        "features": [
            {
                "rank": int(row.rank),
                "feature": str(row.unitig),
                "importance": float(row.importance),
                "cumulative_importance": float(row.cumulative_importance),
            }
            for row in imp_df.itertuples()
        ],
        "cv_accuracy_mean": cv_mean,
        "cv_accuracy_std": cv_std,
        "total_features": int(X.shape[1]),
        "n_known": int(len(X)),
    }
```

- [ ] **Step 5: Run the `Session` tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k feature_importance -v`
Expected: `5 passed`.

- [ ] **Step 6: Add the `FeatureImportanceResponse` schema**

In `acquireml/api/schemas.py`, add after the existing `UpdateSettingsRequest` class (end of file):

```python
class FeatureImportanceRow(BaseModel):
    rank: int
    feature: str
    importance: float
    cumulative_importance: float


class FeatureImportanceResponse(BaseModel):
    features: list[FeatureImportanceRow]
    cv_accuracy_mean: float | None
    cv_accuracy_std: float | None
    total_features: int
    n_known: int
```

- [ ] **Step 7: Write the schema test**

Add to `tests/test_api_schemas.py` (find the existing file's pattern — constructs each schema with sample data, asserts field values):

```python
def test_feature_importance_response_shape():
    body = FeatureImportanceResponse(
        features=[
            FeatureImportanceRow(rank=1, feature="unitig_3", importance=0.42, cumulative_importance=0.42),
        ],
        cv_accuracy_mean=0.91,
        cv_accuracy_std=0.03,
        total_features=500,
        n_known=40,
    )
    assert body.features[0].feature == "unitig_3"
    assert body.cv_accuracy_mean == 0.91


def test_feature_importance_response_allows_null_cv():
    body = FeatureImportanceResponse(
        features=[], cv_accuracy_mean=None, cv_accuracy_std=None,
        total_features=10, n_known=3,
    )
    assert body.cv_accuracy_mean is None
```

Add `FeatureImportanceResponse`, `FeatureImportanceRow` to this file's existing import list from `acquireml.api.schemas`.

- [ ] **Step 8: Add the endpoint**

In `acquireml/api/app.py`, add immediately after the `update_settings` endpoint (the last one added in the previous phase), before `@app.get("/sessions/{name}/export")`:

```python
@app.get("/sessions/{name}/explain", response_model=FeatureImportanceResponse)
def feature_importance(
    top_n: int = 20, sess: Session = Depends(get_session)
) -> FeatureImportanceResponse:
    with sess:
        return FeatureImportanceResponse(**sess.feature_importance(top_n=top_n))
```

Add `FeatureImportanceResponse` to `app.py`'s existing schemas import list.

- [ ] **Step 9: Write the endpoint tests**

Add to `tests/test_api_app.py`, after the last `update_settings` test (reuse the file's existing `_create_session`/`client`/`labeled_csv` fixtures):

```python
def test_explain_returns_ranked_features(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.get("/sessions/azm-project/explain?top_n=5")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["features"]) == 5
    assert body["total_features"] == 10
    assert set(body["features"][0].keys()) == {
        "rank", "feature", "importance", "cumulative_importance",
    }


def test_explain_default_top_n_is_20(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.get("/sessions/azm-project/explain")
    assert resp.status_code == 200
    # the fixture only has 10 features — capped, not padded
    assert len(resp.json()["features"]) == 10


def test_explain_unknown_session_404s(client):
    resp = client.get("/sessions/nope/explain")
    assert resp.status_code == 404
```

- [ ] **Step 10: Run the endpoint tests**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k explain -v`
Expected: `3 passed`.

- [ ] **Step 11: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: `246 passed` (236 + 5 Session tests + 2 schema tests + 3 endpoint tests).

- [ ] **Step 12: Commit**

```bash
git add acquireml/session.py acquireml/api/schemas.py acquireml/api/app.py \
  tests/test_session.py tests/test_api_schemas.py tests/test_api_app.py
git commit -m "Add Session.feature_importance() and GET /sessions/{name}/explain"
```

---

### Task 2: Backend — Session Overview

**Files:**
- Modify: `acquireml/session.py`
- Modify: `acquireml/api/schemas.py`
- Modify: `acquireml/api/app.py`
- Test: `tests/test_session.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Produces: `Session.overview(top_n: int = 15) -> dict` returning `{"n_known", "n_pool", "n_features", "n_positive", "n_negative", "positive_rate", "top_prevalent_features": [{"feature", "prevalence"}]}`. `GET /sessions/{name}/overview?top_n=N` returning `OverviewResponse`.

This is new, session-generic logic — not a wrapper around `explore.py` (which is not imported anywhere in this task; see the design spec's "Scope Correction" section for why).

- [ ] **Step 1: Write the failing `Session` tests**

Add to `tests/test_session.py`, in a new `# ── overview ──` section after `# ── feature_importance ──`:

```python
# ── overview ──────────────────────────────────────────────────────────────────

def test_overview_reports_counts(session):
    result = session.overview()

    assert result["n_known"] == 20
    assert result["n_pool"] == 30
    assert result["n_features"] == 10


def test_overview_class_balance_sums_to_n_known(session):
    result = session.overview()

    assert result["n_positive"] + result["n_negative"] == result["n_known"]
    assert result["positive_rate"] == result["n_positive"] / result["n_known"]


def test_overview_top_prevalent_features_sorted_descending(session):
    result = session.overview(top_n=5)

    assert len(result["top_prevalent_features"]) == 5
    prevalences = [f["prevalence"] for f in result["top_prevalent_features"]]
    assert prevalences == sorted(prevalences, reverse=True)
    for f in result["top_prevalent_features"]:
        assert 0.0 <= f["prevalence"] <= 1.0


def test_overview_caps_top_n_to_total_features(session):
    result = session.overview(top_n=999)

    assert len(result["top_prevalent_features"]) == 10  # fixture has 10 features
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k overview -v`
Expected: FAIL — `AttributeError: 'Session' object has no attribute 'overview'` on every test.

- [ ] **Step 3: Implement `Session.overview`**

Add to `acquireml/session.py`, immediately after `feature_importance()`:

```python
def overview(self, top_n: int = 15) -> dict:
    """Summarize the session's own data: class balance and feature
    prevalence across the known pool. Pure data description — no model
    is trained, safe to compute at any known-pool size."""
    X, y = self._get_known_Xy()
    n_known = len(X)
    n_positive = int(y.sum())
    n_negative = n_known - n_positive

    prevalence = X.mean(axis=0).sort_values(ascending=False)
    top_n_capped = min(top_n, X.shape[1])
    top_features = [
        {"feature": str(name), "prevalence": float(value)}
        for name, value in prevalence.head(top_n_capped).items()
    ]

    return {
        "n_known": n_known,
        "n_pool": len(self._get_pool_X()),
        "n_features": int(X.shape[1]),
        "n_positive": n_positive,
        "n_negative": n_negative,
        "positive_rate": n_positive / n_known if n_known > 0 else None,
        "top_prevalent_features": top_features,
    }
```

- [ ] **Step 4: Run the `Session` tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k overview -v`
Expected: `4 passed`.

- [ ] **Step 5: Add the `OverviewResponse` schema**

In `acquireml/api/schemas.py`, add after `FeatureImportanceResponse`:

```python
class PrevalentFeatureRow(BaseModel):
    feature: str
    prevalence: float


class OverviewResponse(BaseModel):
    n_known: int
    n_pool: int
    n_features: int
    n_positive: int
    n_negative: int
    positive_rate: float | None
    top_prevalent_features: list[PrevalentFeatureRow]
```

- [ ] **Step 6: Write the schema test**

Add to `tests/test_api_schemas.py`:

```python
def test_overview_response_shape():
    body = OverviewResponse(
        n_known=40, n_pool=60, n_features=30,
        n_positive=11, n_negative=29, positive_rate=0.275,
        top_prevalent_features=[PrevalentFeatureRow(feature="unitig_7", prevalence=0.9)],
    )
    assert body.n_known == 40
    assert body.top_prevalent_features[0].prevalence == 0.9
```

Add `OverviewResponse`, `PrevalentFeatureRow` to this file's imports.

- [ ] **Step 7: Add the endpoint**

In `acquireml/api/app.py`, add immediately after the `feature_importance` endpoint from Task 1:

```python
@app.get("/sessions/{name}/overview", response_model=OverviewResponse)
def overview(top_n: int = 15, sess: Session = Depends(get_session)) -> OverviewResponse:
    with sess:
        return OverviewResponse(**sess.overview(top_n=top_n))
```

Add `OverviewResponse` to `app.py`'s schemas import list.

- [ ] **Step 8: Write the endpoint tests**

Add to `tests/test_api_app.py`, after the `test_explain_*` tests:

```python
def test_overview_returns_class_balance_and_prevalence(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.get("/sessions/azm-project/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_known"] == 20
    assert body["n_positive"] + body["n_negative"] == 20
    assert len(body["top_prevalent_features"]) <= 15


def test_overview_unknown_session_404s(client):
    resp = client.get("/sessions/nope/overview")
    assert resp.status_code == 404
```

- [ ] **Step 9: Run the endpoint tests**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k overview -v`
Expected: `2 passed`.

- [ ] **Step 10: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: `253 passed` (246 from Task 1 + 4 Session + 1 schema [`test_overview_response_shape`] + 2 endpoint).

- [ ] **Step 11: Commit**

```bash
git add acquireml/session.py acquireml/api/schemas.py acquireml/api/app.py \
  tests/test_session.py tests/test_api_schemas.py tests/test_api_app.py
git commit -m "Add Session.overview() and GET /sessions/{name}/overview"
```

---

### Task 3: Backend — AL vs Random Comparison

**Files:**
- Modify: `acquireml/session.py`
- Modify: `acquireml/api/schemas.py`
- Modify: `acquireml/api/app.py`
- Test: `tests/test_session.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Produces: `Session.compare_strategies(runs: int = 3) -> dict` returning `{"known_pool_sizes": [int], "al_accuracy": [float], "random_accuracy": [float], "runs": int, "final_gap": float}`. Raises `RuntimeError` when the known pool has fewer than 20 samples. `GET /sessions/{name}/compare?runs=N` returning `CompareResponse`.

This is the compute-heavy endpoint. `session` fixture has exactly 20 known samples — right at the threshold — so it exercises the real auto-scaling formulas, not a comfortably-oversized pool.

- [ ] **Step 1: Write the failing `Session` tests**

Add to `tests/test_session.py`, in a new `# ── compare_strategies ──` section after `# ── overview ──`:

```python
# ── compare_strategies ───────────────────────────────────────────────────────

def test_compare_strategies_returns_matching_length_curves(session):
    """The `session` fixture has exactly 20 known samples — the minimum
    this method accepts — so this also exercises the auto-scaling
    formulas at their lower bound, not just a comfortably large pool."""
    result = session.compare_strategies(runs=2)

    assert len(result["known_pool_sizes"]) == len(result["al_accuracy"])
    assert len(result["known_pool_sizes"]) == len(result["random_accuracy"])
    assert len(result["known_pool_sizes"]) >= 1
    assert result["runs"] == 2


def test_compare_strategies_known_pool_sizes_increase(session):
    result = session.compare_strategies(runs=2)

    sizes = result["known_pool_sizes"]
    assert sizes == sorted(sizes)
    assert sizes[0] < sizes[-1]


def test_compare_strategies_final_gap_matches_last_points(session):
    result = session.compare_strategies(runs=2)

    expected_gap = result["al_accuracy"][-1] - result["random_accuracy"][-1]
    assert result["final_gap"] == pytest.approx(expected_gap, abs=1e-9)


def test_compare_strategies_rejects_small_known_pool(tmp_path, labeled_csv):
    """labeled_csv has 20 samples — trim to 10 to go below the minimum."""
    import pandas as pd
    df = pd.read_csv(labeled_csv, index_col=0).iloc[:10]
    small_csv = tmp_path / "small.csv"
    df.to_csv(small_csv)

    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(small_csv, label_col="outcome")

    with pytest.raises(RuntimeError, match="at least 20 known samples"):
        sess.compare_strategies()
    sess.close()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k compare_strategies -v`
Expected: FAIL — `AttributeError: 'Session' object has no attribute 'compare_strategies'` on every test.

- [ ] **Step 3: Add the required imports to `session.py`**

Add near the top of `acquireml/session.py`, alongside the existing `from acquireml.strategies import ...` line, extend it to also import `RandomSampling`:

```python
from acquireml.strategies import UncertaintySampling, RandomSampling, DiverseSampling, _binary_entropy
```

Add a new import for the engine:

```python
from acquireml.engine import ActiveLearningEngine
```

(Place this new import line after the existing `from acquireml.generic_loader import GenericLoader` line, before the `from acquireml.strategies import ...` line, keeping the file's existing import grouping.)

- [ ] **Step 4: Implement `Session.compare_strategies`**

Add to `acquireml/session.py`, immediately after `overview()`:

```python
def compare_strategies(self, runs: int = 3) -> dict:
    """Hindsight-simulate Active Learning vs Random Sampling over the
    session's own known pool, averaged across `runs` seeds.

    Simulation parameters are auto-scaled from the known pool size —
    this app's CLI defaults (initial_pool=10, batch=25, iterations=15)
    assume a research-scale dataset with thousands of samples; a
    session's known pool is typically far smaller.
    """
    X, y = self._get_known_Xy()
    n_known = len(X)
    if n_known < 20:
        raise RuntimeError(
            f"Need at least 20 known samples to compare strategies "
            f"(have {n_known}). Label more samples first."
        )

    initial_pool = max(5, n_known // 10)
    batch_size = max(2, n_known // 20)
    iterations = min(10, (n_known - initial_pool) // batch_size)

    al_curves, rs_curves = [], []
    al_hist = None
    for run in range(runs):
        al_hist = ActiveLearningEngine(
            X, y, build_estimator("rf"), UncertaintySampling(),
            initial_pool_size=initial_pool, batch_size=batch_size,
            random_state=run,
        ).run(iterations)
        rs_hist = ActiveLearningEngine(
            X, y, build_estimator("rf"), RandomSampling(random_state=run),
            initial_pool_size=initial_pool, batch_size=batch_size,
            random_state=run,
        ).run(iterations)
        al_curves.append([m["balanced_accuracy"] for m in al_hist])
        rs_curves.append([m["balanced_accuracy"] for m in rs_hist])

    sizes = [m["known_pool_size"] for m in al_hist]
    al_mean = np.mean(al_curves, axis=0)
    rs_mean = np.mean(rs_curves, axis=0)

    return {
        "known_pool_sizes": [int(s) for s in sizes],
        "al_accuracy": [float(v) for v in al_mean],
        "random_accuracy": [float(v) for v in rs_mean],
        "runs": runs,
        "final_gap": float(al_mean[-1] - rs_mean[-1]),
    }
```

- [ ] **Step 5: Run the `Session` tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k compare_strategies -v`
Expected: `4 passed`. (This will take a few seconds longer than the plan's other tests — `compare_strategies` genuinely trains multiple models. That's expected, not a hang.)

- [ ] **Step 6: Add the `CompareResponse` schema**

In `acquireml/api/schemas.py`, add after `OverviewResponse`:

```python
class CompareResponse(BaseModel):
    known_pool_sizes: list[int]
    al_accuracy: list[float]
    random_accuracy: list[float]
    runs: int
    final_gap: float
```

- [ ] **Step 7: Write the schema test**

Add to `tests/test_api_schemas.py`:

```python
def test_compare_response_shape():
    body = CompareResponse(
        known_pool_sizes=[5, 7, 9], al_accuracy=[0.6, 0.7, 0.8],
        random_accuracy=[0.55, 0.6, 0.65], runs=3, final_gap=0.15,
    )
    assert body.final_gap == 0.15
    assert len(body.known_pool_sizes) == 3
```

Add `CompareResponse` to this file's imports.

- [ ] **Step 8: Add the endpoint**

In `acquireml/api/app.py`, add immediately after the `overview` endpoint from Task 2:

```python
@app.get("/sessions/{name}/compare", response_model=CompareResponse)
def compare(runs: int = 3, sess: Session = Depends(get_session)) -> CompareResponse:
    with sess:
        return CompareResponse(**sess.compare_strategies(runs=runs))
```

Add `CompareResponse` to `app.py`'s schemas import list.

- [ ] **Step 9: Write the endpoint tests**

Add to `tests/test_api_app.py`, after the `test_overview_*` tests:

```python
def test_compare_returns_two_curves(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.get("/sessions/azm-project/compare?runs=2")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["al_accuracy"]) == len(body["random_accuracy"])
    assert body["runs"] == 2


def test_compare_too_few_known_returns_409(client, tmp_path):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(10, 6)).astype(int),
        index=[f"s_{i}" for i in range(10)],
        columns=[f"f{j}" for j in range(6)],
    )
    df["outcome"] = (df["f0"] | df["f1"]).astype(int)
    small_csv = tmp_path / "small.csv"
    df.to_csv(small_csv)

    with open(small_csv, "rb") as f:
        client.post(
            "/sessions",
            data={"name": "tiny-project", "label_col": "outcome"},
            files={"labeled_file": ("small.csv", f, "text/csv")},
        )

    resp = client.get("/sessions/tiny-project/compare")
    assert resp.status_code == 409


def test_compare_unknown_session_404s(client):
    resp = client.get("/sessions/nope/compare")
    assert resp.status_code == 404
```

- [ ] **Step 10: Run the endpoint tests**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k compare -v`
Expected: `3 passed`.

- [ ] **Step 11: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: `261 passed` (253 from Task 2 + 4 Session + 1 schema [`test_compare_response_shape`] + 3 endpoint). Note this run will take noticeably longer than prior phases' full-suite runs — `compare_strategies` trains many models across its own tests. This is expected.

- [ ] **Step 12: Commit**

```bash
git add acquireml/session.py acquireml/api/schemas.py acquireml/api/app.py \
  tests/test_session.py tests/test_api_schemas.py tests/test_api_app.py
git commit -m "Add Session.compare_strategies() and GET /sessions/{name}/compare"
```

---

### Task 4: Backend — Holdout Validation

**Files:**
- Modify: `acquireml/session.py`
- Modify: `acquireml/api/schemas.py`
- Modify: `acquireml/api/app.py`
- Test: `tests/test_session.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Produces: `Session.validate_holdout(test_size: float = 0.2) -> dict` returning `{"n_train", "n_holdout", "n_holdout_resistant", "n_holdout_sensitive", "balanced_accuracy", "precision", "recall", "f1", "roc_auc": float | None, "tn", "fp", "fn", "tp"}`. Raises `RuntimeError` when the known pool's smaller class has fewer than 4 samples. `GET /sessions/{name}/validate?test_size=X` returning `ValidateResponse`.

- [ ] **Step 1: Write the failing `Session` tests**

Add to `tests/test_session.py`, in a new `# ── validate_holdout ──` section after `# ── compare_strategies ──`:

```python
# ── validate_holdout ─────────────────────────────────────────────────────────

def test_validate_holdout_splits_known_pool(session):
    result = session.validate_holdout(test_size=0.25)

    assert result["n_train"] + result["n_holdout"] == 20
    assert result["n_holdout_resistant"] + result["n_holdout_sensitive"] == result["n_holdout"]


def test_validate_holdout_reports_all_metrics(session):
    result = session.validate_holdout()

    for key in ("balanced_accuracy", "precision", "recall", "f1"):
        assert 0.0 <= result[key] <= 1.0
    assert result["roc_auc"] is None or 0.0 <= result["roc_auc"] <= 1.0


def test_validate_holdout_confusion_counts_sum_to_holdout_size(session):
    result = session.validate_holdout()

    total = result["tn"] + result["fp"] + result["fn"] + result["tp"]
    assert total == result["n_holdout"]


def test_validate_holdout_rejects_small_minority_class(tmp_path):
    """Only 2 positive samples out of 10 — below the 4-sample minimum
    this method requires for a meaningful stratified holdout split."""
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(5)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(10, 6)).astype(int),
        index=[f"s_{i}" for i in range(10)],
        columns=[f"f{j}" for j in range(6)],
    )
    df["outcome"] = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    p = tmp_path / "small.csv"
    df.to_csv(p)

    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(p, label_col="outcome")

    with pytest.raises(RuntimeError, match="at least 4 samples"):
        sess.validate_holdout()
    sess.close()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k validate_holdout -v`
Expected: FAIL — `AttributeError: 'Session' object has no attribute 'validate_holdout'` on every test.

- [ ] **Step 3: Add the required imports to `session.py`**

Add `import math` near the top of `acquireml/session.py` alongside the existing `import json` / `import sqlite3` lines.

Add a new import for the validation function, placed after the existing `from acquireml.explain import (...)` block:

```python
from acquireml.validate import run_validation
```

- [ ] **Step 4: Implement `Session.validate_holdout`**

Add to `acquireml/session.py`, immediately after `compare_strategies()`:

```python
def validate_holdout(self, test_size: float = 0.2) -> dict:
    """Train on a subset of the known pool, evaluate on a held-out slice
    genuinely unseen during training — the same methodology validate.py's
    CLI already uses, applied to the session's own data instead of the
    fixed research dataset."""
    X, y = self._get_known_Xy()
    min_class_count = int(y.value_counts().min())
    if min_class_count < 4:
        raise RuntimeError(
            f"Need at least 4 samples in the smaller class to hold out a "
            f"meaningful test split (have {min_class_count}). Label more "
            f"samples first."
        )

    results = run_validation(X, y, test_size=test_size, random_state=42)
    roc_auc = results["roc_auc"]
    return {
        "n_train": results["n_train"],
        "n_holdout": results["n_holdout"],
        "n_holdout_resistant": results["n_holdout_resistant"],
        "n_holdout_sensitive": results["n_holdout_sensitive"],
        "balanced_accuracy": results["balanced_accuracy"],
        "precision": results["precision"],
        "recall": results["recall"],
        "f1": results["f1"],
        "roc_auc": roc_auc if not math.isnan(roc_auc) else None,
        "tn": results["tn"], "fp": results["fp"],
        "fn": results["fn"], "tp": results["tp"],
    }
```

- [ ] **Step 5: Run the `Session` tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k validate_holdout -v`
Expected: `4 passed`.

- [ ] **Step 6: Add the `ValidateResponse` schema**

In `acquireml/api/schemas.py`, add after `CompareResponse`:

```python
class ValidateResponse(BaseModel):
    n_train: int
    n_holdout: int
    n_holdout_resistant: int
    n_holdout_sensitive: int
    balanced_accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    tn: int
    fp: int
    fn: int
    tp: int
```

- [ ] **Step 7: Write the schema test**

Add to `tests/test_api_schemas.py`:

```python
def test_validate_response_shape():
    body = ValidateResponse(
        n_train=32, n_holdout=8, n_holdout_resistant=3, n_holdout_sensitive=5,
        balanced_accuracy=0.9, precision=0.85, recall=0.95, f1=0.9,
        roc_auc=0.97, tn=5, fp=0, fn=0, tp=3,
    )
    assert body.tp == 3

def test_validate_response_allows_null_roc_auc():
    body = ValidateResponse(
        n_train=32, n_holdout=8, n_holdout_resistant=0, n_holdout_sensitive=8,
        balanced_accuracy=1.0, precision=0.0, recall=0.0, f1=0.0,
        roc_auc=None, tn=8, fp=0, fn=0, tp=0,
    )
    assert body.roc_auc is None
```

Add `ValidateResponse` to this file's imports.

- [ ] **Step 8: Add the endpoint**

In `acquireml/api/app.py`, add immediately after the `compare` endpoint from Task 3:

```python
@app.get("/sessions/{name}/validate", response_model=ValidateResponse)
def validate_holdout(
    test_size: float = 0.2, sess: Session = Depends(get_session)
) -> ValidateResponse:
    with sess:
        return ValidateResponse(**sess.validate_holdout(test_size=test_size))
```

Add `ValidateResponse` to `app.py`'s schemas import list.

- [ ] **Step 9: Write the endpoint tests**

Add to `tests/test_api_app.py`, after the `test_compare_*` tests:

```python
def test_validate_returns_holdout_metrics(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.get("/sessions/azm-project/validate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_train"] + body["n_holdout"] == 20
    assert set(body.keys()) >= {
        "balanced_accuracy", "precision", "recall", "f1", "roc_auc",
        "tn", "fp", "fn", "tp",
    }


def test_validate_small_minority_class_returns_409(client, tmp_path):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(9)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(10, 6)).astype(int),
        index=[f"s_{i}" for i in range(10)],
        columns=[f"f{j}" for j in range(6)],
    )
    df["outcome"] = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    small_csv = tmp_path / "small.csv"
    df.to_csv(small_csv)

    with open(small_csv, "rb") as f:
        client.post(
            "/sessions",
            data={"name": "tiny-project", "label_col": "outcome"},
            files={"labeled_file": ("small.csv", f, "text/csv")},
        )

    resp = client.get("/sessions/tiny-project/validate")
    assert resp.status_code == 409


def test_validate_unknown_session_404s(client):
    resp = client.get("/sessions/nope/validate")
    assert resp.status_code == 404
```

- [ ] **Step 10: Run the endpoint tests**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k validate -v`

Expected: `3 passed`. **Careful with this `-k` filter** — `validate` as a substring also matches any pre-existing test with "validate" in its name from earlier phases if one exists; if the reported count is higher than 3, read the test names in the output and confirm the extra matches are pre-existing tests unrelated to this task, not a sign something's wrong.

- [ ] **Step 11: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: `270 passed` (261 from Task 3 + 4 Session + 2 schema + 3 endpoint). **Verify the actual reported number** rather than trusting this arithmetic; if it differs from 270, recount the `it`/`def test_` blocks this task actually added across both test files before treating it as a problem.

- [ ] **Step 12: Commit**

```bash
git add acquireml/session.py acquireml/api/schemas.py acquireml/api/app.py \
  tests/test_session.py tests/test_api_schemas.py tests/test_api_app.py
git commit -m "Add Session.validate_holdout() and GET /sessions/{name}/validate"
```

---

### Task 5: Frontend — API client additions

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: the four endpoints from Tasks 1-4.
- Produces: `getFeatureImportance(name, topN?)`, `getOverview(name, topN?)`, `getComparison(name, runs?)`, `getValidation(name, testSize?)`, and their four response interfaces — Tasks 6-9's pages import these directly from `client.ts`.

- [ ] **Step 1: Add the four response interfaces**

In `frontend/src/api/client.ts`, add after the existing `UpdateSettingsInput` interface (the last interface currently in the file):

```typescript
export interface FeatureImportanceRow {
  rank: number;
  feature: string;
  importance: number;
  cumulative_importance: number;
}

export interface FeatureImportanceResponse {
  features: FeatureImportanceRow[];
  cv_accuracy_mean: number | null;
  cv_accuracy_std: number | null;
  total_features: number;
  n_known: number;
}

export interface PrevalentFeatureRow {
  feature: string;
  prevalence: number;
}

export interface OverviewResponse {
  n_known: number;
  n_pool: number;
  n_features: number;
  n_positive: number;
  n_negative: number;
  positive_rate: number | null;
  top_prevalent_features: PrevalentFeatureRow[];
}

export interface CompareResponse {
  known_pool_sizes: number[];
  al_accuracy: number[];
  random_accuracy: number[];
  runs: number;
  final_gap: number;
}

export interface ValidateResponse {
  n_train: number;
  n_holdout: number;
  n_holdout_resistant: number;
  n_holdout_sensitive: number;
  balanced_accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number | null;
  tn: number;
  fp: number;
  fn: number;
  tp: number;
}
```

- [ ] **Step 2: Add the four functions**

Add at the end of `frontend/src/api/client.ts`, after `deleteSession` (the last function currently in the file), following `getRecommendations`'s exact optional-query-param pattern (`URL` + `searchParams.set`):

```typescript
export async function getFeatureImportance(
  name: string,
  topN?: number
): Promise<FeatureImportanceResponse> {
  const url = new URL(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/explain`);
  if (topN !== undefined) {
    url.searchParams.set("top_n", String(topN));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getOverview(name: string, topN?: number): Promise<OverviewResponse> {
  const url = new URL(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/overview`);
  if (topN !== undefined) {
    url.searchParams.set("top_n", String(topN));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getComparison(name: string, runs?: number): Promise<CompareResponse> {
  const url = new URL(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/compare`);
  if (runs !== undefined) {
    url.searchParams.set("runs", String(runs));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getValidation(
  name: string,
  testSize?: number
): Promise<ValidateResponse> {
  const url = new URL(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/validate`);
  if (testSize !== undefined) {
    url.searchParams.set("test_size", String(testSize));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}
```

- [ ] **Step 3: Write the tests**

Find `frontend/src/api/client.test.ts` and follow its existing `vi.stubGlobal("fetch", ...)` / `vi.unstubAllGlobals()` pattern exactly (established in an earlier phase specifically because the alternate `global.fetch = ...` syntax doesn't typecheck in this project). Add:

```typescript
describe("getFeatureImportance", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches without a query param when topN is omitted", async () => {
    const mockResponse = { features: [], cv_accuracy_mean: null, cv_accuracy_std: null, total_features: 10, n_known: 20 };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => mockResponse }));

    const result = await getFeatureImportance("proj");

    expect(global.fetch).toHaveBeenCalledWith(new URL(`${API_BASE_URL}/sessions/proj/explain`));
    expect(result).toEqual(mockResponse);
  });

  it("includes top_n when provided", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ features: [], cv_accuracy_mean: null, cv_accuracy_std: null, total_features: 10, n_known: 20 }),
    }));

    await getFeatureImportance("proj", 5);

    const calledUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as URL;
    expect(calledUrl.searchParams.get("top_n")).toBe("5");
  });
});

describe("getOverview", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed response", async () => {
    const mockResponse = { n_known: 20, n_pool: 30, n_features: 10, n_positive: 5, n_negative: 15, positive_rate: 0.25, top_prevalent_features: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => mockResponse }));

    const result = await getOverview("proj");

    expect(result).toEqual(mockResponse);
  });
});

describe("getComparison", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("includes runs when provided", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ known_pool_sizes: [], al_accuracy: [], random_accuracy: [], runs: 5, final_gap: 0 }),
    }));

    await getComparison("proj", 5);

    const calledUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as URL;
    expect(calledUrl.searchParams.get("runs")).toBe("5");
  });

  it("throws with the parsed error detail on a 409", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Need at least 20 known samples to compare strategies (have 10)." }),
    }));

    await expect(getComparison("proj")).rejects.toThrow("Need at least 20 known samples");
  });
});

describe("getValidation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("includes test_size when provided", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        n_train: 16, n_holdout: 4, n_holdout_resistant: 1, n_holdout_sensitive: 3,
        balanced_accuracy: 0.9, precision: 0.8, recall: 1, f1: 0.89, roc_auc: 0.95,
        tn: 3, fp: 0, fn: 0, tp: 1,
      }),
    }));

    await getValidation("proj", 0.3);

    const calledUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as URL;
    expect(calledUrl.searchParams.get("test_size")).toBe("0.3");
  });
});
```

Add `getFeatureImportance`, `getOverview`, `getComparison`, `getValidation` to this test file's existing import line from `./client`.

- [ ] **Step 4: Run the new tests**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: all tests pass, including the 6 new ones above.

- [ ] **Step 5: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `94 passed (94)` (88 + 6 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "Add getFeatureImportance, getOverview, getComparison, getValidation to the API client"
```

---

### Task 6: Frontend — `OverviewPage`

**Files:**
- Create: `frontend/src/pages/OverviewPage.tsx`
- Create: `frontend/src/pages/OverviewPage.module.css`
- Create: `frontend/src/pages/OverviewPage.test.tsx`
- Modify: `frontend/src/components/SessionLayout.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getOverview` from `client.ts` (Task 5).

- [ ] **Step 1: Write `OverviewPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getOverview, type OverviewResponse } from "../api/client";
import styles from "./OverviewPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: OverviewResponse };

export default function OverviewPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getOverview(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;
  const maxPrevalence = Math.max(...data.top_prevalent_features.map((f) => f.prevalence), 0.0001);

  return (
    <div>
      <h2>Session overview</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_known}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_pool}</div>
          <div className={styles.statLabel}>Pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_features}</div>
          <div className={styles.statLabel}>Features</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.positive_rate !== null ? `${(data.positive_rate * 100).toFixed(1)}%` : "—"}
          </div>
          <div className={styles.statLabel}>
            Positive ({data.n_positive} / {data.n_positive + data.n_negative})
          </div>
        </div>
      </div>

      {data.top_prevalent_features.length > 0 && (
        <div className={styles.barCard}>
          <h4>Most prevalent features</h4>
          <ul className={styles.barList}>
            {data.top_prevalent_features.map((f) => (
              <li key={f.feature} className={styles.barRow}>
                <span className={styles.barLabel}>{f.feature}</span>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(f.prevalence / maxPrevalence) * 100}%` }}
                  />
                </div>
                <span className={styles.barValue}>{(f.prevalence * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `OverviewPage.module.css`**

Reuse the exact `.statRow`/`.stat`/`.statValue`/`.statLabel` values already established in `BudgetPage.module.css` (read that file first — this task's `.statRow` etc. should be visually identical, same tokens/sizes, not a divergent re-invention):

```css
.loading,
.error {
  font-family: var(--font-mono);
  color: var(--ink-soft);
}

.error {
  color: var(--red-data);
}

.statRow {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1.5rem;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0.9rem 1.1rem;
  border-radius: 8px;
  background: var(--paper-raised);
  border: 1px solid var(--line);
}

.statValue {
  font-family: var(--font-body);
  font-weight: 800;
  font-size: 1.5rem;
  color: var(--ink);
}

.statLabel {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
  margin-top: 0.2rem;
}

.barCard {
  border-radius: 8px;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  padding: 1rem 1.2rem;
}

.barCard h4 {
  margin: 0 0 0.9rem;
  font-family: var(--font-body);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--ink-soft);
}

.barList {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.barRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 3fr) 3.5ch;
  align-items: center;
  gap: 0.7rem;
}

.barLabel {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.barTrack {
  height: 8px;
  border-radius: 4px;
  background: var(--paper);
  overflow: hidden;
}

.barFill {
  height: 100%;
  background: linear-gradient(90deg, var(--brass), var(--accent));
  border-radius: 4px;
}

.barValue {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--ink-faint);
  text-align: right;
}
```

- [ ] **Step 3: Write `OverviewPage.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import OverviewPage from "./OverviewPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/overview`]}>
      <Routes>
        <Route path="/sessions/:name/overview" element={<OverviewPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("OverviewPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows class balance and feature counts once loaded", async () => {
    vi.spyOn(client, "getOverview").mockResolvedValue({
      n_known: 40, n_pool: 60, n_features: 30, n_positive: 11, n_negative: 29,
      positive_rate: 0.275, top_prevalent_features: [],
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("40")).toBeInTheDocument();
    });
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("27.5%")).toBeInTheDocument();
  });

  it("renders a bar per prevalent feature", async () => {
    vi.spyOn(client, "getOverview").mockResolvedValue({
      n_known: 40, n_pool: 60, n_features: 30, n_positive: 11, n_negative: 29,
      positive_rate: 0.275,
      top_prevalent_features: [
        { feature: "unitig_3", prevalence: 0.9 },
        { feature: "unitig_7", prevalence: 0.4 },
      ],
    });

    renderAtSession("azm-project");

    expect(await screen.findByText("unitig_3")).toBeInTheDocument();
    expect(screen.getByText("unitig_7")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getOverview").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the `OverviewPage` tests**

Run: `cd frontend && npx vitest run src/pages/OverviewPage.test.tsx`
Expected: `3 passed`.

- [ ] **Step 5: Add the nav link to `SessionLayout.tsx`**

In `frontend/src/components/SessionLayout.tsx`, add a new unconditional `NavLink` immediately after the `History` link and before `Settings`:

```tsx
          <NavLink
            to={`/sessions/${name}/overview`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Overview
          </NavLink>
```

- [ ] **Step 6: Wire the route into `App.tsx`**

Add `import OverviewPage from "./pages/OverviewPage";` and, inside the `/sessions/:name` route's children, add `<Route path="overview" element={<OverviewPage />} />` after the `history` route and before `settings`.

- [ ] **Step 7: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `97 passed (97)` (94 from Task 5 + 3 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Manually verify in the browser**

`npm run dev` from `frontend/` + `make api` from the repo root, both in the background. Open a session with real known data, click "Overview" in the nav, confirm the four stat cards render and the prevalent-features bar list shows proportional bars (the longest bar should belong to the feature with the highest percentage shown). Stop both servers when done.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/OverviewPage.tsx frontend/src/pages/OverviewPage.module.css \
  frontend/src/pages/OverviewPage.test.tsx frontend/src/components/SessionLayout.tsx frontend/src/App.tsx
git commit -m "Add OverviewPage: class balance and feature prevalence"
```

---

### Task 7: Frontend — `ExplainPage`

**Files:**
- Create: `frontend/src/pages/ExplainPage.tsx`
- Create: `frontend/src/pages/ExplainPage.module.css`
- Create: `frontend/src/pages/ExplainPage.test.tsx`
- Modify: `frontend/src/components/SessionLayout.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getFeatureImportance` from `client.ts` (Task 5).

- [ ] **Step 1: Write `ExplainPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getFeatureImportance, type FeatureImportanceResponse } from "../api/client";
import styles from "./ExplainPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: FeatureImportanceResponse };

export default function ExplainPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getFeatureImportance(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;
  const maxImportance = Math.max(...data.features.map((f) => f.importance), 0.0001);

  return (
    <div>
      <h2>Feature importance</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.cv_accuracy_mean !== null
              ? `${(data.cv_accuracy_mean * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div className={styles.statLabel}>
            Cross-validated accuracy
            {data.cv_accuracy_std !== null && ` (± ${(data.cv_accuracy_std * 100).toFixed(1)}pp)`}
          </div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.total_features}</div>
          <div className={styles.statLabel}>Total features</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_known}</div>
          <div className={styles.statLabel}>Trained on</div>
        </div>
      </div>

      {data.features.length === 0 ? (
        <p className={styles.empty}>Not enough known samples yet to rank features.</p>
      ) : (
        <div className={styles.barCard}>
          <h4>Top predictive features</h4>
          <ul className={styles.barList}>
            {data.features.map((f) => (
              <li key={f.feature} className={styles.barRow}>
                <span className={styles.barRank}>#{f.rank}</span>
                <span className={styles.barLabel}>{f.feature}</span>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(f.importance / maxImportance) * 100}%` }}
                  />
                </div>
                <span className={styles.barValue}>{f.importance.toFixed(4)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ExplainPage.module.css`**

Same `.statRow`/`.stat`/`.statValue`/`.statLabel`/`.barCard`/`.barList`/`.barRow`/`.barTrack`/`.barFill`/`.barValue`/`.loading`/`.error` rules as `OverviewPage.module.css` (Task 6), plus `.empty` (matching the `.empty { font-family: var(--font-mono); color: var(--ink-soft); }` rule already used by `DashboardPage.module.css`/`BudgetPage.module.css`) and a `.barRank` rule:

```css
.barRank {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--ink-faint);
  width: 2.5ch;
}
```

Adjust `.barRow`'s `grid-template-columns` to account for the extra rank column: `2.5ch minmax(0, 1fr) minmax(0, 3fr) 6ch` (feature names here can be long unitig sequences, so give the value column a bit more room than `OverviewPage`'s percentage column needed).

- [ ] **Step 3: Write `ExplainPage.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import ExplainPage from "./ExplainPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/explain`]}>
      <Routes>
        <Route path="/sessions/:name/explain" element={<ExplainPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ExplainPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows cv accuracy and ranked features once loaded", async () => {
    vi.spyOn(client, "getFeatureImportance").mockResolvedValue({
      features: [
        { rank: 1, feature: "unitig_9", importance: 0.21, cumulative_importance: 0.21 },
      ],
      cv_accuracy_mean: 0.93, cv_accuracy_std: 0.02, total_features: 500, n_known: 40,
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("93.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("unitig_9")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
  });

  it("shows an em dash for cv accuracy when it's null", async () => {
    vi.spyOn(client, "getFeatureImportance").mockResolvedValue({
      features: [{ rank: 1, feature: "unitig_1", importance: 0.5, cumulative_importance: 0.5 }],
      cv_accuracy_mean: null, cv_accuracy_std: null, total_features: 6, n_known: 5,
    });

    renderAtSession("azm-project");

    expect(await screen.findByText("—")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getFeatureImportance").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the `ExplainPage` tests**

Run: `cd frontend && npx vitest run src/pages/ExplainPage.test.tsx`
Expected: `3 passed`.

- [ ] **Step 5: Add the nav link to `SessionLayout.tsx`**

Add a new unconditional `NavLink` immediately after the `Overview` link (added in Task 6) and before `Settings`:

```tsx
          <NavLink
            to={`/sessions/${name}/explain`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Explain
          </NavLink>
```

- [ ] **Step 6: Wire the route into `App.tsx`**

Add `import ExplainPage from "./pages/ExplainPage";` and `<Route path="explain" element={<ExplainPage />} />` after the `overview` route and before `settings`.

- [ ] **Step 7: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `100 passed (100)` (97 from Task 6 + 3 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Manually verify in the browser**

`npm run dev` + `make api`. Click "Explain" in the nav, confirm the cross-validated accuracy stat and the ranked feature bars render, with the #1-ranked feature's bar visibly the longest. Stop both servers when done.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/ExplainPage.tsx frontend/src/pages/ExplainPage.module.css \
  frontend/src/pages/ExplainPage.test.tsx frontend/src/components/SessionLayout.tsx frontend/src/App.tsx
git commit -m "Add ExplainPage: feature importance ranking"
```

---

### Task 8: Frontend — `ComparePage`

**Files:**
- Create: `frontend/src/pages/ComparePage.tsx`
- Create: `frontend/src/pages/ComparePage.module.css`
- Create: `frontend/src/pages/ComparePage.test.tsx`
- Modify: `frontend/src/components/SessionLayout.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getComparison` from `client.ts` (Task 5).

**This is the one page in the app that does NOT fetch on mount.** Every other page (including the three built in Tasks 6-7) fetches its data in a `useEffect` on load, matching this app's established pattern since Phase 1. `ComparePage` is a deliberate, spec-mandated exception: its endpoint is the most compute-heavy in the app (it trains many models per request), so auto-fetching on every visit would silently cost several seconds of server time each time a researcher merely navigates here. Data only loads when the "Run comparison" button is clicked.

- [ ] **Step 1: Write `ComparePage.tsx`**

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getComparison, type CompareResponse } from "../api/client";
import styles from "./ComparePage.module.css";

type RunState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: CompareResponse };

interface ComparePoint {
  size: number;
  al: number;
  random: number;
}

function toChartData(data: CompareResponse): ComparePoint[] {
  return data.known_pool_sizes.map((size, i) => ({
    size,
    al: data.al_accuracy[i] * 100,
    random: data.random_accuracy[i] * 100,
  }));
}

export default function ComparePage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<RunState>({ status: "idle" });

  async function handleRun() {
    if (!name) return;
    setState({ status: "loading" });
    try {
      const data = await getComparison(name);
      setState({ status: "loaded", data });
    } catch (err) {
      setState({ status: "error", message: (err as Error).message });
    }
  }

  return (
    <div>
      <h2>Active learning vs. random sampling</h2>
      <p className={styles.intro}>
        Simulates both strategies on this session's own known data to show how much
        faster active learning reaches a given accuracy compared to random sampling.
        This trains several models and can take a few seconds.
      </p>

      <button type="button" onClick={handleRun} disabled={state.status === "loading"} className={styles.runButton}>
        {state.status === "loading" ? "Running…" : "Run comparison"}
      </button>

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && (
        <>
          <div className={styles.chartCard}>
            <span className="bracket bracket-tl" />
            <span className="bracket bracket-tr" />
            <span className="bracket bracket-bl" />
            <span className="bracket bracket-br" />
            <div className={styles.chartHead}>
              <h4>Accuracy vs. known pool size</h4>
              <div className={styles.chartLegend}>
                <span className={styles.legendActual}>● active learning</span>
                <span className={styles.legendProjected}>┄ random</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={toChartData(state.data)} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="size"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  stroke="var(--ink-faint)"
                  tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
                  label={{
                    value: "Known pool size",
                    position: "insideBottom",
                    offset: -6,
                    fill: "var(--ink-faint)",
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="var(--ink-faint)"
                  tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
                  tickFormatter={(v: number) => `${Math.round(v)}%`}
                  label={{
                    value: "Accuracy",
                    angle: -90,
                    position: "insideLeft",
                    fill: "var(--ink-faint)",
                  }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--paper)",
                    border: "1px solid var(--accent)",
                    borderRadius: 6,
                  }}
                  labelStyle={{ color: "var(--ink)" }}
                  labelFormatter={(v: number) => `${v} known`}
                  formatter={(value: number, dataKey: string) => [
                    `${value.toFixed(1)}%`,
                    dataKey === "al" ? "Active learning" : "Random",
                  ]}
                />
                <Line type="monotone" dataKey="al" stroke="var(--accent)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--accent)" }} name="al" />
                <Line type="monotone" dataKey="random" stroke="var(--brass)" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3, fill: "var(--brass)" }} name="random" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className={styles.summary}>
            Active learning reached{" "}
            <strong className={styles.summaryValue}>
              {Math.abs(state.data.final_gap * 100).toFixed(1)} percentage points
            </strong>{" "}
            {state.data.final_gap >= 0 ? "higher" : "lower"} accuracy than random sampling at
            the same number of experiments, averaged over {state.data.runs} run
            {state.data.runs === 1 ? "" : "s"}.
          </p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ComparePage.module.css`**

Reuse the exact `.chartCard`/`.chartHead`/`.chartLegend`/`.legendActual`/`.legendProjected` rules already established in `BudgetPage.module.css` (read that file first — copy the values, this is the same visual pattern applied to a second chart, not a new one), plus:

```css
.intro {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--ink-soft);
  max-width: 640px;
  margin-bottom: 1.2rem;
}

.error {
  font-family: var(--font-mono);
  color: var(--red-data);
  margin-top: 0.8rem;
}

.runButton {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--paper);
  background: var(--accent-deep);
  border: none;
  padding: 0.75rem 1.4rem;
  border-radius: 3px;
  cursor: pointer;
  margin-bottom: 1.5rem;
}

.runButton:hover:not(:disabled) {
  background: var(--accent);
}

.runButton:disabled {
  opacity: 0.6;
  cursor: default;
}

.summary {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--ink);
  margin-top: 1rem;
}

.summaryValue {
  color: var(--accent);
  font-size: 1rem;
}
```

- [ ] **Step 3: Write `ComparePage.test.tsx`**

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import ComparePage from "./ComparePage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/compare`]}>
      <Routes>
        <Route path="/sessions/:name/compare" element={<ComparePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ComparePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch on mount", () => {
    const spy = vi.spyOn(client, "getComparison");

    renderAtSession("azm-project");

    expect(spy).not.toHaveBeenCalled();
  });

  it("fetches exactly once when the run button is clicked", async () => {
    const spy = vi.spyOn(client, "getComparison").mockResolvedValue({
      known_pool_sizes: [5, 7, 9],
      al_accuracy: [0.6, 0.75, 0.85],
      random_accuracy: [0.55, 0.6, 0.65],
      runs: 3,
      final_gap: 0.2,
    });

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledTimes(1);
    });
    expect(spy).toHaveBeenCalledWith("azm-project");
  });

  it("shows the final gap in plain language once loaded", async () => {
    vi.spyOn(client, "getComparison").mockResolvedValue({
      known_pool_sizes: [5, 7, 9],
      al_accuracy: [0.6, 0.75, 0.85],
      random_accuracy: [0.55, 0.6, 0.65],
      runs: 3,
      final_gap: 0.2,
    });

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    expect(await screen.findByText(/20\.0 percentage points/i)).toBeInTheDocument();
    expect(screen.getByText(/higher/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getComparison").mockRejectedValue(
      new Error("Need at least 20 known samples to compare strategies (have 10).")
    );

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    expect(await screen.findByText(/at least 20 known samples/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the `ComparePage` tests**

Run: `cd frontend && npx vitest run src/pages/ComparePage.test.tsx`
Expected: `4 passed`.

- [ ] **Step 5: Add the nav link to `SessionLayout.tsx`**

Add a new unconditional `NavLink` immediately after the `Explain` link (added in Task 7) and before `Settings`:

```tsx
          <NavLink
            to={`/sessions/${name}/compare`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Compare
          </NavLink>
```

- [ ] **Step 6: Wire the route into `App.tsx`**

Add `import ComparePage from "./pages/ComparePage";` and `<Route path="compare" element={<ComparePage />} />` after the `explain` route and before `settings`.

- [ ] **Step 7: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `104 passed (104)` (100 from Task 7 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Manually verify in the browser**

`npm run dev` + `make api`. Click "Compare" in the nav — confirm nothing loads automatically and only the intro text + button are visible. Click "Run comparison," confirm a brief loading state, then the chart and plain-language summary render. If the session you're testing on has fewer than 20 known samples, confirm the error message renders clearly instead of a raw stack trace. Stop both servers when done.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/ComparePage.tsx frontend/src/pages/ComparePage.module.css \
  frontend/src/pages/ComparePage.test.tsx frontend/src/components/SessionLayout.tsx frontend/src/App.tsx
git commit -m "Add ComparePage: button-triggered AL vs random simulation"
```

---

### Task 9: Frontend — `ValidatePage`

**Files:**
- Create: `frontend/src/pages/ValidatePage.tsx`
- Create: `frontend/src/pages/ValidatePage.module.css`
- Create: `frontend/src/pages/ValidatePage.test.tsx`
- Modify: `frontend/src/components/SessionLayout.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getValidation` from `client.ts` (Task 5).

- [ ] **Step 1: Write `ValidatePage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getValidation, type ValidateResponse } from "../api/client";
import styles from "./ValidatePage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: ValidateResponse };

export default function ValidatePage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getValidation(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;

  return (
    <div>
      <h2>Holdout validation</h2>
      <p className={styles.intro}>
        Trained on {data.n_train} known samples, evaluated on {data.n_holdout} held-out
        samples the model never saw during training.
      </p>

      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.balanced_accuracy * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Balanced accuracy</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.precision * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Precision</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.recall * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Recall</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.f1 * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>F1</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.roc_auc !== null ? data.roc_auc.toFixed(3) : "—"}
          </div>
          <div className={styles.statLabel}>ROC-AUC</div>
        </div>
      </div>

      <div className={styles.matrixCard}>
        <h4>Confusion matrix</h4>
        <div className={styles.matrixGrid}>
          <div className={styles.matrixCell}>
            <div className={styles.matrixCount}>{data.tn}</div>
            <div className={styles.matrixLabel}>Correctly cleared sensitive strains</div>
          </div>
          <div className={`${styles.matrixCell} ${styles.matrixMiss}`}>
            <div className={styles.matrixCount}>{data.fp}</div>
            <div className={styles.matrixLabel}>False alarms (false positives)</div>
          </div>
          <div className={`${styles.matrixCell} ${styles.matrixMiss}`}>
            <div className={styles.matrixCount}>{data.fn}</div>
            <div className={styles.matrixLabel}>Missed resistant strains (false negatives)</div>
          </div>
          <div className={styles.matrixCell}>
            <div className={styles.matrixCount}>{data.tp}</div>
            <div className={styles.matrixLabel}>Correctly caught resistant strains</div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `ValidatePage.module.css`**

Same `.loading`/`.error`/`.statRow`/`.stat`/`.statValue`/`.statLabel` rules already established (copy from `BudgetPage.module.css`, same values), plus `.intro` (copy from `ComparePage.module.css`, Task 8, same values) and a new confusion-matrix grid:

```css
.matrixCard {
  border-radius: 8px;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  padding: 1rem 1.2rem;
}

.matrixCard h4 {
  margin: 0 0 0.9rem;
  font-family: var(--font-body);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--ink-soft);
}

.matrixGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
}

.matrixCell {
  padding: 0.9rem 1rem;
  border-radius: 6px;
  background: var(--paper);
  border: 1px solid var(--line);
}

.matrixMiss {
  border-color: var(--red-data);
}

.matrixCount {
  font-family: var(--font-body);
  font-weight: 800;
  font-size: 1.6rem;
  color: var(--ink);
}

.matrixLabel {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--ink-faint);
  margin-top: 0.3rem;
}
```

- [ ] **Step 3: Write `ValidatePage.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import ValidatePage from "./ValidatePage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/validate`]}>
      <Routes>
        <Route path="/sessions/:name/validate" element={<ValidatePage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleResult = {
  n_train: 32, n_holdout: 8, n_holdout_resistant: 3, n_holdout_sensitive: 5,
  balanced_accuracy: 0.9, precision: 0.85, recall: 0.95, f1: 0.9,
  roc_auc: 0.97, tn: 5, fp: 0, fn: 0, tp: 3,
};

describe("ValidatePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the five headline metrics once loaded", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue(sampleResult);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("90.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("85.0%")).toBeInTheDocument();
    expect(screen.getByText("95.0%")).toBeInTheDocument();
    expect(screen.getByText("0.970")).toBeInTheDocument();
  });

  it("shows an em dash for roc-auc when it's null", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue({ ...sampleResult, roc_auc: null });

    renderAtSession("azm-project");

    expect(await screen.findByText("—")).toBeInTheDocument();
  });

  it("shows all four confusion matrix cells", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue(sampleResult);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText(/correctly caught resistant/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/correctly cleared sensitive/i)).toBeInTheDocument();
    expect(screen.getByText(/false alarms/i)).toBeInTheDocument();
    expect(screen.getByText(/missed resistant/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getValidation").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the `ValidatePage` tests**

Run: `cd frontend && npx vitest run src/pages/ValidatePage.test.tsx`
Expected: `4 passed`.

- [ ] **Step 5: Add the nav link to `SessionLayout.tsx`**

Add a new unconditional `NavLink` immediately after the `Compare` link (added in Task 8) and before `Settings`:

```tsx
          <NavLink
            to={`/sessions/${name}/validate`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Validate
          </NavLink>
```

- [ ] **Step 6: Wire the route into `App.tsx`**

Add `import ValidatePage from "./pages/ValidatePage";` and `<Route path="validate" element={<ValidatePage />} />` after the `compare` route and before `settings`.

- [ ] **Step 7: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `108 passed (108)` (104 from Task 8 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Manually verify in the browser**

`npm run dev` + `make api`. Click "Validate" in the nav, confirm the five metric cards render and the confusion matrix shows four cells with the same plain-language labels `validate.py`'s CLI report already uses. Stop both servers when done.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/ValidatePage.tsx frontend/src/pages/ValidatePage.module.css \
  frontend/src/pages/ValidatePage.test.tsx frontend/src/components/SessionLayout.tsx frontend/src/App.tsx
git commit -m "Add ValidatePage: holdout validation metrics and confusion matrix"
```

---

### Task 10: Full regression pass, browser walkthrough, docs

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run the full frontend suite**

Run: `cd frontend && npm test -- --run`
Expected: passes cleanly. Record the exact total reported — this is the real number to use in Step 5's docs update, not any number estimated earlier in this plan.

- [ ] **Step 2: Run the typecheck and production build**

Run: `cd frontend && npm run build`
Expected: succeeds.

- [ ] **Step 3: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q` (from repo root)
Expected: passes cleanly (per Task 4's Step 11, should be 270 — confirm this is still accurate, since no backend work happens after Task 4). This run will take noticeably longer than a typical full-suite run in this project, since `compare_strategies`'s tests genuinely train many models — that's expected, not a hang.

- [ ] **Step 4: Full browser walkthrough of everything this plan added**

`npm run dev` + `make api`. Using a real or `acquireml demo --init` session with a reasonably-sized known pool (at least 20 known samples, ideally more, so `ComparePage`'s minimum-data path isn't the only one exercised):
- Overview: confirm the four stat cards and prevalence bar list render sensibly.
- Explain: confirm the CV-accuracy stat and ranked feature bars render.
- Compare: confirm it does NOT auto-load, click "Run comparison," confirm the chart and plain-language summary render after a brief wait.
- Validate: confirm the five metric cards and confusion matrix render.
- Also test at least one insufficient-data path for real (not just via mocked tests) — either find/create a session with fewer than 20 known samples and confirm Compare shows a clear error, or fewer than 4 in the minority class and confirm Validate shows a clear error.
- Spot-check that nothing from Phases 1-4 regressed: Dashboard, Recommendations (full create→recommend→submit→dashboard-update lifecycle), History + CSV export, Settings (edit + reset/delete confirm-then-cancel), the sortable session list, Budget's chart and projection, and the Cmd+K command palette (confirm it still opens/filters/navigates, and that it does NOT need to know about the four new pages — the design spec didn't add them to the palette's static command list, so confirm this was correctly left alone rather than half-wired).

Stop both servers when done.

- [ ] **Step 5: Update `CLAUDE.md`**

Find the existing "**Web UI frontend**" paragraph and extend it (don't replace its existing content) with what this phase added: the four new pages (Overview, Explain, Compare, Validate), noting `ComparePage` is the one page that doesn't fetch on mount. Update the frontend test count to the real number recorded in Step 1. Find the "**Web UI backend**" paragraph and add a sentence noting the four new analysis endpoints and that they reuse `explain.py`/`validate.py`'s dataset-agnostic functions plus `ActiveLearningEngine` directly (not `explore.py` — note briefly why, referencing the scope correction, so a future reader doesn't wonder why "dataset overview" isn't a literal `explore.py` wrapper). Update the backend test count (236 → 270, or whatever Step 3's actual number was) everywhere it appears in `CLAUDE.md`. Also update the **Feature Roadmap** section (or **Current Status & What's Next**, whichever currently references "Phase 5-6" or "analysis endpoints" as future work) to mark this phase complete, matching how prior phases' completion was recorded there.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "Document Phase 5+6 (overview, explain, compare, validate pages) in CLAUDE.md"
```
