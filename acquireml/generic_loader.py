"""
generic_loader.py — Format-agnostic data loader

Accepts .csv, .tsv, .xlsx/.xls, .Rtab, and .vcf/.vcf.gz files. Format is
detected from the file extension; ambiguous extensions are resolved by
content sniffing.

Returns (X, y) in the same convention as DataLoader: rows=samples,
columns=features. y is None when no label_col is specified (unlabeled pool),
and always None for Rtab/VCF since those formats carry no phenotype column.
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd


class GenericLoader:
    """Load tabular lab data from CSV, TSV, Excel, or Rtab files.

    Parameters
    ----------
    data_path : str or Path
    label_col : str, optional
        Column name containing binary labels (0/1). When omitted, y is None.
    """

    def __init__(
        self,
        data_path: str | Path,
        label_col: str | None = None,
    ) -> None:
        self.data_path = Path(data_path)
        self.label_col = label_col
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

    # ── Format detection ──────────────────────────────────────────────────────

    def _detect_format(self) -> str:
        name = self.data_path.name.lower()
        if name.endswith(".vcf") or name.endswith(".vcf.gz"):
            return "vcf"
        ext = self.data_path.suffix.lower()
        if ext == ".rtab":
            return "rtab"
        if ext == ".tsv":
            return "tsv"
        if ext in (".xlsx", ".xls"):
            return "excel"
        if ext == ".csv":
            return "csv"
        return self._sniff_delimiter()

    def _sniff_delimiter(self) -> str:
        with open(self.data_path, "r", encoding="utf-8", errors="replace") as fh:
            first_line = fh.readline()
        return "tsv" if first_line.count("\t") > first_line.count(",") else "csv"

    # ── Readers ───────────────────────────────────────────────────────────────

    def _read_rtab(self) -> pd.DataFrame:
        X_raw = pd.read_csv(self.data_path, sep=" ", index_col=0, low_memory=False)
        return X_raw.T.astype(np.uint8)

    def _read_vcf(self) -> pd.DataFrame:
        """Parse a standard VCF (GATK/bcftools output) into a binary presence matrix.

        Each variant becomes a feature column (1 = sample carries at least one
        non-reference allele at that site, 0 = homozygous reference or missing
        genotype), matching the Rtab convention so VCF data is a drop-in
        alternative to unitig matrices.
        """
        opener = gzip.open if self.data_path.name.lower().endswith(".gz") else open

        samples: list[str] = []
        variant_ids: list[str] = []
        rows: list[list[int]] = []

        with opener(self.data_path, "rt") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("##"):
                    continue
                if line.startswith("#CHROM"):
                    samples = line.lstrip("#").split("\t")[9:]
                    continue
                fields = line.split("\t")
                chrom, pos, vid, ref, alt = fields[:5]
                fmt_fields = fields[8].split(":")
                gt_idx = fmt_fields.index("GT") if "GT" in fmt_fields else 0

                variant_name = vid if vid != "." else f"{chrom}:{pos}_{ref}>{alt}"
                presence = [
                    1
                    if any(
                        a not in ("0", ".", "")
                        for a in sample_field.split(":")[gt_idx].replace("|", "/").split("/")
                    )
                    else 0
                    for sample_field in fields[9:]
                ]
                variant_ids.append(variant_name)
                rows.append(presence)

        if not samples:
            raise ValueError(f"No #CHROM header line found in VCF file: {self.data_path}")

        X = pd.DataFrame(rows, index=variant_ids, columns=samples, dtype=np.uint8)
        return X.T

    def _read_tabular(self, fmt: str) -> pd.DataFrame:
        if fmt == "tsv":
            return pd.read_csv(self.data_path, sep="\t", index_col=0)
        if fmt == "excel":
            return pd.read_excel(self.data_path, index_col=0)
        return pd.read_csv(self.data_path, index_col=0)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
        """Return (X, y).

        Returns
        -------
        X : pd.DataFrame, shape (n_samples, n_features)
        y : pd.Series or None
        """
        fmt = self._detect_format()

        if fmt == "rtab":
            X = self._read_rtab()
            y = None
        elif fmt == "vcf":
            X = self._read_vcf()
            y = None
        else:
            df = self._read_tabular(fmt)
            if self.label_col is not None:
                if self.label_col not in df.columns:
                    raise ValueError(
                        f"Label column {self.label_col!r} not found. "
                        f"Available columns: {list(df.columns)}"
                    )
                y = df[self.label_col].astype(int)
                X = df.drop(columns=[self.label_col])
            else:
                X = df
                y = None

        return X, y

    def summary(self) -> str:
        X, y = self.load()
        fmt = self._detect_format().upper()
        lines = [
            f"File     : {self.data_path.name}",
            f"Format   : {fmt}",
            f"Samples  : {len(X):,}",
            f"Features : {X.shape[1]:,}",
        ]
        if y is not None:
            lines += [
                f"Positive : {int(y.sum()):,} ({y.mean():.1%})",
                f"Negative : {int((y == 0).sum()):,} ({(y == 0).mean():.1%})",
            ]
        return "\n".join(lines)
