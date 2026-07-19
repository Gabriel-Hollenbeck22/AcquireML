# Web UI (Full Session Lifecycle) — Design

## Purpose

CLAUDE.md's roadmap lists "Phase 9 — Lab Interface: Web UI for non-programmer
lab scientists" as planned. This design builds it: a real web application
that lets a lab scientist run the entire prospective active-learning session
loop (create a session, get recommendations, submit results, track progress)
without ever touching the CLI or a terminal.

This is being built ahead of outreach feedback, by explicit choice: no
researcher has asked for this yet. The project is optimizing for steady,
visible progress over time rather than rushing to a finished product, and a
custom app naturally decomposes into well-scoped, frequently-committable
pieces that fit that goal.

## Scope

**Full session lifecycle**, not just a viewer:
- Create a named session (upload labeled data + unlabeled pool, configure
  label column, model choice, stopping criteria, cost tracking, diversity,
  calibration)
- Get recommendations as an interactive table
- Submit lab results via a form (replacing manual CSV editing)
- View status, round-by-round history, and interactive charts
- Manage multiple named local sessions (mirrors the CLI's `--name` /
  `--db` flexibility, e.g. one session per antibiotic/project)

## Deployment model

**Local, single-machine tool**, not hosted. Both the API and the frontend
run on the lab scientist's own machine. No accounts, no auth, no
multi-tenancy. This matches the project's current stage (early, unfunded)
and the CLI's own existing model (one local session at a time).

**Why this doesn't create lock-in for a future hosted version:** the
`Session` class in `session.py` is already architected as "one SQLite file
= one isolated session" — that's how the CLI works today via `--db`, not a
UI-specific decision. A future hosted, multi-user version would only need a
routing layer on top (mapping a user/browser to a session file); it would
not require changing `Session`'s core logic. The CLI itself would never
need to change either way — a CLI is inherently local/single-user by
nature. The one thing this design does to keep that future pivot cheap:
session-file resolution (mapping a session name to its `.db` path) is
implemented as one small, isolated function in the backend, not inlined
everywhere, so growing it from "fixed local folder" to "per-user path"
later is a contained change.

**Session storage:** `~/.acquireml/sessions/<name>.db`. Sessions are
auto-discovered by scanning this directory — no file picker, no path
management exposed to the user.

## Architecture

Two independent local processes over HTTP:

- **Backend:** FastAPI, wrapping `session.py`'s existing `Session` class
  directly. No rewrite of core session/model logic — the backend is a thin
  translation layer between HTTP requests and the same methods the CLI
  already calls (`init`, `recommend`, `update`, `status`, `history`,
  `reset`, `export`).
- **Frontend:** React + Vite. Talks to the backend via a small JSON API.

Uploaded files (labeled data, pool data) are saved to a temp path on
arrival and handed to the existing `GenericLoader` unchanged — it already
reads from a file path, so no loader changes are needed for the upload
path itself.

### Backend endpoints

| Method | Path | Wraps |
|---|---|---|
| GET | `/sessions` | scan session dir, read `meta`/`rounds` from each `.db` for quick stats |
| POST | `/sessions` | `Session.init` (file uploads + config) |
| GET | `/sessions/{name}/status` | `Session.status` |
| GET | `/sessions/{name}/history` | `Session.history` |
| GET | `/sessions/{name}/recommend?batch_size=N` | `Session.recommend`, returned as JSON rows |
| POST | `/sessions/{name}/update` | `Session.update`, accepts JSON results instead of a CSV |
| POST | `/sessions/{name}/reset` | `Session.reset` |
| GET | `/sessions/{name}/export` | `Session.export` |
| DELETE | `/sessions/{name}` | remove the `.db` file (no existing CLI equivalent needed — this is pure file deletion, not a `Session` method) |

Charts are **not** pre-rendered server-side PNGs. The API returns raw
round-history numbers (round, accuracy, cost if tracked, timestamp); the
frontend renders real interactive charts from that data.

### Frontend pages

1. **Session picker** — list of local sessions with quick stats (round,
   known/pool size, latest accuracy) + "New session"
2. **New-session wizard** — file upload (labeled + pool data), label
   column selection, config (name, model, patience, min-delta,
   cost-per-sample, diversity weight, calibration)
3. **Dashboard** — status summary, stopping-warning banner when
   applicable, interactive accuracy-over-rounds chart (+ cost chart if
   cost tracking is on)
4. **Recommendations** — table of the current batch (sample ID,
   uncertainty score, P(positive), predicted class) with an inline
   results-entry form, submitting to `/update`
5. **History** — full round-by-round table + charts, export

## Visual direction

Same Noir & Gold identity as the landing page (deep warm near-black,
antique-gold accent, Cormorant + Manrope), adapted for UI density rather
than reused as-is:
- Tighter spacing than the landing page's editorial pacing — a dashboard
  is scanned, not read top-to-bottom
- A lighter secondary surface for data tables, so dark-on-dark doesn't
  hurt legibility of dense tabular data
- The brass/gold accent does double duty: visual identity *and* a
  semantic "needs attention" signal (stopping warnings, pending results)

This is a deliberate reuse, not a default: the "instrument panel" concept
established for the landing page (brass waypoint markers, gauge-style
framing) arguably fits a real dashboard showing live accuracy/cost/round
data more naturally than it fit a marketing page.

## Explicitly out of scope

- No authentication, no hosting, no multi-user support
- No CLI changes — the CLI keeps working exactly as it does today; this
  is a second, independent consumer of `session.py`, not a replacement
- No real-time/websocket updates — each action is a plain request/response
  with a loading state during training (matches the CLI's existing
  spinner UX for the same multi-second model-fit wait)
- No new chart-generation code reused from `round_report.py` — this
  design supersedes static PNG charts with interactive ones for the web
  UI specifically; `round_report.py` is untouched and keeps serving the
  CLI/session-update flow as-is

## Testing approach

Backend: standard FastAPI test-client based tests per endpoint, using the
same synthetic-data fixtures pattern already established in
`tests/test_session.py`. Frontend: component/integration tests for the
results-entry form and the new-session wizard specifically (the two places
with real validation logic — column matching, label values); the read-only
views (dashboard, history) are lower-risk and get lighter coverage.
