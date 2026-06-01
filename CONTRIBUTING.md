# Contributing to AcquireML

Thanks for your interest. AcquireML is an early-stage research project and contributions are welcome — whether that's a bug report, a new query strategy, or an additional antibiotic dataset.

---

## Ways to Contribute

- **Report a bug** — open a GitHub Issue with the error message and the command you ran
- **Suggest or implement a new query strategy** — see the section below
- **Add a new antibiotic dataset** — see the section below
- **Improve documentation or usage examples** — edit `README.md` or the module docstrings
- **Ask a question** — open a GitHub Issue labeled `question`

---

## Development Setup

```bash
git clone https://github.com/Gabriel-Hollenbeck22/AcquireML.git
cd AcquireML
pip install -e ".[dev]"
make test   # should show 38 passing tests
```

You'll also need to download the dataset. Place `archive.zip` from [Kaggle](https://www.kaggle.com/datasets/deepcontractor/identifying-antibiotic-resistant-bacteria) in the `data/` directory. AcquireML extracts it automatically on first run.

---

## Adding a New Query Strategy

The engine is designed to be extended. All query strategies live in `acquireml/strategies.py` and inherit from `QueryStrategy`:

```python
class QueryStrategy(ABC):
    @abstractmethod
    def select_batch(
        self,
        model: BaseEstimator,
        X_pool: np.ndarray,
        n: int,
    ) -> np.ndarray:
        """Return indices (into X_pool rows) of the n most informative samples."""
```

To add your own strategy, implement `select_batch()` and return an array of integer indices into `X_pool`. That's the entire contract.

**Example — a strategy that picks the samples with the highest predicted probability of resistance:**

```python
class HighConfidenceResistanceSampling(QueryStrategy):
    """Preferentially test strains the model thinks are most likely resistant."""

    def select_batch(self, model, X_pool, n):
        proba = model.predict_proba(X_pool)[:, 1]
        return np.argsort(proba)[::-1][:n]
```

Once written, your strategy works automatically with `ActiveLearningEngine`, `compare.py`, and `recommend.py` — no other changes needed.

---

## Adding a New Antibiotic Dataset

The antibiotic → file mapping lives at the top of `acquireml/loader.py`:

```python
ANTIBIOTIC_MAP: dict[str, tuple[str, str]] = {
    "azm": ("azm_sr_gwas_filtered_unitigs.Rtab", "azm_sr"),
    "cip": ("cip_sr_gwas_filtered_unitigs.Rtab", "cip_sr"),
    "cfx": ("cfx_sr_gwas_filtered_unitigs.Rtab", "cfx_sr"),
}
```

To add a new antibiotic, add one entry: `"short_name": ("filename.Rtab", "label_column")`. The `.Rtab` file should be space-separated with unitig sequences as rows and sample IDs as columns (the standard format — `DataLoader` transposes it automatically).

---

## Code Style

- Standard Python — no linter enforced, no formatter required
- Comments should explain the *why*, not the *what*
- Follow the existing module pattern: a class or set of functions, a `main()` function, an `_build_parser()` function, and a docstring at the top of the file explaining what it does in plain English

---

## Running Tests

```bash
make test          # runs all 38 tests with verbose output
```

Tests live in `tests/`. Each module has its own test file (`test_loader.py`, `test_engine.py`, `test_recommend.py`, `test_validate.py`). New functionality should come with tests — look at the existing files for the fixture pattern used.

---

## Questions

Open a GitHub Issue at [github.com/Gabriel-Hollenbeck22/AcquireML/issues](https://github.com/Gabriel-Hollenbeck22/AcquireML/issues).
