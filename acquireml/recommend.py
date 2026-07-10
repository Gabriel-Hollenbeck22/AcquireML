"""
recommend.py — Phase 3: Live Experiment Recommendations

This is the actual product.

The simulation engine (engine.py) proved the concept by replaying history:
it showed that if a lab had used AcquireML from the start, it would have
reached high accuracy with far fewer experiments than random selection.

This module does something real: given a CSV of NEW, UNTESTED bacterial
strains (just their DNA fingerprints — no resistance labels), it trains a
model on all available historical data and tells you which strains to test
first.  Rank 1 = the experiment that would teach the model the most.

Expected input CSV format
-------------------------
- Rows   : one per bacterial strain (use a sample ID as the row index)
- Columns: unitig sequences matching the training data column names
- Values : binary (1 = DNA fragment present, 0 = absent)
- NO resistance label column — these are the strains you haven't tested yet

Example
-------
    python -m acquireml.recommend \\
        --antibiotic azm \\
        --input-file my_new_strains.csv \\
        --top-n 10 \\
        --output recommendations.csv

The output (terminal table + optional CSV) shows each strain ranked by how
much information the model thinks it would gain from testing it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box as rich_box

from acquireml import __version__
from acquireml.loader import DataLoader
from acquireml.explain import predict_at_threshold, train_full_model
from acquireml.strategies import UncertaintySampling, _binary_entropy

console = Console()


def load_new_strains(input_file: Path) -> pd.DataFrame:
    """Read the user-supplied CSV of unlabelled strains.

    Accepts comma- or tab-separated files.  The first column is treated as
    the sample ID index.  Raises a clear error if the file looks wrong.
    """
    try:
        df = pd.read_csv(input_file, index_col=0)
    except Exception as exc:
        raise ValueError(
            f"Could not read {input_file}: {exc}\n"
            "Make sure the file is a CSV with sample IDs in the first column."
        ) from exc

    if df.empty or df.shape[1] == 0:
        raise ValueError(
            f"{input_file} appears empty or has only one column. "
            "Expected: rows = strains, columns = unitig sequences."
        )
    return df


def align_to_training(
    X_new: pd.DataFrame,
    training_columns: list[str],
) -> tuple[pd.DataFrame, float]:
    """Align new strains to the exact column set the model was trained on.

    Missing columns are filled with 0 (unitig absent in these strains).
    Extra columns are dropped (not part of the training vocabulary).
    The column order is matched exactly so the model receives the right input.

    Returns
    -------
    X_aligned : pd.DataFrame  — same columns and order as training data
    coverage  : float         — fraction of training columns present in new data
    """
    present = set(X_new.columns) & set(training_columns)
    coverage = len(present) / len(training_columns) if training_columns else 0.0
    X_aligned = X_new.reindex(columns=training_columns, fill_value=0).astype(np.uint8)
    return X_aligned, coverage


def rank_strains(
    model,
    X_aligned: pd.DataFrame,
    top_n: int | None,
) -> pd.DataFrame:
    """Score every new strain by uncertainty and return a ranked DataFrame.

    The strain ranked #1 is the one the model is most uncertain about —
    the experiment that would provide the most new information.
    """
    proba = model.predict_proba(X_aligned.values)
    uncertainty = _binary_entropy(proba)
    predictions = predict_at_threshold(model, X_aligned.values)

    # Sort all strains from most → least uncertain
    order = np.argsort(uncertainty)[::-1]

    results = pd.DataFrame({
        "rank":             np.arange(1, len(order) + 1),
        "strain_id":        X_aligned.index[order],
        "uncertainty_score": uncertainty[order].round(6),
        "p_resistant":      proba[order, 1].round(4) if proba.shape[1] > 1
                            else np.zeros(len(order)),
        "predicted_class":  ["Resistant" if p == 1 else "Sensitive"
                             for p in predictions[order]],
    })

    if top_n is not None:
        results = results.head(top_n)

    return results.reset_index(drop=True)


def print_results(results: pd.DataFrame, antibiotic: str, n_total: int) -> None:
    """Render a Rich table of the ranked recommendations."""
    drug_names = {"azm": "Azithromycin", "cip": "Ciprofloxacin", "cfx": "Cefixime"}
    drug = drug_names.get(antibiotic, antibiotic.upper())

    showing = len(results)
    table = Table(
        title=f"Recommended Experiments — {drug} Resistance\n"
              f"Showing top {showing} of {n_total} submitted strains  ·  "
              f"Rank 1 = test this first",
        box=rich_box.ROUNDED,
        header_style="bold magenta",
        border_style="bright_black",
    )
    table.add_column("Rank",       justify="right", style="dim", min_width=4)
    table.add_column("Strain ID",  justify="left")
    table.add_column("Uncertainty",justify="right", style="bold")
    table.add_column("P(Resistant)",justify="right")
    table.add_column("Prediction", justify="left")

    for row in results.itertuples():
        pred_colour = "red" if row.predicted_class == "Resistant" else "green"
        table.add_row(
            str(row.rank),
            str(row.strain_id),
            f"{row.uncertainty_score:.4f}",
            f"{row.p_resistant:.3f}",
            f"[{pred_colour}]{row.predicted_class}[/{pred_colour}]",
        )

    console.print(table)
    console.print(
        "\n  [dim]Uncertainty score: 1.0 = model is completely unsure (test this first)  ·  "
        "0.0 = model is confident (lower priority)[/dim]"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="acquireml.recommend",
        description="Rank new, unlabelled bacterial strains by experimental priority",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--antibiotic", choices=["azm", "cip", "cfx"], default="azm",
        help="Which antibiotic model to train",
    )
    p.add_argument(
        "--data-dir", type=Path, default=Path("data"),
        help="Directory containing training data (or archive.zip)",
    )
    p.add_argument(
        "--input-file", type=Path, required=True,
        metavar="CSV",
        help="CSV of new unlabelled strains (rows=strains, cols=unitigs)",
    )
    p.add_argument(
        "--top-n", type=int, default=None,
        metavar="N",
        help="Show only the top N recommendations (default: show all)",
    )
    p.add_argument(
        "--output", type=Path, default=None,
        metavar="CSV",
        help="Save full ranked list as a CSV file",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main() -> None:
    args = _build_parser().parse_args()

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  "
            "[italic]Live Experiment Recommender[/italic]",
            border_style="cyan",
        )
    )

    # ── Load and validate new strains ─────────────────────────────────────────
    try:
        X_new = load_new_strains(args.input_file)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)

    console.print(f"  [bold]New strains:[/bold] {len(X_new):,}  ·  "
                  f"[bold]Columns in file:[/bold] {X_new.shape[1]:,}\n")

    # ── Load training data ────────────────────────────────────────────────────
    with console.status("[bold]Loading training dataset…[/bold]"):
        try:
            loader = DataLoader(data_dir=args.data_dir, antibiotic=args.antibiotic)
            X_train, y_train = loader.load()
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    training_columns = list(X_train.columns)
    console.print(f"  [bold]Training data:[/bold] {len(X_train):,} samples  ·  "
                  f"{len(training_columns):,} unitigs  ·  "
                  f"{y_train.sum():,} resistant ({y_train.mean():.1%})\n")

    # ── Align columns ─────────────────────────────────────────────────────────
    X_aligned, coverage = align_to_training(X_new, training_columns)
    if coverage < 0.5:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Only {coverage:.0%} of training "
            f"unitig columns are present in your input file. "
            f"Results may be unreliable — verify your CSV column names match "
            f"the unitig sequences in the training .Rtab file.\n"
        )
    else:
        console.print(f"  [bold]Column coverage:[/bold] {coverage:.1%} of training "
                      f"features present in new data\n")

    # ── Train model ───────────────────────────────────────────────────────────
    with console.status(
        f"[bold]Training {args.antibiotic.upper()} model on {len(X_train):,} samples…[/bold]"
    ):
        model = train_full_model(X_train, y_train, random_state=args.seed)

    # ── Rank strains ──────────────────────────────────────────────────────────
    with console.status("[bold]Ranking strains by experimental value…[/bold]"):
        results = rank_strains(model, X_aligned, top_n=args.top_n)

    # ── Display ───────────────────────────────────────────────────────────────
    print_results(results, antibiotic=args.antibiotic, n_total=len(X_new))

    # ── Save CSV ──────────────────────────────────────────────────────────────
    if args.output:
        # Always save the full ranking even if --top-n limits the display
        full_results = rank_strains(model, X_aligned, top_n=None)
        full_results.to_csv(args.output, index=False)
        console.print(f"\n  Full ranking saved → [bold]{args.output.resolve()}[/bold]")

    console.rule(style="bright_black")


if __name__ == "__main__":
    main()
