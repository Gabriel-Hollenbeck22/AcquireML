from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich import box as rich_box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sklearn.ensemble import RandomForestClassifier

from acquireml import __version__
from acquireml.engine import ActiveLearningEngine
from acquireml.loader import DataLoader
from acquireml.strategies import UncertaintySampling
from acquireml.session_cli import build_session_parser

console = Console()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="acquireml",
        description="AcquireML — Autonomous Active Learning Engine for genomic optimization",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = p.add_subparsers(dest="command")
    build_session_parser(subparsers)

    # Legacy simulation flags live on the top-level parser for backward compat
    p.add_argument(
        "--antibiotic",
        choices=["azm", "cip", "cfx"],
        default="azm",
        help="Antibiotic resistance target",
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        metavar="PATH",
        help="Directory containing .Rtab files and metadata.csv (or archive.zip)",
    )
    p.add_argument(
        "--iterations",
        type=int,
        default=10,
        metavar="N",
        help="Active learning iterations to simulate",
    )
    p.add_argument(
        "--initial-pool",
        type=int,
        default=10,
        metavar="N",
        help="Samples seeding the initial Known Pool",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=10,
        metavar="N",
        help="Samples recommended per iteration (lab batch size)",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _delta(current: float, previous: float) -> str:
    diff = current - previous
    color = "green" if diff >= 0 else "red"
    sign = "+" if diff >= 0 else ""
    return f"[{color}]{sign}{diff:.4f}[/{color}]"


def main() -> None:
    args = _build_parser().parse_args()

    # Dispatch session subcommand
    if args.command == "session":
        args.func(args)
        return

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  "
            "[italic]Autonomous Experimental Engine[/italic]",
            border_style="cyan",
        )
    )

    # ── Load data ─────────────────────────────────────────────────────
    with console.status("[bold]Extracting and loading genomic dataset…[/bold]"):
        try:
            loader = DataLoader(data_dir=args.data_dir, antibiotic=args.antibiotic)
            X, y = loader.load()
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    console.print(
        f"  [bold]Target[/bold]    [magenta]{args.antibiotic.upper()}[/magenta] resistance\n"
        f"  [bold]Samples[/bold]   {len(X):,}  ·  "
        f"[bold]Unitigs[/bold]  {X.shape[1]:,}\n"
        f"  [bold]Resistant[/bold] {y.sum():,} ({y.mean():.1%})  ·  "
        f"[bold]Sensitive[/bold] {(y == 0).sum():,} ({(y == 0).mean():.1%})\n"
    )

    # ── Run engine ────────────────────────────────────────────────────
    engine = ActiveLearningEngine(
        X=X,
        y=y,
        estimator=RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=args.seed,
            n_jobs=-1,
        ),
        strategy=UncertaintySampling(),
        initial_pool_size=args.initial_pool,
        batch_size=args.batch_size,
        random_state=args.seed,
    )

    with console.status("[bold]Running active learning simulation…[/bold]"):
        history = engine.run(args.iterations)

    # ── Results dashboard ─────────────────────────────────────────────
    table = Table(
        title=f"Simulation Results — {args.antibiotic.upper()} Resistance Optimization",
        box=rich_box.ROUNDED,
        header_style="bold magenta",
        border_style="bright_black",
    )
    table.add_column("Iter", style="dim", justify="right", min_width=4)
    table.add_column("Known Pool", justify="right")
    table.add_column("Unexplored", justify="right")
    table.add_column("Bal. Accuracy", justify="right", style="bold")
    table.add_column("Explored %", justify="right")
    table.add_column("Δ Accuracy", justify="right")

    for i, m in enumerate(history):
        label = "Init" if i == 0 else str(i)
        delta_str = "" if i == 0 else _delta(m["balanced_accuracy"], history[i - 1]["balanced_accuracy"])
        table.add_row(
            label,
            f"{m['known_pool_size']:,}",
            f"{m['pool_remaining']:,}",
            f"{m['balanced_accuracy']:.4f}",
            f"{m['exploration_rate']:.2%}",
            delta_str,
        )

    console.print(table)

    # ── Summary ───────────────────────────────────────────────────────
    init_acc = history[0]["balanced_accuracy"]
    final_acc = history[-1]["balanced_accuracy"]
    lift = final_acc - init_acc
    sign = "+" if lift >= 0 else ""

    console.print()
    console.print(
        f"  [bold]Baseline accuracy[/bold]  (Init):      {init_acc:.4f}\n"
        f"  [bold]Final accuracy[/bold]    (Iter {args.iterations}):   {final_acc:.4f}  "
        f"([{'green' if lift >= 0 else 'red'}]{sign}{lift:.4f}[/{'green' if lift >= 0 else 'red'}] lift)\n"
        f"  [bold]Explored[/bold]:  {history[-1]['exploration_rate']:.2%} of genetic search space\n"
        f"  [bold]Lab runs[/bold]:  {history[-1]['known_pool_size']:,} / {len(X):,} total samples"
    )
    console.rule(style="bright_black")


if __name__ == "__main__":
    main()
