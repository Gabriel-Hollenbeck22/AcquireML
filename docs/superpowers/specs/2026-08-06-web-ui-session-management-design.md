# Web UI — Session Management & Portfolio — Design

## Purpose

Phase 4 of the web UI. Phases 1-3 (merged) built the FastAPI backend, a
5-page React frontend covering the full session lifecycle, and a re-skinned
visual system. This phase adds the pieces of the existing backend/CLI that
have no UI yet, plus one genuinely new capability:

1. **Session Settings page** — edit a running session's tunable parameters
   (patience, min_delta, cost_per_sample, diversity_weight, model,
   calibration) and trigger reset/delete — the CLI's `session update` loop
   already lets a researcher change these via re-running `session init`
   flags conceptually, but there is no in-place edit path anywhere today,
   web or CLI. Needs one new backend endpoint.
2. **Multi-session Portfolio** — upgrade `SessionListPage`'s flat card list
   into a real comparison view (sortable, at-a-glance accuracy/cost/round
   across all sessions). No backend changes — `GET /sessions` already
   returns everything needed per session.
3. **Cost & Budget projection page** — for sessions tracking
   `cost_per_sample`, project spend-to-target from the existing
   accuracy/cost history. Pure frontend computation on `GET /history` data
   already fetched elsewhere — no backend changes.
4. **Command palette (⌘K)** — fast keyboard navigation across sessions and
   pages. Pure frontend, no backend changes.

This phase is scoped to be buildable and reviewable as one branch, same as
Phase 3. Phases 5-6 (analysis endpoints + pages: feature importance,
dataset overview, AL-vs-random, holdout validation) remain separate future
work — this phase's Settings/Portfolio/Cost/palette additions do not depend
on them.

## 1. Session Settings Page

### Backend: `PATCH /sessions/{name}/settings`

New endpoint, new `Session` method. Follows the existing pattern in
`acquireml/session.py` exactly — a thin method that validates and calls
`_set_meta`, mirroring how `init()` already sets these same six meta keys.

**`Session.update_settings(self, **kwargs) -> dict`** (new method, placed
in `session.py` near `init()` since it shares its validation):

```python
def update_settings(
    self,
    patience: Optional[int] = None,
    min_delta: Optional[float] = None,
    cost_per_sample: Optional[float] = None,
    diversity_weight: Optional[float] = None,
    model: Optional[str] = None,
    calibrate: Optional[bool] = None,
    calibration_method: Optional[str] = None,
) -> dict:
    """Update one or more of a session's tunable settings in place.

    Only provided (non-None) fields are changed. Takes effect starting
    with the next `recommend`/`update` round — does not retroactively
    alter past rounds' history. Returns the full updated settings dict
    (same shape as `status()`'s settings-related keys).
    """
    if model is not None and model not in MODEL_CHOICES:
        raise ValueError(
            f"Unknown model {model!r}. Choose one of: {', '.join(MODEL_CHOICES)}"
        )
    if calibration_method is not None and calibration_method not in CALIBRATION_METHODS:
        raise ValueError(
            f"Unknown calibration method {calibration_method!r}. "
            f"Choose one of: {', '.join(CALIBRATION_METHODS)}"
        )
    if patience is not None:
        self._set_meta("patience", str(patience))
    if min_delta is not None:
        self._set_meta("min_delta", str(min_delta))
    if cost_per_sample is not None:
        self._set_meta("cost_per_sample", str(cost_per_sample))
    if diversity_weight is not None:
        self._set_meta("diversity_weight", str(diversity_weight))
    if model is not None:
        self._set_meta("model", model)
    if calibrate is not None:
        self._set_meta("calibrate", "true" if calibrate else "false")
    if calibration_method is not None:
        self._set_meta("calibration_method", calibration_method)
    return self.status()
```

Reuses `self.status()` for the return value rather than hand-building a
settings-only dict — `status()` already reads every one of these fields
back from meta, so the response reflects exactly what was persisted, not
what the caller merely requested (important since `_set_meta` round-trips
through string storage).

**API endpoint** (`acquireml/api/app.py`), same shape as the existing
`reset` endpoint:

```python
@app.patch("/sessions/{name}/settings", response_model=StatusResponse)
def update_settings(body: UpdateSettingsRequest, sess: Session = Depends(get_session)) -> StatusResponse:
    with sess:
        result = sess.update_settings(**body.model_dump(exclude_none=True))
        return StatusResponse(**result)
```

**Schema** (`acquireml/api/schemas.py`):

```python
class UpdateSettingsRequest(BaseModel):
    """All fields optional — only provided ones are changed."""
    patience: int | None = None
    min_delta: float | None = None
    cost_per_sample: float | None = None
    diversity_weight: float | None = None
    model: str | None = None
    calibrate: bool | None = None
    calibration_method: str | None = None
```

Reuses the existing `StatusResponse` as the return type rather than
inventing a new one — the endpoint's job is "tell me the settings are now
X", and `StatusResponse` already carries every settings field plus the
session's current round/accuracy/etc., which is useful confirmation
context for the page to redisplay after a save.

**No changes needed** to `reset` or `delete` endpoints — both already
exist (`POST /sessions/{name}/reset`, `DELETE /sessions/{name}`) and this
page is simply the first UI surface for them.

### Frontend: `SettingsPage`

New route: `/sessions/:name/settings`, added as a fourth child route under
`SessionLayout` alongside Dashboard/Recommend/History, with a fourth nav
link ("Settings").

`frontend/src/pages/SettingsPage.tsx` — fetches `getStatus(name)` on
mount (reuses the existing `client.ts` function, no new GET needed for the
initial values), renders a form pre-filled with current values:

- Patience (number input), Min delta (number input), Cost per sample
  (number input, optional — blank means "not tracked"), Diversity weight
  (number input), Model (`<select>` of `rf`/`gbm`/`lr`/`svm`), Calibrate
  (checkbox), Calibration method (`<select>` of `sigmoid`/`isotonic`,
  disabled unless Calibrate is checked).
- "Save changes" button — `PATCH`es only the fields, then re-fetches
  status to confirm and shows a brief success message inline (no
  navigation away, matching this page's "settings, not a wizard step"
  character).
- A separate "Danger zone" section below the form, visually set apart
  (bordered, using `--red-data` for emphasis): "Reset session" button
  (calls the existing `reset` endpoint, confirms via a native
  `window.confirm` first — this is the one destructive action in the whole
  app with an existing precedent worth following: none of the other
  session-scoped pages currently confirm anything, so a plain
  `window.confirm` is proportionate here rather than introducing a new
  modal component for one button) and "Delete session" button (calls the
  existing `DELETE` endpoint, same `window.confirm` pattern, then
  navigates to `/` on success since the session no longer exists).

**API client additions** (`frontend/src/api/client.ts`):

```typescript
export interface UpdateSettingsInput {
  patience?: number;
  minDelta?: number;
  costPerSample?: number;
  diversityWeight?: number;
  model?: string;
  calibrate?: boolean;
  calibrationMethod?: string;
}

export async function updateSettings(
  name: string,
  input: UpdateSettingsInput
): Promise<StatusResponse> { ... }
```

`updateSettings` sends a JSON body (like `submitResults`, not a `FormData`
upload like `createSession`) whose keys are the snake_case names
`UpdateSettingsRequest` expects (`min_delta`, `cost_per_sample`,
`diversity_weight`, `calibration_method`) — the function's job is exactly
the camelCase-input-to-snake_case-wire-format mapping, one key per
non-undefined field on `input`, omitting anything left `undefined` so the
backend's `exclude_none=True` sees only the fields the researcher actually
changed:

```typescript
export async function resetSession(name: string): Promise<ResetResponse> { ... }

export async function deleteSession(name: string): Promise<void> { ... }
```

(`ResetResponse` needs its own TypeScript interface, mirroring
`acquireml/api/schemas.py::ResetResponse` — `{ n_known: number; n_pool:
number; rounds_cleared: number }` — following the exact same
mirroring discipline as every other interface in this file.)

## 2. Multi-session Portfolio

Upgrades `SessionListPage` in place — no new route. Currently each session
renders as a card with name + "Round N · K known · P in pool [·
accuracy]". The portfolio view keeps the card-per-session shape (consistent
with the rest of the app's density, and avoids a jarring layout change from
"cards" to "table" for what's still fundamentally a small list) but adds:

- **Sortable header row** above the cards: "Sort by" with options Name,
  Round, Accuracy, Known count — client-side sort of the already-fetched
  `SessionSummary[]`, no new endpoint.
- **Each card gains a compact inline stat row** (Round / Known / Pool /
  Accuracy as four small labeled numbers, matching Dashboard's stat-card
  visual language at a smaller scale) instead of the current single line
  of prose — makes cross-session comparison actually scannable at a
  glance, which prose text doesn't support.
- **Accuracy gets a small color cue**: numbers >= 90% get a subtle
  `--accent`-tinted background chip, matching no new component — just a
  conditional class on the existing accuracy stat.

No backend changes: `GET /sessions` (`SessionSummary`) already returns
`name`, `current_round`, `n_known`, `n_pool`, `n_pending`,
`latest_accuracy` — everything this view needs.

New file: `frontend/src/pages/SessionListPage.tsx` gains a `sortSessions`
helper function, factored out the same way `chartData.ts` was factored out
of `AccuracyChart.tsx` in Phase 3 — pure logic separated from rendering so
it can be unit-tested without a DOM.

## 3. Cost & Budget Projection Page

New route: `/sessions/:name/budget`, fifth child route under
`SessionLayout`, fifth nav link ("Budget") — **conditionally shown only
when the session has `cost_per_sample` set** (checked via the already-
fetched session status in `SessionLayout`; sessions with no cost tracking
have nothing to project). This is the one nav link in the app that isn't
unconditionally present, which is intentional: showing a "Budget" tab that
immediately 404s or shows an empty state for the majority of sessions
(cost tracking is opt-in) would be worse than omitting it.

**Frontend-only, no backend changes.** Consumes `GET /history` (already
fetched by Dashboard/History) — same data, new analysis.

`frontend/src/pages/BudgetPage.tsx`:

- Fetches `getHistory(name)` and `getStatus(name)`.
- Shows current spend (`total_cost` from status) and current accuracy.
- **Projection**: linear regression of accuracy-vs-cumulative-cost over
  the history rows (simple least-squares on the existing round data — no
  new dependency, this is a ~15-line pure function), then a form where the
  researcher enters a target accuracy (e.g. "95%") and the page computes
  projected additional spend to reach it, based on the fitted trend.
  Below-target-already and insufficient-data (fewer than 2 completed
  rounds) are both handled as explicit empty/informational states rather
  than a bad regression — a 1-2 point fit is not a trend, and the page
  says so rather than projecting from noise.
- Renders its own small, standalone SVG visualization (not a reuse of
  `AccuracyChart`) — a simple accuracy-vs-cost scatter of the real history
  points, a fitted trend line through them, and the projected point marked
  distinctly (e.g. a dashed line continuing to it, different marker
  style). Deliberately not extended from the shared `AccuracyChart`
  component: that component is already reviewed and in production use on
  Dashboard/History, and threading a projection-specific
  `projectedPoint` prop through it for a single consumer would add
  surface area (and regression risk) to shared code for a page-specific
  need. A plain inline SVG (in the ~40-80 line range, similar scale to
  `AccuracyChart` itself) keeps the projection visualization fully
  contained to `BudgetPage` and easy to unit-test for its data-to-geometry
  mapping the same way `chartData.ts` is tested — without touching
  `AccuracyChart.tsx` at all.

New file: `frontend/src/lib/costProjection.ts` — the pure regression/
projection math, tested independently of any component (matching
`chartData.ts`'s precedent from Phase 3: pure logic lives in its own
file, is unit-tested directly, and the component that renders it stays
thin).

## 4. Command Palette (⌘K)

**Frontend-only, no backend changes.**

New component `frontend/src/components/CommandPalette.tsx`, mounted once
in `AppShell` (the same place the ambient-motion effects from Phase 3
live — `AppShell` is already the app-wide shell, this is a natural second
responsibility for it: global keyboard-triggered UI, not per-page).

- Triggered by `Cmd+K` / `Ctrl+K` (checked via a `keydown` listener on
  `window`, added in a `useEffect` in `AppShell`) or clicking a small
  persistent "⌘K" hint chip in the shell's corner (keyboard-only
  discovery is a bad pattern — the hint chip is the affordance that tells
  a first-time user this exists at all).
- Opens a centered modal-style overlay (dark backdrop, matching the app's
  existing dark theme — no separate light-mode treatment needed since the
  app has no theme toggle) with a text input and a filtered list below it.
- **Static command set for this phase** (kept deliberately small — this is
  navigation, not a general action-runner):
  - "Go to session: {name}" for every existing session (fetched via the
    already-available `listSessions()` — the palette calls this itself on
    open, it's a cheap GET), navigates to `/sessions/{name}`.
  - "New session" → `/new`.
  - When inside a session's routes (detected via `useParams` at the
    `AppShell` level is not possible since `AppShell` sits above the
    router's route-param scope — instead, the palette reads the current
    session name out of the URL path directly via `useLocation`, matching
    a `/sessions/([^/]+)` pattern, no new routing dependency): "Dashboard"
    / "Recommendations" / "History" / "Settings" / "Budget" (only if cost
    tracking is on, matching the nav's own conditional) for the current
    session.
- Fuzzy-ish filtering: simple case-insensitive substring match on the
  command label, sorted by match position (earlier match = higher) — no
  new dependency for this; a ~10-line pure function is enough for a
  command list of this size (sessions count + ~6 static items).
- `Escape` closes it; `↑`/`↓` moves selection; `Enter` executes the
  selected command.

New file: `frontend/src/lib/commandFilter.ts` — the pure filter/sort
function, unit-tested independently (same pure-logic-separated-from-
rendering pattern as `chartData.ts` and `costProjection.ts` above).

## Routing Summary

Extends `App.tsx`'s existing nested routes under `/sessions/:name`:

```
/                              SessionListPage (now a Portfolio view)
/new                           NewSessionPage
/sessions/:name                DashboardPage       (existing)
/sessions/:name/recommend      RecommendationsPage (existing)
/sessions/:name/history        HistoryPage         (existing)
/sessions/:name/settings       SettingsPage        (new)
/sessions/:name/budget         BudgetPage          (new, nav-conditional)
```

`SessionLayout`'s nav gains two more `NavLink`s (Settings always,
Budget conditional on `cost_per_sample !== null` from the session's
status, which `SessionLayout` will need to fetch — currently it doesn't
fetch anything, it's a pure layout shell reading only the `:name` param.
This is the one architectural change to an existing component: giving
`SessionLayout` a `getStatus` fetch on mount, the same pattern every
other page already uses, purely to decide whether to render the Budget
link).

## Testing Approach

Same discipline as Phases 1-3: React Testing Library against rendered
output for pages, pure-function unit tests for anything with real logic
(`sortSessions`, `costProjection.ts`, `commandFilter.ts`), API client
functions tested with mocked `fetch`. Backend: the new `update_settings`
method and endpoint get tests following the exact pattern of the existing
`reset`/`init` tests in `tests/test_session.py` and `tests/test_api_app.py`
— round-trip a change through the endpoint and confirm `status()` reflects
it, plus a rejection test for an invalid `model`/`calibration_method`
value (mirroring `init()`'s existing validation tests).

`CommandPalette` and `SettingsPage`'s destructive-action confirmations are
the two places in this phase that most need a real browser check beyond
unit tests (keyboard-driven UI and `window.confirm` don't reflect
realistically in jsdom) — final verification for this phase should
include a live walkthrough of: opening the palette via keyboard, filtering
to a session, navigating via Enter; and editing settings, then reset, then
delete, confirming each destructive action actually asks before acting.

## Explicitly Out of Scope

- No changes to Phases 5-6 (analysis endpoints/pages) — unrelated work,
  separate future phase.
- No general-purpose command palette actions beyond navigation (no "create
  session from here", no inline settings editing via the palette) — YAGNI
  for a first pass; navigation is the proven, low-risk win.
- No historical settings audit trail (e.g. "patience was 3, changed to 5
  on 2026-08-06") — `update_settings` overwrites meta in place, matching
  how every other session config value already behaves (nothing in this
  system currently versions config changes).
- No bulk actions on the Portfolio view (no multi-select delete, no
  bulk export) — out of scope, single-session actions live on each
  session's own Settings page.
- No non-linear cost projection models — a simple linear fit is the
  stated scope; if a researcher's accuracy curve is genuinely non-linear
  (very plausible for active learning, which is often concave), the page
  should say the projection is a rough linear estimate, not present it as
  precise.
