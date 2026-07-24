# Web UI Frontend — Dashboard, Recommendations, History — Design

## Purpose

Phase 2 of the React frontend. Phase 1 (merged) built the toolchain, the
Noir & Gold identity, a typed API client, and two pages (session list,
new-session creation). This phase adds the three pages deferred from the
original web UI design spec (`docs/superpowers/specs/2026-07-19-web-ui-design.md`):
Dashboard, Recommendations, and History — completing the full session
lifecycle in the UI (create → recommend → submit results → track
progress → export), matching what the backend has supported since it was
built.

## Page content (unchanged from the original spec, restated for reference)

- **Dashboard** — status summary, a stopping-warning banner when the
  backend's `should_stop` is true, an interactive accuracy-over-rounds
  chart (+ cost chart if `cost_per_sample` was set on the session).
- **Recommendations** — table of the current batch (sample ID,
  uncertainty score, P(positive), predicted class) with an inline
  results-entry form (one 0/1 input per row), submitting the whole batch
  to `/update` at once.
- **History** — full round-by-round table, the same chart components as
  the dashboard, and an export-to-CSV button.

## Routing

Extends the existing `App.tsx` (currently `/` and `/new`) with three
session-scoped routes, mirroring the backend's own URL structure
(`/sessions/{name}/status`, `/sessions/{name}/recommend`, etc.) rather
than inventing a different shape:

- `/sessions/:name` — Dashboard
- `/sessions/:name/recommend` — Recommendations
- `/sessions/:name/history` — History

Chosen over a single-route/tabs approach specifically so each page is
independently bookmarkable, shareable, and survives a reload without
losing place — consistent with how the backend itself treats each
concern as its own endpoint.

A small shared layout component (session name in a header + nav links
between the three pages) avoids each page reimplementing navigation
chrome. `SessionListPage`'s existing session cards become links into
`/sessions/:name` (currently plain, non-interactive `<div>`s).

## Charting

**Recharts.** Chosen because: it composes cleanly with the existing CSS
custom-property token system (chart colors can reference `--accent`,
`--brass`, `--red-data` directly via inline style props rather than a
separate chart-specific palette), it's the most widely-used React
charting library (highest learning value, per the same reasoning that
picked React over Streamlit and TypeScript's learning value), and it's
declarative/component-based rather than an imperative canvas API,
fitting the rest of this codebase's style.

Two chart types needed: a line chart (accuracy-over-rounds, optionally a
second line/axis for cumulative cost) and nothing more exotic — no bar
charts, no heatmaps. Both the Dashboard and History pages render the
same chart from the same `GET /history` data, so this is one shared
chart component, not two implementations.

## API client extensions

`frontend/src/api/client.ts` (existing file, extended — not a new
parallel client) gains five functions, following the exact pattern
already established by `listSessions`/`createSession`:

- `getStatus(name: string): Promise<StatusResponse>`
- `getHistory(name: string): Promise<HistoryRow[]>`
- `getRecommendations(name: string, batchSize?: number): Promise<RecommendResponse>`
- `submitResults(name: string, results: ResultRow[]): Promise<UpdateResponse>`
- `exportHistory(name: string): Promise<Blob>` (the backend returns a
  CSV file download, not JSON — this function returns the raw blob for
  the page to trigger a browser download from)

TypeScript interfaces (`StatusResponse`, `HistoryRow`, `RecommendResponse`,
`RecommendRow`, `ResultRow`, `UpdateResponse`) mirror
`acquireml/api/schemas.py`'s equivalents exactly, same discipline as
Phase 1's `SessionSummary`/`SessionCreateResponse`.

## Explicitly out of scope

- No changes to the backend (`acquireml/api/`) — this phase is a pure
  frontend consumer of already-built, already-tested endpoints.
- No changes to Phase 1's session list or creation pages beyond making
  the session cards clickable links into the new dashboard route.
- No session `reset`/`delete` UI yet — the backend supports both, but
  neither was in the original 5-page design; a future addition if wanted.
- No polling/auto-refresh — the dashboard shows a snapshot on load, same
  request-per-navigation model as Phase 1's pages. Real-time updates
  aren't needed for a tool where "update" is an explicit researcher
  action (submitting lab results), not a continuously-changing feed.

## Testing approach

Same as Phase 1: React Testing Library against rendered output, API
client functions tested with mocked `fetch`. Chart components get a
lighter touch — verifying the chart renders with the right data points
present in the DOM (Recharts renders SVG, which RTL can query), not
pixel-level visual assertions.
