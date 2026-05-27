"""
explore.py — Exploratory Data Analysis for the AcquireML dataset.

Generates a 4-panel visual overview that tells the story of the dataset:
  - How bad is the resistance problem for each drug?
  - How has Ciprofloxacin resistance grown over time?
  - Where in the world did these samples come from?
  - How large is each antibiotic's dataset?

Usage:
    python -m acquireml.explore
    python -m acquireml.explore --data-dir data --output data_overview.png
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


# ── Colours ───────────────────────────────────────────────────────────────────
C_RED    = "#DC2626"   # resistant / warning
C_GREEN  = "#16A34A"   # sensitive / good
C_BLUE   = "#2563EB"   # neutral / informational
C_ORANGE = "#EA580C"   # secondary accent


def _ensure_extracted(data_dir: Path) -> None:
    """Unzip archive.zip into data_dir if the flat files aren't already there."""
    if not (data_dir / "metadata.csv").exists():
        zip_path = data_dir / "archive.zip"
        if not zip_path.exists():
            raise FileNotFoundError(
                f"Cannot find archive.zip or metadata.csv in {data_dir}. "
                "Make sure the data directory is correct."
            )
        print("  Extracting archive.zip…")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(data_dir)


def plot_overview(data_dir: Path, output_path: Path) -> None:
    _ensure_extracted(data_dir)

    meta = pd.read_csv(data_dir / "metadata.csv", index_col=0)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(
        "AcquireML  —  Dataset Overview: Antibiotic Resistance in Neisseria gonorrhoeae",
        fontsize=13, fontweight="bold", y=1.01,
    )

    # ── Panel 1: Resistance rate per antibiotic ───────────────────────────────
    ax = axes[0, 0]

    drug_info = {
        "Azithromycin\n(AZM)": "azm_sr",
        "Ciprofloxacin\n(CIP)": "cip_sr",
        "Cefixime\n(CFX)": "cfx_sr",
    }
    names, rates, totals, resistant_counts = [], [], [], []
    for label, col in drug_info.items():
        vals = meta[col].dropna().astype(int)
        names.append(label)
        rates.append(vals.mean() * 100)
        totals.append(len(vals))
        resistant_counts.append(int(vals.sum()))

    bars = ax.bar(names, rates, color=[C_RED, C_RED, C_RED],
                  alpha=0.80, edgecolor="white", linewidth=1.5, width=0.45)

    for bar, rate, res, tot in zip(bars, rates, resistant_counts, totals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.0,
            f"{rate:.1f}%\n({res:,} / {tot:,})",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
        )

    ax.set_title("Resistance Rate by Antibiotic", fontweight="bold", pad=10)
    ax.set_ylabel("% of Tested Strains Resistant")
    ax.set_ylim(0, max(rates) * 1.45)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor("#FAFAFA")

    # ── Panel 2: CIP resistance trend over time ───────────────────────────────
    ax = axes[0, 1]

    ts = meta[["Year", "cip_sr"]].copy()
    ts = ts[ts["Year"].notna() & ts["cip_sr"].notna()]
    # Pandas stores Year as float when NaNs are present — convert cleanly
    ts["Year"] = ts["Year"].astype(float).astype(int)
    ts["cip_sr"] = ts["cip_sr"].astype(int)
    # Keep only plausible years (discard any corrupt entries)
    ts = ts[(ts["Year"] >= 1960) & (ts["Year"] <= 2030)]

    by_year = ts.groupby("Year")["cip_sr"].agg(["mean", "count"])
    by_year = by_year[by_year["count"] >= 5]   # require ≥5 samples per year

    ax.fill_between(by_year.index, by_year["mean"] * 100,
                    alpha=0.18, color=C_RED)
    ax.plot(by_year.index, by_year["mean"] * 100,
            color=C_RED, linewidth=2.5, marker="o", markersize=4, zorder=3)

    # Annotate the alarming crossover above 50 %
    ax.axhline(50, color="grey", linestyle="--", linewidth=0.9,
               alpha=0.6, label="50 % threshold")

    ax.set_title("Ciprofloxacin Resistance Trend Over Time", fontweight="bold", pad=10)
    ax.set_xlabel("Year")
    ax.set_ylabel("% Resistant")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_ylim(0, 100)
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor("#FAFAFA")

    # Add a text note about the trend
    ax.text(
        0.03, 0.93,
        "0 % → ~48 % in 30 years",
        transform=ax.transAxes,
        fontsize=8, color=C_RED, fontstyle="italic",
        verticalalignment="top",
    )

    # ── Panel 3: Geographic distribution ─────────────────────────────────────
    ax = axes[1, 0]

    country_counts = (
        meta["Country"]
        .dropna()
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .value_counts()
        .head(10)
    )

    # Plot horizontal bars (most → least, top to bottom)
    y_pos = range(len(country_counts))
    bars = ax.barh(
        list(country_counts.index)[::-1],
        list(country_counts.values)[::-1],
        color=C_BLUE, alpha=0.80, edgecolor="white",
    )
    for bar in bars:
        ax.text(
            bar.get_width() + 12,
            bar.get_y() + bar.get_height() / 2,
            f"{int(bar.get_width()):,}",
            va="center", fontsize=9,
        )

    ax.set_title("Top 10 Countries by Sample Count", fontweight="bold", pad=10)
    ax.set_xlabel("Number of Bacterial Samples")
    ax.set_xlim(0, country_counts.max() * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor("#FAFAFA")

    # ── Panel 4: Dataset scale (samples + features) per antibiotic ───────────
    ax  = axes[1, 1]
    ax2 = ax.twinx()   # second y-axis for unitig counts

    antibiotics    = ["AZM", "CIP", "CFX"]
    sample_counts  = [
        int(meta["azm_sr"].notna().sum()),
        int(meta["cip_sr"].notna().sum()),
        int(meta["cfx_sr"].notna().sum()),
    ]
    unitig_counts  = [515, 8_873, 384]   # from direct Rtab inspection
    x = np.arange(3)
    w = 0.35

    b1 = ax.bar(x - w / 2, sample_counts, w,
                color=C_GREEN, alpha=0.85, edgecolor="white", label="Labeled Samples")
    b2 = ax2.bar(x + w / 2, unitig_counts, w,
                 color=C_BLUE, alpha=0.85, edgecolor="white", label="DNA Features (Unitigs)")

    for bar in b1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                f"{int(bar.get_height()):,}", ha="center", fontsize=8)
    for bar in b2:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 80,
                 f"{int(bar.get_height()):,}", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(antibiotics)
    ax.set_title("Dataset Scale per Antibiotic", fontweight="bold", pad=10)
    ax.set_ylabel("Labeled Samples", color=C_GREEN)
    ax2.set_ylabel("DNA Features (Unitigs)", color=C_BLUE)
    ax.tick_params(axis="y", labelcolor=C_GREEN)
    ax2.tick_params(axis="y", labelcolor=C_BLUE)
    ax.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    ax.set_facecolor("#FAFAFA")

    legend_handles = [
        mpatches.Patch(color=C_GREEN, label="Labeled Samples"),
        mpatches.Patch(color=C_BLUE,  label="DNA Features (Unitigs)"),
    ]
    ax.legend(handles=legend_handles, fontsize=8, loc="upper right")

    # ── Final layout ──────────────────────────────────────────────────────────
    fig.tight_layout(rect=[0, 0, 1, 0.99])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Overview chart saved → {output_path.resolve()}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="acquireml.explore",
        description="Generate a visual overview of the AcquireML dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--output",   type=Path, default=Path("data_overview.png"))
    return p


def main() -> None:
    args = _build_parser().parse_args()
    print("Generating dataset overview…")
    plot_overview(data_dir=args.data_dir, output_path=args.output)
    print("Done.")


if __name__ == "__main__":
    main()
