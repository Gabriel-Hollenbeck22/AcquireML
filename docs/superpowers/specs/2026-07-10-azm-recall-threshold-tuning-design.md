# AZM Recall Improvement via Threshold Tuning — Design

## Problem

Holdout validation on Azithromycin (AZM) resistance shows 84.3% balanced
accuracy but only 69.7% recall: the model misses roughly 3 in 10 truly
resistant strains, despite high precision (89.9%). This is the one open
technical weakness flagged in `CLAUDE.md`.

Root cause: every prediction call in the codebase uses scikit-learn's
default 0.5 probability cutoff. `build_estimator()` already sets
`class_weight="balanced"` for rf/lr/svm, which helps *training* weigh the
rare (resistant) class more heavily, but that's a separate concern from the
*decision threshold* applied at prediction time. Under class imbalance
(13% resistant for AZM), 0.5 is rarely the accuracy-optimal cutoff.

## Goal

Make the recall/precision tradeoff reflect a cross-validated, data-driven
choice instead of an unexamined default — as the model's actual default
behavior (not an opt-in flag), so every consumer of `train_full_model()`
benefits automatically.

## Approach

### 1. Cross-validated threshold search (`explain.py`)

Add `find_best_threshold(estimator, X, y, cv, metric="balanced_accuracy")`:
- Runs `cross_val_predict(estimator, X, y, cv=StratifiedKFold(cv), method="predict_proba")`
  to get honest out-of-fold probabilities (no leakage from testing on
  training data).
- Scans candidate thresholds from 0.05 to 0.95 in steps of 0.01.
- Returns the threshold that maximizes balanced accuracy (not raw recall —
  optimizing pure recall would degenerate to calling everything
  "resistant"; balanced accuracy keeps precision honest while still
  correcting the 0.5 default's imbalance blind spot).

### 2. Wire into `train_full_model()`

After fitting (with or without calibration), compute the threshold and
store it as a plain attribute: `model.threshold_ = <value>`.

**Explicitly not a wrapper class.** Existing tests assert
`isinstance(model, RandomForestClassifier)` and
`isinstance(model, CalibratedClassifierCV)` after calling
`train_full_model()`. A wrapper object would break every one of those and
force call sites to unwrap. A plain attribute (sklearn's own
trailing-underscore convention for fitted state) is invisible to
`isinstance` and free to attach.

### 3. New helper: `predict_at_threshold(model, X)`

```python
def predict_at_threshold(model, X):
    threshold = getattr(model, "threshold_", 0.5)
    proba = model.predict_proba(X)[:, 1]
    return (proba >= threshold).astype(int)
```

`predict_proba` itself is never touched or overridden, so uncertainty
sampling (`strategies.py`, which only ever calls `predict_proba`) is
completely unaffected by this change.

### 4. Call sites switched from `.predict(X)` to `predict_at_threshold(model, X)`

- `session.py` `_train()` — round accuracy tracking (currently line ~168)
- `session.py` `recommend()` — predicted_class label (currently line ~387)
- `recommend.py` `rank_strains()` — predicted_class label (currently line ~109)
- `validate.py` `run_validation()` — holdout confusion matrix / precision /
  recall / F1 (this is the number cited in `CLAUDE.md`)

`roc_auc` in `validate.py` is threshold-independent (uses raw `predict_proba`)
and needs no change.

### 5. Bundled reuse fix: `validate.py`

`validate.py` currently builds its own private `RandomForestClassifier(...)`
instead of calling `explain.train_full_model()` like every other module
does (recommend.py, session.py, explain.py itself). This is exactly the
kind of duplication `CLAUDE.md`'s conventions call out ("reuse over
duplication"). It also means the threshold fix would never reach the
reported holdout number unless fixed.

`run_validation()` will be refactored to:
1. `train_test_split` on the DataFrame/Series directly (not `.values`),
   preserving index and columns.
2. Call `train_full_model(X_train, y_train, random_state=random_state)`
   instead of constructing its own `RandomForestClassifier`.
3. Use `predict_at_threshold(model, X_holdout.values)` for `y_pred`.

This is a behavior-preserving refactor plus the threshold fix in one step:
same `class_weight="balanced"`, same `n_estimators=300`, same random state
semantics — just routed through the shared function.

## Scope boundary

`engine.py` (the `ActiveLearningEngine` hindsight simulation used by
`cli.py`'s `make run` and `compare.py`'s `make compare`) constructs its own
`RandomForestClassifier` directly and re-fits it via `clone()` every
iteration. It never calls `build_estimator()` or `train_full_model()`.
This design does **not** touch that path — it's a different product
surface (retrospective AL-vs-random learning-curve comparison, not the
real-world prospective session loop), and pulling it in would require
reworking the `clone()`-based per-iteration re-fit to also carry a
threshold. Out of scope for this change.

## Edge cases

- **Small/imbalanced known pools** (e.g. CFX has only 5 resistant samples
  total): if `min_class_count` is too small for the requested CV fold
  count, threshold search is skipped and `threshold_` defaults to 0.5 —
  mirroring the existing calibration fallback already in `train_full_model()`.
- **`--calibrate` + threshold tuning together**: threshold search runs
  against the calibrated pipeline (not the raw base estimator) for
  correctness, since calibration remaps probability values and a threshold
  tuned on raw scores wouldn't transfer cleanly. This means nested CV
  (calibration's internal CV inside the threshold search's CV) and is
  measurably slower. This only affects the opt-in `--calibrate` path, not
  the default session/validate/recommend behavior.

## Testing

- New unit tests for `find_best_threshold()`: picks a sensible threshold on
  a synthetic imbalanced dataset; falls back to 0.5 when the minority class
  is too small.
- New unit tests for `predict_at_threshold()`: applies `threshold_` when
  present, defaults to 0.5 when absent.
- Existing 171 tests must stay green unmodified (isinstance checks and
  `predict_proba` shape checks are unaffected by design).
- Manual verification: `make validate --antibiotic azm` (or equivalent CLI
  invocation) run before and after, comparing recall/precision/balanced
  accuracy to confirm the intended improvement on real data.
