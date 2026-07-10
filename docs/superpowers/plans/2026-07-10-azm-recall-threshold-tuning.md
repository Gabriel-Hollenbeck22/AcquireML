# AZM Recall Threshold Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded 0.5 prediction cutoff with a cross-validated,
balanced-accuracy-optimal decision threshold, applied as the default
behavior everywhere a trained model classifies a strain (session loop,
recommend, holdout validation), to fix AZM's 69.7% holdout recall.

**Architecture:** `explain.py` gains two small functions —
`find_best_threshold()` (searches for the best cutoff via
`cross_val_predict`) and `predict_at_threshold()` (applies a model's tuned
cutoff instead of assuming 0.5). `train_full_model()` calls the former and
stores the result as a plain `model.threshold_` attribute (not a wrapper
class, to avoid breaking existing `isinstance()` checks). Four call sites
across `session.py`, `recommend.py`, and `validate.py` switch from
`model.predict(X)` to `predict_at_threshold(model, X)`. `validate.py` is
also refactored to call `train_full_model()` instead of constructing its
own separate `RandomForestClassifier`, which is both a dedup fix and the
only way the threshold fix reaches the reported holdout numbers.

**Tech Stack:** Python, scikit-learn (`cross_val_predict`, `StratifiedKFold`,
`balanced_accuracy_score`), pandas, pytest.

## Global Constraints

- Threshold search must use out-of-fold probabilities (`cross_val_predict`),
  never the final model's own training-set probabilities — avoids leakage.
- Optimize for **balanced accuracy**, not raw recall (spec: "optimizing pure
  recall would degenerate to calling everything resistant").
- No wrapper class around the fitted estimator — `model.threshold_` must be
  a plain attribute so existing `isinstance(model, RandomForestClassifier)`
  / `isinstance(model, CalibratedClassifierCV)` tests keep passing unmodified.
- `predict_proba` is never overridden or wrapped — uncertainty sampling in
  `strategies.py` must be completely unaffected.
- Small/imbalanced known pools (minority class smaller than the requested
  CV fold count) fall back to `threshold_ = 0.5`, mirroring the existing
  calibration fallback pattern in `train_full_model()`.
- `engine.py` / `cli.py` / `compare.py` (the `make run` / `make compare`
  hindsight-simulation path) are out of scope — they build their own
  `RandomForestClassifier` directly and never call `train_full_model()`.
- All 171 existing tests must stay green, unmodified.

---

### Task 1: `find_best_threshold()` in explain.py

**Files:**
- Modify: `acquireml/explain.py:36` (imports), after `acquireml/explain.py:74`
  (after `build_estimator`, before `train_full_model`)
- Test: `tests/test_explain.py`

**Interfaces:**
- Produces: `find_best_threshold(estimator, X: np.ndarray, y: np.ndarray, cv: int, metric: str = "balanced_accuracy") -> float`
  — `X`/`y` are already-`.values` numpy arrays. `cv` is the exact fold count
  to use (caller is responsible for clamping it to a value `<= minority
  class count`, matching the pattern `find_best_threshold` itself does not
  guard against — callers guard). Returns a float in `[0.05, 0.95]`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_explain.py`:

```python
from acquireml.explain import find_best_threshold


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_explain.py -k find_best_threshold -v`
Expected: FAIL with `ImportError: cannot import name 'find_best_threshold'`

- [ ] **Step 3: Implement `find_best_threshold()`**

In `acquireml/explain.py`, update the import block (currently lines 32-37):

```python
from sklearn.base import BaseEstimator
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.svm import SVC
```

Insert this function after `build_estimator()` (after line 74, before the
`# ── Colours` section):

```python
def find_best_threshold(
    estimator: BaseEstimator,
    X: np.ndarray,
    y: np.ndarray,
    cv: int,
    metric: str = "balanced_accuracy",
) -> float:
    """Cross-validated search for the predict() decision threshold.

    Returns the probability cutoff (0.05-0.95) that maximizes `metric` on
    out-of-fold predictions, instead of assuming sklearn's default of 0.5.
    Uses cross_val_predict so the search never scores a fold's predictions
    against data that fold's fitted model was trained on. Under class
    imbalance (e.g. AZM's 13% resistant rate), 0.5 is rarely the
    accuracy-optimal cutoff.

    Caller is responsible for ensuring `cv` does not exceed the minority
    class count (StratifiedKFold raises otherwise).
    """
    if metric != "balanced_accuracy":
        raise ValueError(f"Unknown threshold metric {metric!r}")

    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    proba = cross_val_predict(
        estimator, X, y, cv=skf, method="predict_proba", n_jobs=-1
    )[:, 1]

    candidates = np.arange(0.05, 0.951, 0.01)
    scores = [balanced_accuracy_score(y, proba >= t) for t in candidates]
    return float(candidates[int(np.argmax(scores))])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_explain.py -k find_best_threshold -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add acquireml/explain.py tests/test_explain.py
git commit -m "Add find_best_threshold(): cross-validated decision threshold search"
```

---

### Task 2: `predict_at_threshold()` in explain.py

**Files:**
- Modify: `acquireml/explain.py` (add function near `find_best_threshold`)
- Test: `tests/test_explain.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (independent helper), but is
  designed to read the `threshold_` attribute Task 3 will attach.
- Produces: `predict_at_threshold(model, X) -> np.ndarray` — an array of
  0/1 ints, same shape as `model.predict(X)` would give.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_explain.py`:

```python
from acquireml.explain import predict_at_threshold


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_explain.py -k predict_at_threshold -v`
Expected: FAIL with `ImportError: cannot import name 'predict_at_threshold'`

- [ ] **Step 3: Implement `predict_at_threshold()`**

In `acquireml/explain.py`, add directly after `find_best_threshold()`:

```python
def predict_at_threshold(model: BaseEstimator, X) -> np.ndarray:
    """Classify using the model's tuned decision threshold.

    Falls back to 0.5 if the model was never routed through
    train_full_model() (and so never got a threshold_ attribute).
    predict_proba is never touched here — anything that only needs
    probabilities (uncertainty sampling) should keep calling it directly.
    """
    threshold = getattr(model, "threshold_", 0.5)
    proba = model.predict_proba(X)[:, 1]
    return (proba >= threshold).astype(int)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_explain.py -k predict_at_threshold -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add acquireml/explain.py tests/test_explain.py
git commit -m "Add predict_at_threshold(): classify using a model's tuned cutoff"
```

---

### Task 3: Wire threshold search into `train_full_model()`

**Files:**
- Modify: `acquireml/explain.py:90-128` (the existing `train_full_model` body)
- Test: `tests/test_explain.py`

**Interfaces:**
- Consumes: `find_best_threshold()` from Task 1.
- Produces: `train_full_model(..., tune_threshold: bool = True, threshold_cv: int = 5)`
  — same return type as before (a fitted `RandomForestClassifier` /
  `GradientBoostingClassifier` / `LogisticRegression` / `SVC` /
  `CalibratedClassifierCV`), now always carrying a `.threshold_` float
  attribute (0.5 when tuning was skipped or disabled).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_explain.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_explain.py -k train_full_model_threshold -v`
Expected: FAIL — `AttributeError: ... no attribute 'threshold_'`

- [ ] **Step 3: Rewrite `train_full_model()`**

Replace the existing function body (`acquireml/explain.py:90-128`) with:

```python
def train_full_model(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int = 42,
    model_name: str = "rf",
    calibrate: bool = False,
    calibration_method: str = "sigmoid",
    tune_threshold: bool = True,
    threshold_cv: int = 5,
) -> BaseEstimator:
    """Train a classifier on the entire labelled dataset.

    model_name selects the estimator: "rf" (default, Random Forest — also
    the only one with feature_importances_ used by explain.py), "gbm"
    (Gradient Boosting), "lr" (Logistic Regression), or "svm" (probability-
    calibrated SVC).

    When calibrate=True, the fitted estimator is wrapped in
    CalibratedClassifierCV so predict_proba reflects true observed
    frequencies rather than the model's raw (often over/under-confident)
    scores — this directly improves uncertainty sampling, which relies on
    predict_proba being meaningfully close to p=0.5 for genuinely uncertain
    samples. Calibration needs at least 2 samples per class per CV fold; if
    the known pool is too small or too imbalanced for that, it's skipped
    and the plain (uncalibrated) model is returned instead.

    When tune_threshold=True (default), a cross-validated decision
    threshold is found via find_best_threshold() and stored as
    model.threshold_ — callers that classify (rather than just rank by
    probability) should use predict_at_threshold(model, X) instead of
    model.predict(X) to make use of it. Falls back to threshold_ = 0.5
    when the known pool is too small/imbalanced for the requested CV,
    same fallback pattern as calibration.
    """
    base = build_estimator(model_name, random_state=random_state)
    min_class_count = int(pd.Series(y).value_counts().min())

    if not calibrate:
        estimator = base
    else:
        cal_cv = min(3, min_class_count)
        estimator = (
            CalibratedClassifierCV(base, method=calibration_method, cv=cal_cv)
            if cal_cv >= 2
            else base
        )

    threshold = 0.5
    if tune_threshold:
        cv = min(threshold_cv, min_class_count)
        if cv >= 2:
            threshold = find_best_threshold(estimator, X.values, y.values, cv=cv)

    estimator.fit(X.values, y.values)
    estimator.threshold_ = threshold
    return estimator
```

- [ ] **Step 4: Run the full explain test file to verify everything passes**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_explain.py -v`
Expected: All tests PASS (previous calibration tests included — they check
`isinstance`, which is unaffected by the new `.threshold_` attribute)

- [ ] **Step 5: Commit**

```bash
git add acquireml/explain.py tests/test_explain.py
git commit -m "Wire cross-validated threshold tuning into train_full_model()"
```

---

### Task 4: Switch `session.py` to `predict_at_threshold()`

**Files:**
- Modify: `acquireml/session.py:35` (import), `acquireml/session.py:168`, `acquireml/session.py:387`
- Test: `tests/test_session.py` (no new tests — existing suite must stay green;
  this task is a pure call-site swap with no new observable behavior beyond
  what Task 3 already changed)

**Interfaces:**
- Consumes: `predict_at_threshold(model, X)` from Task 2.

- [ ] **Step 1: Update the import**

In `acquireml/session.py:35`, change:

```python
from acquireml.explain import CALIBRATION_METHODS, MODEL_CHOICES, train_full_model
```

to:

```python
from acquireml.explain import (
    CALIBRATION_METHODS,
    MODEL_CHOICES,
    predict_at_threshold,
    train_full_model,
)
```

- [ ] **Step 2: Update `_train()` (line 168)**

Change:

```python
        acc = float(balanced_accuracy_score(y_known, model.predict(X_known)))
```

to:

```python
        acc = float(balanced_accuracy_score(y_known, predict_at_threshold(model, X_known)))
```

- [ ] **Step 3: Update `recommend()` (line 387)**

Change:

```python
        predictions = model.predict(X_pool.values)
```

to:

```python
        predictions = predict_at_threshold(model, X_pool.values)
```

- [ ] **Step 4: Run the session test suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -v`
Expected: All tests PASS, no changes needed (these tests check structural
behavior — DataFrame columns, stopping criteria, status output — not exact
predicted-class values)

- [ ] **Step 5: Commit**

```bash
git add acquireml/session.py
git commit -m "session.py: classify via predict_at_threshold instead of raw 0.5 cutoff"
```

---

### Task 5: Switch `recommend.py` to `predict_at_threshold()`

**Files:**
- Modify: `acquireml/recommend.py:48` (import), `acquireml/recommend.py:109`
- Test: `tests/test_recommend.py` (existing suite must stay green)

**Interfaces:**
- Consumes: `predict_at_threshold(model, X)` from Task 2.

- [ ] **Step 1: Update the import**

In `acquireml/recommend.py:48`, change:

```python
from acquireml.explain import train_full_model
```

to:

```python
from acquireml.explain import predict_at_threshold, train_full_model
```

- [ ] **Step 2: Update `rank_strains()` (line 109)**

Change:

```python
    predictions = model.predict(X_aligned.values)
```

to:

```python
    predictions = predict_at_threshold(model, X_aligned.values)
```

- [ ] **Step 3: Run the recommend test suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_recommend.py -v`
Expected: All tests PASS unmodified (tests check column presence/shape, not
exact predicted_class values)

- [ ] **Step 4: Commit**

```bash
git add acquireml/recommend.py
git commit -m "recommend.py: classify via predict_at_threshold instead of raw 0.5 cutoff"
```

---

### Task 6: Refactor `validate.py` to reuse `train_full_model()`

**Files:**
- Modify: `acquireml/validate.py:37` (imports), `acquireml/validate.py:57-104` (`run_validation`)
- Test: `tests/test_validate.py` (existing suite must stay green — this is a
  behavior-preserving refactor plus the threshold fix)

**Interfaces:**
- Consumes: `train_full_model()` (already existed) and `predict_at_threshold()`
  from Task 2, both from `acquireml.explain`.
- Produces: same `run_validation(X, y, test_size, random_state) -> dict`
  signature and return shape as before — no caller of `run_validation`
  needs to change.

- [ ] **Step 1: Update imports**

In `acquireml/validate.py`, remove the now-unused direct import (line 37):

```python
from sklearn.ensemble import RandomForestClassifier
```

Add, near the other local imports:

```python
from acquireml.explain import predict_at_threshold, train_full_model
```

(`acquireml.loader` is already imported at line ~49 — add the new import
on the line directly below it.)

- [ ] **Step 2: Rewrite `run_validation()` (currently lines 57-104)**

Replace the function body with:

```python
def run_validation(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float,
    random_state: int,
) -> dict:
    """Train on a subset, evaluate on a genuinely-unseen holdout.

    Returns a dict of metrics plus the confusion matrix and holdout sizes.
    """
    # The stratify=y argument keeps the same resistant/sensitive ratio in
    # both splits — important because the data is imbalanced.
    X_train, X_holdout, y_train, y_holdout = train_test_split(
        X, y,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )

    model = train_full_model(X_train, y_train, random_state=random_state)

    # Predict on the holdout — strains the model has never seen
    y_pred = predict_at_threshold(model, X_holdout.values)
    y_proba = model.predict_proba(X_holdout.values)[:, 1]

    cm = confusion_matrix(y_holdout.values, y_pred)
    # cm layout: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm.ravel()

    return {
        "n_train": len(y_train),
        "n_holdout": len(y_holdout),
        "n_holdout_resistant": int(y_holdout.values.sum()),
        "n_holdout_sensitive": int((y_holdout.values == 0).sum()),
        "balanced_accuracy": balanced_accuracy_score(y_holdout.values, y_pred),
        "precision": precision_score(y_holdout.values, y_pred, zero_division=0),
        "recall": recall_score(y_holdout.values, y_pred, zero_division=0),
        "f1": f1_score(y_holdout.values, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_holdout.values, y_proba) if len(np.unique(y_holdout.values)) > 1 else float("nan"),
        "confusion_matrix": cm,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }
```

Note the split now runs on the DataFrame/Series directly (not `.values`) so
`train_full_model()` gets a proper `X_train` DataFrame with column names —
required because `train_full_model()`'s signature expects `pd.DataFrame`/
`pd.Series` and calls `.values` internally itself.

- [ ] **Step 3: Run the validate test suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_validate.py -v`
Expected: All 6 existing tests PASS unmodified

- [ ] **Step 4: Commit**

```bash
git add acquireml/validate.py
git commit -m "validate.py: reuse train_full_model() instead of duplicating RF construction"
```

---

### Task 7: Full suite verification + real-data check

**Files:** none (verification only)

- [ ] **Step 1: Run the complete test suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: All tests pass (171 previously existing + 8 new from Tasks 1-3 = 179 passed), zero failures

- [ ] **Step 2: Run holdout validation on real AZM data to confirm the fix**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m acquireml.validate --antibiotic azm`

Expected: terminal report shows recall meaningfully above the prior 69.7%
baseline (some drop in precision from 89.9% is expected and acceptable —
that's the tradeoff being tuned), and balanced accuracy at or above the
prior 84.3% baseline. Record the actual before/after numbers.

- [ ] **Step 3: Run holdout validation on real CIP data as a regression check**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m acquireml.validate --antibiotic cip`

Expected: balanced accuracy stays at or near the prior 97.6% baseline (CIP
was already performing well — this confirms threshold tuning doesn't hurt
an already-good model).

- [ ] **Step 4: Update CLAUDE.md's "Key Results" section**

In `CLAUDE.md`, replace the AZM holdout line under "## Key Results (so far)"
with the actual measured numbers from Step 2 (exact wording depends on the
real output — update balanced accuracy, precision, recall, ROC-AUC to the
new measured values, and remove or update the "Improving AZM recall is an
open task" note since it's now addressed).

- [ ] **Step 5: Final commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md AZM holdout numbers after threshold tuning fix"
```

- [ ] **Step 6: Report readiness**

Summarize for the user: branch name, commits made, before/after AZM
recall/precision/balanced-accuracy numbers, CIP regression-check result,
full test count. State that the branch is ready to push per the
project's feature-branch workflow (merge to main is a separate, explicit
step).
