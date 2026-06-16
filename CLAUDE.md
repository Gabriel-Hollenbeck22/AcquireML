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
- `make test`      — run all tests (100 on main)

CLI entry point: `acquireml --antibiotic azm --iterations 10` (registered via pyproject.toml).

**Session commands** (real-world lab loop — merged to main):
```
acquireml session init --data labeled.csv --label-col resistance --pool unlabeled.csv --name proj --patience 3 --min-delta 0.005
acquireml session recommend --batch-size 10 --output recommendations.csv
acquireml session update results.csv
acquireml session status
acquireml session history
```

## Repository Structure

```
acquireml/                  Python package
  __init__.py               version = "0.1.0"
  loader.py                 DataLoader — reads .Rtab, transposes, aligns X/y, auto-extracts zip
  strategies.py             QueryStrategy ABC + UncertaintySampling + RandomSampling
  engine.py                 ActiveLearningEngine — the hindsight active-learning simulation loop
  cli.py                    Rich terminal dashboard + session subcommand dispatcher
  compare.py                Learning-curve comparison: active learning vs random sampling
  explore.py                4-panel EDA / dataset overview chart
  explain.py                Feature importance (which DNA fragments predict resistance)
  recommend.py              Phase 3 product: rank NEW unlabeled strains by experimental priority
  validate.py               Rigorous holdout validation on genuinely-unseen strains
  generic_loader.py         Format-agnostic loader: CSV/TSV/Excel/Rtab, auto-detected by extension
  session.py                SQLite-backed prospective active learning session (real-world loop)
  session_cli.py            CLI subcommands for the session workflow
tests/                      100 tests (test_loader/test_engine/test_recommend/test_validate/
                              test_generic_loader/test_session)
docs/                       Charts committed for README display (PNGs)
data/                       archive.zip + extracted .Rtab + metadata.csv (NOT in git — too big)
Makefile                   Developer shortcuts
pyproject.toml             Package config, deps, entry point (openpyxl added for Excel support)
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
- **Feature branch workflow:** one feature per branch, test until 100% green, demo running,
  then Gabe approves commit. Never commit mid-build. Never ask permission during a build.

## Branch Map (as of 2026-06-16)

- `main` — Phases 1–3 + holdout validation + real-world engine + stopping criteria +
  cost tracking + batch diversity + round report + VCF support + model selection +
  calibration. 148 tests. Stable. Pushed to GitHub.
- All eight feature branches (`feature/real-world-engine`, `feature/stopping-criteria`,
  `feature/cost-tracking`, `feature/batch-diversity`, `feature/round-report`,
  `feature/vcf-support`, `feature/model-selection`, `feature/calibration`) are merged
  into `main`. They still exist as branches but are no longer ahead of main.
- Reminder: after merging a feature branch into local main, always `git push origin main`
  right away — local merges are invisible on GitHub until pushed.

## Session Module Design

**GenericLoader** (`generic_loader.py`): accepts CSV, TSV, Excel, or Rtab. Format detected
from extension; content-sniffed if ambiguous. Returns `(X, y)` where y is None for unlabeled
files. Drop-in alongside existing DataLoader — does not replace it.

**Session** (`session.py`): SQLite-backed prospective loop. Three tables: `meta` (config),
`samples` (id + status: known/pool/pending), `rounds` (accuracy history). Feature data is
NOT stored in the DB — reloaded from original files on demand. Stopping criteria: configurable
`patience` (rounds) and `min_delta` (minimum accuracy improvement). Warning fires in
`update`, `recommend`, and `status` output when plateau detected.

**Session workflow for a researcher:**
1. `session init` — provide labeled data + unlabeled pool
2. `session recommend` — get CSV of top-N most informative samples to test
3. Fill in the `label` column in the CSV (0/1)
4. `session update results.csv` — feed results back, model retrains
5. Repeat until stopping warning fires or pool is exhausted

## Feature Roadmap

Building one at a time, each on its own branch, merged to main once 100% tested:
1. ✅ Stopping criteria (patience + min_delta) — merged
2. ✅ Cost tracking — researcher inputs cost-per-experiment; session tracks spend vs accuracy — merged
3. ✅ Batch diversity — diversity term added to uncertainty sampling via `DiverseSampling` — merged
4. ✅ Round report — `round_report.py` auto-generates an accuracy (+ cost, if tracked) curve
   PNG after each `session update`, configurable via `session init --report-path` — merged
5. ✅ VCF file support — `GenericLoader` parses .vcf/.vcf.gz (GATK/bcftools output) into the
   same binary presence/absence matrix convention as Rtab — merged
6. ✅ Model selection — `--model rf|gbm|lr|svm` flag on `session init`, built via
   `build_estimator()` in explain.py — merged
7. ✅ Calibration — `--calibrate`/`--calibration-method sigmoid|isotonic` on `session init`
   wraps the model in CalibratedClassifierCV, with automatic fallback when a round's known
   pool is too small/imbalanced for cross-validation — merged
8. Demo mode / synthetic data generator — try the tool without real data — **next up**

## Current Status & What's Next

148 tests passing on main. Repo still private. All work pushed to GitHub.

**Technical:** Feature branch work ongoing (see roadmap above). Next (and last roadmap)
feature to build: demo mode / synthetic data generator.

**Outreach (paused pending repo going public):**
- Pre-outreach prep: flip repo public (day before first email), write a founder's one-pager.
- Reach out to AMR researchers to LEARN (not pitch): top target Prof. Yonatan Grad (Harvard,
  N. gonorrhoeae genomics leader); also Dr. Nicole Wheeler (Birmingham, ML for AMR).
- LinkedIn outreach prompt already drafted (ask Claude to surface it from conversation history).

## Working Style With Gabe

Beginner CS student + founder mindset. Explain plainly, what-before-how, use analogies. He prefers
polished autonomous design calls over mid-flow clarifying questions. Slow, summer-long pace —
prioritize understanding over speed. During implementation: make autonomous calls, no mid-build
questions, demo it running before reporting done.
