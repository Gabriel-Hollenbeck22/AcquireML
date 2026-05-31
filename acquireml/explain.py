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
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

from acquireml.loader import DataLoader


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
) -> RandomForestClassifier:
    """Train a Random Forest on the entire labelled dataset."""
    model = RandomForestClassifier(
        n_estimators=300,     # more trees = more stable importance estimates
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X.values, y.values)
    return model


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
