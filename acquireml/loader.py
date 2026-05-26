from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

ANTIBIOTIC_MAP: dict[str, tuple[str, str]] = {
    "azm": ("azm_sr_gwas_filtered_unitigs.Rtab", "azm_sr"),
    "cip": ("cip_sr_gwas_filtered_unitigs.Rtab", "cip_sr"),
    "cfx": ("cfx_sr_gwas_filtered_unitigs.Rtab", "cfx_sr"),
}


class DataLoader:
    """Loads and aligns genomic unitig features with antibiotic resistance labels.

    Rtab files ship with unitigs as rows and samples as columns; this class
    transposes them so the returned X is (samples × unitigs), consistent with
    scikit-learn conventions.  Samples missing a resistance label are dropped
    before the feature matrix is returned.
    """

    def __init__(self, data_dir: str | Path, antibiotic: str = "azm") -> None:
        self.data_dir = Path(data_dir)
        if antibiotic not in ANTIBIOTIC_MAP:
            raise ValueError(
                f"antibiotic must be one of {list(ANTIBIOTIC_MAP.keys())}, got {antibiotic!r}"
            )
        self.antibiotic = antibiotic
        self._rtab_filename, self._label_col = ANTIBIOTIC_MAP[antibiotic]
        self._ensure_extracted()

    def _ensure_extracted(self) -> None:
        rtab_path = self.data_dir / self._rtab_filename
        zip_path = self.data_dir / "archive.zip"
        if not rtab_path.exists():
            if not zip_path.exists():
                raise FileNotFoundError(
                    f"Neither {rtab_path} nor {zip_path} was found. "
                    "Place archive.zip in the data directory."
                )
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(self.data_dir)

    def load(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Return aligned feature matrix X and resistance label vector y.

        Returns
        -------
        X : pd.DataFrame, shape (n_samples, n_unitigs)
            Binary unitig presence/absence matrix indexed by sample ID.
        y : pd.Series, shape (n_samples,)
            Integer resistance labels (1 = resistant, 0 = sensitive).
        """
        rtab_path = self.data_dir / self._rtab_filename
        metadata_path = self.data_dir / "metadata.csv"

        # Raw Rtab: index = unitig sequences, columns = sample IDs.
        X_raw = pd.read_csv(rtab_path, sep=" ", index_col=0, low_memory=False)
        X = X_raw.T.astype(np.uint8)
        del X_raw

        metadata = pd.read_csv(metadata_path, index_col=0)
        metadata = metadata.dropna(subset=[self._label_col])

        common_idx = X.index.intersection(metadata.index)
        if len(common_idx) == 0:
            raise ValueError(
                "No samples overlap between the Rtab file and metadata.csv. "
                "Verify that sample ID formats are consistent between files."
            )

        X = X.loc[common_idx]
        y = metadata.loc[common_idx, self._label_col].astype(int)
        y.name = self._label_col

        return X, y

    def summary(self) -> str:
        X, y = self.load()
        return (
            f"Antibiotic : {self.antibiotic.upper()}\n"
            f"Samples    : {len(X):,}\n"
            f"Unitigs    : {X.shape[1]:,}\n"
            f"Resistant  : {y.sum():,} ({y.mean():.1%})\n"
            f"Sensitive  : {(y == 0).sum():,} ({(y == 0).mean():.1%})"
        )
