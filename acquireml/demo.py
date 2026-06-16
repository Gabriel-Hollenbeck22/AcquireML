"""
demo.py — Synthetic data generator and zero-setup demo mode

Lets anyone try AcquireML's real-world session loop without the actual
N. gonorrhoeae dataset. Generates a binary feature matrix in the same
presence/absence convention as the Rtab unitig files (1 = "fragment"
present, 0 = absent), where a handful of "causal" features drive the
label and the rest are noise — mirroring the real biology, where a small
number of DNA fragments are far more predictive than the bulk of features.

Usage:
    acquireml demo                       # generate files + print next steps
    acquireml demo --init                # also create a ready-to-use session
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel

from acquireml import __version__

console = Console()


def generate_synthetic_dataset(
    n_known: int = 40,
    n_pool: int = 60,
    n_features: int = 30,
    n_informative: int = 3,
    resistance_rate: float = 0.3,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Generate a synthetic labeled set + unlabeled pool.

    Returns
    -------
    X_known : DataFrame, binary features for the labeled samples
    y_known : Series, binary labels (0/1)
    X_pool  : DataFrame, binary features for the unlabeled samples
    """
    rng = np.random.default_rng(random_state)
    n_total = n_known + n_pool

    X = rng.integers(0, 2, size=(n_total, n_features)).astype(np.uint8)

    # A small set of "causal" features drives the label; everything else is
    # noise, matching the real dataset's finding that one or two DNA
    # fragments carry most of the predictive signal.
    informative_idx = rng.choice(n_features, size=n_informative, replace=False)
    weights = rng.uniform(0.5, 1.5, size=n_informative)
    signal = X[:, informative_idx] @ weights
    noise = rng.normal(0.0, 0.3, size=n_total)
    score = signal + noise

    threshold = np.quantile(score, 1 - resistance_rate)
    y = (score > threshold).astype(int)

    sample_ids = [f"demo_{i:04d}" for i in range(n_total)]
    columns = [f"unitig_{j}" for j in range(n_features)]
    X_df = pd.DataFrame(X, index=sample_ids, columns=columns)
    y_series = pd.Series(y, index=sample_ids, name="resistant")

    known_ids, pool_ids = sample_ids[:n_known], sample_ids[n_known:]
    return X_df.loc[known_ids], y_series.loc[known_ids], X_df.loc[pool_ids]


def write_demo_files(
    output_dir: str | Path,
    n_known: int = 40,
    n_pool: int = 60,
    n_features: int = 30,
    n_informative: int = 3,
    resistance_rate: float = 0.3,
    random_state: int = 42,
) -> dict:
    """Write demo_labeled.csv and demo_pool.csv to output_dir. Returns a summary dict."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    X_known, y_known, X_pool = generate_synthetic_dataset(
        n_known=n_known,
        n_pool=n_pool,
        n_features=n_features,
        n_informative=n_informative,
        resistance_rate=resistance_rate,
        random_state=random_state,
    )

    labeled_path = output_dir / "demo_labeled.csv"
    pool_path = output_dir / "demo_pool.csv"

    labeled_df = X_known.copy()
    labeled_df["resistant"] = y_known
    labeled_df.to_csv(labeled_path)
    X_pool.to_csv(pool_path)

    return {
        "labeled_path": labeled_path,
        "pool_path": pool_path,
        "n_known": len(X_known),
        "n_pool": len(X_pool),
        "n_features": n_features,
        "n_resistant": int(y_known.sum()),
        "resistance_rate": float(y_known.mean()),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_demo(args: argparse.Namespace) -> None:
    summary = write_demo_files(
        output_dir=args.output_dir,
        n_known=args.n_known,
        n_pool=args.n_pool,
        n_features=args.n_features,
        n_informative=args.n_informative,
        resistance_rate=args.resistance_rate,
        random_state=args.seed,
    )

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  Demo data generated",
            border_style="cyan",
        )
    )
    console.print(f"  [bold]Labeled samples[/bold]  {summary['n_known']:,} → {summary['labeled_path']}")
    console.print(f"  [bold]Unlabeled pool[/bold]   {summary['n_pool']:,} → {summary['pool_path']}")
    console.print(f"  [bold]Features[/bold]         {summary['n_features']:,} (binary, like Rtab unitigs)")
    console.print(
        f"  [bold]Resistant[/bold]        {summary['n_resistant']:,} "
        f"({summary['resistance_rate']:.1%}) in the labeled set"
    )

    if not args.init:
        console.print()
        console.print(
            "  Next step: [bold]acquireml session init --data "
            f"{summary['labeled_path']} --label-col resistant --pool "
            f"{summary['pool_path']} --name demo[/bold]"
        )
        return

    from acquireml.session import Session

    db_path = Path(args.output_dir) / "demo_session.db"
    if db_path.exists():
        db_path.unlink()

    with Session(db_path) as sess:
        init_summary = sess.init(
            data_path=summary["labeled_path"],
            label_col="resistant",
            pool_path=summary["pool_path"],
            name="demo",
        )

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  Demo session ready",
            border_style="cyan",
        )
    )
    console.print(f"  [bold]Database[/bold]  {init_summary['db_path']}")
    console.print()
    console.print(
        "  Next step: [bold]acquireml session recommend --db "
        f"{db_path} --batch-size 10 --output recommendations.csv[/bold]"
    )


def build_demo_parser(subparsers) -> None:
    """Attach the 'demo' subcommand to an existing subparsers object."""
    p = subparsers.add_parser(
        "demo",
        help="Generate synthetic data to try AcquireML without real lab data",
    )
    p.add_argument("--output-dir", type=Path, default=Path("demo_data"), metavar="DIR")
    p.add_argument("--n-known", type=int, default=40, metavar="N",
                    help="Labeled samples to generate (default: 40)")
    p.add_argument("--n-pool", type=int, default=60, metavar="N",
                    help="Unlabeled pool samples to generate (default: 60)")
    p.add_argument("--n-features", type=int, default=30, metavar="N",
                    help="Binary features per sample (default: 30)")
    p.add_argument("--n-informative", type=int, default=3, metavar="N",
                    help="Features that actually drive the label (default: 3)")
    p.add_argument("--resistance-rate", type=float, default=0.3, metavar="F",
                    help="Target fraction of positive/resistant labels (default: 0.3)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--init", action="store_true",
                    help="Also create a ready-to-use session from the generated files")
    p.set_defaults(func=cmd_demo)
