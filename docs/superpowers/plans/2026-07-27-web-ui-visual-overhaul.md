# Web UI Visual System Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin the five existing web UI pages (session list, new session, dashboard, recommendations, history) and the shared chart component with a denser, sans-serif, motion-forward visual system, replacing the landing-page-derived editorial identity.

**Architecture:** Token/typography changes ripple outward from `tokens.css` and `global.css`. Two new hooks (`useCountUp`, `useCursorGlow`) and one new `AppShell` component provide the reusable motion primitives. Each existing page/component is then retrofitted to use the new tokens and, where the design calls for it, the new motion primitives. No new pages, routes, or backend changes.

**Tech Stack:** React 18, TypeScript 5 (strict), Vite 5, Vitest 2 + React Testing Library 16, React Router 6, Recharts 2, CSS Modules.

## Global Constraints

- New token values (exact, from `tokens.css`'s target state below): `--paper: #0f0d0a`, `--paper-raised: #161310`, `--ink-dim: #6b6350` (new), `--accent: #e0bd6c` (was `--accent-bright`), `--accent-deep: #c9a24b` (was `--accent`), `--line: #2a2419`, `--line-strong: #4a3f26`, `--shadow: 0 8px 24px rgba(0, 0, 0, 0.4)`. `--ink`, `--ink-soft`, `--ink-faint`, `--brass`, `--red-data` are unchanged.
- `--font-display` and the Cormorant Google Fonts import are removed from `frontend/` entirely. The landing page (`docs/index.html`) is untouched — it has its own inlined fonts and does not read `frontend/index.html`.
- `--font-body` becomes `"Manrope", -apple-system, system-ui, sans-serif`. Manrope's Google Fonts import gains weight `800` (currently `400;600`).
- Every `var(--accent-bright)` call site becomes `var(--accent)`. Every existing `var(--accent)` call site (that isn't the token definition itself) becomes `var(--accent-deep)`. Do this as an exact, exhaustive rename — Task 1 lists every file found by grep; if a task's own edits introduce a new `var(--accent...)` usage, use the new names directly.
- No new pages, routes, or `acquireml/api/` backend changes anywhere in this plan.
- No light/dark theme toggle.
- No changes to any page's data/interaction logic (`RecommendationsPage`'s submit-filtering, the StrictMode dedup fix, `HistoryPage`'s export flow, etc.) — this plan is visual/motion only.
- Full frontend test suite (`npm test` from `frontend/`) must stay green after every task; `npx tsc --noEmit` must stay clean (strict mode, `noUnusedLocals`/`noUnusedParameters` are on).
- Per `CLAUDE.md`: before the final task reports done, the dev server must be run and every page clicked through in a real browser — this is not optional polish, it's how this project verifies UI work.

---

### Task 1: Design tokens and typography

**Files:**
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/index.html`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/components/SessionLayout.module.css`
- Modify: `frontend/src/components/AccuracyChart.tsx`
- Modify: `frontend/src/pages/SessionListPage.module.css`
- Modify: `frontend/src/pages/NewSessionPage.module.css`
- Modify: `frontend/src/pages/RecommendationsPage.module.css`
- Modify: `frontend/src/pages/HistoryPage.module.css`
- Modify: `frontend/src/pages/DashboardPage.module.css`

**Interfaces:**
- Produces: the final token names (`--paper`, `--paper-raised`, `--ink`, `--ink-soft`, `--ink-faint`, `--ink-dim`, `--accent`, `--accent-deep`, `--brass`, `--red-data`, `--line`, `--line-strong`, `--shadow`, `--font-body`, `--font-mono`) that every later task's CSS must use. `--font-display` no longer exists anywhere in `frontend/` after this task — later tasks must not reintroduce it.

This task is mechanical (token values + a global rename) and touches many files, but every change is a like-for-like substitution with no new markup — it's one reviewable unit, and the existing test suite should pass completely unchanged (these are visual-only CSS/font changes).

- [ ] **Step 1: Update `tokens.css` to the new values**

Replace the entire file:

```css
:root {
  --paper: #0f0d0a;
  --paper-raised: #161310;
  --ink: #ede6d6;
  --ink-soft: #b7ac94;
  --ink-faint: #8a8069;
  --ink-dim: #6b6350;
  --accent: #e0bd6c;
  --accent-deep: #c9a24b;
  --brass: #9c7a3e;
  --red-data: #a6534c;
  --line: #2a2419;
  --line-strong: #4a3f26;
  --shadow: 0 8px 24px rgba(0, 0, 0, 0.4);

  --font-body: "Manrope", -apple-system, system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", monospace;
}
```

- [ ] **Step 2: Update the Google Fonts import in `frontend/index.html`**

Change:

```html
<link
  href="https://fonts.googleapis.com/css2?family=Cormorant:wght@600;700&family=Manrope:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
  rel="stylesheet"
/>
```

to:

```html
<link
  href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap"
  rel="stylesheet"
/>
```

- [ ] **Step 3: Update `global.css`'s heading rule**

In `frontend/src/styles/global.css`, change:

```css
h1,
h2,
h3 {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--ink);
}
```

to:

```css
h1,
h2,
h3 {
  font-family: var(--font-body);
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--ink);
}
```

And change the `a` rule's accent reference from `var(--accent)` to `var(--accent-deep)`:

```css
a {
  color: var(--accent-deep);
}
```

- [ ] **Step 4: Remove the remaining `--font-display` usages**

In `frontend/src/components/SessionLayout.module.css`, change `.sessionName`:

```css
.sessionName {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--ink);
}
```

to:

```css
.sessionName {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  letter-spacing: 0.03em;
  color: var(--ink-dim);
}
```

(This becomes the `SESSION://<name>` mono readout — Task 3 changes the JSX to prepend the `SESSION://` prefix. This task only changes the CSS/font.)

In `frontend/src/pages/SessionListPage.module.css`, change `.sessionName`:

```css
.sessionName {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--ink);
}
```

to:

```css
.sessionName {
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--ink);
}
```

In `frontend/src/pages/DashboardPage.module.css`, change `.statValue`:

```css
.statValue {
  font-family: var(--font-display);
  font-size: 1.8rem;
  color: var(--ink);
}
```

to:

```css
.statValue {
  font-family: var(--font-body);
  font-weight: 800;
  font-size: 1.5rem;
  color: var(--ink);
}
```

- [ ] **Step 5: Run a grep to confirm no `font-display` references remain**

Run: `grep -rn "font-display\|Cormorant" frontend/src/`
Expected: no output (empty).

- [ ] **Step 6: Rename `var(--accent-bright)` to `var(--accent)`**

Three call sites, each identical in shape — the hover state of a filled accent button:

In `frontend/src/pages/SessionListPage.module.css`:
```css
.newLink:hover {
  background: var(--accent);
}
```

In `frontend/src/pages/NewSessionPage.module.css`:
```css
.submit:hover {
  background: var(--accent);
}
```

In `frontend/src/pages/RecommendationsPage.module.css`:
```css
.submit:hover {
  background: var(--accent);
}
```

- [ ] **Step 7: Rename the remaining `var(--accent)` call sites to `var(--accent-deep)`**

In `frontend/src/pages/SessionListPage.module.css`, `.newLink`:
```css
.newLink {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  text-decoration: none;
  color: var(--paper);
  background: var(--accent-deep);
  padding: 0.6rem 1rem;
  border-radius: 3px;
}
```

In `frontend/src/pages/NewSessionPage.module.css`, `.submit`:
```css
.submit {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--paper);
  background: var(--accent-deep);
  border: none;
  padding: 0.75rem 1.4rem;
  border-radius: 3px;
  cursor: pointer;
}
```

In `frontend/src/pages/RecommendationsPage.module.css`, `.submit`:
```css
.submit {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--paper);
  background: var(--accent-deep);
  border: none;
  padding: 0.75rem 1.4rem;
  border-radius: 3px;
  cursor: pointer;
}
```

In `frontend/src/pages/HistoryPage.module.css`, `.exportButton:hover`:
```css
.exportButton:hover {
  border-color: var(--accent-deep);
  color: var(--accent-deep);
}
```

In `frontend/src/components/SessionLayout.module.css`, `.nav a:hover` (this rule is fully replaced again in Task 3 — apply the rename here anyway so the file is never in a broken intermediate state if these tasks are reviewed independently):
```css
.nav a:hover {
  color: var(--accent-deep);
}
```

In `frontend/src/components/AccuracyChart.tsx`, change both `var(--accent)` references:
```tsx
        <Line
          yAxisId="accuracy"
          type="monotone"
          dataKey="accuracy"
          stroke="var(--accent-deep)"
          strokeWidth={2}
          dot={{ fill: "var(--accent-deep)" }}
          name="Accuracy %"
        />
```

(Task 6 changes `AccuracyChart.tsx` further — this step only does the rename so the component isn't left referencing a token that no longer exists.)

- [ ] **Step 8: Run a grep to confirm no `--accent-bright` references remain and `--accent`/`--accent-deep` are used correctly**

Run: `grep -rn -- "--accent-bright" frontend/src/`
Expected: no output.

Run: `grep -rn -- "--accent\b" frontend/src/ | grep -v "\-\-accent-deep"`
Expected: only the definition in `tokens.css` and the 9 renamed-to-`--accent` hover call sites from Step 6 (3) plus any remaining bare `--accent` reads that were intentionally left as `--accent` — cross-check against the list in this step's Steps 6-7 above; every other occurrence should be `--accent-deep`.

- [ ] **Step 9: Run the full test suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `41 passed (41)` — identical count to before this task, since no test asserts on font-family/color and no DOM structure changed.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 10: Manually verify in the browser**

Run: `npm run dev` (frontend) and `make api` (backend, from repo root, separate terminal). Open `http://localhost:5173`, click through all five pages. Confirm: no serif font anywhere, no console errors, all existing functionality (session list, create, dashboard stats, recommend, history, export) still works exactly as before — only colors/fonts should look different at this point (cards/hover/motion come in later tasks). Stop both servers when done.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/styles/tokens.css frontend/index.html frontend/src/styles/global.css \
  frontend/src/components/SessionLayout.module.css frontend/src/components/AccuracyChart.tsx \
  frontend/src/pages/SessionListPage.module.css frontend/src/pages/NewSessionPage.module.css \
  frontend/src/pages/RecommendationsPage.module.css frontend/src/pages/HistoryPage.module.css \
  frontend/src/pages/DashboardPage.module.css
git commit -m "Update design tokens and drop the serif display font from the app"
```

---

### Task 2: AppShell — ambient motion (scan-line, grid, cursor glow)

**Files:**
- Create: `frontend/src/hooks/useCursorGlow.ts`
- Create: `frontend/src/hooks/useCursorGlow.test.ts`
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/AppShell.module.css`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `useCursorGlow(): { onMouseMove: (event: React.MouseEvent<HTMLElement>) => void }` — later tasks do not need this directly (only `AppShell` uses it), but it's exported in case a later phase wants the same effect elsewhere. `AppShell` component: `({ children }: { children: ReactNode }) => JSX.Element` — wraps the whole app exactly once, in `App.tsx`.

- [ ] **Step 1: Write `useCursorGlow`**

Create `frontend/src/hooks/useCursorGlow.ts`:

```ts
import type { MouseEvent } from "react";

export function useCursorGlow() {
  function onMouseMove(event: MouseEvent<HTMLElement>) {
    const el = event.currentTarget;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--gx", `${event.clientX - rect.left}px`);
    el.style.setProperty("--gy", `${event.clientY - rect.top}px`);
  }

  return { onMouseMove };
}
```

- [ ] **Step 2: Write the test for `useCursorGlow`**

Create `frontend/src/hooks/useCursorGlow.test.ts`:

```ts
import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useCursorGlow } from "./useCursorGlow";

function TestTarget() {
  const { onMouseMove } = useCursorGlow();
  return (
    <div
      data-testid="target"
      onMouseMove={onMouseMove}
      style={{ position: "absolute", width: 200, height: 100 }}
    />
  );
}

describe("useCursorGlow", () => {
  it("sets --gx and --gy custom properties relative to the element on mousemove", () => {
    const { getByTestId } = render(<TestTarget />);
    const el = getByTestId("target");
    // jsdom's getBoundingClientRect returns all-zero by default, so
    // clientX/clientY map directly to --gx/--gy here.
    fireEvent.mouseMove(el, { clientX: 42, clientY: 17 });
    expect(el.style.getPropertyValue("--gx")).toBe("42px");
    expect(el.style.getPropertyValue("--gy")).toBe("17px");
  });
});
```

- [ ] **Step 3: Run the new test to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/useCursorGlow.test.ts`
Expected: `1 passed (1)`.

- [ ] **Step 4: Write `AppShell`**

Create `frontend/src/components/AppShell.tsx`:

```tsx
import type { ReactNode } from "react";
import { useCursorGlow } from "../hooks/useCursorGlow";
import styles from "./AppShell.module.css";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { onMouseMove } = useCursorGlow();

  return (
    <div className={styles.shell} onMouseMove={onMouseMove}>
      <div className={styles.scan} />
      <div className={styles.content}>{children}</div>
    </div>
  );
}
```

Create `frontend/src/components/AppShell.module.css`:

```css
.shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(224, 189, 108, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(224, 189, 108, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}

.shell::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    220px circle at var(--gx, 50%) var(--gy, 50%),
    rgba(224, 189, 108, 0.06),
    transparent 70%
  );
  pointer-events: none;
}

.scan {
  position: absolute;
  left: 0;
  right: 0;
  height: 160px;
  top: -160px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(224, 189, 108, 0.05) 45%,
    rgba(224, 189, 108, 0.08) 50%,
    rgba(224, 189, 108, 0.05) 55%,
    transparent
  );
  animation: scan 6s linear infinite;
  pointer-events: none;
}

@keyframes scan {
  to {
    top: 100%;
  }
}

.content {
  position: relative;
  z-index: 1;
}
```

- [ ] **Step 5: Wire `AppShell` into `App.tsx`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<SessionListPage />} />
          <Route path="/new" element={<NewSessionPage />} />
          <Route path="/sessions/:name" element={<SessionLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="recommend" element={<RecommendationsPage />} />
            <Route path="history" element={<HistoryPage />} />
          </Route>
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Run the full test suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `42 passed (42)` — the 41 from before Task 1 plus the 1 new `useCursorGlow` test. `App.test.tsx` must still pass unchanged, confirming `AppShell` doesn't interfere with routing.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 7: Manually verify in the browser**

`npm run dev` + `make api`. Confirm the background grid texture is visible (subtle), a horizontal band sweeps top-to-bottom repeatedly, and moving the mouse produces a soft glow that follows the cursor. Stop both servers when done.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useCursorGlow.ts frontend/src/hooks/useCursorGlow.test.ts \
  frontend/src/components/AppShell.tsx frontend/src/components/AppShell.module.css frontend/src/App.tsx
git commit -m "Add AppShell: background grid, scan-line sweep, cursor-reactive glow"
```

---

### Task 3: SessionLayout — active nav underline, mono session label

**Files:**
- Modify: `frontend/src/components/SessionLayout.tsx`
- Modify: `frontend/src/components/SessionLayout.module.css`
- Create: `frontend/src/components/SessionLayout.test.tsx`

**Interfaces:**
- Consumes: nothing from Tasks 1-2 beyond the renamed tokens.
- Produces: nothing later tasks depend on directly (this is a leaf change).

No test currently exists for `SessionLayout` — this task adds one, since it's about to gain real conditional logic (active-link detection) worth locking down.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/SessionLayout.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import SessionLayout from "./SessionLayout";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<div>dashboard content</div>} />
          <Route path="recommend" element={<div>recommend content</div>} />
          <Route path="history" element={<div>history content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("SessionLayout", () => {
  it("shows the session name as a mono SESSION:// label", () => {
    renderAt("/sessions/azm-project");
    expect(screen.getByText("SESSION://azm-project")).toBeInTheDocument();
  });

  it("marks only the Dashboard link active on the index route", () => {
    renderAt("/sessions/azm-project");
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveClass("active");
    expect(screen.getByRole("link", { name: "Recommendations" })).not.toHaveClass("active");
    expect(screen.getByRole("link", { name: "History" })).not.toHaveClass("active");
  });

  it("marks only the Recommendations link active on the recommend route", () => {
    renderAt("/sessions/azm-project/recommend");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveClass("active");
    expect(screen.getByRole("link", { name: "Recommendations" })).toHaveClass("active");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/components/SessionLayout.test.tsx`
Expected: FAIL — text is currently `azm-project` not `SESSION://azm-project`, and no link ever has an `active` class.

- [ ] **Step 3: Update `SessionLayout.tsx`**

```tsx
import { NavLink, Outlet, useParams } from "react-router-dom";
import styles from "./SessionLayout.module.css";

export default function SessionLayout() {
  const { name } = useParams<{ name: string }>();

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.sessionName}>SESSION://{name}</div>
        <nav className={styles.nav}>
          <NavLink
            to={`/sessions/${name}`}
            end
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Dashboard
          </NavLink>
          <NavLink
            to={`/sessions/${name}/recommend`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Recommendations
          </NavLink>
          <NavLink
            to={`/sessions/${name}/history`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            History
          </NavLink>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

The `end` prop on the Dashboard `NavLink` is required — without it, `/sessions/:name` (a prefix of the recommend/history routes) would report active on every route.

- [ ] **Step 4: Update `SessionLayout.module.css`'s nav rules for the underline slide**

```css
.nav {
  display: flex;
  gap: 1.2rem;
}

.nav a {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  text-decoration: none;
  color: var(--ink-faint);
  position: relative;
  padding-bottom: 4px;
  transition: color 0.15s ease;
}

.nav a::after {
  content: "";
  position: absolute;
  left: 0;
  right: 100%;
  bottom: 0;
  height: 1.5px;
  background: var(--accent);
  transition: right 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav a:hover {
  color: var(--accent);
}

.nav a:hover::after,
.nav a.active::after {
  right: 0;
}

.nav a.active {
  color: var(--accent);
}
```

(`.sessionName` was already updated in Task 1, Step 4 — no change needed here.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/SessionLayout.test.tsx`
Expected: `3 passed (3)`.

- [ ] **Step 6: Run the full suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `45 passed (45)`.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 7: Manually verify in the browser**

Confirm the session name reads `SESSION://<name>` in mono, the current page's nav link is gold with an underline, and hovering another link slides an underline in under the cursor.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/SessionLayout.tsx frontend/src/components/SessionLayout.module.css \
  frontend/src/components/SessionLayout.test.tsx
git commit -m "Add active-state underline nav and mono session label to SessionLayout"
```

---

### Task 4: `useCountUp` + DashboardPage stat cards

**Files:**
- Create: `frontend/src/hooks/useCountUp.ts`
- Create: `frontend/src/hooks/useCountUp.test.ts`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/pages/DashboardPage.module.css`
- Modify: `frontend/src/pages/DashboardPage.test.tsx`

**Interfaces:**
- Produces: `useCountUp(target: number, durationMs?: number): number` — animates from 0 to `target` on mount/target-change, returns the current animated value each render. Exported for reuse but only `DashboardPage` consumes it in this plan.

**Correctness note carried into this task's steps:** `DashboardPage.tsx` currently returns early for `state.status === "loading" | "error"` before computing `sessionStatus`. React hooks must run unconditionally on every render — calling `useCountUp` after those early returns would call a different number of hooks between the "loading" render and the "loaded" render and crash. The steps below compute safe fallback numbers *before* the early returns so `useCountUp` is always called exactly 4 times, every render.

- [ ] **Step 1: Write `useCountUp`**

Create `frontend/src/hooks/useCountUp.ts`:

```ts
import { useEffect, useState } from "react";

export function useCountUp(target: number, durationMs = 700): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let frame: number;
    let start: number | null = null;

    function step(timestamp: number) {
      if (start === null) start = timestamp;
      const progress = Math.min((timestamp - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) {
        frame = requestAnimationFrame(step);
      }
    }

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs]);

  return value;
}
```

- [ ] **Step 2: Write the test for `useCountUp`**

Create `frontend/src/hooks/useCountUp.test.ts`:

```ts
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useCountUp } from "./useCountUp";

describe("useCountUp", () => {
  it("animates from 0 up to the target value", async () => {
    const { result } = renderHook(() => useCountUp(50, 50));

    expect(result.current).toBeGreaterThanOrEqual(0);

    await waitFor(
      () => {
        expect(result.current).toBe(50);
      },
      { timeout: 1000 }
    );
  });

  it("starts a fresh animation when the target changes", async () => {
    const { result, rerender } = renderHook(({ target }) => useCountUp(target, 50), {
      initialProps: { target: 10 },
    });

    await waitFor(() => expect(result.current).toBe(10), { timeout: 1000 });

    rerender({ target: 25 });

    await waitFor(() => expect(result.current).toBe(25), { timeout: 1000 });
  });
});
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/useCountUp.test.ts`
Expected: `2 passed (2)`. (The 50ms duration keeps this fast; jsdom's `requestAnimationFrame` runs on a real timer, so this genuinely waits out the animation rather than faking it.)

- [ ] **Step 4: Update `DashboardPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getHistory,
  getStatus,
  type HistoryRow,
  type StatusResponse,
} from "../api/client";
import AccuracyChart from "../components/AccuracyChart";
import { useCountUp } from "../hooks/useCountUp";
import styles from "./DashboardPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessionStatus: StatusResponse; history: HistoryRow[] };

export default function DashboardPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    Promise.all([getStatus(name), getHistory(name)])
      .then(([sessionStatus, history]) => {
        if (!cancelled) setState({ status: "loaded", sessionStatus, history });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  // Hooks run unconditionally on every render, so compute safe fallbacks
  // here rather than after the loading/error early returns below.
  const round = state.status === "loaded" ? state.sessionStatus.current_round : 0;
  const known = state.status === "loaded" ? state.sessionStatus.n_known : 0;
  const pool = state.status === "loaded" ? state.sessionStatus.n_pool : 0;
  const accuracyTarget =
    state.status === "loaded" && state.sessionStatus.latest_accuracy !== null
      ? state.sessionStatus.latest_accuracy * 100
      : 0;

  const animatedRound = Math.round(useCountUp(round));
  const animatedKnown = Math.round(useCountUp(known));
  const animatedPool = Math.round(useCountUp(pool));
  const animatedAccuracy = useCountUp(accuracyTarget);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { sessionStatus, history } = state;

  return (
    <div>
      {sessionStatus.should_stop && (
        <div className={styles.stopBanner}>
          Stopping recommended: {sessionStatus.stop_reason}
        </div>
      )}

      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{animatedRound}</div>
          <div className={styles.statLabel}>Round</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{animatedKnown}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{animatedPool}</div>
          <div className={styles.statLabel}>In pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {sessionStatus.latest_accuracy !== null ? `${animatedAccuracy.toFixed(1)}%` : "—"}
          </div>
          <div className={styles.statLabel}>Accuracy</div>
        </div>
      </div>

      {history.length > 0 ? (
        <AccuracyChart history={history} />
      ) : (
        <p className={styles.empty}>No rounds completed yet.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Update `DashboardPage.module.css`'s `.statRow` and `.stat` for card density + lock-on hover**

```css
.statRow {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1.5rem;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0.9rem 1.1rem;
  border-radius: 8px;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.stat:hover {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(224, 189, 108, 0.25), 0 8px 24px rgba(0, 0, 0, 0.4);
  transform: translateY(-1px);
}
```

(`.statValue`/`.statLabel`/`.stopBanner`/`.loading`/`.error`/`.empty` are unchanged beyond Task 1's font/token edits — leave them as-is.)

- [ ] **Step 6: Update `DashboardPage.test.tsx`'s timing-sensitive assertions**

The three assertions that check final stat text now need to tolerate the count-up animation (default duration 700ms). Change:

```tsx
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("93.0%")).toBeInTheDocument();
```

to:

```tsx
    await waitFor(
      () => {
        expect(screen.getByText("2")).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("93.0%")).toBeInTheDocument();
```

(Only the first `waitFor` needs the extended timeout — by the time it resolves, all four `useCountUp` calls have settled together since they share the same default duration and mount at the same time, so the two plain assertions right after it don't need their own wait.)

- [ ] **Step 7: Run `DashboardPage`'s tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/DashboardPage.test.tsx`
Expected: `4 passed (4)`.

- [ ] **Step 8: Run the full suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `47 passed (47)` (45 + 2 new `useCountUp` tests, `DashboardPage.test.tsx`'s own count unchanged at 4).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 9: Manually verify in the browser**

Open a session's dashboard. Confirm the four stat numbers count up from 0 on load, and hovering a stat card shows the gold "lock-on" border + glow + slight lift.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/hooks/useCountUp.ts frontend/src/hooks/useCountUp.test.ts \
  frontend/src/pages/DashboardPage.tsx frontend/src/pages/DashboardPage.module.css \
  frontend/src/pages/DashboardPage.test.tsx
git commit -m "Add useCountUp and animate DashboardPage's stat cards"
```

---

### Task 5: SessionListPage, RecommendationsPage, HistoryPage — density pass

**Files:**
- Modify: `frontend/src/pages/SessionListPage.module.css`
- Modify: `frontend/src/pages/RecommendationsPage.module.css`
- Modify: `frontend/src/pages/HistoryPage.module.css`

`NewSessionPage` needs no changes in this task — the design spec's only requirement for it was the token/font updates already done in Task 1, and it has no session cards or tables to apply density treatment to.

No `.tsx` changes in this task — every change is CSS-only (hover treatment, table density), so no test file needs updating and no new tests are required (the existing tests assert on content/behavior, not styling).

- [ ] **Step 1: Add lock-on hover to session cards**

In `frontend/src/pages/SessionListPage.module.css`, change `.sessionCard`:

```css
.sessionCard {
  display: block;
  padding: 1.2rem 1.4rem;
  margin-bottom: 0.8rem;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.sessionCard:hover {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(224, 189, 108, 0.25), 0 8px 24px rgba(0, 0, 0, 0.4);
  transform: translateY(-1px);
}
```

- [ ] **Step 2: Table density pass on RecommendationsPage**

In `frontend/src/pages/RecommendationsPage.module.css`, update the table rules:

```css
.table th,
.table td {
  text-align: left;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--line);
}

.table td {
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.table tbody tr {
  transition: background-color 0.15s ease;
}

.table tbody tr:hover {
  background: var(--paper-raised);
}
```

(This replaces only the existing `.table th, .table td` rule and adds two new rules after it — `.table th`'s own separate rule, `.table select`, `.srOnly`, `.submit`, `.submitError` are unchanged.)

- [ ] **Step 3: Table density pass on HistoryPage**

In `frontend/src/pages/HistoryPage.module.css`, apply the same treatment:

```css
.table th,
.table td {
  text-align: left;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--line);
}

.table td {
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.table tbody tr {
  transition: background-color 0.15s ease;
}

.table tbody tr:hover {
  background: var(--paper-raised);
}
```

- [ ] **Step 4: Run the full suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `47 passed (47)` — unchanged from Task 4, since this task is CSS-only.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Manually verify in the browser**

Confirm session cards lift and glow on hover on the session list. On Recommendations and History, confirm table rows highlight on hover and data cells read in monospace.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SessionListPage.module.css frontend/src/pages/RecommendationsPage.module.css \
  frontend/src/pages/HistoryPage.module.css
git commit -m "Add hover treatment to session cards and table rows"
```

---

### Task 6: AccuracyChart — card wrapper, wider layout, draw-in, glow, pulse

**Files:**
- Modify: `frontend/src/components/AccuracyChart.tsx`
- Create: `frontend/src/components/AccuracyChart.module.css`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/components/AccuracyChart.test.tsx`

**Interfaces:**
- Consumes: nothing new. `AccuracyChart`'s props (`{ history: HistoryRow[] }`) are unchanged, so `DashboardPage` and `HistoryPage` need no changes to keep using it.
- Produces: `AccuracyChart` now renders its own card wrapper (border, corner brackets, header) — callers no longer need to wrap it themselves. This is why "avoid blank space" is fixed here rather than per-caller: today the chart has no wrapping card at all, just a bare `ResponsiveContainer`, and the surrounding page has no width constraint on it either.

**Verified before writing this task:** jsdom cannot render Recharts' internal SVG at all — `ResponsiveContainer` produces a zero-size container in the test environment (confirmed by spiking it: rendering `AccuracyChart` in a test and inspecting `container.innerHTML` shows an empty `.recharts-responsive-container` div, no `<svg>`, no `.recharts-line-curve`). This means the draw-in/glow/pulse CSS added in this task is **not testable via `vitest`** — the existing two smoke tests (container renders, given real vs. empty history) still pass because they only check for `.recharts-responsive-container`'s presence, not its contents. Step 5 below is a live-browser check, not a unit test, and it is not optional — it's the only way this task's core visual change gets verified at all.

- [ ] **Step 1: Add the shared corner-bracket utility classes**

In `frontend/src/styles/global.css`, append:

```css
.bracket {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 1.5px solid var(--line-strong);
  opacity: 0.8;
  pointer-events: none;
}

.bracket-tl {
  top: 6px;
  left: 6px;
  border-right: none;
  border-bottom: none;
}

.bracket-tr {
  top: 6px;
  right: 6px;
  border-left: none;
  border-bottom: none;
}

.bracket-bl {
  bottom: 6px;
  left: 6px;
  border-right: none;
  border-top: none;
}

.bracket-br {
  bottom: 6px;
  right: 6px;
  border-left: none;
  border-top: none;
}
```

- [ ] **Step 2: Write `AccuracyChart.module.css`**

Create `frontend/src/components/AccuracyChart.module.css`:

```css
.card {
  position: relative;
  border-radius: 8px;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  padding: 16px 10px 10px;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 0 10px 8px;
}

.head h4 {
  margin: 0;
  font-family: var(--font-body);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--ink-soft);
}

.legend {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--accent);
}

.chartWrap :global(.recharts-line-curve) {
  stroke-dasharray: 1000;
  stroke-dashoffset: 1000;
  animation: draw 1.1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 0.15s;
  filter: url(#chartGlow);
}

@keyframes draw {
  to {
    stroke-dashoffset: 0;
  }
}

.pulseRing {
  animation: pulse 2s ease-out infinite;
  transform-origin: center;
}

@keyframes pulse {
  0% {
    r: 5;
    opacity: 0.8;
  }
  100% {
    r: 14;
    opacity: 0;
  }
}
```

(`stroke-dasharray: 1000` is comfortably larger than any realistic path length here — a session's round count is small — so the whole line is hidden at `dashoffset: 1000` and fully drawn by the time it reaches `0`, regardless of exact path length.)

- [ ] **Step 3: Update `AccuracyChart.tsx`**

```tsx
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryRow } from "../api/client";
import { historyHasCost, historyToChartData } from "./chartData";
import styles from "./AccuracyChart.module.css";

interface AccuracyChartProps {
  history: HistoryRow[];
}

function PulsingDot(props: { cx?: number; cy?: number; index?: number; totalPoints: number }) {
  const { cx, cy, index, totalPoints } = props;
  if (cx === undefined || cy === undefined || index === undefined) return null;
  const isLast = index === totalPoints - 1;
  return (
    <g>
      {isLast && (
        <circle
          className={styles.pulseRing}
          cx={cx}
          cy={cy}
          r={5}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={1.5}
        />
      )}
      <circle
        cx={cx}
        cy={cy}
        r={isLast ? 4.5 : 3.5}
        fill={isLast ? "var(--accent)" : "var(--paper-raised)"}
        stroke="var(--accent)"
        strokeWidth={2}
      />
    </g>
  );
}

export default function AccuracyChart({ history }: AccuracyChartProps) {
  const data = historyToChartData(history);
  const hasCost = historyHasCost(history);

  return (
    <div className={styles.card}>
      <span className="bracket bracket-tl" />
      <span className="bracket bracket-tr" />
      <span className="bracket bracket-bl" />
      <span className="bracket bracket-br" />
      <div className={styles.head}>
        <h4>Accuracy over rounds</h4>
        <span className={styles.legend}>● accuracy</span>
      </div>
      <div className={styles.chartWrap}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 8 }}>
            <defs>
              <filter id="chartGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
            <XAxis
              dataKey="round"
              stroke="var(--ink-faint)"
              tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
              label={{ value: "Round", position: "insideBottom", offset: -4, fill: "var(--ink-faint)" }}
            />
            <YAxis
              yAxisId="accuracy"
              domain={[0, 100]}
              stroke="var(--ink-faint)"
              tick={{ fill: "var(--ink-faint)", fontSize: 12 }}
              label={{ value: "Accuracy %", angle: -90, position: "insideLeft", fill: "var(--ink-faint)" }}
            />
            {hasCost && (
              <YAxis
                yAxisId="cost"
                orientation="right"
                stroke="var(--brass)"
                tick={{ fill: "var(--brass)", fontSize: 12 }}
                label={{ value: "Cumulative cost", angle: 90, position: "insideRight", fill: "var(--brass)" }}
              />
            )}
            <Tooltip
              contentStyle={{
                background: "var(--paper)",
                border: "1px solid var(--accent)",
                borderRadius: 6,
              }}
              labelStyle={{ color: "var(--ink)" }}
            />
            <Line
              yAxisId="accuracy"
              type="monotone"
              dataKey="accuracy"
              stroke="var(--accent)"
              strokeWidth={2.5}
              dot={<PulsingDot totalPoints={data.length} />}
              name="Accuracy %"
            />
            {hasCost && (
              <Line
                yAxisId="cost"
                type="monotone"
                dataKey="cost"
                stroke="var(--brass)"
                strokeWidth={2}
                dot={{ fill: "var(--brass)" }}
                name="Cumulative cost"
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

Notes on this diff versus the design spec's original technique:
- The glow `<filter>` is defined via a plain `<defs>` JSX child inside `<LineChart>` (the same pattern Recharts' own gradient-fill examples use — Recharts passes unrecognized children like `<defs>` straight through into the rendered SVG), rather than a Recharts `defs` prop (Recharts 2's `LineChart` has no such prop).
- The draw-in animation targets `.recharts-line-curve` via `:global(...)` inside the CSS module (needed because that class name comes from Recharts, not from this module, so CSS Modules' scoping must be bypassed for that one selector).
- The four corner-bracket `<span>`s reference the plain (non-module) classes added to `global.css` in Step 1 directly as literal strings (`"bracket bracket-tl"`, not `styles.bracket`) — they live outside this component's CSS module by design, so any future card elsewhere in the app can reuse the same four classes.

- [ ] **Step 4: Run the existing chart tests to confirm they still pass**

Run: `cd frontend && npx vitest run src/components/AccuracyChart.test.tsx`
Expected: `2 passed (2)` — both existing smoke tests (container renders, given real vs. empty history) still hold; they only ever checked for `.recharts-responsive-container`, which is unaffected by this task's changes.

- [ ] **Step 5: Manually verify in the browser — this is the real verification for this task**

`npm run dev` + `make api`. Create or open a session with at least 2 completed rounds (use `acquireml demo --init` and run one round through the UI if you don't have one handy — see `CLAUDE.md`'s demo instructions). On the Dashboard and History pages:
- Confirm the chart card has visible corner brackets and fills the full width of its container (no large empty margin on the right — this was the specific "avoid blank space" feedback from the design review).
- Confirm the line visibly draws itself in (animates from nothing to the full line) shortly after the page loads, with a soft glow.
- Confirm the most recent point pulses (an expanding, fading ring).
- Confirm hovering a point still shows the Recharts tooltip with the round number and value (unchanged from before this task).

If the draw-in/glow does not render correctly (e.g. `.recharts-line-curve` isn't the actual class name in the installed Recharts version, or the `:global()` selector doesn't reach it), fall back to a CSS `clip-path` reveal on `.chartWrap` instead (e.g. animating `clip-path: inset(0 100% 0 0)` to `inset(0 0 0 0)`) — visually similar, no dependency on Recharts' internal class names. Note in the commit message which technique ended up being used.

- [ ] **Step 6: Run the full suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `47 passed (47)` — unchanged, per Step 4.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AccuracyChart.tsx frontend/src/components/AccuracyChart.module.css \
  frontend/src/styles/global.css frontend/src/components/AccuracyChart.test.tsx
git commit -m "Give AccuracyChart its own card, draw-in/glow/pulse motion, and a full-width layout"
```

(If Step 4 required no changes to `AccuracyChart.test.tsx`, `git add` that path is a no-op — fine either way.)

---

### Task 7: Full regression pass, browser walkthrough, docs

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run the full frontend suite**

Run: `cd frontend && npm test -- --run`
Expected: `47 passed (47)`.

- [ ] **Step 2: Run the typecheck and production build**

Run: `cd frontend && npm run build`
Expected: succeeds (this runs `tsc --noEmit && vite build`, catching both type errors and any build-time issue the dev server wouldn't surface).

- [ ] **Step 3: Run the backend suite (unaffected by this plan, but confirm no regressions)**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q` (from repo root)
Expected: `221 passed`.

- [ ] **Step 4: Full browser walkthrough of all five pages**

`npm run dev` + `make api`. Using a real or `acquireml demo --init` session with at least one completed round:
- Session list: cards lift/glow on hover, no serif font, background grid + scan-line visible.
- New session: form renders correctly, submit button uses the new accent colors.
- Dashboard: stat cards count up and lock-on-hover; chart card has brackets, draws in, pulses, fills its width.
- Recommendations: nav underline is active on this page, table rows highlight on hover, submitting still works end-to-end (reuse the same lifecycle check from the previous phase — create a batch, submit a few results, confirm it navigates back to the dashboard with updated stats).
- History: same chart treatment as Dashboard, export CSV still downloads a real file.

Stop both servers when done.

- [ ] **Step 5: Update `CLAUDE.md`'s "Web UI frontend" paragraph**

Add a sentence describing the visual system after the existing description of the five pages (find the paragraph starting "**Web UI frontend** (`frontend/`):" in `CLAUDE.md`), noting: the app now uses a denser sans-serif visual system (Manrope throughout, no serif font — that's reserved for the landing page only), a shared `AppShell` providing ambient background motion (grid texture, scan-line sweep, cursor-reactive glow), `useCountUp`/`useCursorGlow` hooks, and `AccuracyChart` drawing itself in with a glow and a pulsing latest point. Update the frontend test count in that paragraph (and anywhere else in `CLAUDE.md` citing "41 frontend tests") to the new total from Step 1.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "Document the web UI visual system overhaul in CLAUDE.md"
```
