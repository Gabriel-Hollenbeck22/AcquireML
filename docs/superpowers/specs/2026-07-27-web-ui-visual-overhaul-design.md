# Web UI Visual System Overhaul — Design

## Purpose

The web UI (session list, new session, dashboard, recommendations, history —
built across two earlier phases) currently reuses the landing page's
editorial "Noir & Gold" identity as-is: a serif display font (Cormorant) for
headings and stat values, and generous whitespace suited to a one-page
marketing pitch. That identity fits the landing page but reads as sparse and
unprofessional as a working data tool.

This phase re-skins the five existing pages and the shared chart component
with a denser, more technical visual language — sans-serif throughout,
tighter spacing, and a small set of subtle motion primitives (count-up
numbers, a chart that draws itself in, cursor-reactive glow, a scan-line
sweep) approved via the visual companion. It is Phase 3 of a four-phase plan:

1. ~~Web UI backend~~ (merged)
2. ~~Web UI frontend foundation + dashboard~~ (merged)
3. **Visual system overhaul** (this spec) — re-skin existing pages, no new pages, no backend changes
4. Session management & portfolio (Settings page, Multi-session Portfolio, Cost & Budget projection, Command palette)
5. Analysis endpoints (backend: feature importance, dataset overview, AL-vs-random comparison, holdout validation)
6. Analysis pages (frontend, built on Phase 5)

Phases 4-6 are deliberately out of scope here and will each get their own
brainstorm/spec/plan cycle. Building the visual system first means every page
added in Phases 4 and 6 gets built directly in the new system instead of
needing a re-skin later.

## Visual Direction (approved via visual companion)

Keeps the existing brand accent (gold/brass) so the app still reads as the
same product as the landing page, but modernizes everything else:

- Dark, neutral background (darker and less warm than the current `--paper`)
- Sans-serif throughout — the serif display font is dropped from the app
  entirely (kept only on the landing page, a separate static file this
  phase does not touch)
- Denser, card-based layout — less whitespace, more information visible
  at once
- A small, consistent motion vocabulary rather than a static page

## Design Tokens

`frontend/src/styles/tokens.css` values change to match the approved
mockups (`.superpowers/brainstorm/98748-1785182481/content/motion-v3.html`
is the reference — read it directly for exact values if anything below is
ambiguous):

```css
:root {
  --paper: #0f0d0a;
  --paper-raised: #161310;
  --ink: #ede6d6;
  --ink-soft: #b7ac94;
  --ink-faint: #8a8069;
  --ink-dim: #6b6350;       /* new tier: mono hints, micro-copy */
  --accent: #e0bd6c;         /* was --accent-bright; now the primary accent */
  --accent-deep: #c9a24b;    /* was --accent; secondary/deep gold */
  --brass: #9c7a3e;
  --red-data: #a6534c;
  --line: #2a2419;
  --line-strong: #4a3f26;
  --shadow: 0 8px 24px rgba(0, 0, 0, 0.4);

  --font-body: "Manrope", -apple-system, system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", monospace;
}
```

`--font-display` and the Cormorant import are removed from `tokens.css` and
`frontend/index.html`'s Google Fonts URL. Add weight 800 to the Manrope
import (currently 400;600) for bold stat values:

```
family=Manrope:wght@400;600;800
```

**Renaming existing token consumers:** every `var(--accent-bright)` in the
codebase becomes `var(--accent)`, and every existing `var(--accent)` becomes
`var(--accent-deep)`. Grep for both before editing — do not assume the two
call sites already found (`AccuracyChart.tsx`, `global.css`) are the only
ones.

## Typography

- `global.css`'s `h1, h2, h3` rule switches `font-family` from
  `var(--font-display)` to `var(--font-body)`, weight `700`.
- `DashboardPage.module.css`'s `.statValue` switches from
  `var(--font-display)` at `1.8rem` to `var(--font-body)` weight `800` at
  `1.5rem` (denser, matches the mockup's tighter stat cards).
- Every other `font-family: var(--font-display)` reference (grep found
  matches in `SessionLayout.module.css` and `SessionListPage.module.css` —
  confirm there are no others) is replaced with `var(--font-body)`.
- `IBM Plex Mono` usage is unchanged in kind but extends to a couple of new
  spots per the mockup: the session-name readout in `SessionLayout`'s nav
  becomes a mono "SESSION://name"-style label instead of the current plain
  heading text, and hint/caption text uses mono at a small size + `--ink-dim`.

## Motion System

Extracted as reusable pieces rather than copy-pasted per page. Implementation
approach for each, in increasing order of complexity:

**Pure CSS (no new JS):**
- **Nav underline slide** — `::after` pseudo-element transitioning `right`
  from `100%` to `0%` on hover/active, as prototyped.
- **Stat-card "lock-on" hover** — border-color + box-shadow transition on
  hover, no JS.
- **Corner reticle brackets** — four small absolutely-positioned bordered
  divs per card, a shared `.bracket`/`.bracket.tl/tr/bl/br` class set in
  `global.css` so any card can opt in with four extra `<div>`s.
- **Scan-line sweep** — an absolutely positioned gradient band animated via
  `@keyframes` translating `top` from `-120px` to `100%`, `pointer-events:
  none`, looping.
- **Background grid texture** — repeating linear-gradient on a `::before`
  pseudo-element, static (no animation).

**CSS + a small amount of JS:**
- **Cursor-reactive glow** — a `mousemove` listener setting `--gx`/`--gy`
  CSS custom properties consumed by a `radial-gradient(... at var(--gx)
  var(--gy) ...)`. One shared React hook (`useCursorGlow`, returns a ref and
  the two custom properties to spread onto the element's `style`) rather
  than duplicating the listener per component.
- **Count-up numbers** — a small `useCountUp(target: number, durationMs?)`
  hook using `requestAnimationFrame` with cubic ease-out, mirroring the
  vanilla JS in the mockup. Used for stat values (Round, Known, Pool,
  Accuracy) on `DashboardPage`.

**Chart-specific (Recharts + CSS):**
- **Line draw-in + glow** — Recharts renders standard SVG; the line path
  gets a `.recharts-line-curve` class we can target from CSS. Apply a
  `stroke-dasharray`/`stroke-dashoffset` keyframe animation (same technique
  as the mockup) scoped to `AccuracyChart`'s wrapper, and add an SVG
  `<filter>` (`feGaussianBlur` + `feMerge`) via Recharts' `defs` prop,
  referenced from the line's `style={{ filter: "url(#chartGlow)" }}`.
- **Pulse on latest point** — Recharts' `<Line dot={...}>` accepts a custom
  dot renderer; the custom renderer draws two overlapping circles for the
  last data index only (a static one + one with a CSS pulse animation),
  matching the mockup's `.pulse-ring`.
- **Risk flag:** Recharts' internal class names (`recharts-line-curve` etc.)
  are stable across recent major versions but are not a documented public
  API. The plan for this phase should include an early spike task that
  verifies the draw-in + glow technique actually works against the
  project's installed Recharts version before the rest of `AccuracyChart`'s
  rework depends on it. If it doesn't pan out, the fallback is animating a
  CSS `clip-path` reveal over the whole chart instead of a true stroke
  draw-in — visually close, no dependence on internal class names.

**Where the ambient effects (scan-line, grid texture, cursor glow) live:**
today `App.tsx` has no shared shell — it's routes directly under
`BrowserRouter`. This phase adds a lightweight `AppShell` component
(`frontend/src/components/AppShell.tsx`) wrapping `<Routes>`, so the
scan-line/grid/cursor-glow render once for the whole app rather than being
duplicated (and separately animated) on every page.

## Component-by-Component Changes

- **`tokens.css`** — token value changes above.
- **`frontend/index.html`** — Google Fonts URL: drop Cormorant, add Manrope
  weight 800.
- **`global.css`** — heading font-family swap; add shared `.bracket`
  utility classes; add scan-line/grid keyframes and classes for `AppShell`.
- **`AppShell.tsx`** (new) — wraps `<Routes>`; owns the scan-line sweep,
  background grid texture, and cursor-reactive glow (via `useCursorGlow`).
- **`SessionLayout`** — nav uses the underline-slide links; session name
  becomes a mono `SESSION://<name>` style label; card/bracket treatment on
  the layout shell if it reads better with one (implementer's call, match
  the mockup's spirit).
- **`SessionListPage` / `NewSessionPage`** — token/font updates; session
  cards get the lock-on hover treatment already used for stat cards.
- **`DashboardPage`** — stat values use `useCountUp`; stat cards get
  lock-on hover + corner brackets; stop-banner restyled with the new
  tokens.
- **`AccuracyChart`** — gridlines (Recharts `<CartesianGrid>`, already
  partially there — audit and tighten), draw-in + glow, pulse-on-latest-point,
  corner brackets on the chart's card wrapper, audit `ResponsiveContainer`
  padding/margins so the chart fills its card width (this was the specific
  "avoid blank space" feedback from the mockup review).
- **`RecommendationsPage` / `HistoryPage`** — token/font updates; table
  styling pass (mono for numeric data cells, subtle row hover highlight).

## Testing Approach

This phase changes CSS and adds a small number of pure-logic hooks; it does
not change page structure, routing, or data flow, so the existing 41 tests
should keep passing largely unchanged (update any assertion that happens to
match old class-derived text, but none currently assert on font-family or
color). New tests, matching the project's existing pattern of testing pure
logic separately from rendering (`chartData.ts`'s precedent):

- `useCountUp` and `useCursorGlow`: tested as pure hooks (via
  `@testing-library/react`'s `renderHook`) — verify `useCountUp` reaches
  the target value and `useCursorGlow` updates the returned coordinates on
  a simulated mousemove.
- `AccuracyChart`: existing tests (renders with the right data points
  present in the DOM) still apply; add one assertion that the glow
  `<filter>` def and the draw-in class are present so a future refactor
  can't silently drop the effect.

No pixel-level visual assertions — final validation is manual, per
`CLAUDE.md`'s standing instruction to run the dev server and check UI
changes in a real browser before reporting complete. Given the number of
components touched, do a full click-through of all five pages (not just
the ones directly edited) before calling the phase done.

## Explicitly Out of Scope

- No new pages or routes (Phases 4 and 6).
- No new backend endpoints or backend changes of any kind.
- No changes to the landing page (`docs/index.html`) — it keeps Cormorant
  and its existing identity; this phase touches `frontend/` only.
- No light/dark theme toggle — single dark theme, matching the current app
  and the landing page.
- No changes to `RecommendationsPage`'s or any other page's *data* /
  interaction logic (the StrictMode dedup fix, submit-filtering logic,
  etc. from the previous phase are untouched) — this phase is visual only.
