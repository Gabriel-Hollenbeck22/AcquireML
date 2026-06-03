# AcquireML — Project Context for Claude

This file orients a fresh Claude session (or collaborator) that has no prior context.
Read it fully before working on the project.

## What AcquireML Is

AcquireML is an **Autonomous Experimental Engine** — an active-learning / Bayesian-optimization
tool for genomics. The pitch: most genomics AI tools are *predictive classifiers* (commodity).
AcquireML is different — it's a **"GPS for labs"**: instead of just predicting an outcome, it tells
a scientist *which expensive physical experiment to run next* to map a biological system in the
fewest possible lab trials. It treats high-dimensional genetic variants as a black-box
optimization problem and uses **Uncertainty Sampling** to pick the most informative next experiment.

This is a B2B startup project by Gabe Hollenbeck, a beginner CS student. It's a slow, summer-long,
learning-focused project — not a rush job. Explain things plainly (what before how); Gabe is still
learning ML/CS vocabulary.

## The Problem Domain

Phase 1 dataset: **antibiotic resistance in *Neisseria gonorrhoeae*** (gonorrhea), which is rapidly
evolving to defeat modern antibiotics. Ciprofloxacin went from 0% resistance (1980s) to ~46% today.

The model learns: given a bacterial strain's DNA fingerprint, predict whether it will resist a drug.

## Environment & How to Run (IMPORTANT)

**Python interpreter gotcha:** plain `python3` on this machine may resolve to Xcode's Python 3.9,
which lacks pandas/scikit-learn/matplotlib. The working interpreter is:
`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`
Either run `make install` first (installs the package + deps into whatever `python3` resolves to),
or call that full path directly.

**Directory gotcha:** the repo and package live in the INNER folder
`/Users/gabehollenbeck/Desktop/AcquireML/AcquireML/`. Run all commands from there, or data
paths (`data/...`) will not resolve.

**Common commands** (via Makefile — `PYTHON ?= python3`):
- `make install`   — pip install -e ".[dev]"
- `make run`       — run the active learning engine (AZM, 10 iterations)
- `make compare`   — AL vs Random learning curve (AZM) → learning_curve.png
- `make compare-cip` — same for Ciprofloxacin
- `make explore`   — 4-panel dataset overview → data_overview.png
- `make explain`   — rank predictive DNA fragments → azm_importance.png
- `make recommend` — rank new unlabeled strains (edit --input-file first)
- `make validate`  — holdout test on unseen strains → azm_validation.png
- `make test`      — run all 38 tests

CLI entry point: `acquireml --antibiotic azm --iterations 10` (registered via pyproject.toml).

## Repository Structure

```
acquireml/                  Python package
  __init__.py               version = "0.1.0"
  loader.py                 DataLoader — reads .Rtab, transposes, aligns X/y, auto-extracts zip
  strategies.py             QueryStrategy ABC + UncertaintySampling + RandomSampling
  engine.py                 ActiveLearningEngine — the hindsight active-learning simulation loop
  cli.py                    Rich terminal dashboard (the `acquireml` command)
  compare.py                Learning-curve comparison: active learning vs random sampling
  explore.py                4-panel EDA / dataset overview chart
  explain.py                Feature importance (which DNA fragments predict resistance)
  recommend.py              Phase 3 product: rank NEW unlabeled strains by experimental priority
  validate.py               Rigorous holdout validation on genuinely-unseen strains
tests/                      38 tests (test_loader/test_engine/test_recommend/test_validate)
docs/                       Charts committed for README display (PNGs)
data/                       archive.zip + extracted .Rtab + metadata.csv (NOT in git — too big)
Makefile                   Developer shortcuts
pyproject.toml             Package config, deps, entry point
README.md                  Public-facing project narrative + embedded charts
CONTRIBUTING.md            Collaborator guide
CLAUDE.md                  This file
```

## Data Details & Quirks

Data source: Kaggle — "Identifying Antibiotic Resistant Bacteria". Raw files are NOT in git
(too large). `archive.zip` lives in `data/`; DataLoader auto-extracts on first run.

Three antibiotic targets (each has its own .Rtab unitig matrix):

| Code | Drug          | Rtab file                              | Label col | Labeled | Resistant |
|------|---------------|----------------------------------------|-----------|---------|-----------|
| azm  | Azithromycin  | azm_sr_gwas_filtered_unitigs.Rtab      | azm_sr    | 3,478   | 447 (13%) |
| cip  | Ciprofloxacin | cip_sr_gwas_filtered_unitigs.Rtab      | cip_sr    | 3,088   | 1,428 (46%) |
| cfx  | Cefixime      | cfx_sr_gwas_filtered_unitigs.Rtab      | cfx_sr    | 3,401   | 5 (0.1%)  |

Format quirks (already handled in loader.py — know them before touching data code):
- Rtab filenames use the `_sr` suffix (the original project brief had them wrong).
- Rtab files are space-separated; rows = unitigs, columns = samples → must TRANSPOSE so rows=samples.
- Rtab index column is named `pattern_id`; sample IDs (e.g. ERR1549286) are the column headers.
- metadata.csv index column is `Sample_ID`; target columns end in `_sr`; many are NaN → dropna before aligning.
- Feature values are binary (1 = DNA unitig present, 0 = absent). Labels: 1 = resistant, 0 = sensitive.
- CFX has only 5 resistant samples — too imbalanced to be useful; focus demos on AZM and CIP.

## Key Results (so far)

Holdout validation (train on 80%, predict on 20% the model never saw):
- **CIP: 97.6% balanced accuracy** on 618 unseen strains (ROC-AUC 0.996).
- **AZM: 84.3% balanced accuracy** on 696 unseen strains (ROC-AUC 0.979) — high precision (89.9%),
  lower recall (69.7%) because resistance is rare. Improving AZM recall is an open task.

Active learning vs random sampling (same # experiments):
- AZM: 95.0% vs 83.3% (+11.7 pp). CIP: 99.1% vs 96.9% (+2.2 pp).

Feature importance: for AZM a single DNA fragment explains ~21% of predictive power (matches known
biology — a specific point mutation confers azithromycin resistance). CIP resistance is spread
across many features (matches its multi-gene biology).

## Conventions & Design Decisions

- **Strategy pattern:** new query strategies subclass `QueryStrategy` (in strategies.py) and
  implement `select_batch(model, X_pool, n)`. They then work automatically with engine, compare,
  and recommend — no other changes needed. This is the main extension point.
- **Module pattern:** each runnable module has a top docstring (plain English), a `_build_parser()`
  argparse function, a `main()`, and uses `matplotlib.use("Agg")` (non-interactive — saves to file,
  never opens a GUI window, which previously caused hangs).
- **Charts:** generated PNGs land in the repo root; the ones embedded in the README are copied into
  `docs/` and committed. Root-level PNGs and `demo_*.csv` are gitignored.
- **Reuse over duplication:** e.g. recommend.py imports `train_full_model` from explain.py.

## Git Workflow

- Repo: github.com/Gabriel-Hollenbeck22/AcquireML (currently PRIVATE — see roadmap).
- Commit when work is complete; commit messages end with a `Co-Authored-By: Claude` trailer.
- The notebook (.ipynb) and raw data are gitignored; `docs/*.png` are intentionally committed.

## Current Status & What's Next

Phases 1–3 + holdout validation complete. 38 tests passing. Repo still private.

Next up (see Gabe's auto-memory "Outreach Checklist" for detail):
- Pre-outreach prep: flip repo public (day before first email), write a founder's one-pager.
- Reach out to AMR researchers to LEARN (not pitch): top target Prof. Yonatan Grad (Harvard,
  N. gonorrhoeae genomics leader); also Dr. Nicole Wheeler (Birmingham, ML for AMR).
- Optional technical work: improve AZM recall; add more query strategies; eventually a web UI.

## Working Style With Gabe

Beginner CS student + founder mindset. Explain plainly, what-before-how, use analogies. He prefers
polished autonomous design calls over mid-flow clarifying questions. Slow, summer-long pace —
prioritize understanding over speed.
