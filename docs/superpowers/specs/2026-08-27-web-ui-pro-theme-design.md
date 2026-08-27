# Web UI "Pro" Theme — Design Spec

## Context

The current web UI (`frontend/`) has a dark, "electric blue," motion-forward visual
system: scan-line sweeps, a cursor-reactive glow, pulsing active-nav glow, etc.
(see CLAUDE.md's "Web UI frontend" section for the full history). Gabe wants a
second, more professional/clean visual option to compare it against — explicitly
not a replacement. His words: "not vibe coded like this one."

Explored via the visual-companion tool across three rounds:
1. Four rough directions (today's look for reference, Minimal SaaS, Clinical/Lab
   Report, Restrained Dark) → picked **Clinical / Lab Report**.
2. Three typography/accent executions of that direction (Navy Instrument /
   Editorial Serif / Mono-forward Lab) → picked **Navy Instrument** (Inter
   throughout, IBM Plex Mono for data/numbers, navy accent).
3. A "flare" pass adding soft elevation shadows, a subtle gradient on the primary
   accent, a gradient-fill chart, and real hover states → approved, with one note:
   make sure charts read as scientific (visible gridlines/axes), kept clean.

Chart note resolved without a new mockup round: the real implementation reuses
Recharts (same library the current app already uses, with `CartesianGrid`, axis
lines, and tick labels), just restyled in the new palette — the flare mockup's
chart was a hand-drawn placeholder SVG for speed, not a preview of the real
component, so gridlines were never in question for the actual build.

## Goal

Build a second, fully professional/clean visual theme for the web UI, covering
every page the current app has, reachable at its own set of routes so both can be
viewed side by side in the same running app — without touching or risking the
existing dark/electric-blue UI.

## Scope

**All pages**, not a subset: `SessionListPage`, `NewSessionPage`, and the nine
session-scoped pages (`DashboardPage`, `RecommendationsPage`, `HistoryPage`,
`OverviewPage`, `ExplainPage`, `ComparePage`, `ValidatePage`, `SettingsPage`,
`BudgetPage`), plus the shared `SessionLayout` nav shell, `AppShell` wrapper,
`AccuracyChart`, and `CommandPalette`.

Out of scope: the landing page (`docs/index.html`) is untouched — this is only
about `frontend/`. No backend changes — the Pro theme consumes the exact same
`GET`/`POST`/`PATCH` endpoints via the exact same `api/client.ts` functions.

## Approach: parallel routes, shared logic, separate presentation

**Coexistence mechanism** (decided with Gabe): new routes in the *same* React/Vite
app — not a second project with its own `package.json`/dev server — under a
`/pro` prefix. One `npm run dev` shows both; no new build tooling, no second
server to remember to start.

**Directory:** a new `frontend/src/pro/` tree, mirroring the shape of the
existing `pages/`/`components/`/`styles/` directories, so it's obvious at a
glance which files belong to which theme and neither accidentally imports the
other's CSS modules:

```
frontend/src/pro/
  styles/
    tokens.css         # new design tokens (below) — completely separate file
                        # from styles/tokens.css, not an extension of it
  components/
    ProAppShell.tsx / .module.css      # plain wrapper, no scan/glow/cursor effects
    ProSessionLayout.tsx / .module.css # left sidebar, gradient active state
    ProAccuracyChart.tsx / .module.css # Recharts chart restyled (see Charts below)
    ProCommandPalette.tsx / .module.css
  pages/
    ProSessionListPage.tsx / .module.css / .test.tsx
    ProNewSessionPage.tsx / .module.css / .test.tsx
    ProDashboardPage.tsx / .module.css / .test.tsx
    ProRecommendationsPage.tsx / .module.css / .test.tsx
    ProHistoryPage.tsx / .module.css / .test.tsx
    ProOverviewPage.tsx / .module.css / .test.tsx
    ProExplainPage.tsx / .module.css / .test.tsx
    ProComparePage.tsx / .module.css / .test.tsx
    ProValidatePage.tsx / .module.css / .test.tsx
    ProSettingsPage.tsx / .module.css / .test.tsx
    ProBudgetPage.tsx / .module.css / .test.tsx
```

**What gets reused verbatim (no duplication):**
- `api/client.ts` — every fetch function and response type, unchanged.
- Pure logic/utility modules that already live separately from presentation in
  this codebase: `pages/sessionSort.ts`, `pages/costProjection.ts`,
  `pages/budgetChartData.ts`, `components/chartData.ts`,
  `components/commandFilter.ts`. These have no visual opinion — they're safe to
  import from both the classic pages and the new Pro pages.
- `hooks/useCountUp.ts` — a numeric easing hook, no visual opinion, reused as-is
  for the Pro dashboard's stat-card count-up (kept from the current app, since
  Gabe approved "a couple of tasteful one-time entrance animations" as the kind
  of restrained motion that fits Pro, unlike the glow/scan effects).
- `hooks/useCursorGlow.ts` — **not** reused. Pro has no cursor-reactive glow.

**What's new (presentation only):** every `.tsx`/`.module.css` pair above.
Each new page fetches data through the exact same `api/client.ts` calls the
existing page does (same loading/error states, same endpoints), and renders
different markup/styling against it. No page-level business logic changes.

**Routing:** `App.tsx` currently wraps its entire `<Routes>` tree in one
`<AppShell>`, so the motion effects apply everywhere today. To let `/pro/*` use
a completely different, motion-free wrapper, `App.tsx` splits into two
sibling branches under one `<BrowserRouter>`:

```tsx
<BrowserRouter>
  <Routes>
    <Route path="/pro/*" element={<ProApp />} />
    <Route path="/*" element={<ClassicApp />} />
  </Routes>
</BrowserRouter>
```

`ClassicApp` is today's `App.tsx` body (unchanged: `<AppShell><Routes>...` with
all the existing routes/paths, still mounted at `/`, `/new`,
`/sessions/:name/...`). `ProApp` is `<ProAppShell><Routes>` with the mirrored
route shape at `/pro`, `/pro/new`, `/pro/sessions/:name/...`. Existing bookmarks
and the classic app's internal links are unaffected — nothing currently at `/`
moves.

## Visual System — "Navy Instrument"

New tokens file, `frontend/src/pro/styles/tokens.css` (not an extension of the
existing `styles/tokens.css` — a separate set of custom properties scoped to
`.pro-root` or similar, so there's no risk of one theme's tokens leaking into
the other if both are ever rendered in the same DOM tree, e.g. during Vitest
runs):

```css
--pro-paper: #f8fafc;        /* page background */
--pro-surface: #ffffff;      /* card/sidebar background */
--pro-ink: #0f172a;          /* primary text */
--pro-ink-soft: #475569;     /* secondary text */
--pro-ink-faint: #94a3b8;    /* labels, captions */
--pro-accent: #1e40af;       /* navy — solid accent (icons, links, chart line) */
--pro-accent-bright: #2563eb;/* gradient endpoint, paired with --pro-accent */
--pro-line: #eef2f6;         /* hairline borders (sidebar, table rules) */
--pro-line-soft: #f1f5f9;    /* lighter rule, e.g. table row dividers */
--pro-warn-bg: #fffbeb;
--pro-warn-border: #fde68a;
--pro-warn-ink: #92400e;
--pro-pos-bg: #ecfdf5;
--pro-pos-ink: #047857;
--pro-neg-bg: #fef2f2;
--pro-neg-ink: #b91c1c;
--pro-radius-sm: 6px;
--pro-radius-md: 9px;
--pro-radius-lg: 12px;
--pro-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05), 0 1px 8px rgba(15, 23, 42, 0.04);
--pro-shadow-md: 0 6px 16px rgba(15, 23, 42, 0.09);
--pro-shadow-btn: 0 2px 8px rgba(30, 64, 175, 0.25);
--pro-font-body: "Inter", -apple-system, system-ui, sans-serif;
--pro-font-mono: "IBM Plex Mono", monospace;
```

**Fonts:** IBM Plex Mono is already loaded (shared with the classic app's font
link in `frontend/index.html`). Inter needs to be added to that same Google
Fonts `<link>` — one shared HTML file, additive only, so the classic app is
unaffected (it never references `font-family: 'Inter'`). Inter is used for all
UI text/headings in Pro; IBM Plex Mono is reserved for data — numbers, table
cells, session names — exactly like the classic app's "mono for machine-ish
values" convention (see CLAUDE.md), just carried into a light theme instead of
dark.

**Sidebar:** `ProSessionLayout` — left sidebar, `--pro-surface` background,
`1px solid var(--pro-line)` right border (no fixed/full-height positioning
requirement carried over from the classic redesign — a normal in-flow sidebar
is fine here since Pro has no motion system to reference), nav links get
`border-radius: 7px` and a subtle `translateX(2px)` on hover; the active link
gets a `linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright))`
background with white text and `box-shadow: var(--pro-shadow-btn)` — not a
left-edge accent bar like the classic app, a fully filled pill instead.

**Cards/stats:** `var(--pro-surface)` background, `border-radius: var(--pro-radius-md)`,
`box-shadow: var(--pro-shadow-sm)` (no border) at rest; stat cards specifically
lift on hover (`translateY(-2px)`, shadow escalates to `--pro-shadow-md`) and
their number uses a subtle `background: linear-gradient(135deg, --pro-ink,
--pro-accent)` text-fill for a touch of richness, matching the approved mockup.

**Buttons:** primary = gradient background (`--pro-accent` → `--pro-accent-bright`),
white text, `--pro-shadow-btn`, lifts slightly on hover; ghost/secondary =
white background, `1px solid var(--pro-line)`, border turns `--pro-accent` on
hover.

**Charts:** `ProAccuracyChart` reuses **Recharts** (already a project dependency,
already used by the classic `AccuracyChart`/`BudgetPage`/`ComparePage`/
`ValidatePage`) — not a new charting approach. Differences from the classic
chart component: `CartesianGrid` uses `--pro-line-soft` (light gray, not the
classic app's dashed blue-tinted grid), the line stroke is `--pro-accent`
with a `linearGradient`-filled `Area` beneath it (`--pro-accent` fading to
transparent, matching the approved flare mockup), axis ticks use
`--pro-ink-faint` in `--pro-font-mono`, and none of the classic chart's glow
`<filter>` or pulsing-ring latest-point treatment carries over — the latest
point gets a plain filled circle with a soft halo (a static, non-animated
`<circle>` at larger radius + lower opacity behind it, not a CSS `@keyframes`
pulse).

**Motion — what carries over vs. what doesn't:** Pro keeps two of the classic
app's restrained motion ideas, dropped from "atmospheric" (always-running) to
"purposeful" (one-time, on mount/interaction): `useCountUp` on stat-card
numbers, and ordinary CSS `transition` on hover/press states (cards, nav links,
buttons — all specified above). Pro does **not** get: the `AppShell` background
grid texture, scan-line sweep, or cursor-reactive glow; the sidebar's scanning
glow sweep or pulsing edge-glow border; or any `@keyframes`-driven idle-state
pulsing (the classic active-nav-link glow pulse, the classic chart's latest-
point pulsing ring). `ProAppShell` keeps the *functional* pieces of `AppShell` — the
Cmd+K keydown listener, palette-open state, and a hint chip in the corner —
just with no pseudo-element background effects: a `--pro-paper`-colored
container rendering `{children}`, the same Cmd+K listener wired to
`ProCommandPalette`, and a plain bordered hint chip (`--pro-surface`
background, `--pro-shadow-sm`, no hover glow) instead of the classic chip's
glow-on-hover treatment.

`ProCommandPalette` reuses `commandFilter.ts` for all matching/filtering logic
unchanged — only its presentation differs: a `--pro-surface` modal with
`--pro-shadow-md`, a dimmed `--pro-ink`-at-low-opacity backdrop, and the
keyboard-selected row getting the same gradient treatment as the sidebar's
active nav link (`--pro-accent` → `--pro-accent-bright`, white text) rather
than the classic palette's glow/border treatment.

## Non-goals

- No dark-mode variant of Pro in this pass — light only. (The classic app
  already covers dark; Gabe didn't ask for a second dark theme.)
- No user-facing theme switcher/toggle UI — reaching `/pro` is done by typing
  the URL or a link, not a runtime preference. Revisit if Gabe decides Pro
  should become the default later.
- No changes to `docs/index.html` (landing page) or any backend code.
- Not replacing or deleting anything in the classic `pages/`/`components/`/
  `styles/` trees.

## Testing

Same conventions as the rest of the frontend: each new `Pro*Page.tsx` gets a
co-located `.test.tsx` using the existing patterns (mock `api/client.ts` via
`vi.spyOn`, render with `MemoryRouter`, assert on loading/loaded/error states)
— largely adaptable from the classic page's existing test file, since the
data-fetching behavior is identical and only the rendered markup differs.
`npx tsc --noEmit` and `npm test -- --run` must stay clean throughout, same as
every other frontend change in this project.
