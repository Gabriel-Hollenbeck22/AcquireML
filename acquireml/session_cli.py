"""
session_cli.py — CLI commands for the prospective active learning session

Subcommands
-----------
  init        Create a new session from labeled data + optional unlabeled pool
  recommend   Get the next batch of experiments to run
  update      Feed lab results back and retrain
  status      Show current session state
  history     Show round-by-round accuracy history
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich import box as rich_box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from acquireml import __version__
from acquireml.session import Session, DEFAULT_DB_NAME

console = Console()


# ── Shared parser ─────────────────────────────────────────────────────────────

def _add_db_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--db",
        type=Path,
        default=Path(DEFAULT_DB_NAME),
        metavar="PATH",
        help=f"Session database file (default: {DEFAULT_DB_NAME})",
    )


# ── init ──────────────────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> None:
    with Session(args.db) as sess:
        try:
            summary = sess.init(
                data_path=args.data,
                label_col=args.label_col,
                pool_path=args.pool,
                name=args.name,
                patience=args.patience,
                min_delta=args.min_delta,
                cost_per_sample=args.cost_per_sample,
                diversity_weight=args.diversity,
                report_path=args.report_path,
            )
        except FileExistsError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  Session initialised",
            border_style="cyan",
        )
    )
    console.print(f"  [bold]Name[/bold]           {summary['name']}")
    console.print(f"  [bold]Known pool[/bold]     {summary['n_known']:,} labeled samples")
    console.print(f"  [bold]Unlabeled pool[/bold] {summary['n_pool']:,} samples")
    console.print(f"  [bold]Label column[/bold]   {summary['label_col']!r}")
    console.print(f"  [bold]Stop patience[/bold]  {summary['patience']} rounds  ·  "
                  f"[bold]Min delta[/bold] {summary['min_delta']}")
    if summary["cost_per_sample"] is not None:
        console.print(f"  [bold]Cost/sample[/bold]    ${summary['cost_per_sample']:,.2f}")
    if summary["diversity_weight"] > 0.0:
        console.print(f"  [bold]Diversity[/bold]      {summary['diversity_weight']} "
                      "(0=uncertainty only, 1=diversity only)")
    console.print(f"  [bold]Database[/bold]       {summary['db_path']}")
    console.print(f"  [bold]Round report[/bold]   {summary['report_path']}")
    console.print()
    console.print(
        "  Next step: [bold]acquireml session recommend --batch-size 10 "
        "--output recommendations.csv[/bold]"
    )


# ── recommend ─────────────────────────────────────────────────────────────────

def cmd_recommend(args: argparse.Namespace) -> None:
    with Session(args.db) as sess:
        if not sess.db_path.exists():
            console.print(
                f"[bold red]Error:[/bold red] No session found at {args.db}. "
                "Run 'acquireml session init' first."
            )
            sys.exit(1)
        try:
            results = sess.recommend(
                batch_size=args.batch_size,
                output_path=args.output,
            )
            current_round = sess._get_meta("current_round")
        except RuntimeError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    table = Table(
        title=f"Round {current_round} "
              f"— Recommended Experiments  ·  Fill in 'label' column, then run session update",
        box=rich_box.ROUNDED,
        header_style="bold magenta",
        border_style="bright_black",
    )
    table.add_column("Rank", justify="right", style="dim", min_width=4)
    table.add_column("Sample ID", justify="left")
    table.add_column("Uncertainty", justify="right", style="bold")
    table.add_column("P(Positive)", justify="right")
    table.add_column("Prediction", justify="left")
    table.add_column("Label (fill in)", justify="center", style="yellow")

    for row in results.itertuples():
        colour = "red" if row.predicted_class == "positive" else "green"
        table.add_row(
            str(row.rank),
            str(row.sample_id),
            f"{row.uncertainty_score:.4f}",
            f"{row.p_positive:.3f}",
            f"[{colour}]{row.predicted_class}[/{colour}]",
            "___",
        )

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  "
            f"Round {current_round} Recommendations",
            border_style="cyan",
        )
    )
    console.print(table)
    console.print(
        "\n  [dim]Uncertainty: 1.0 = test this first  ·  0.0 = model is confident[/dim]"
    )
    if results.attrs.get("should_stop"):
        console.print(
            f"\n  [bold yellow]⚠ Stopping recommended:[/bold yellow] "
            f"{results.attrs['stop_reason']}"
        )
    if args.output:
        console.print(
            f"\n  CSV saved → [bold]{Path(args.output).resolve()}[/bold]"
            "\n  Fill in the [bold yellow]label[/bold yellow] column "
            "(0 = negative, 1 = positive), then run:"
            f"\n  [bold]acquireml session update {args.output}[/bold]"
        )


# ── update ────────────────────────────────────────────────────────────────────

def cmd_update(args: argparse.Namespace) -> None:
    with Session(args.db) as sess:
        if not sess.db_path.exists():
            console.print(
                f"[bold red]Error:[/bold red] No session found at {args.db}."
            )
            sys.exit(1)
        try:
            summary = sess.update(args.results)
        except (ValueError, RuntimeError) as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    acc = summary["accuracy"]
    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  "
            f"Round {summary['round']} complete",
            border_style="cyan",
        )
    )
    console.print(f"  [bold]Results returned[/bold]    {summary['n_returned']}")
    console.print(f"  [bold]Known pool[/bold]          {summary['n_known']:,} samples")
    console.print(f"  [bold]Unlabeled pool[/bold]      {summary['n_pool']:,} samples remaining")
    console.print(
        f"  [bold]Model accuracy[/bold]      "
        f"[{'green' if acc >= 0.8 else 'yellow'}]{acc:.4f}[/{'green' if acc >= 0.8 else 'yellow'}] "
        f"balanced accuracy (training set)"
    )
    if summary.get("round_cost") is not None:
        console.print(
            f"  [bold]Round cost[/bold]          ${summary['round_cost']:,.2f}  ·  "
            f"[bold]Total spent[/bold] ${summary['cumulative_cost']:,.2f}"
        )
    if summary.get("report_path"):
        console.print(f"  [bold]Round report[/bold]        {summary['report_path']}")
    if summary.get("should_stop"):
        console.print(
            f"\n  [bold yellow]⚠ Stopping recommended:[/bold yellow] "
            f"{summary['stop_reason']}"
        )
    elif summary["n_pool"] > 0:
        console.print(
            "\n  Next: [bold]acquireml session recommend --batch-size 10 "
            "--output recommendations.csv[/bold]"
        )
    else:
        console.print("\n  [bold green]Unlabeled pool exhausted — session complete.[/bold green]")


# ── status ────────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    with Session(args.db) as sess:
        if not sess.db_path.exists():
            console.print(
                f"[bold red]Error:[/bold red] No session at {args.db}."
            )
            sys.exit(1)
        s = sess.status()

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  Session Status",
            border_style="cyan",
        )
    )
    acc_str = f"{s['latest_accuracy']:.4f}" if s["latest_accuracy"] is not None else "n/a"
    console.print(f"  [bold]Session name[/bold]    {s['name']}")
    console.print(f"  [bold]Current round[/bold]   {s['current_round']}")
    console.print(f"  [bold]Known pool[/bold]      {s['n_known']:,}")
    console.print(f"  [bold]Unlabeled pool[/bold]  {s['n_pool']:,}")
    console.print(f"  [bold]Pending results[/bold] {s['n_pending']}")
    console.print(f"  [bold]Latest accuracy[/bold] {acc_str}")
    console.print(f"  [bold]Stop patience[/bold]   {s['patience']} rounds  ·  "
                  f"[bold]Min delta[/bold] {s['min_delta']}")
    if s.get("cost_per_sample") is not None:
        console.print(
            f"  [bold]Cost/sample[/bold]     ${s['cost_per_sample']:,.2f}  ·  "
            f"[bold]Total spent[/bold] ${s['total_cost']:,.2f}"
        )
    dw = s.get("diversity_weight", 0.0)
    console.print(f"  [bold]Diversity[/bold]       {dw} "
                  f"({'diverse+uncertain' if dw > 0 else 'uncertainty only'})")
    if s.get("should_stop"):
        console.print(
            f"\n  [bold yellow]⚠ Stopping recommended:[/bold yellow] {s['stop_reason']}"
        )
    if s.get("report_path"):
        console.print(f"  [bold]Round report[/bold]    {s['report_path']}")
    console.print(f"  [bold]Created[/bold]         {s['created_at']}")


# ── history ───────────────────────────────────────────────────────────────────

def cmd_history(args: argparse.Namespace) -> None:
    with Session(args.db) as sess:
        if not sess.db_path.exists():
            console.print(
                f"[bold red]Error:[/bold red] No session at {args.db}."
            )
            sys.exit(1)
        rows = sess.history()

    if not rows:
        console.print("No rounds completed yet.")
        return

    show_cost = any(r.get("round_cost") is not None for r in rows)

    table = Table(
        title="Session History",
        box=rich_box.ROUNDED,
        header_style="bold magenta",
        border_style="bright_black",
    )
    table.add_column("Round", justify="right", style="dim")
    table.add_column("Known Pool", justify="right")
    table.add_column("Bal. Accuracy", justify="right", style="bold")
    if show_cost:
        table.add_column("Round Cost", justify="right", style="green")
        table.add_column("Total Spent", justify="right", style="bold green")
    table.add_column("Timestamp", justify="left", style="dim")

    for r in rows:
        acc = r["accuracy"]
        acc_str = f"{acc:.4f}" if acc is not None else "pending"
        row_data = [
            str(r["round_number"]),
            f"{r['n_known']:,}",
            acc_str,
        ]
        if show_cost:
            rc = r.get("round_cost")
            cc = r.get("cumulative_cost")
            row_data.append(f"${rc:,.2f}" if rc is not None else "—")
            row_data.append(f"${cc:,.2f}" if cc is not None else "—")
        row_data.append(r["created_at"][:19].replace("T", " "))
        table.add_row(*row_data)

    console.print(
        Panel.fit(
            f"[bold cyan]AcquireML[/bold cyan] v{__version__}  ·  Round History",
            border_style="cyan",
        )
    )
    console.print(table)


# ── Parser ────────────────────────────────────────────────────────────────────

def build_session_parser(subparsers) -> None:
    """Attach the 'session' subcommand group to an existing subparsers object."""
    session_p = subparsers.add_parser(
        "session",
        help="Prospective active learning session (real-world lab loop)",
    )
    session_sub = session_p.add_subparsers(dest="session_cmd", required=True)

    # -- init
    p_init = session_sub.add_parser("init", help="Create a new session")
    _add_db_arg(p_init)
    p_init.add_argument("--data", type=Path, required=True,
                         metavar="FILE",
                         help="Labeled data file (CSV/TSV/Excel/Rtab)")
    p_init.add_argument("--label-col", required=True,
                         metavar="COL",
                         help="Column name containing 0/1 labels")
    p_init.add_argument("--pool", type=Path, default=None,
                         metavar="FILE",
                         help="Unlabeled pool file (no label column)")
    p_init.add_argument("--name", default="session",
                         help="Human-readable session name")
    p_init.add_argument("--patience", type=int, default=3, metavar="N",
                         help="Rounds of no improvement before stopping is recommended (default: 3)")
    p_init.add_argument("--min-delta", type=float, default=0.005, metavar="F",
                         help="Minimum accuracy improvement to count as progress (default: 0.005)")
    p_init.add_argument("--cost-per-sample", type=float, default=None, metavar="COST",
                         help="Cost per lab experiment in your currency (e.g. 150.00). "
                              "Enables spend tracking. Optional.")
    p_init.add_argument("--diversity", type=float, default=0.0, metavar="W",
                         help="Diversity weight for batch selection, 0.0–1.0 "
                              "(0=uncertainty only, 0.5=balanced, 1=diversity only). Default: 0.0")
    p_init.add_argument("--report-path", type=Path, default=None, metavar="PNG",
                         help="Where to (re)write the round progress chart after every "
                              "'session update' (default: <db_stem>_report.png)")
    p_init.set_defaults(func=cmd_init)

    # -- recommend
    p_rec = session_sub.add_parser("recommend", help="Get next experiment batch")
    _add_db_arg(p_rec)
    p_rec.add_argument("--batch-size", type=int, default=10, metavar="N")
    p_rec.add_argument("--output", type=Path, default=None, metavar="CSV",
                        help="Save recommendations to this CSV")
    p_rec.set_defaults(func=cmd_recommend)

    # -- update
    p_upd = session_sub.add_parser("update", help="Feed lab results back")
    _add_db_arg(p_upd)
    p_upd.add_argument("results", type=Path, metavar="RESULTS_CSV",
                        help="Filled-in recommendations CSV")
    p_upd.set_defaults(func=cmd_update)

    # -- status
    p_sta = session_sub.add_parser("status", help="Show session state")
    _add_db_arg(p_sta)
    p_sta.set_defaults(func=cmd_status)

    # -- history
    p_his = session_sub.add_parser("history", help="Show round-by-round history")
    _add_db_arg(p_his)
    p_his.set_defaults(func=cmd_history)
