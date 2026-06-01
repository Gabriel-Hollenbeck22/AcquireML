"""
validate.py — Rigorous Holdout Validation

The demo in recommend.py is a *demonstration*, not proof: the strains it
ranked came from the same data the model trained on. A skeptical scientist
will rightly ask — does this work on strains the model has NEVER seen?

This module answers that honestly. It:
  1. Splits the labelled dataset into a TRAIN set and a HOLDOUT set
  2. Trains the model on the TRAIN set only — the holdout is locked away
  3. Predicts resistance for every holdout strain (genuinely unseen)
  4. Compares predictions against the true labels the model never had access to
  5. Reports honest metrics: balanced accuracy, precision, recall, ROC-AUC,
     and a full confusion matrix

This is the difference between "look, it works" and "here is proof it
generalises to new data."

Usage:
    python -m acquireml.validate
    python -m acquireml.validate --antibiotic cip --test-size 0.3
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box as rich_box
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

from acquireml import __version__
from acquireml.loader import DataLoader

console = Console()

DRUG_NAMES = {"azm": "Azithromycin", "cip": "Ciprofloxacin", "cfx": "Cefixime"}
DRUG_COLOURS = {"azm": "#2563EB", "cip": "#DC2626", "cfx": "#16A34A"}


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
        X.values, y.values,
        test_size=test_size,
        stratify=y.values,
        random_state=random_state,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Predict on the holdout — strains the model has never seen
    y_pred = model.predict(X_holdout)
    y_proba = model.predict_proba(X_holdout)[:, 1]

    cm = confusion_matrix(y_holdout, y_pred)
    # cm layout: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm.ravel()

    return {
        "n_train": len(y_train),
        "n_holdout": len(y_holdout),
        "n_holdout_resistant": int(y_holdout.sum()),
        "n_holdout_sensitive": int((y_holdout == 0).sum()),
        "balanced_accuracy": balanced_accuracy_score(y_holdout, y_pred),
        "precision": precision_score(y_holdout, y_pred, zero_division=0),
        "recall": recall_score(y_holdout, y_pred, zero_division=0),
        "f1": f1_score(y_holdout, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_holdout, y_proba) if len(np.unique(y_holdout)) > 1 else float("nan"),
        "confusion_matrix": cm,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def print_report(results: dict, antibiotic: str) -> None:
    """Print a human-readable validation report to the terminal."""
    drug = DRUG_NAMES.get(antibiotic, antibiotic.upper())

    # ── Metrics table ─────────────────────────────────────────────────────────
    table = Table(
        title=f"Holdout Validation — {drug} Resistance\n"
              f"Trained on {results['n_train']:,} strains  ·  "
              f"Tested on {results['n_holdout']:,} UNSEEN strains",
        box=rich_box.ROUNDED,
        header_style="bold magenta",
        border_style="bright_black",
    )
    table.add_column("Metric", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("What it means", style="dim")

    table.add_row("Balanced Accuracy", f"{results['balanced_accuracy']:.1%}",
                  "Overall correctness, fair to rare classes")
    table.add_row("Precision", f"{results['precision']:.1%}",
                  "When it says 'resistant', how often is it right")
    table.add_row("Recall (Sensitivity)", f"{results['recall']:.1%}",
                  "Of all truly resistant strains, how many it caught")
    table.add_row("F1 Score", f"{results['f1']:.1%}",
                  "Balance of precision and recall")
    table.add_row("ROC-AUC", f"{results['roc_auc']:.3f}",
                  "Ranking quality (1.0 = perfect, 0.5 = random)")

    console.print(table)

    # ── Confusion matrix as plain English ─────────────────────────────────────
    console.print(
        f"\n  [bold]On {results['n_holdout']:,} strains the model had never seen:[/bold]\n"
        f"    [green]✓[/green] Correctly caught resistant strains : "
        f"[bold]{results['tp']}[/bold] of {results['n_holdout_resistant']}\n"
        f"    [green]✓[/green] Correctly cleared sensitive strains: "
        f"[bold]{results['tn']}[/bold] of {results['n_holdout_sensitive']}\n"
        f"    [red]✗[/red] Missed resistant strains (false negatives): "
        f"[bold]{results['fn']}[/bold]\n"
        f"    [red]✗[/red] False alarms (false positives)           : "
        f"[bold]{results['fp']}[/bold]"
    )


def plot_confusion_matrix(results: dict, antibiotic: str, output_path: Path) -> None:
    """Save a confusion matrix heatmap for the holdout predictions."""
    drug = DRUG_NAMES.get(antibiotic, antibiotic.upper())
    colour = DRUG_COLOURS.get(antibiotic, "#2563EB")
    cm = results["confusion_matrix"]

    fig, ax = plt.subplots(figsize=(7, 6))

    # Normalise each row to show proportions, but annotate with raw counts
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)

    labels = ["Sensitive", "Resistant"]
    ax.set_xticks([0, 1]); ax.set_xticklabels(labels)
    ax.set_yticks([0, 1]); ax.set_yticklabels(labels)
    ax.set_xlabel("Model Prediction", fontsize=11, fontweight="bold")
    ax.set_ylabel("True Lab Result", fontsize=11, fontweight="bold")

    # Annotate each cell with count + percentage
    cell_labels = [
        ["True Negative", "False Positive"],
        ["False Negative", "True Positive"],
    ]
    for i in range(2):
        for j in range(2):
            count = cm[i, j]
            pct = cm_norm[i, j]
            text_colour = "white" if pct > 0.5 else "black"
            ax.text(j, i, f"{cell_labels[i][j]}\n\n{count:,}\n({pct:.1%})",
                    ha="center", va="center", color=text_colour,
                    fontsize=10, fontweight="bold")

    ax.set_title(
        f"Holdout Validation — {drug} Resistance\n"
        f"Predictions on {results['n_holdout']:,} strains the model never saw  ·  "
        f"Balanced accuracy: {results['balanced_accuracy']:.1%}",
        fontsize=12, fontweight="bold", pad=14,
    )

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Proportion of true class")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    console.print(f"\n  Confusion matrix chart saved → [bold]{output_path.resolve()}[/bold]")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="acquireml.validate",
        description="Rigorous holdout validation — test on strains the model never saw",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--antibiotic", choices=["azm", "cip", "cfx"], default="azm")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--test-size", type=float, default=0.2,
                   help="Fraction of data locked away as the unseen holdout")
    p.add_argument("--output", type=Path, default=None,
                   help="Output path for confusion matrix chart "
                        "(default: {antibiotic}_validation.png)")
    p.add_argument("--seed", type=int, default=42)
    return p


def main() -> None:
    args = _build_parser().parse_args()
    output = args.output or Path(f"{args.antibiotic}_validation.png")

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  "
            "[italic]Holdout Validation[/italic]",
            border_style="cyan",
        )
    )

    with console.status("[bold]Loading dataset…[/bold]"):
        loader = DataLoader(data_dir=args.data_dir, antibiotic=args.antibiotic)
        X, y = loader.load()

    console.print(f"  [bold]Dataset:[/bold] {len(X):,} labelled strains  ·  "
                  f"{X.shape[1]:,} unitigs  ·  "
                  f"{y.sum():,} resistant ({y.mean():.1%})")
    console.print(f"  [bold]Split:[/bold] {1 - args.test_size:.0%} train  /  "
                  f"{args.test_size:.0%} unseen holdout\n")

    with console.status("[bold]Training on train split, predicting on unseen holdout…[/bold]"):
        results = run_validation(X, y, test_size=args.test_size, random_state=args.seed)

    print_report(results, antibiotic=args.antibiotic)
    plot_confusion_matrix(results, antibiotic=args.antibiotic, output_path=output)

    console.rule(style="bright_black")


if __name__ == "__main__":
    main()
