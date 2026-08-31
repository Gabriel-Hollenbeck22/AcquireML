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
- `make api`       — run the web UI backend API (dev server, auto-reload)
- `make test`      — run all tests (272 on main)

CLI entry point: `acquireml --antibiotic azm --iterations 10` (registered via pyproject.toml).

**Session commands** (real-world lab loop — merged to main):
```
acquireml session init --data labeled.csv --label-col resistance --pool unlabeled.csv --name proj --patience 3 --min-delta 0.005
acquireml session recommend --batch-size 10 --output recommendations.csv
acquireml session update results.csv
acquireml session status
acquireml session history
acquireml demo --init    # zero-setup: generates synthetic data + a ready-to-use session
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
  generic_loader.py         Format-agnostic loader: CSV/TSV/Excel/Rtab/VCF, auto-detected by extension
  session.py                SQLite-backed prospective active learning session (real-world loop)
  session_cli.py            CLI subcommands for the session workflow
  round_report.py           Generates the accuracy/cost progress PNG after each session update
  demo.py                   Synthetic data generator + `acquireml demo --init` zero-setup session
  api/                      FastAPI web UI backend — store.py (session path resolution),
                              schemas.py (Pydantic models), app.py (the FastAPI app + endpoints)
tests/                      272 tests (test_loader/test_engine/test_recommend/test_validate/
                              test_generic_loader/test_session/test_explain/test_round_report/
                              test_demo/test_api_store/test_api_schemas/test_api_app)
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

Holdout validation (train on 80%, predict on 20% the model never saw). Every model trained via
`train_full_model()` now gets a cross-validated decision threshold (`model.threshold_`, tuned to
maximize balanced accuracy via `explain.find_best_threshold()`) instead of assuming scikit-learn's
default 0.5 cutoff — this fixed AZM's recall gap:
- **CIP: 97.7% balanced accuracy** on 618 unseen strains (ROC-AUC 0.996, precision 95.3%, recall 99.7%).
- **AZM: 93.9% balanced accuracy** on 696 unseen strains (ROC-AUC 0.979, precision 86.0%, recall 89.9%
  — up from 69.7% recall / 84.3% balanced accuracy before threshold tuning, at the cost of ~4pp precision).

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

## Branch Map (as of 2026-07-27)

- `main` — Phases 1–3 + holdout validation + real-world engine + stopping criteria +
  cost tracking + batch diversity + round report + VCF support + model selection +
  calibration + demo mode + AZM recall threshold tuning + landing page + full web UI
  (FastAPI backend + React frontend, all 11 pages — including the Phase 5+6 analysis
  pages: Overview, Explain, Compare, Validate). 272 backend tests + 108 frontend
  tests. Stable. Pushed to GitHub. Repo is public.
- All feature branches (`feature/real-world-engine`, `feature/stopping-criteria`,
  `feature/cost-tracking`, `feature/batch-diversity`, `feature/round-report`,
  `feature/vcf-support`, `feature/model-selection`, `feature/calibration`,
  `feature/demo-mode`) are merged into `main`. They still exist as branches but are
  no longer ahead of main. The web UI branches (`feature/web-ui-backend`,
  `feature/web-ui-frontend-foundation`, `feature/web-ui-dashboard`) and
  `feature/azm-recall-threshold-tuning` were merged and deleted after merge.
- Reminder: after merging a feature branch into local main, always `git push origin main`
  right away — local merges are invisible on GitHub until pushed.

## Session Module Design

**GenericLoader** (`generic_loader.py`): accepts CSV, TSV, Excel, Rtab, or VCF (.vcf/.vcf.gz —
parsed into the same binary presence/absence matrix as Rtab, GT field decides presence/absence,
missing genotypes treated as absent). Format detected from extension; content-sniffed if
ambiguous. Returns `(X, y)` where y is None for unlabeled files (always None for Rtab/VCF).
Drop-in alongside existing DataLoader — does not replace it.

**Session** (`session.py`): SQLite-backed prospective loop. Three tables: `meta` (config),
`samples` (id + status: known/pool/pending), `rounds` (accuracy history). Feature data is
NOT stored in the DB — reloaded from original files on demand. Stopping criteria: configurable
`patience` (rounds) and `min_delta` (minimum accuracy improvement). Warning fires in
`update`, `recommend`, and `status` output when plateau detected. Model trained each round is
selectable via `model` meta (rf/gbm/lr/svm, built by `explain.build_estimator()`), optionally
wrapped in `CalibratedClassifierCV` when `calibrate=True` (auto-falls-back to uncalibrated if
the known pool is too small/imbalanced for cross-validation). After every `update`, an
accuracy/cost progress PNG is regenerated via `round_report.generate_round_report()`.

**Session workflow for a researcher:**
1. `session init` — provide labeled data + unlabeled pool
2. `session recommend` — get CSV of top-N most informative samples to test
3. Fill in the `label` column in the CSV (0/1)
4. `session update results.csv` — feed results back, model retrains
5. Repeat until stopping warning fires or pool is exhausted

**Web UI backend** (`acquireml/api/`): a FastAPI app exposing the same
session lifecycle over local HTTP, for the React frontend. `store.py`
resolves session names to `~/.acquireml/sessions/<name>.db`
(auto-discovered, no path ever comes from the client). `schemas.py`
mirrors `Session`'s existing dict returns as Pydantic models. `app.py` is
a thin translation layer — no session/model logic lives here. Run with
`make api` (or `uvicorn acquireml.api.app:app --reload`). A later phase added
`PATCH /sessions/{name}/settings` (body: `UpdateSettingsRequest`, all fields
optional) so patience/min_delta/cost_per_sample/diversity_weight/model/
calibration can be edited in place via `Session.update_settings()` (which has
its own independent validation logic), applying only the non-None fields sent.
Phase 5+6 added four session-scoped analysis endpoints — `GET .../explain`,
`GET .../overview`, `GET .../compare`, `GET .../validate` — each backed by a
new `Session` method (`feature_importance()`, `overview()`,
`compare_strategies()`, `validate_holdout()`). Three of the four reuse
existing dataset-agnostic functions directly: `explain.py`'s
`train_full_model()`/`extract_importances()`/`get_cross_val_score()` for
Explain, `ActiveLearningEngine` (the same hindsight-simulation engine the
core product already uses) for Compare, and `validate.py`'s `run_validation()`
for Validate. Overview is new logic rather than a wrapper, and — notably —
none of the four wrap `explore.py`: unlike the other three CLI modules,
`explore.py` hardcodes the original research dataset's `metadata.csv` schema
(`azm_sr`/`cip_sr`/`cfx_sr` columns, `Year`, `Country`, even a hardcoded
unitig-count array), so it can't work against an arbitrary uploaded session;
`Session.overview()` computes class balance and feature prevalence from
whatever data the session actually has instead, and `explore.py` itself is
untouched.

**Web UI frontend** (`frontend/`): React + TypeScript + Vite, talking to
the backend at `http://localhost:8000`. `src/api/client.ts` is the sole
place that knows the backend's URL and response shapes — every
page/component imports typed functions from it, never calls `fetch`
directly. `src/styles/tokens.css` originally carried the same Noir & Gold
color palette as the landing page (`docs/index.html`) — same hex values
— but a later redesign moved the app to its own darker, cooler "electric
blue" identity (`--paper: #0a0a0d`, `--accent: #3b9eff`) distinct from the
landing page's warm gold, which is untouched and remains the app's
visual baseline only historically; fonts still loaded from Google Fonts'
CDN instead of inlined (that inlining was only needed for the landing
page's strict-CSP artifact renderer) — Manrope and IBM Plex Mono only
(see the visual-system note below on why the landing page's serif face
isn't among them). Covers
the full session
lifecycle across eleven pages: `SessionListPage` and `NewSessionPage`
(create), `SessionLayout` (shared left-sidebar nav shell — fixed to the
viewport's left edge and spanning the full height, rather than sitting
in-flow as a bordered card, for the nine session-scoped
routes below), `DashboardPage` (status + stopping-warning banner +
accuracy/cost chart), `RecommendationsPage` (batch table with inline 0/1
result entry, submits to `/update`), `HistoryPage` (round table +
chart + CSV export), `SettingsPage` (edit + danger zone),
`BudgetPage` (cost/accuracy trend projection), and the four Phase 5+6
analysis pages `OverviewPage`, `ExplainPage`, `ComparePage`, and
`ValidatePage` (see below). Routing is `/`, `/new`, and
`/sessions/:name[/recommend|/history|/overview|/explain|/compare|/validate|/settings|/budget]`
via nested React Router routes.
Charts use Recharts, reading the same CSS custom-property tokens as the
rest of the UI. A later visual-overhaul pass gave the app a denser,
motion-forward visual system distinct from the landing page: Manrope is
used throughout (the landing page's serif face, Cormorant, is now
reserved for the landing page only, never loaded by the app), and a
shared `AppShell` component wraps every route, rendering a faint
background grid texture, a slow scan-line sweep, and a cursor-reactive
glow (via the `useCursorGlow` hook) behind the page content. Within that
shell, `DashboardPage`'s stat cards animate their numbers in with a
`useCountUp` hook, and the shared `AccuracyChart` card (used by both
`DashboardPage` and `HistoryPage`) draws its line in on mount with a
glow filter and a pulsing ring around the latest data point. Run with `npm run dev` from
`frontend/` (needs the backend running too — `make api` in another
terminal). Test with `npm test` from `frontend/`; type-check with
`npx tsc --noEmit`. Verified end-to-end against the real backend in a
real browser (create → recommend → submit results → dashboard/history
update → CSV export), not just each side's own mocked tests — this pass
also caught and fixed a real bug: `RecommendationsPage`'s `GET /recommend`
call has a server-side side effect (marks the batch "pending"), so React
18 StrictMode's dev-mode double-invoke of effects made it fire twice and
fail on the second call; fixed with a `useRef` dedup key guarding the
fetch, separate from the mount-tracking ref (a plain `cancelled` flag
isn't enough here, since the phantom StrictMode cleanup would mark the
one real in-flight request as cancelled before it resolves).
A later session-management phase (branch `feature/web-ui-session-management`)
added the remaining two pages plus a global command palette. `SettingsPage`
pre-fills a form from the session's current status and PATCHes
`/sessions/{name}/settings` on save with the full current form state (only
`cost_per_sample` is conditionally omitted, when the field is left blank, so
it's excluded rather than coerced to 0 — the backend's `UpdateSettingsRequest`
still treats every field as optional and only applies what it receives), and
carries a "Danger zone" with `Reset session` and `Delete session` buttons,
each gated behind a native `window.confirm` before it calls its endpoint —
cancelling the dialog leaves the session untouched. `SessionListPage` became
a sortable portfolio view: every session renders as a card with four stats
(round/known/pool/accuracy), a `Sort by` dropdown (name/round/accuracy/known,
via the pure comparator in `sessionSort.ts`, where a null accuracy always
sorts last), and a `highAccuracy` CSS-module class that highlights the
accuracy stat once a session clears a threshold. `BudgetPage` — its nav link
rendered only when the session has cost tracking enabled — fits an
ordinary-least-squares trend of accuracy against cumulative cost
(`costProjection.ts`'s `fitLinearTrend`/`projectCostForTarget`) and, given a
target accuracy typed into an input, projects the additional spend needed
(clamped to never go negative), falling back to an explanatory message when
there are fewer than two rounds with both accuracy and cost recorded or the
trend isn't increasing. A Cmd+K/Ctrl+K `CommandPalette` (opened via a global
keydown listener plus a "⌘K" hint chip rendered by `AppShell` on every route,
filtered by `commandFilter.ts`) jumps to any session or, from inside one, any
of its five sub-pages, with arrow keys to move the selection, Enter to
navigate, and Escape or a backdrop click to close it without navigating.
Phase 5+6 (branch `feature/web-ui-analysis-pages`) added four session-scoped
analysis pages, all reusing the same nav shell, CSS conventions, and
stat-card/bar-list patterns established by the earlier pages: `OverviewPage`
(four stat cards — known/pool/features/positive rate — plus a proportionally
sorted feature-prevalence bar list), `ExplainPage` (cross-validated accuracy
stat plus a ranked, strictly-decreasing top-feature-importance bar list),
`ComparePage` (active learning vs. random sampling), and `ValidatePage`
(five holdout metric cards — balanced accuracy, precision, recall, F1,
ROC-AUC — plus a four-quadrant confusion matrix, its labels matched
character-for-character to `validate.py`'s own CLI wording). `ComparePage` is
the one page in the whole app that does not fetch on mount — the comparison
trains several models and can take a few seconds, so it shows an explanatory
description and a "Run comparison" button and only calls
`GET /sessions/{name}/compare` on click, rendering the chart and a
plain-language summary sentence once the response lands. The command palette
was deliberately left unchanged by this phase — none of the four new pages
were added to `commandFilter.ts`'s static command list, so `⌘K` still jumps
only to the original five sub-pages (Dashboard/Recommendations/History/
Settings/Budget) plus any session.
108 frontend tests.
A later pass redesigned `SessionLayout` again at Gabe's request: the nav
moved from a horizontal top bar to the fixed full-height left sidebar
described above, and `tokens.css` moved off the landing page's "Noir &
Gold" palette onto its own darker, cooler electric-blue identity (see
the Web UI frontend note above). The sidebar also picked up motion
consistent with `AppShell`'s scan/cursor-glow effects — a slow scanning
glow sweep, a pulsing edge-glow line on its right border, a sliding
triangle indicator plus a `translateX` nudge on nav-link hover, and a
pulsing glow on the active link. That triangle was originally a text
character (`content: "\203A"` in a `::before`) rendered in CSS, which
per the accname spec gets pulled into the link's computed accessible
name — every nav link's real accessible name was "› Dashboard", "›
Recommendations", etc., found and fixed by swapping it for a
border-drawn triangle (`content: ""`) so it's purely decorative.

A later plan (branch `feature/web-ui-pro-theme`) added a second, parallel
visual theme for the same app rather than restyling the existing one: a
"Pro" theme reachable at `/pro/*`, alongside the classic dark
electric-blue app which stays mounted at `/` completely unchanged.
`App.tsx` picks between the two entirely at the router level — a
top-level `<Routes>` sends every `/pro*` path to `ProApp` and everything
else to the existing `ClassicApp`, so the two never share a layout
component or a CSS scope at runtime, only the code they both import.
`frontend/src/pro/` mirrors the classic app's shape one-for-one:
`pages/` holds all eleven routed pages (`ProSessionListPage`,
`ProNewSessionPage`, `ProDashboardPage`, `ProRecommendationsPage`,
`ProHistoryPage`, `ProOverviewPage`, `ProExplainPage`,
`ProComparePage`, `ProValidatePage`, `ProSettingsPage`,
`ProBudgetPage`), and `components/` holds the four shell pieces:
`ProAppShell` (a plain, motion-free wrapper standing in for
`AppShell` — it has no background texture and no motion effects at
all, in deliberate contrast to the classic `AppShell`'s background
grid, scan-line sweep, and cursor-reactive glow), `ProCommandPalette`
(standing in for `CommandPalette`), `ProAccuracyChart` (standing in
for `AccuracyChart`), and `ProSessionLayout` (standing in for
`SessionLayout`, with its own in-flow, sticky-positioned (`position:
sticky; top: 2rem`) sidebar card rather than the classic app's
fixed-to-viewport full-height sidebar). Nothing about what the app
knows or does was rebuilt: every Pro page imports the same typed
functions from `src/api/client.ts`, and the same pure-logic modules —
`sessionSort.ts`, `costProjection.ts`, `commandFilter.ts`,
`budgetChartData.ts`, `chartData.ts`, `useCountUp.ts` — that the
classic pages already used, unchanged. The Pro tree is presentation
only: new components, new CSS, no new endpoints, no new data-fetching
logic, and the same page-level behaviors the classic app already got
right (Compare's click-to-run instead of fetch-on-mount, the
StrictMode double-fetch guard on Recommendations, the `window.confirm`
gate on Settings' danger zone, Budget's conditional nav visibility).
The Pro identity is named "Navy Instrument" — a light, cooler-toned
counterpart to the classic app's dark electric blue: Inter for UI text
and IBM Plex Mono for numerics (both from Google Fonts, matching the
classic app's CDN-not-inlined approach), a flat light `--pro-paper`
background (`#f8fafc`) rather than the classic app's near-black paper,
with navy-to-blue `linear-gradient(135deg, ...)` accents (`--pro-accent`
`#1e40af` to `--pro-accent-bright` `#2563eb`) reused across buttons, the
active-nav pill, the command palette's selected row, and gradient-filled
stat/number values (headings stay flat `var(--pro-ink)`) — its own
`--pro-*`-prefixed CSS custom properties (`frontend/src/pro/styles/
tokens.css`, scoped under a `.pro-root` class) kept separate from
`tokens.css` so the two themes can never bleed into each other by
accident. Frontend test count: 108 → 166.

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
8. ✅ Demo mode — `demo.py` generates a synthetic binary feature matrix (small set of causal
   features + noise, mirroring the real biology) and `acquireml demo --init` spins up a
   ready-to-use session with zero real data — merged

**All 8 planned features are now built and merged into main.** Next roadmap pass (not yet
scoped) would need fresh ideas from Gabe — see "Current Status & What's Next" below.

## Current Status & What's Next

272 backend tests + 108 frontend tests passing on main. Repo is public. All work
pushed to GitHub.

**Technical:** Full original feature roadmap complete (stopping criteria → cost
tracking → batch diversity → round report → VCF support → model selection →
calibration → demo mode), plus AZM recall threshold tuning, a landing page
(`docs/index.html`), and a complete web UI — FastAPI backend (`acquireml/api/`)
and an 11-page React frontend (`frontend/`) covering the full session lifecycle
(create → recommend → submit results → dashboard/history → CSV export) plus
session settings editing, a sortable portfolio session list, a cost/accuracy
budget projection page, and a Cmd+K command palette, verified end-to-end in a
real browser against real servers. ✅ Phase 5+6 (analysis pages) is also now
complete: four session-scoped pages — Session Overview, Feature Importance
(Explain), AL-vs-Random Comparison, and Holdout Validation — wrapping the
dataset-agnostic cores of `explain.py` and `validate.py` plus
`ActiveLearningEngine` directly for the comparison simulation (`explore.py`
deliberately left untouched — see the Web UI backend note above), also
verified end-to-end in a real browser including both the happy path and a
genuinely insufficient-data error path (not just mocked tests). No specific next
feature queued — check with Gabe for what's next (candidates: README refresh to
showcase the web UI, or moving into outreach now that the repo is public and has
a polished demo surface).

**Outreach:**
- Repo is public; landing page is live at `docs/index.html` (GitHub Pages, served from
  `docs/.nojekyll` — GitHub Pages runs `docs/` through Jekyll by default, which broke the
  deploy pipeline for three straight pushes with zero content-level errors; `.nojekyll`
  makes Pages serve the folder as raw static files instead. If a future push to `docs/`
  doesn't show up live, check the repo's Actions tab for a failed "pages build and
  deployment" run before assuming the content itself is wrong).
- Reach out to AMR researchers to LEARN (not pitch). Target list, roughly in outreach-priority order:
  - **Tier 1:** Prof. Yonatan Grad (Harvard Chan School — N. gonorrhoeae genomics leader);
    Dr. Nicole Wheeler (Birmingham — ML for AMR).
  - **Tier 2 (closest technical match — unitig/k-mer ML for AMR, i.e. your exact method):**
    Dr. John Lees (EMBL-EBI / Cambridge Infectious Diseases, runs bacpop.org — builds
    `pyseer` and `unitig-caller`, the tooling family your loader's unitig convention
    comes from); Mario Marchand & Alexandre Drouin (Université Laval — built Kover,
    interpretable ML directly on k-mer presence/absence for AMR).
  - **Tier 3 (N. gonorrhoeae surveillance specifically):** Koji Yahara & Makoto Ohnishi
    (NIID Tokyo — gonorrhea AMR genomic surveillance/lineage evolution); Evonne Woodson &
    Brian Raphael (CDC, Division of STD Prevention — run the US GISP/AR Lab Network WGS
    surveillance this project's Kaggle dataset likely traces back to); Derek Aanensen
    (Centre for Genomic Pathogen Surveillance, Oxford/Sanger — built Pathogenwatch,
    including a dedicated N. gonorrhoeae scheme).
  - **Tier 4 (validates the active-learning half of the pitch, not AMR-specific):**
    CRyPTIC Consortium — Zamin Iqbal, Derrick Crook, Tim Peto (Oxford) — largest WGS+ML
    AMR effort outside gonorrhea (tuberculosis), useful as a cross-pathogen comparison point.
  - Tiers 2–3 are likely better first messages than Tier 1: they're more likely to reply
    since the tool speaks directly to something they built, not just the disease area.
- A LinkedIn outreach message was drafted for Prof. Grad/Dr. Wheeler in an earlier session
  but was never saved anywhere durable (not committed, not in memory) — it no longer exists
  and would need to be redrafted from scratch if wanted.

## Working Style With Gabe

Beginner CS student + founder mindset. Explain plainly, what-before-how, use analogies. He prefers
polished autonomous design calls over mid-flow clarifying questions. Slow, summer-long pace —
prioritize understanding over speed. During implementation: make autonomous calls, no mid-build
questions, demo it running before reporting done.
