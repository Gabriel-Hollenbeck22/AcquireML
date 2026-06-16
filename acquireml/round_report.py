"""
round_report.py — Round-by-round accuracy/cost chart for a prospective session

Turns the session's round history (accuracy, and cost if tracked) into a
single PNG so a researcher can see progress at a glance without reading
table output. Regenerated automatically after every `session update`.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive: saves to file, never opens a window
import matplotlib.pyplot as plt

COLOUR_ACC = "#2563EB"   # blue — accuracy
COLOUR_COST = "#16A34A"  # green — cumulative cost


def generate_round_report(
    history: list[dict],
    output_path: str | Path,
    session_name: str = "session",
) -> Path:
    """Plot balanced accuracy (and cumulative cost, if tracked) across rounds.

    Parameters
    ----------
    history : list of round dicts, as returned by Session.history()
        Each dict has round_number, accuracy, cumulative_cost (may be None).
    output_path : where to save the PNG.
    session_name : used in the chart title.

    Returns
    -------
    Path to the saved PNG. Rounds with accuracy=None (e.g. the just-created,
    not-yet-updated round) are skipped.
    """
    output_path = Path(output_path)
    rows = [r for r in history if r.get("accuracy") is not None]

    fig, ax = plt.subplots(figsize=(9, 5.5))

    if not rows:
        ax.text(
            0.5, 0.5, "No completed rounds yet",
            ha="center", va="center", fontsize=12, color="grey",
            transform=ax.transAxes,
        )
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        round_numbers = [r["round_number"] for r in rows]
        accuracies = [r["accuracy"] for r in rows]

        ax.plot(
            round_numbers, accuracies,
            color=COLOUR_ACC, linewidth=2.5, marker="o", markersize=6,
            label="Balanced accuracy",
        )
        ax.set_xlabel("Round", fontsize=11)
        ax.set_ylabel("Balanced Accuracy", color=COLOUR_ACC, fontsize=11)
        ax.set_ylim(0.0, 1.02)
        ax.tick_params(axis="y", labelcolor=COLOUR_ACC)
        ax.set_xticks(round_numbers)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)

        has_cost = any(r.get("cumulative_cost") is not None for r in rows)
        if has_cost:
            costs = [r.get("cumulative_cost") or 0.0 for r in rows]
            ax2 = ax.twinx()
            ax2.plot(
                round_numbers, costs,
                color=COLOUR_COST, linewidth=2, linestyle="--",
                marker="s", markersize=5, label="Cumulative cost",
            )
            ax2.set_ylabel("Cumulative Cost ($)", color=COLOUR_COST, fontsize=11)
            ax2.tick_params(axis="y", labelcolor=COLOUR_COST)
            ax2.spines[["top"]].set_visible(False)

            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="lower right")
        else:
            ax.legend(fontsize=9, loc="lower right")

    ax.set_title(
        f"AcquireML — Round Progress  ·  {session_name}",
        fontsize=13, fontweight="bold", pad=14,
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
