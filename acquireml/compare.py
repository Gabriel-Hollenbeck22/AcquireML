"""
compare.py — Learning Curve Comparison: Active Learning vs Random Sampling

Runs the simulation multiple times with different random seeds so the results
aren't a fluke of one lucky (or unlucky) starting sample.  Then plots both
strategies on the same chart so we can see which one learns faster.

Usage:
    python -m acquireml.compare
    python -m acquireml.compare --antibiotic cip --iterations 20 --runs 5
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.ensemble import RandomForestClassifier

from acquireml.loader import DataLoader
from acquireml.engine import ActiveLearningEngine
from acquireml.strategies import UncertaintySampling, RandomSampling


# ── Colours ───────────────────────────────────────────────────────────────────
COLOUR_AL = "#2563EB"    # blue  — Active Learning
COLOUR_RS = "#DC2626"    # red   — Random Sampling


def _run_strategy(X, y, strategy, initial_pool: int, batch: int,
                  iterations: int, seed: int) -> list[dict]:
    """Run one full simulation and return the history list."""
    engine = ActiveLearningEngine(
        X=X,
        y=y,
        estimator=RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        ),
        strategy=strategy,
        initial_pool_size=initial_pool,
        batch_size=batch,
        random_state=seed,          # <-- same seed = same starting 10 samples
    )
    return engine.run(iterations)


def _extract_curve(history: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Pull (known_pool_sizes, balanced_accuracies) arrays out of a history."""
    sizes = np.array([m["known_pool_size"] for m in history])
    accs  = np.array([m["balanced_accuracy"] for m in history])
    return sizes, accs


def run_comparison(
    X, y,
    antibiotic: str,
    initial_pool: int,
    batch: int,
    iterations: int,
    n_runs: int,
    output_path: Path,
) -> None:
    """Run both strategies n_runs times, average the curves, and save the chart."""

    al_curves: list[np.ndarray] = []
    rs_curves: list[np.ndarray] = []
    x_axis: np.ndarray | None = None

    print(f"\nRunning {n_runs} simulation(s) × 2 strategies "
          f"({iterations} iterations each)…\n")

    for run in range(n_runs):
        seed = run  # different seed each run → different starting pool each run

        al_hist = _run_strategy(X, y, UncertaintySampling(),
                                initial_pool, batch, iterations, seed)
        rs_hist = _run_strategy(X, y, RandomSampling(random_state=seed),
                                initial_pool, batch, iterations, seed)

        sizes, al_acc = _extract_curve(al_hist)
        _,     rs_acc = _extract_curve(rs_hist)

        if x_axis is None:
            x_axis = sizes  # same for every run

        al_curves.append(al_acc)
        rs_curves.append(rs_acc)

        # Print a one-line summary for each run so the user can see progress
        print(f"  Run {run + 1}/{n_runs} | "
              f"AL final: {al_acc[-1]:.4f} | RS final: {rs_acc[-1]:.4f} | "
              f"Δ = {al_acc[-1] - rs_acc[-1]:+.4f}")

    # Stack into 2-D arrays (n_runs × n_iterations+1) and compute statistics
    al_mat = np.vstack(al_curves)
    rs_mat = np.vstack(rs_curves)

    al_mean, al_std = al_mat.mean(axis=0), al_mat.std(axis=0)
    rs_mean, rs_std = rs_mat.mean(axis=0), rs_mat.std(axis=0)

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))

    # Shaded bands show ± 1 standard deviation across runs
    ax.fill_between(x_axis, al_mean - al_std, al_mean + al_std,
                    alpha=0.15, color=COLOUR_AL)
    ax.fill_between(x_axis, rs_mean - rs_std, rs_mean + rs_std,
                    alpha=0.15, color=COLOUR_RS)

    # Main lines
    ax.plot(x_axis, al_mean, color=COLOUR_AL, linewidth=2.5,
            label="Active Learning (Uncertainty Sampling)")
    ax.plot(x_axis, rs_mean, color=COLOUR_RS, linewidth=2.5,
            linestyle="--", label="Random Sampling (Baseline)")

    # Mark the start point
    ax.axvline(x=initial_pool, color="grey", linestyle=":", linewidth=1,
               alpha=0.7, label=f"Starting point ({initial_pool} samples)")

    # Labels, title, legend
    drug_names = {"azm": "Azithromycin", "cip": "Ciprofloxacin", "cfx": "Cefixime"}
    drug = drug_names.get(antibiotic, antibiotic.upper())

    ax.set_title(
        f"AcquireML — Active Learning vs Random Sampling\n"
        f"{drug} Resistance · {n_runs} run(s) · mean ± 1 std",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xlabel("Number of Lab Experiments Run (Known Pool Size)", fontsize=11)
    ax.set_ylabel("Balanced Accuracy", fontsize=11)
    ax.set_ylim(0.4, 1.02)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    # Annotation: gap at the final iteration
    gap = al_mean[-1] - rs_mean[-1]
    ax.annotate(
        f"Δ = {gap:+.3f} accuracy\nat {x_axis[-1]} experiments",
        xy=(x_axis[-1], al_mean[-1]),
        xytext=(x_axis[-1] * 0.72, al_mean[-1] - 0.07),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2),
        fontsize=9,
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\nChart saved → {output_path.resolve()}")
    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="acquireml.compare",
        description="Compare Active Learning vs Random Sampling learning curves",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--antibiotic", choices=["azm", "cip", "cfx"], default="azm")
    p.add_argument("--data-dir",   type=Path,  default=Path("data"))
    p.add_argument("--iterations", type=int,   default=15,
                   help="Active learning iterations per run")
    p.add_argument("--initial-pool", type=int, default=10)
    p.add_argument("--batch-size",   type=int, default=25,
                   help="Experiments recommended per iteration")
    p.add_argument("--runs", type=int, default=5,
                   help="Independent repetitions (more = smoother curve)")
    p.add_argument("--output", type=Path, default=Path("learning_curve.png"))
    return p


def main() -> None:
    args = _build_parser().parse_args()

    print("Loading genomic dataset…")
    loader = DataLoader(data_dir=args.data_dir, antibiotic=args.antibiotic)
    X, y = loader.load()
    print(f"  {len(X):,} samples · {X.shape[1]:,} unitigs · "
          f"{y.sum():,} resistant ({y.mean():.1%})")

    run_comparison(
        X=X, y=y,
        antibiotic=args.antibiotic,
        initial_pool=args.initial_pool,
        batch=args.batch_size,
        iterations=args.iterations,
        n_runs=args.runs,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
