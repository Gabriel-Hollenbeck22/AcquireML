"""
explain.py — Feature Importance Analysis for AcquireML

After proving the model works, the natural next question is: *which specific
DNA fragments (unitigs) is the model actually using to predict resistance?*

This module trains a Random Forest on the full labelled dataset for a chosen
antibiotic, then ranks every unitig by how useful it was for making predictions.
The result is a chart showing the top predictors — essentially a map of which
genetic markers drive antibiotic resistance.

This is important for three reasons:
  1. Scientists need to understand *why* a model predicts what it predicts.
  2. It validates the model is learning real biology, not statistical noise.
  3. High-importance unitigs are candidates for follow-up wet lab investigation.

Usage:
    python -m acquireml.explain
    python -m acquireml.explain --antibiotic cip --top-n 30
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.svm import SVC

from acquireml.loader import DataLoader

# Model registry for the `--model` flag. Each must support predict_proba,
# since QueryStrategy.select_batch relies on it for uncertainty scoring.
MODEL_CHOICES = ("rf", "gbm", "lr", "svm")

# Calibration methods for the `--calibrate` flag (see CalibratedClassifierCV).
CALIBRATION_METHODS = ("sigmoid", "isotonic")


def build_estimator(model_name: str = "rf", random_state: int = 42) -> BaseEstimator:
    """Construct the estimator matching --model rf|gbm|lr|svm."""
    if model_name == "rf":
        return RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )
    if model_name == "gbm":
        return GradientBoostingClassifier(random_state=random_state)
    if model_name == "lr":
        return LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=random_state,
        )
    if model_name == "svm":
        return SVC(
            probability=True,
            class_weight="balanced",
            random_state=random_state,
        )
    raise ValueError(
        f"Unknown model {model_name!r}. Choose one of: {', '.join(MODEL_CHOICES)}"
    )


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


# ── Colours ───────────────────────────────────────────────────────────────────
DRUG_COLOURS = {
    "azm": "#2563EB",   # blue
    "cip": "#DC2626",   # red
    "cfx": "#16A34A",   # green
}
DRUG_NAMES = {
    "azm": "Azithromycin",
    "cip": "Ciprofloxacin",
    "cfx": "Cefixime",
}


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


def get_cross_val_score(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int = 42,
    n_splits: int = 5,
) -> tuple[float, float]:
    """Return mean ± std balanced accuracy across k stratified folds.

    This gives a more honest accuracy estimate than a single train/test split,
    because the dataset is imbalanced (far more sensitive than resistant strains).
    """
    model = RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = cross_val_score(model, X.values, y.values,
                             cv=cv, scoring="balanced_accuracy")
    return float(scores.mean()), float(scores.std())


def extract_importances(
    model: RandomForestClassifier,
    feature_names: list[str],
    top_n: int,
) -> pd.DataFrame:
    """Return a DataFrame of the top_n most important features, sorted descending."""
    importances = model.feature_importances_
    df = pd.DataFrame({
        "unitig":     feature_names,
        "importance": importances,
    })
    df = df.sort_values("importance", ascending=False).head(top_n).reset_index(drop=True)
    df["rank"] = df.index + 1
    df["cumulative_importance"] = df["importance"].cumsum()
    return df


def plot_importances(
    importances_df: pd.DataFrame,
    antibiotic: str,
    cv_mean: float,
    cv_std: float,
    total_features: int,
    output_path: Path,
) -> None:
    """Generate and save the feature importance chart."""
    drug  = DRUG_NAMES[antibiotic]
    colour = DRUG_COLOURS[antibiotic]
    top_n = len(importances_df)

    fig, axes = plt.subplots(1, 2, figsize=(15, max(6, top_n * 0.32)),
                             gridspec_kw={"width_ratios": [3, 1]})

    # ── Left panel: horizontal bar chart of top N unitigs ─────────────────────
    ax = axes[0]

    # Shorten long unitig sequences for display (keep first + last 8 chars)
    def shorten(seq: str, maxlen: int = 24) -> str:
        if len(seq) <= maxlen:
            return seq
        return seq[:10] + "…" + seq[-10:]

    labels = [
        f"#{row.rank}  {shorten(row.unitig)}"
        for row in importances_df.itertuples()
    ]
    values = importances_df["importance"].values

    # Colour bars by their rank (darker = more important)
    bar_colours = [
        plt.cm.Blues(0.4 + 0.6 * (1 - i / top_n))   # type: ignore[attr-defined]
        for i in range(top_n)
    ]
    bars = ax.barh(labels[::-1], values[::-1],
                   color=bar_colours[::-1], edgecolor="white", linewidth=0.5)

    # Annotate each bar with its importance value
    for bar, val in zip(bars, values[::-1]):
        ax.text(
            bar.get_width() + max(values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}",
            va="center", ha="left", fontsize=7.5,
        )

    ax.set_title(
        f"Top {top_n} Predictive DNA Fragments — {drug} Resistance\n"
        f"Trained on full dataset  ·  "
        f"Cross-validated accuracy: {cv_mean:.3f} ± {cv_std:.3f}",
        fontsize=11, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Feature Importance (Mean Decrease in Impurity)", fontsize=10)
    ax.set_xlim(0, max(values) * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor("#FAFAFA")

    # ── Right panel: cumulative importance curve ───────────────────────────────
    ax2 = axes[1]

    cum = importances_df["cumulative_importance"].values
    ranks = importances_df["rank"].values

    ax2.plot(ranks, cum * 100, color=colour, linewidth=2.5, marker="o", markersize=4)
    ax2.fill_between(ranks, cum * 100, alpha=0.12, color=colour)

    # Mark where cumulative importance crosses 50 % and 80 %
    for threshold, label in [(0.5, "50%"), (0.8, "80%")]:
        cross_idx = np.searchsorted(cum, threshold)
        if cross_idx < len(ranks):
            ax2.axhline(threshold * 100, color="grey", linestyle="--",
                        linewidth=0.8, alpha=0.6)
            ax2.axvline(ranks[cross_idx], color="grey", linestyle="--",
                        linewidth=0.8, alpha=0.6)
            ax2.annotate(
                f"{label} of importance\ncaptured by top {ranks[cross_idx]}",
                xy=(ranks[cross_idx], threshold * 100),
                xytext=(ranks[cross_idx] + 1.5, threshold * 100 - 8),
                fontsize=7.5, color="grey",
            )

    ax2.set_title("Cumulative Importance\nof Top Features", fontsize=10,
                  fontweight="bold", pad=12)
    ax2.set_xlabel(f"Number of Top Features (out of {total_features:,} total)")
    ax2.set_ylabel("Cumulative Importance (%)")
    ax2.set_ylim(0, 105)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.set_facecolor("#FAFAFA")

    fig.tight_layout(rect=[0, 0, 1, 0.99])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Chart saved → {output_path.resolve()}")


def run_analysis(
    data_dir: Path,
    antibiotic: str,
    top_n: int,
    output_path: Path,
    random_state: int = 42,
) -> pd.DataFrame:
    """Full pipeline: load → cross-validate → train → rank → plot."""

    print(f"\nLoading {antibiotic.upper()} dataset…")
    loader = DataLoader(data_dir=data_dir, antibiotic=antibiotic)
    X, y = loader.load()
    print(f"  {len(X):,} samples  ·  {X.shape[1]:,} unitigs  ·  "
          f"{y.sum():,} resistant ({y.mean():.1%})")

    print(f"\nCross-validating (5-fold stratified)…")
    cv_mean, cv_std = get_cross_val_score(X, y, random_state=random_state)
    print(f"  Balanced accuracy: {cv_mean:.4f} ± {cv_std:.4f}")

    print(f"\nTraining full model on all {len(X):,} samples…")
    model = train_full_model(X, y, random_state=random_state)

    print(f"\nRanking top {top_n} features by importance…")
    imp_df = extract_importances(model, list(X.columns), top_n)

    # Print summary table to terminal
    print(f"\n{'Rank':<5} {'Importance':>12}  {'Cumulative':>11}  Unitig (first 40 chars)")
    print("-" * 80)
    for row in imp_df.itertuples():
        print(f"  {row.rank:<4} {row.importance:>12.6f}  "
              f"{row.cumulative_importance:>10.1%}  "
              f"{row.unitig[:40]}")

    plot_importances(
        importances_df=imp_df,
        antibiotic=antibiotic,
        cv_mean=cv_mean,
        cv_std=cv_std,
        total_features=X.shape[1],
        output_path=output_path,
    )
    return imp_df


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="acquireml.explain",
        description="Rank DNA fragments by their predictive importance for antibiotic resistance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--antibiotic", choices=["azm", "cip", "cfx"], default="azm")
    p.add_argument("--data-dir",   type=Path,  default=Path("data"))
    p.add_argument("--top-n",      type=int,   default=20,
                   help="How many top features to show in the chart")
    p.add_argument("--output",     type=Path,  default=None,
                   help="Output file path (default: {antibiotic}_importance.png)")
    p.add_argument("--seed",       type=int,   default=42)
    return p


def main() -> None:
    args = _build_parser().parse_args()
    output = args.output or Path(f"{args.antibiotic}_importance.png")
    run_analysis(
        data_dir=args.data_dir,
        antibiotic=args.antibiotic,
        top_n=args.top_n,
        output_path=output,
        random_state=args.seed,
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
