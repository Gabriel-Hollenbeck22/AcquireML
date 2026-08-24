# Web UI — Analysis Pages (Feature Importance, Overview, AL vs Random, Validation) — Design

## Purpose

Phase 5+6 of the web UI, combined into one deliverable (same reasoning Phase 4
used for bundling Settings/Portfolio/Budget/Palette: closely related,
reviewable as one branch). Surfaces four analysis capabilities that
currently exist only as CLI commands producing static PNGs
(`make explain`, `make explore`, `make compare`, `make validate`) as
interactive web UI pages, scoped to a session's own data — consistent with
how the rest of the web UI treats "a session" as the unit of everything
(no antibiotic-specific concept exists anywhere in the web UI today).

## Scope Correction: Dataset Overview

The original phase-5/6 framing (see `CLAUDE.md`'s roadmap notes) assumed
each of the four CLI modules would translate directly into a session-scoped
endpoint. Investigation before writing this spec found that's true for
three of them — `explain.py`, `compare.py`, `validate.py` all have a
dataset-agnostic core (they take `X`/`y` directly) — but **not** for
`explore.py`: it hardcodes the original research dataset's specific
`metadata.csv` schema (`azm_sr`/`cip_sr`/`cfx_sr` columns, `Year`,
`Country`, and even a hardcoded unitig-count array from manual Rtab
inspection). A session created from an arbitrary uploaded CSV has none of
those columns, so wrapping `explore.py` as-is would only work for sessions
built from the original fixed dataset — inconsistent with every other
session-scoped feature in this app.

**Resolution:** replace "Dataset Overview" with a new, genuinely
session-generic **Session Overview** page: class balance, feature count,
and feature prevalence, computed from whatever data the session actually
has. This is new logic, not a wrapper around `explore.py` — `explore.py`
itself is untouched by this phase.

## Backend

Four new `Session` methods (in `acquireml/session.py`, alongside `status()`/
`update_settings()`), four new endpoints (`acquireml/api/app.py`), four new
response schemas (`acquireml/api/schemas.py`). All four reuse
`Session._get_known_Xy()` / `_load_all_features()` — no new data-loading
paths.

### 1. Feature Importance — `GET /sessions/{name}/explain`

**`Session.feature_importance(self, top_n: int = 20) -> dict`**

```python
def feature_importance(self, top_n: int = 20) -> dict:
    """Rank the session's features by predictive importance.

    Trains a fresh Random Forest on the full known pool (independent of
    whatever model the session's own recommend/update cycle uses — feature
    importance specifically needs feature_importances_, which only
    RandomForestClassifier exposes among this app's model choices) and
    ranks every feature. When the known pool has at least 2 samples in
    every class, also reports a 5-fold (or fewer, if a class has fewer
    than 5 members) cross-validated balanced accuracy as a sanity check —
    skipped (None) when the pool is too small/imbalanced for CV, same
    graceful-degradation pattern as init()'s calibration/threshold tuning.
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

Reuses `train_full_model`, `extract_importances`, `get_cross_val_score` from
`explain.py` directly (all already dataset-agnostic) — `run_analysis()` and
`plot_importances()` (the CLI/matplotlib-specific orchestration) are not
touched or called. `model_name="rf"` is hardcoded regardless of the
session's own configured model, since only `RandomForestClassifier`
exposes `feature_importances_` among this app's `MODEL_CHOICES` — the
docstring states this explicitly so it isn't mistaken for a bug when a
`gbm`/`lr`/`svm` session's importance ranking doesn't match its own
prediction model.

**No minimum-known-samples gate at the `Session` method level** — `train_full_model`
and `RandomForestClassifier.fit` both handle very small pools without
raising (CV is what needs the graceful skip, already handled above). The
frontend shows an appropriately worded page for a small/fresh session
rather than the backend refusing to compute anything.

**Endpoint** (placed after the existing `reset` endpoint, before `export`,
matching this file's existing ordering-by-recency-of-addition convention):

```python
@app.get("/sessions/{name}/explain", response_model=FeatureImportanceResponse)
def feature_importance(top_n: int = 20, sess: Session = Depends(get_session)) -> FeatureImportanceResponse:
    with sess:
        return FeatureImportanceResponse(**sess.feature_importance(top_n=top_n))
```

**Schema:**

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

### 2. Session Overview — `GET /sessions/{name}/overview`

**`Session.overview(self, top_n: int = 15) -> dict`** — entirely new logic,
not derived from `explore.py`:

```python
def overview(self, top_n: int = 15) -> dict:
    """Summarize the session's own data: class balance and feature
    prevalence across the known pool. Does not train a model — this is
    pure data description, safe to compute at any pool size (including
    zero pool samples, though every session has at least the labeled
    data supplied at init() so n_pool == 0 known-only is the only
    realistic edge case, not zero known)."""
    X, y = self._get_known_Xy()
    n_known = len(X)
    n_positive = int(y.sum())
    n_negative = n_known - n_positive

    prevalence = X.mean(axis=0).sort_values(ascending=False)
    top_features = [
        {"feature": str(name), "prevalence": float(value)}
        for name, value in prevalence.head(top_n).items()
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

"Prevalence" = fraction of known samples where that binary feature is `1`
(present) — directly meaningful for this app's Rtab/VCF-style
presence/absence feature convention (documented in `CLAUDE.md`'s Data
Details section), works identically for a CSV-uploaded session as long as
its feature columns are binary, which every session's data already is by
this app's existing convention (no new assumption introduced).

**Endpoint:**

```python
@app.get("/sessions/{name}/overview", response_model=OverviewResponse)
def overview(top_n: int = 15, sess: Session = Depends(get_session)) -> OverviewResponse:
    with sess:
        return OverviewResponse(**sess.overview(top_n=top_n))
```

**Schema:**

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

### 3. AL vs Random Comparison — `GET /sessions/{name}/compare`

The compute-heavy one: simulates both strategies over the session's own
known pool (hindsight simulation — `ActiveLearningEngine`, same engine the
core product already uses) multiple times and averages the curves. No
async job queue exists anywhere in this app (every existing endpoint,
including `recommend`/`update`, already trains synchronously within the
request), so this follows the same synchronous pattern — bounded tightly
enough to stay fast.

**Minimum data requirement:** needs at least 20 known samples (arbitrary
but concrete threshold — below this, `initial_pool_size`/`batch_size`
auto-scaling below produces a degenerate 0-1-iteration curve not worth
displaying). Raises `RuntimeError` below the threshold, mirroring the
existing `recommend()` method's `RuntimeError` pattern for pool-empty —
the API layer's existing global `RuntimeError` → 409 handler covers this
without new endpoint code.

**Auto-scaled simulation parameters** (the CLI's own defaults — 15
iterations, pool of 10, batch of 25, 5 runs — assume thousands of samples;
a session's known pool is typically far smaller, so these must scale down
or the engine errors out selecting more initial samples than exist):

```python
def compare_strategies(self, runs: int = 3) -> dict:
    """Hindsight-simulate Active Learning vs Random Sampling over the
    session's own known pool, averaged across `runs` seeds. Simulation
    parameters are auto-scaled from the known pool size — this app's CLI
    defaults (initial_pool=10, batch=25, iterations=15) assume a
    research-scale dataset with thousands of samples; a session's known
    pool is typically far smaller."""
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

    sizes = [m["known_pool_size"] for m in al_hist]  # same across runs
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

Uses `build_estimator("rf")` from `explain.py` (not the session's own
configured model) for the same reason feature importance does — this is a
methodology comparison independent of whichever model the session happens
to be configured with, and `compare.py`'s own CLI already hardcodes
`RandomForestClassifier` for this exact reason (consistency with existing
precedent, not a new decision). `n_estimators=100` (via `build_estimator`,
not the heavier 300 `explain.py`'s own default uses elsewhere) matches
`compare.py`'s existing choice of a lighter forest for repeated-simulation
speed.

**Endpoint:**

```python
@app.get("/sessions/{name}/compare", response_model=CompareResponse)
def compare(runs: int = 3, sess: Session = Depends(get_session)) -> CompareResponse:
    with sess:
        return CompareResponse(**sess.compare_strategies(runs=runs))
```

**Schema:**

```python
class CompareResponse(BaseModel):
    known_pool_sizes: list[int]
    al_accuracy: list[float]
    random_accuracy: list[float]
    runs: int
    final_gap: float
```

### 4. Holdout Validation — `GET /sessions/{name}/validate`

**`Session.validate_holdout(self, test_size: float = 0.2) -> dict`**

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
    return {
        "n_train": results["n_train"],
        "n_holdout": results["n_holdout"],
        "n_holdout_resistant": results["n_holdout_resistant"],
        "n_holdout_sensitive": results["n_holdout_sensitive"],
        "balanced_accuracy": results["balanced_accuracy"],
        "precision": results["precision"],
        "recall": results["recall"],
        "f1": results["f1"],
        "roc_auc": (
            results["roc_auc"] if not math.isnan(results["roc_auc"]) else None
        ),
        "tn": results["tn"], "fp": results["fp"],
        "fn": results["fn"], "tp": results["tp"],
    }
```

Reuses `run_validation` from `validate.py` directly (already
dataset-agnostic and already returns clean, JSON-shaped values — the only
translation needed is the numpy `confusion_matrix` array itself, which is
dropped from the response in favor of the four already-extracted
`tn`/`fp`/`fn`/`tp` ints, and NaN→`None` for `roc_auc` when the holdout
happens to be single-class, matching Pydantic's inability to serialize
`float('nan')` as JSON `null` automatically).

**Endpoint:**

```python
@app.get("/sessions/{name}/validate", response_model=ValidateResponse)
def validate_holdout(test_size: float = 0.2, sess: Session = Depends(get_session)) -> ValidateResponse:
    with sess:
        return ValidateResponse(**sess.validate_holdout(test_size=test_size))
```

**Schema:**

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

## Frontend

Four new pages, four new nav links, four new routes — all unconditional
(unlike Budget's cost-tracking-conditional link, none of these four
features has an analogous "isn't set up for this session" flag; every
session has known samples by construction). Each page handles its own
too-little-data empty state, matching `BudgetPage`'s existing precedent
(its "not enough completed rounds" message) rather than `SessionLayout`
growing more conditional-fetch logic — `SessionLayout`'s nav gains four
plain, unconditional `NavLink`s, no new status fetch needed.

Routes: `/sessions/:name/explain`, `/sessions/:name/overview`,
`/sessions/:name/compare`, `/sessions/:name/validate`.

Nav order: Dashboard, Recommendations, History, Overview, Explain, Compare,
Validate, Settings, Budget — Overview/Explain/Compare/Validate placed
between History and Settings (the "look at your data" group sits with the
other data-facing pages, ahead of the "manage the session" group).

### `OverviewPage`

Stat cards (Known / Pool / Features / Class balance, matching the
`.statRow`/`.stat` pattern already used on Dashboard/Budget) plus a
horizontal bar list of the top prevalent features (feature name + a
filled bar sized to its prevalence percentage — plain CSS, not a new
charting dependency, since this is a simple ranked list rather than a
continuous scale needing Recharts' axis/tooltip machinery).

### `ExplainPage`

Same stat-card treatment for `cv_accuracy_mean ± cv_accuracy_std` (shown
as "—" when null, matching how `DashboardPage` already renders a null
`latest_accuracy`) and `total_features`/`n_known`. Below that, a
horizontal bar chart of the top features by importance — reuses the same
plain-CSS bar-list approach as `OverviewPage` (both are "ranked list with
a magnitude bar," the same visual pattern, deliberately not two different
implementations) rather than a Recharts bar chart, since neither needs
axis ticks/gridlines/hover tooltips to be readable — a labeled, sorted
list with proportional bars is the same idiom (`explain.py`'s own CLI
chart) translated to a lightweight web equivalent.

### `ComparePage`

A "Run comparison" button (not auto-fetched on page load, unlike every
other page in this app) — this is the one page where fetching on mount is
wrong: the endpoint is the most compute-heavy in the app, and a researcher
revisiting this page shouldn't silently re-trigger several seconds of
model training just by navigating here. Shows a loading state while the
request is in flight, then a Recharts `LineChart` (two lines: AL solid
accent-colored, Random dashed brass-colored, X axis = known pool size, Y
axis = balanced accuracy 0-100%) — reuses Recharts (already a dependency,
already used by `AccuracyChart` and the rebuilt `BudgetPage` chart) rather
than another hand-rolled SVG, for the same "real gridlines/ticks/tooltip"
reasons the Budget page chart was rebuilt for. Below the chart, the
`final_gap` stated in plain language ("Active learning reached X.X pp
higher accuracy than random sampling at the same number of experiments").
If the backend's `RuntimeError` (too few known samples) surfaces as a 409,
shown as the same kind of empty-state message the other pages use, not a
raw error.

### `ValidatePage`

Stat-card row for the five headline metrics (Balanced Accuracy, Precision,
Recall, F1, ROC-AUC — "—" when ROC-AUC is null), plus a 2×2 confusion
matrix rendered as a plain CSS grid (four cells: TN/FP/FN/TP, each showing
its count and the plain-language label `validate.py`'s own CLI report
already uses — "Correctly caught resistant strains," etc. — reusing that
established wording rather than inventing new copy).

## API Client Additions

`frontend/src/api/client.ts` gains four functions and their response
interfaces, following the exact existing pattern (mirror
`acquireml/api/schemas.py` field-for-field, `encodeURIComponent` on the
session name, `parseErrorDetail` on failure):

```typescript
export async function getFeatureImportance(name: string, topN?: number): Promise<FeatureImportanceResponse>
export async function getOverview(name: string, topN?: number): Promise<OverviewResponse>
export async function getComparison(name: string, runs?: number): Promise<CompareResponse>
export async function getValidation(name: string, testSize?: number): Promise<ValidateResponse>
```

## Testing Approach

Backend: each new `Session` method gets tests following the exact pattern
already established in `tests/test_session.py` (fixtures already exist:
`labeled_csv`, `pool_csv`, `session`) — a happy-path test, an
insufficient-data test asserting the specific `RuntimeError` message where
applicable (`compare_strategies`, `validate_holdout`), and for
`feature_importance` specifically, one test confirming `cv_accuracy_mean`
is `None` when the known pool is too small/imbalanced for CV (mirroring
the existing calibration-fallback tests' structure). Endpoint tests follow
`tests/test_api_app.py`'s existing pattern (`_create_session`/`client`
fixtures, one 200 test, one 404-unknown-session test, one
400/409-insufficient-data test where applicable).

Frontend: page tests follow the exact RTL pattern already established by
`SettingsPage.test.tsx`/`BudgetPage.test.tsx` — loading/loaded/error
states via mocked `client.ts` functions. `ComparePage` additionally tests
that the comparison does NOT fetch on mount (no `client.getComparison`
call until the button is clicked) and that clicking the button triggers
exactly one call.

## Explicitly Out of Scope

- No async/background job queue for the compare endpoint — synchronous,
  bounded tightly enough to stay fast, matching every other endpoint in
  this app.
- No changes to any of the four CLI modules (`explain.py`, `explore.py`,
  `compare.py`, `validate.py`) or their existing CLI commands — this phase
  only adds new `Session` methods and endpoints that reuse their
  dataset-agnostic functions; `run_analysis()`, `plot_overview()`,
  `run_comparison()`, and the CLI `main()`s are all untouched.
- No literal wrapper around `explore.py` — see "Scope Correction" above.
  `explore.py` is not imported by any new code in this phase.
- No caching of analysis results — every page fetch (or, for Compare, every
  button click) re-runs the computation fresh. A session's known pool can
  change between visits (a researcher runs `session update` between looks
  at the Explain page), so a stale cached result would be actively
  misleading; re-computing is the correct default given this app's
  existing "no polling, but always fresh on load" pattern from Phase 1-4.
- No configurable `top_n`/`runs`/`test_size` UI controls in this phase —
  the endpoints accept them as query params (useful for testing and future
  extension) but the frontend pages call them with fixed defaults. Adding
  UI controls for these is a natural, low-risk future addition once the
  base pages exist, not required for this phase to be useful.
