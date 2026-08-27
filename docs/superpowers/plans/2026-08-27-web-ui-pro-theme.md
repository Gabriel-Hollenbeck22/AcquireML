# Web UI "Pro" Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a second, professional/clean "Navy Instrument" visual theme for the
web UI, covering every page, reachable at `/pro/*` routes alongside the existing
dark/electric-blue app — without touching or risking anything in the current app.

**Architecture:** A new `frontend/src/pro/` tree (styles/components/pages) mirrors
the shape of the existing `styles/`/`components/`/`pages/` trees. `App.tsx` splits
into `ClassicApp` (today's app, unchanged, still mounted at `/`) and `ProApp` (new,
mounted at `/pro/*`), each with its own shell. Pro pages reuse `api/client.ts` and
every pure-logic module verbatim (`sessionSort.ts`, `costProjection.ts`,
`budgetChartData.ts`, `chartData.ts`, `commandFilter.ts`, `useCountUp.ts`) — only
presentation (`.tsx` markup + `.module.css`) is new.

**Tech Stack:** React 18, TypeScript 5 (strict), Vite 5, React Router v6, Recharts 2,
Vitest 2 + React Testing Library 16, CSS Modules.

**Spec:** `docs/superpowers/specs/2026-08-27-web-ui-pro-theme-design.md` — read
this for the full rationale and the three rounds of visual-companion mockups this
design came out of. This plan implements that spec exactly; do not re-derive
design decisions from scratch.

## Global Constraints

- New files only live under `frontend/src/pro/` (styles/components/pages) — never
  add Pro-prefixed files anywhere inside the existing `styles/`/`components/`/
  `pages/` directories, and never edit any existing page/component's `.tsx` or
  `.module.css` except `App.tsx` (Task 4) and `frontend/index.html` (Task 1, font
  link only).
- Every Pro page fetches data through the **exact same** `api/client.ts` functions
  the classic page uses — same function names, same call signatures, same
  loading/error state shape (`{status: "loading"} | {status: "error", message} |
  {status: "loaded", ...}`). Do not introduce new API functions or change any
  existing one.
- Design tokens: `--pro-*` custom properties only, defined once in
  `frontend/src/pro/styles/tokens.css`, scoped under a `.pro-root` class applied
  by `ProAppShell`. Never reference the classic app's tokens (`--paper`,
  `--accent`, etc.) from any Pro file, and never reference `--pro-*` tokens from
  any classic file.
- Fonts: Inter for all Pro UI text/headings (`var(--pro-font-body)`), IBM Plex
  Mono for all data/numeric values (`var(--pro-font-mono)`) — every stat number,
  every table cell containing a value, every session name.
- No `AppShell.test.tsx` equivalent is required for `ProAppShell` — the existing
  codebase has no `AppShell.test.tsx` either (its only interactive surface, the
  Cmd+K listener, is covered indirectly through `CommandPalette.test.tsx`); the
  same applies to `ProCommandPalette.test.tsx`, which *is* required (mirrors the
  existing `CommandPalette.test.tsx`).
- Motion allowed in Pro: `useCountUp` on stat-card numbers (reused hook,
  unchanged), and ordinary CSS `transition` on `:hover`/`:active` states. Motion
  NOT allowed in Pro: any `@keyframes` animation, any pseudo-element glow/scan/
  cursor-tracking effect, any idle-state pulsing. If a task's code below includes
  a `transition`, keep it; do not add `animation`/`@keyframes` anywhere in `pro/`.
- Every new page ships with a co-located `.test.tsx` adapted from the matching
  classic page's existing test file (named identically, `Pro`-prefixed) —
  behavior assertions carry over unchanged (same loading/error/data-shape
  behavior, since the data-fetching code is unchanged); only the queries that
  depend on removed/renamed classic-only text change.
- `npx tsc --noEmit` and `npm test -- --run` must stay clean after every task.

---

### Task 1: Pro design tokens + Inter font

**Files:**
- Create: `frontend/src/pro/styles/tokens.css`
- Modify: `frontend/index.html:9` (font link)

**Interfaces:**
- Produces: every `--pro-*` custom property listed below, consumed by every
  later task's `.module.css` files.

- [ ] **Step 1: Create the tokens file**

```css
/* frontend/src/pro/styles/tokens.css */
.pro-root {
  --pro-paper: #f8fafc;
  --pro-surface: #ffffff;
  --pro-ink: #0f172a;
  --pro-ink-soft: #475569;
  --pro-ink-faint: #94a3b8;
  --pro-accent: #1e40af;
  --pro-accent-bright: #2563eb;
  --pro-line: #eef2f6;
  --pro-line-soft: #f1f5f9;
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

  background: var(--pro-paper);
  color: var(--pro-ink);
  font-family: var(--pro-font-body);
  min-height: 100vh;
}
```

- [ ] **Step 2: Add Inter to the shared Google Fonts link**

In `frontend/index.html`, the existing font `<link>` (around line 9) reads:

```html
      href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap"
```

Change it to add the Inter family (weights 400/500/600/700, matching what the
Pro mockups used) alongside the existing two:

```html
      href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
```

Note `IBM+Plex+Mono` gained weight `600` (needed by Pro's stat numbers/headings
that use mono at weight 600) — this is additive and does not change how the
classic app's mono text (which only ever uses 400/500) renders.

- [ ] **Step 3: Verify the full suite is still green**

Run: `cd frontend && npm test -- --run`
Expected: `108 passed (108)` — unchanged, since no component consumes
`tokens.css` yet in this task.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pro/styles/tokens.css frontend/index.html
git commit -m "Add Pro theme design tokens and load Inter font"
```

---

### Task 2: `ProAppShell` + `ProCommandPalette`

**Files:**
- Create: `frontend/src/pro/components/ProAppShell.tsx`
- Create: `frontend/src/pro/components/ProAppShell.module.css`
- Create: `frontend/src/pro/components/ProCommandPalette.tsx`
- Create: `frontend/src/pro/components/ProCommandPalette.module.css`
- Create: `frontend/src/pro/components/ProCommandPalette.test.tsx`

**Interfaces:**
- Consumes: `../../styles/tokens.css` is NOT imported here — this task imports
  `../styles/tokens.css` (the Pro one, from Task 1) as a side-effect CSS import
  in `ProAppShell.tsx`, the same pattern `main.tsx` uses for the classic
  `styles/global.css`. Consumes `commandFilter.ts`'s `filterCommands`/`Command`
  (unchanged import path `../../components/commandFilter`), and `api/client.ts`'s
  `getStatus`/`listSessions` (unchanged import path `../../api/client`).
- Produces: `ProAppShell` (children wrapper), used by `ProApp` in Task 4.

- [ ] **Step 1: Write `ProCommandPalette.tsx`**

Same behavior as the classic `CommandPalette.tsx` (same hooks, same keyboard
handling, same `filterCommands` logic) — only the route paths change (`/pro/...`
prefix) and the presentation is new:

```tsx
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getStatus, listSessions } from "../../api/client";
import { filterCommands, type Command } from "../../components/commandFilter";
import styles from "./ProCommandPalette.module.css";

interface ProCommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export default function ProCommandPalette({ open, onClose }: ProCommandPaletteProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [sessionNames, setSessionNames] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [currentSessionCostTracked, setCurrentSessionCostTracked] = useState(false);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelectedIndex(0);
    listSessions()
      .then((sessions) => setSessionNames(sessions.map((s) => s.name)))
      .catch(() => setSessionNames([]));
  }, [open]);

  const currentSessionName = useMemo(() => {
    const match = location.pathname.match(/^\/pro\/sessions\/([^/]+)/);
    return match ? match[1] : null;
  }, [location.pathname]);

  useEffect(() => {
    if (!open || !currentSessionName) {
      setCurrentSessionCostTracked(false);
      return;
    }
    getStatus(currentSessionName)
      .then((status) => {
        setCurrentSessionCostTracked(
          status?.cost_per_sample !== null && status?.cost_per_sample !== undefined
        );
      })
      .catch(() => setCurrentSessionCostTracked(false));
  }, [open, currentSessionName]);

  const commands = useMemo<Command[]>(() => {
    const go = (path: string) => () => {
      navigate(path);
      onClose();
    };
    const list: Command[] = [
      { id: "new-session", label: "New session", action: go("/pro/new") },
      ...sessionNames.map((name) => ({
        id: `go-${name}`,
        label: `Go to session: ${name}`,
        action: go(`/pro/sessions/${name}`),
      })),
    ];
    if (currentSessionName) {
      list.push(
        { id: "cur-dashboard", label: "Dashboard", action: go(`/pro/sessions/${currentSessionName}`) },
        { id: "cur-recommend", label: "Recommendations", action: go(`/pro/sessions/${currentSessionName}/recommend`) },
        { id: "cur-history", label: "History", action: go(`/pro/sessions/${currentSessionName}/history`) },
        { id: "cur-settings", label: "Settings", action: go(`/pro/sessions/${currentSessionName}/settings`) }
      );
      if (currentSessionCostTracked) {
        list.push({ id: "cur-budget", label: "Budget", action: go(`/pro/sessions/${currentSessionName}/budget`) });
      }
    }
    return list;
  }, [sessionNames, currentSessionName, currentSessionCostTracked, navigate, onClose]);

  const filtered = filterCommands(commands, query);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        filtered[selectedIndex]?.action();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, filtered, selectedIndex, onClose]);

  if (!open) return null;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.palette} onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          className={styles.input}
          placeholder="Jump to a session or page…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <ul className={styles.list}>
          {filtered.map((cmd, i) => (
            <li
              key={cmd.id}
              className={i === selectedIndex ? styles.selected : undefined}
              onMouseEnter={() => setSelectedIndex(i)}
              onClick={cmd.action}
            >
              {cmd.label}
            </li>
          ))}
          {filtered.length === 0 && <li className={styles.noResults}>No matches</li>}
        </ul>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `ProCommandPalette.module.css`**

```css
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 14vh;
  z-index: 100;
}

.palette {
  width: min(560px, 90vw);
  background: var(--pro-surface);
  border-radius: var(--pro-radius-lg);
  box-shadow: var(--pro-shadow-md);
  overflow: hidden;
}

.input {
  width: 100%;
  border: none;
  border-bottom: 1px solid var(--pro-line);
  padding: 14px 16px;
  font-family: var(--pro-font-body);
  font-size: 0.95rem;
  color: var(--pro-ink);
  outline: none;
  box-sizing: border-box;
}

.input:focus {
  outline: none;
}

.list {
  list-style: none;
  margin: 0;
  padding: 6px;
  max-height: 320px;
  overflow-y: auto;
}

.list li {
  padding: 9px 12px;
  border-radius: var(--pro-radius-sm);
  font-size: 0.85rem;
  color: var(--pro-ink-soft);
  cursor: pointer;
}

.selected {
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
}

.noResults {
  color: var(--pro-ink-faint);
  cursor: default;
}
```

- [ ] **Step 3: Write `ProCommandPalette.test.tsx`**

Adapted from the classic `CommandPalette.test.tsx` — identical behavior, routes
prefixed with `/pro`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProCommandPalette from "./ProCommandPalette";

describe("ProCommandPalette", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <MemoryRouter>
        <ProCommandPalette open={false} onClose={vi.fn()} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("lists sessions as commands when open", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      { name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.9 },
    ]);
    render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    expect(await screen.findByText(/go to session: azm-project/i)).toBeInTheDocument();
  });

  it("filters commands as the query changes", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      { name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.9 },
    ]);
    render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    await screen.findByText(/go to session: azm-project/i);
    fireEvent.change(screen.getByPlaceholderText(/jump to/i), { target: { value: "new session" } });

    expect(screen.getByText("New session")).toBeInTheDocument();
    expect(screen.queryByText(/go to session: azm-project/i)).not.toBeInTheDocument();
  });

  it("calls onClose when Escape is pressed", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={onClose} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/jump to/i)).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when clicking the backdrop", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    const onClose = vi.fn();
    const { container } = render(
      <MemoryRouter>
        <ProCommandPalette open={true} onClose={onClose} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/jump to/i)).toBeInTheDocument();
    });
    fireEvent.click(container.firstChild as Element);

    expect(onClose).toHaveBeenCalled();
  });

  it("does not show a Budget command for a session without cost tracking", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });
    render(
      <MemoryRouter initialEntries={["/pro/sessions/azm-project"]}>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    expect(await screen.findByText("Dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Budget")).not.toBeInTheDocument();
  });

  it("shows a Budget command for a session with cost tracking", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: 12.5,
      total_cost: 125, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });
    render(
      <MemoryRouter initialEntries={["/pro/sessions/azm-project"]}>
        <ProCommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>
    );

    expect(await screen.findByText("Budget")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Write `ProAppShell.tsx`**

```tsx
import { useEffect, useState, type ReactNode } from "react";
import "../styles/tokens.css";
import ProCommandPalette from "./ProCommandPalette";
import styles from "./ProAppShell.module.css";

interface ProAppShellProps {
  children: ReactNode;
}

export default function ProAppShell({ children }: ProAppShellProps) {
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className={`pro-root ${styles.shell}`}>
      {children}
      <button
        type="button"
        className={styles.paletteHint}
        onClick={() => setPaletteOpen(true)}
        aria-label="Open command palette"
      >
        ⌘K
      </button>
      <ProCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
```

- [ ] **Step 5: Write `ProAppShell.module.css`**

```css
.shell {
  position: relative;
}

.paletteHint {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 10;
  background: var(--pro-surface);
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  padding: 6px 10px;
  font-family: var(--pro-font-mono);
  font-size: 0.8rem;
  color: var(--pro-ink-faint);
  cursor: pointer;
  box-shadow: var(--pro-shadow-sm);
  transition: color 0.15s ease, box-shadow 0.15s ease;
}

.paletteHint:hover {
  color: var(--pro-accent);
  box-shadow: var(--pro-shadow-md);
}
```

- [ ] **Step 6: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/components/ProCommandPalette.test.tsx`
Expected: `7 passed`.

Run: `npm test -- --run`
Expected: `115 passed (115)` (108 + 7 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pro/components/ProAppShell.tsx frontend/src/pro/components/ProAppShell.module.css \
  frontend/src/pro/components/ProCommandPalette.tsx frontend/src/pro/components/ProCommandPalette.module.css \
  frontend/src/pro/components/ProCommandPalette.test.tsx
git commit -m "Add ProAppShell and ProCommandPalette"
```

---

### Task 3: `ProAccuracyChart`

**Files:**
- Create: `frontend/src/pro/components/ProAccuracyChart.tsx`
- Create: `frontend/src/pro/components/ProAccuracyChart.module.css`
- Create: `frontend/src/pro/components/ProAccuracyChart.test.tsx`

**Interfaces:**
- Consumes: `historyToChartData`/`historyHasCost` from `../../components/chartData`
  (unchanged), `HistoryRow` type from `../../api/client`.
- Produces: `ProAccuracyChart({ history: HistoryRow[] })`, used by
  `ProDashboardPage` (Task 6) and `ProHistoryPage` (Task 8).

Per the spec: reuses Recharts (already a dependency), keeps real gridlines/axes,
but drops the classic chart's glow `<filter>` and pulsing-ring latest-point
treatment in favor of a gradient-filled area under the accuracy line and a
plain static halo (not `@keyframes`-animated) behind the latest point.

- [ ] **Step 1: Write `ProAccuracyChart.tsx`**

```tsx
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryRow } from "../../api/client";
import { historyHasCost, historyToChartData } from "../../components/chartData";
import styles from "./ProAccuracyChart.module.css";

interface ProAccuracyChartProps {
  history: HistoryRow[];
}

function ProDot(props: { cx?: number; cy?: number; index?: number; totalPoints: number }) {
  const { cx, cy, index, totalPoints } = props;
  if (cx === undefined || cy === undefined || index === undefined) return null;
  const isLast = index === totalPoints - 1;
  return (
    <g>
      {isLast && <circle cx={cx} cy={cy} r={9} fill="var(--pro-accent)" opacity={0.15} />}
      <circle
        cx={cx}
        cy={cy}
        r={isLast ? 4.5 : 3.5}
        fill={isLast ? "var(--pro-accent)" : "var(--pro-surface)"}
        stroke="var(--pro-accent)"
        strokeWidth={2}
      />
    </g>
  );
}

export default function ProAccuracyChart({ history }: ProAccuracyChartProps) {
  const data = historyToChartData(history);
  const hasCost = historyHasCost(history);

  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <h4>Accuracy over rounds</h4>
        <span className={styles.legend}>● accuracy</span>
      </div>
      <div className={styles.chartWrap}>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 8 }}>
            <defs>
              <linearGradient id="proAreaFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--pro-accent)" stopOpacity={0.16} />
                <stop offset="100%" stopColor="var(--pro-accent)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--pro-line-soft)" />
            <XAxis
              dataKey="round"
              stroke="var(--pro-ink-faint)"
              tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
              label={{ value: "Round", position: "insideBottom", offset: -4, fill: "var(--pro-ink-faint)" }}
            />
            <YAxis
              yAxisId="accuracy"
              domain={[0, 100]}
              stroke="var(--pro-ink-faint)"
              tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
              label={{ value: "Accuracy %", angle: -90, position: "insideLeft", fill: "var(--pro-ink-faint)" }}
            />
            {hasCost && (
              <YAxis
                yAxisId="cost"
                orientation="right"
                stroke="var(--pro-ink-soft)"
                tick={{ fill: "var(--pro-ink-soft)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
                label={{ value: "Cumulative cost", angle: 90, position: "insideRight", fill: "var(--pro-ink-soft)" }}
              />
            )}
            <Tooltip
              contentStyle={{
                background: "var(--pro-surface)",
                border: "1px solid var(--pro-line)",
                borderRadius: 6,
                boxShadow: "var(--pro-shadow-md)",
              }}
              labelStyle={{ color: "var(--pro-ink)" }}
            />
            <Area
              yAxisId="accuracy"
              type="monotone"
              dataKey="accuracy"
              stroke="var(--pro-accent)"
              strokeWidth={2.5}
              fill="url(#proAreaFill)"
              dot={<ProDot totalPoints={data.length} />}
              name="Accuracy %"
            />
            {hasCost && (
              <Line
                yAxisId="cost"
                type="monotone"
                dataKey="cost"
                stroke="var(--pro-ink-soft)"
                strokeWidth={2}
                strokeDasharray="4 3"
                dot={{ fill: "var(--pro-ink-soft)", r: 3 }}
                name="Cumulative cost"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `ProAccuracyChart.module.css`**

```css
.card {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 16px 18px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.head h4 {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.legend {
  font-family: var(--pro-font-mono);
  font-size: 0.7rem;
  color: var(--pro-accent);
}

.chartWrap {
  width: 100%;
}
```

- [ ] **Step 3: Write `ProAccuracyChart.test.tsx`**

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProAccuracyChart from "./ProAccuracyChart";
import type { HistoryRow } from "../../api/client";

const sampleHistory: HistoryRow[] = [
  {
    round_number: 1,
    n_known: 25,
    accuracy: 0.85,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-19T00:00:00Z",
  },
  {
    round_number: 2,
    n_known: 30,
    accuracy: 0.9,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-20T00:00:00Z",
  },
];

describe("ProAccuracyChart", () => {
  it("renders without crashing given real history data", () => {
    const { container } = render(<ProAccuracyChart history={sampleHistory} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });

  it("renders without crashing given empty history", () => {
    const { container } = render(<ProAccuracyChart history={[]} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/components/ProAccuracyChart.test.tsx`
Expected: `2 passed`.

Run: `npm test -- --run`
Expected: `117 passed (117)` (115 + 2 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pro/components/ProAccuracyChart.tsx frontend/src/pro/components/ProAccuracyChart.module.css \
  frontend/src/pro/components/ProAccuracyChart.test.tsx
git commit -m "Add ProAccuracyChart"
```

---

### Task 4: Split `App.tsx` into `ClassicApp`/`ProApp`, add `ProSessionListPage` + `ProNewSessionPage`

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Create: `frontend/src/pro/pages/ProSessionListPage.tsx`
- Create: `frontend/src/pro/pages/ProSessionListPage.module.css`
- Create: `frontend/src/pro/pages/ProSessionListPage.test.tsx`
- Create: `frontend/src/pro/pages/ProNewSessionPage.tsx`
- Create: `frontend/src/pro/pages/ProNewSessionPage.module.css`
- Create: `frontend/src/pro/pages/ProNewSessionPage.test.tsx`

**Interfaces:**
- Consumes: `sortSessions`/`SortKey` from `../../pages/sessionSort` (unchanged),
  `listSessions`/`createSession`/`SessionSummary` from `../../api/client`
  (unchanged), `ProAppShell` from Task 2.
- Produces: `ClassicApp`/`ProApp` split inside `App.tsx` — every later task adds
  routes to `ProApp`'s `<Routes>` block, never touches `ClassicApp`.

- [ ] **Step 1: Rewrite `App.tsx`**

React Router v6's wildcard-mount pattern: a parent `<Route path="/pro/*">` makes
everything after `/pro/` the "remaining" pathname, so a `<Routes>` nested inside
the element it renders matches against that remainder — `path="/"` there means
`/pro`, `path="/new"` means `/pro/new`, exactly mirroring how the classic routes
already work at the top level.

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import HistoryPage from "./pages/HistoryPage";
import OverviewPage from "./pages/OverviewPage";
import ExplainPage from "./pages/ExplainPage";
import ComparePage from "./pages/ComparePage";
import ValidatePage from "./pages/ValidatePage";
import SettingsPage from "./pages/SettingsPage";
import BudgetPage from "./pages/BudgetPage";
import ProAppShell from "./pro/components/ProAppShell";
import ProSessionListPage from "./pro/pages/ProSessionListPage";
import ProNewSessionPage from "./pro/pages/ProNewSessionPage";

function ClassicApp() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="recommend" element={<RecommendationsPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="explain" element={<ExplainPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="validate" element={<ValidatePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="budget" element={<BudgetPage />} />
        </Route>
      </Routes>
    </AppShell>
  );
}

function ProApp() {
  return (
    <ProAppShell>
      <Routes>
        <Route path="/" element={<ProSessionListPage />} />
        <Route path="/new" element={<ProNewSessionPage />} />
      </Routes>
    </ProAppShell>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/pro/*" element={<ProApp />} />
        <Route path="/*" element={<ClassicApp />} />
      </Routes>
    </BrowserRouter>
  );
}
```

Later tasks (5–14) add exactly one more `<Route>` line to `ProApp`'s `<Routes>`
each (Task 5 adds the `/sessions/:name` `ProSessionLayout` parent route with a
nested `index` route; Tasks 6–14 each add one nested route under it) — never
touch `ClassicApp`.

- [ ] **Step 2: Add a `/pro` smoke test to `App.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "./api/client";
import App from "./App";

describe("App", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the session list at the root route", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });
  });

  it("renders the Pro session list at the /pro route", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    window.history.pushState({}, "", "/pro");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 3: Write `ProSessionListPage.tsx`**

Same behavior as the classic `SessionListPage.tsx` — same loading/error/empty/
loaded states, same sort dropdown wired to the same `sortSessions` — links point
at `/pro/...` instead of `/...`:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionSummary } from "../../api/client";
import { sortSessions, type SortKey } from "../../pages/sessionSort";
import styles from "./ProSessionListPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessions: SessionSummary[] };

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "name", label: "Name" },
  { value: "round", label: "Round" },
  { value: "accuracy", label: "Accuracy" },
  { value: "known", label: "Known" },
];

export default function ProSessionListPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [sortBy, setSortBy] = useState<SortKey>("name");

  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then((sessions) => {
        if (!cancelled) setState({ status: "loaded", sessions });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Sessions</h1>
        <Link to="/pro/new" className={styles.newLink}>
          New session
        </Link>
      </div>

      {state.status === "loaded" && state.sessions.length > 0 && (
        <div className={styles.sortRow}>
          <label htmlFor="sortBy">Sort by</label>
          <select id="sortBy" value={sortBy} onChange={(e) => setSortBy(e.target.value as SortKey)}>
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      )}

      {state.status === "loading" && <p className={styles.loading}>Loading…</p>}

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && state.sessions.length === 0 && (
        <p className={styles.empty}>No sessions yet — create one to get started.</p>
      )}

      {state.status === "loaded" && state.sessions.length > 0 && (
        <div className={styles.cardGrid}>
          {sortSessions(state.sessions, sortBy).map((session) => (
            <Link
              key={session.name}
              to={`/pro/sessions/${session.name}`}
              className={styles.sessionCard}
            >
              <div className={styles.sessionName}>{session.name}</div>
              <div className={styles.statRow}>
                <div className={styles.stat}>
                  <div className={styles.statValue}>{session.current_round}</div>
                  <div className={styles.statLabel}>Round</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles.statValue}>{session.n_known}</div>
                  <div className={styles.statLabel}>Known</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles.statValue}>{session.n_pool}</div>
                  <div className={styles.statLabel}>Pool</div>
                </div>
                <div className={styles.stat}>
                  <div
                    className={
                      session.latest_accuracy !== null && session.latest_accuracy >= 0.9
                        ? `${styles.statValue} ${styles.highAccuracy}`
                        : styles.statValue
                    }
                  >
                    {session.latest_accuracy !== null ? `${(session.latest_accuracy * 100).toFixed(1)}%` : "—"}
                  </div>
                  <div className={styles.statLabel}>Accuracy</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Write `ProSessionListPage.module.css`**

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem clamp(2rem, 4vw, 4rem);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.header h1 {
  font-size: 1.5rem;
}

.newLink {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1.1rem;
  border-radius: var(--pro-radius-sm);
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
  text-decoration: none;
  box-shadow: var(--pro-shadow-btn);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.newLink:hover {
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.35);
  transform: translateY(-1px);
}

.sortRow {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 1.25rem;
  font-size: 0.8rem;
  color: var(--pro-ink-soft);
}

.sortRow select {
  font-family: var(--pro-font-body);
  font-size: 0.82rem;
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  background: var(--pro-surface);
  color: var(--pro-ink);
}

.loading,
.error,
.empty {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.cardGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.sessionCard {
  display: block;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 1.1rem 1.2rem;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.sessionCard:hover {
  box-shadow: var(--pro-shadow-md);
  transform: translateY(-2px);
}

.sessionName {
  font-weight: 700;
  font-size: 1rem;
  margin-bottom: 0.8rem;
  color: var(--pro-ink);
}

.statRow {
  display: flex;
  gap: 0.6rem;
}

.stat {
  flex: 1;
}

.statValue {
  font-family: var(--pro-font-mono);
  font-size: 1rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.highAccuracy {
  color: var(--pro-pos-ink);
}

.statLabel {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pro-ink-faint);
  margin-top: 0.15rem;
}
```

- [ ] **Step 5: Write `ProSessionListPage.test.tsx`**

Adapted from `SessionListPage.test.tsx` — only the new-session link's expected
`href` changes, from `/new` to `/pro/new`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProSessionListPage from "./ProSessionListPage";

describe("ProSessionListPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state, then the list of sessions", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      {
        name: "azm-project",
        current_round: 2,
        n_known: 45,
        n_pool: 55,
        n_pending: 0,
        latest_accuracy: 0.93,
      },
    ]);

    render(
      <MemoryRouter>
        <ProSessionListPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("azm-project")).toBeInTheDocument();
    });
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
    expect(screen.getByText("93.0%")).toBeInTheDocument();
  });

  it("shows an empty state when there are no sessions", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <ProSessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
    });
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "listSessions").mockRejectedValue(new Error("network down"));

    render(
      <MemoryRouter>
        <ProSessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/network down/i)).toBeInTheDocument();
    });
  });

  it("links to the new-session page", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <ProSessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /new session/i })).toHaveAttribute(
        "href",
        "/pro/new"
      );
    });
  });

  it("sorts sessions when the sort dropdown changes", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([
      { name: "zeta", current_round: 1, n_known: 5, n_pool: 5, n_pending: 0, latest_accuracy: null },
      { name: "alpha", current_round: 1, n_known: 5, n_pool: 5, n_pending: 0, latest_accuracy: null },
    ]);
    render(
      <MemoryRouter>
        <ProSessionListPage />
      </MemoryRouter>
    );

    const links = await screen.findAllByRole("link", { name: /zeta|alpha/ });
    expect(links[0]).toHaveTextContent("alpha");
  });
});
```

- [ ] **Step 6: Write `ProNewSessionPage.tsx`**

Same behavior as the classic `NewSessionPage.tsx` — navigates to `/pro` (not
`/`) on success:

```tsx
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createSession } from "../../api/client";
import styles from "./ProNewSessionPage.module.css";

export default function ProNewSessionPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [labelCol, setLabelCol] = useState("");
  const [labeledFile, setLabeledFile] = useState<File | null>(null);
  const [poolFile, setPoolFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitError(null);

    if (!name.trim()) {
      setValidationError("Session name is required.");
      return;
    }
    if (!labelCol.trim()) {
      setValidationError("Label column is required.");
      return;
    }
    if (!labeledFile) {
      setValidationError("A labeled data file is required.");
      return;
    }
    setValidationError(null);

    setSubmitting(true);
    try {
      await createSession({
        name: name.trim(),
        labelCol: labelCol.trim(),
        labeledFile,
        poolFile: poolFile ?? undefined,
      });
      navigate("/pro");
    } catch (err) {
      setSubmitError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <h1>New session</h1>
      <form onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label htmlFor="name">Session name</label>
          <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
        </div>

        <div className={styles.field}>
          <label htmlFor="labelCol">Label column</label>
          <input id="labelCol" type="text" value={labelCol} onChange={(e) => setLabelCol(e.target.value)} />
        </div>

        <div className={styles.field}>
          <label htmlFor="labeledFile">Labeled data file</label>
          <input id="labeledFile" type="file" onChange={(e) => setLabeledFile(e.target.files?.[0] ?? null)} />
        </div>

        <div className={styles.field}>
          <label htmlFor="poolFile">Unlabeled pool file (optional)</label>
          <input id="poolFile" type="file" onChange={(e) => setPoolFile(e.target.files?.[0] ?? null)} />
        </div>

        {validationError && <p className={styles.validationError}>{validationError}</p>}

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "Creating…" : "Create session"}
        </button>

        {submitError && <p className={styles.submitError}>{submitError}</p>}
      </form>
    </div>
  );
}
```

- [ ] **Step 7: Write `ProNewSessionPage.module.css`**

```css
.container {
  max-width: 520px;
  margin: 0 auto;
  padding: 2.5rem clamp(2rem, 4vw, 4rem);
}

.container h1 {
  font-size: 1.4rem;
  margin-bottom: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.field label {
  font-size: 0.8rem;
  color: var(--pro-ink-soft);
  font-weight: 600;
}

.field input {
  font-family: var(--pro-font-body);
  font-size: 0.88rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  background: var(--pro-surface);
  color: var(--pro-ink);
  box-sizing: border-box;
  width: 100%;
}

.field input:focus {
  outline: none;
  border-color: var(--pro-accent);
}

.validationError,
.submitError {
  font-size: 0.8rem;
  color: var(--pro-neg-ink);
  background: var(--pro-neg-bg);
  border-radius: var(--pro-radius-sm);
  padding: 0.5rem 0.7rem;
  margin-bottom: 0.75rem;
}

.submit {
  display: inline-flex;
  align-items: center;
  padding: 0.6rem 1.3rem;
  border: none;
  border-radius: var(--pro-radius-sm);
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: var(--pro-shadow-btn);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.submit:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.35);
  transform: translateY(-1px);
}

.submit:disabled {
  opacity: 0.6;
  cursor: default;
}
```

- [ ] **Step 8: Write `ProNewSessionPage.test.tsx`**

Adapted from `NewSessionPage.test.tsx` (unchanged — the original test never
asserts the post-submit navigation target, only `createSession`'s call args and
the rendered messages, so nothing route-specific needs to change):

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProNewSessionPage from "./ProNewSessionPage";

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/session name/i), {
    target: { value: "azm-project" },
  });
  fireEvent.change(screen.getByLabelText(/label column/i), {
    target: { value: "outcome" },
  });
  const file = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
  fireEvent.change(screen.getByLabelText(/labeled data file/i), {
    target: { files: [file] },
  });
}

describe("ProNewSessionPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits the form and calls createSession with the entered values", async () => {
    const createSpy = vi.spyOn(client, "createSession").mockResolvedValue({
      name: "azm-project",
      n_known: 20,
      n_pool: 0,
      label_col: "outcome",
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
    });

    render(
      <MemoryRouter>
        <ProNewSessionPage />
      </MemoryRouter>
    );

    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /create session/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledTimes(1);
    });
    const [input] = createSpy.mock.calls[0];
    expect(input.name).toBe("azm-project");
    expect(input.labelCol).toBe("outcome");
    expect(input.labeledFile.name).toBe("labeled.csv");
  });

  it("shows a validation message and does not submit when the name is blank", async () => {
    const createSpy = vi.spyOn(client, "createSession");

    render(
      <MemoryRouter>
        <ProNewSessionPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/label column/i), {
      target: { value: "outcome" },
    });
    const file = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText(/labeled data file/i), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: /create session/i }));

    expect(await screen.findByText(/session name is required/i)).toBeInTheDocument();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("shows the backend's error message on failure (e.g. duplicate name)", async () => {
    vi.spyOn(client, "createSession").mockRejectedValue(
      new Error("Session already exists at /path/to/azm-project.db.")
    );

    render(
      <MemoryRouter>
        <ProNewSessionPage />
      </MemoryRouter>
    );

    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /create session/i }));

    expect(
      await screen.findByText(/session already exists/i)
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 9: Run the new tests and the full suite**

Run: `cd frontend && npx vitest run src/App.test.tsx src/pro/pages/ProSessionListPage.test.tsx src/pro/pages/ProNewSessionPage.test.tsx`
Expected: `2 + 5 + 3 = 10 passed`.

Run: `npm test -- --run`
Expected: `126 passed (126)` (117 + 1 new App test + 5 + 3 new page tests).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 10: Manually verify in the browser**

`npm run dev` + `make api`. Visit `http://localhost:5173/` — confirm the classic
app still looks and behaves exactly as before (dark, electric blue). Visit
`http://localhost:5173/pro` — confirm a light, navy-accented session list
renders instead, with a working "New session" link to `/pro/new` and a working
Cmd+K palette. Stop both servers when done.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/pro/pages/ProSessionListPage.tsx \
  frontend/src/pro/pages/ProSessionListPage.module.css frontend/src/pro/pages/ProSessionListPage.test.tsx \
  frontend/src/pro/pages/ProNewSessionPage.tsx frontend/src/pro/pages/ProNewSessionPage.module.css \
  frontend/src/pro/pages/ProNewSessionPage.test.tsx
git commit -m "Split App.tsx into ClassicApp/ProApp; add ProSessionListPage and ProNewSessionPage"
```

---

### Task 5: `ProSessionLayout` + `ProDashboardPage`

**Files:**
- Create: `frontend/src/pro/components/ProSessionLayout.tsx`
- Create: `frontend/src/pro/components/ProSessionLayout.module.css`
- Create: `frontend/src/pro/components/ProSessionLayout.test.tsx`
- Create: `frontend/src/pro/pages/ProDashboardPage.tsx`
- Create: `frontend/src/pro/pages/ProDashboardPage.module.css`
- Create: `frontend/src/pro/pages/ProDashboardPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getStatus`/`getHistory`/`StatusResponse`/`HistoryRow` from
  `../../api/client` (unchanged), `useCountUp` from `../../hooks/useCountUp`
  (unchanged), `ProAccuracyChart` from Task 3.
- Produces: `ProSessionLayout` — the session-scoped nav shell every later page
  task (6–13) nests under. Bundled with `ProDashboardPage` in this task because
  it's the layout's `index` route — there is no page-less way to wire the parent
  route in `ProApp` otherwise.

Per the spec, `ProSessionLayout`'s sidebar is a normal in-flow card (not the
classic app's fixed-to-viewport, full-height sidebar) — `position: sticky` inside
the page's own scroll, `--pro-surface` background, `box-shadow` instead of a
full border, and the active link is a filled gradient pill rather than a
left-edge accent bar.

- [ ] **Step 1: Write `ProSessionLayout.tsx`**

```tsx
import { useEffect, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { getStatus, type StatusResponse } from "../../api/client";
import styles from "./ProSessionLayout.module.css";

export default function ProSessionLayout() {
  const { name } = useParams<{ name: string }>();
  const [status, setStatus] = useState<StatusResponse | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getStatus(name)
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        // Nav still works without status — only the conditional Budget
        // link depends on it, and it simply won't appear on error.
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  return (
    <div className={styles.container}>
      <aside className={styles.sidebar}>
        <div className={styles.sessionName}>SESSION: {name}</div>
        <nav className={styles.nav}>
          <NavLink
            to={`/pro/sessions/${name}`}
            end
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Dashboard
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/recommend`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Recommendations
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/history`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            History
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/overview`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Overview
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/explain`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Explain
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/compare`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Compare
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/validate`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Validate
          </NavLink>
          <NavLink
            to={`/pro/sessions/${name}/settings`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Settings
          </NavLink>
          {status?.cost_per_sample !== null && status?.cost_per_sample !== undefined && (
            <NavLink
              to={`/pro/sessions/${name}/budget`}
              className={({ isActive }) => (isActive ? styles.active : undefined)}
            >
              Budget
            </NavLink>
          )}
        </nav>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Write `ProSessionLayout.module.css`**

```css
.container {
  display: flex;
  align-items: flex-start;
  gap: 2rem;
  max-width: 1320px;
  margin: 0 auto;
  padding: 2rem clamp(2rem, 4vw, 4rem);
}

.sidebar {
  flex: 0 0 224px;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-lg);
  box-shadow: var(--pro-shadow-sm);
  padding: 1.4rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
  position: sticky;
  top: 2rem;
}

.sessionName {
  font-family: var(--pro-font-mono);
  font-size: 0.7rem;
  color: var(--pro-ink-faint);
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--pro-line);
  word-break: break-word;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.nav a {
  display: block;
  padding: 0.5rem 0.7rem;
  border-radius: 7px;
  font-family: var(--pro-font-body);
  font-size: 0.85rem;
  color: var(--pro-ink-soft);
  text-decoration: none;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    transform 0.15s ease;
}

.nav a:hover:not(.active) {
  background: var(--pro-line-soft);
  color: var(--pro-accent);
  transform: translateX(2px);
}

.nav a.active {
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
  font-weight: 600;
  box-shadow: var(--pro-shadow-btn);
}

.main {
  flex: 1;
  min-width: 0;
}
```

- [ ] **Step 3: Write `ProSessionLayout.test.tsx`**

Adapted from `SessionLayout.test.tsx` — routes prefixed with `/pro`, session
name label reads `SESSION: name` (no `//`, matching the approved mockup) instead
of the classic app's `SESSION://name`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProSessionLayout from "./ProSessionLayout";
import styles from "./ProSessionLayout.module.css";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/pro/sessions/:name" element={<ProSessionLayout />}>
          <Route index element={<div>dashboard content</div>} />
          <Route path="recommend" element={<div>recommend content</div>} />
          <Route path="history" element={<div>history content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProSessionLayout", () => {
  it("shows the session name as a mono SESSION label", () => {
    renderAt("/pro/sessions/azm-project");
    expect(screen.getByText("SESSION: azm-project")).toBeInTheDocument();
  });

  it("marks only the Dashboard link active on the index route", () => {
    renderAt("/pro/sessions/azm-project");
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "Recommendations" })).not.toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "History" })).not.toHaveClass(styles.active);
  });

  it("marks only the Recommendations link active on the recommend route", () => {
    renderAt("/pro/sessions/azm-project/recommend");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveClass(styles.active);
    expect(screen.getByRole("link", { name: "Recommendations" })).toHaveClass(styles.active);
  });
});

describe("ProSessionLayout settings/budget nav", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("always shows a Settings link", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });

    renderAt("/pro/sessions/azm-project");

    expect(await screen.findByRole("link", { name: "Settings" })).toBeInTheDocument();
  });

  it("does not show a Budget link when cost_per_sample is null", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });

    renderAt("/pro/sessions/azm-project");

    await screen.findByRole("link", { name: "Settings" });
    expect(screen.queryByRole("link", { name: "Budget" })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Write `ProDashboardPage.tsx`**

Deliberate difference from the classic `DashboardPage.tsx`: this adds a
`<h2>Dashboard</h2>` title. The classic Dashboard is the one classic page with
no heading at all (every other classic page has one); the approved mockup
showed a "Dashboard" title, and every other Pro page in this plan has a title
too, so Pro is consistently titled rather than inheriting that one classic
inconsistency.

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getHistory,
  getStatus,
  type HistoryRow,
  type StatusResponse,
} from "../../api/client";
import ProAccuracyChart from "../components/ProAccuracyChart";
import { useCountUp } from "../../hooks/useCountUp";
import styles from "./ProDashboardPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessionStatus: StatusResponse; history: HistoryRow[] };

export default function ProDashboardPage() {
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
      <h2 className={styles.title}>Dashboard</h2>
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
        <ProAccuracyChart history={history} />
      ) : (
        <p className={styles.empty}>No rounds completed yet.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Write `ProDashboardPage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--pro-ink);
}

.stopBanner {
  background: var(--pro-warn-bg);
  border: 1px solid var(--pro-warn-border);
  border-left: 3px solid #d97706;
  border-radius: var(--pro-radius-sm);
  padding: 0.6rem 0.8rem;
  font-size: 0.8rem;
  color: var(--pro-warn-ink);
  margin-bottom: 1rem;
}

.statRow {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1rem;
}

.stat {
  flex: 1;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 0.85rem 1rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--pro-shadow-md);
}

.statValue {
  font-family: var(--pro-font-mono);
  font-size: 1.4rem;
  font-weight: 600;
  background: linear-gradient(135deg, var(--pro-ink), var(--pro-accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.statLabel {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--pro-ink-faint);
  margin-top: 0.25rem;
}

.loading,
.error,
.empty {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}
```

- [ ] **Step 6: Write `ProDashboardPage.test.tsx`**

Adapted from `DashboardPage.test.tsx` — routes prefixed with `/pro`, same
assertions otherwise:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProDashboardPage from "./ProDashboardPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}`]}>
      <Routes>
        <Route path="/pro/sessions/:name" element={<ProDashboardPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProDashboardPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows status stats and the chart once loaded", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project",
      current_round: 2,
      n_known: 45,
      n_pool: 55,
      n_pending: 0,
      latest_accuracy: 0.93,
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      total_cost: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
      should_stop: false,
      stop_reason: "",
      created_at: "2026-07-19T00:00:00Z",
    });
    vi.spyOn(client, "getHistory").mockResolvedValue([
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.85,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ]);

    renderAtSession("azm-project");

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(
      () => {
        expect(screen.getByText("93.0%")).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
  });

  it("shows a stopping-recommended banner when should_stop is true", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project",
      current_round: 5,
      n_known: 60,
      n_pool: 10,
      n_pending: 0,
      latest_accuracy: 0.95,
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      total_cost: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
      should_stop: true,
      stop_reason: "Accuracy has not improved by >=0.005 for 3 rounds.",
      created_at: "2026-07-19T00:00:00Z",
    });
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("azm-project");

    expect(
      await screen.findByText(/accuracy has not improved/i)
    ).toBeInTheDocument();
  });

  it("shows an empty-history message instead of the chart when no rounds exist", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "new-project",
      current_round: 0,
      n_known: 20,
      n_pool: 30,
      n_pending: 0,
      latest_accuracy: null,
      patience: 3,
      min_delta: 0.005,
      cost_per_sample: null,
      total_cost: null,
      diversity_weight: 0,
      model: "rf",
      calibrate: false,
      calibration_method: "sigmoid",
      should_stop: false,
      stop_reason: "",
      created_at: "2026-07-19T00:00:00Z",
    });
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("new-project");

    expect(await screen.findByText(/no rounds completed yet/i)).toBeInTheDocument();
  });

  it("shows an error message when either request fails", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("No session named 'x'."));
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Wire `ProSessionLayout`/`ProDashboardPage` into `App.tsx`**

Add two imports and one nested `<Route>` block to `ProApp`'s `<Routes>` (leave
`ClassicApp` untouched):

```tsx
import ProSessionLayout from "./pro/components/ProSessionLayout";
import ProDashboardPage from "./pro/pages/ProDashboardPage";
```

```tsx
function ProApp() {
  return (
    <ProAppShell>
      <Routes>
        <Route path="/" element={<ProSessionListPage />} />
        <Route path="/new" element={<ProNewSessionPage />} />
        <Route path="/sessions/:name" element={<ProSessionLayout />}>
          <Route index element={<ProDashboardPage />} />
        </Route>
      </Routes>
    </ProAppShell>
  );
}
```

- [ ] **Step 8: Run the new tests and the full suite**

Run: `cd frontend && npx vitest run src/pro/components/ProSessionLayout.test.tsx src/pro/pages/ProDashboardPage.test.tsx`
Expected: `5 + 4 = 9 passed`.

Run: `npm test -- --run`
Expected: `135 passed (135)` (126 + 9 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 9: Manually verify in the browser**

`npm run dev` + `make api`. Visit `/pro/sessions/<a-real-session-name>` — confirm
the light sidebar renders all 8 (or 9, if cost-tracked) nav links, the active
link shows the gradient pill, hovering an inactive link nudges it right, and the
Dashboard stats/chart render correctly. Stop both servers when done.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pro/components/ProSessionLayout.tsx frontend/src/pro/components/ProSessionLayout.module.css \
  frontend/src/pro/components/ProSessionLayout.test.tsx frontend/src/pro/pages/ProDashboardPage.tsx \
  frontend/src/pro/pages/ProDashboardPage.module.css frontend/src/pro/pages/ProDashboardPage.test.tsx \
  frontend/src/App.tsx
git commit -m "Add ProSessionLayout and ProDashboardPage"
```

---

### Task 6: `ProRecommendationsPage`

**Files:**
- Create: `frontend/src/pro/pages/ProRecommendationsPage.tsx`
- Create: `frontend/src/pro/pages/ProRecommendationsPage.module.css`
- Create: `frontend/src/pro/pages/ProRecommendationsPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getRecommendations`/`submitResults`/`RecommendRow` from
  `../../api/client` (unchanged).

Carries over the classic page's StrictMode double-invoke fix verbatim (the
`fetchedForName`/`isMounted` ref pair) — this is a correctness fix for a real
bug (see CLAUDE.md), not classic-app-specific styling, so it must not be dropped.

- [ ] **Step 1: Write `ProRecommendationsPage.tsx`**

```tsx
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getRecommendations,
  submitResults,
  type RecommendRow,
} from "../../api/client";
import styles from "./ProRecommendationsPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; rows: RecommendRow[] };

export default function ProRecommendationsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const fetchedForName = useRef<string | null>(null);
  const isMounted = useRef(false);

  useEffect(() => {
    if (!name) return;
    isMounted.current = true;

    // Same StrictMode double-invoke fix as the classic RecommendationsPage:
    // getRecommendations has a server-side side effect (marks the batch
    // "pending"), so fetchedForName must survive the phantom cleanup below —
    // only isMounted resets there.
    if (fetchedForName.current !== name) {
      fetchedForName.current = name;
      getRecommendations(name)
        .then((response) => {
          if (isMounted.current) setState({ status: "loaded", rows: response.rows });
        })
        .catch((err: Error) => {
          if (isMounted.current) setState({ status: "error", message: err.message });
        });
    }

    return () => {
      isMounted.current = false;
    };
  }, [name]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (state.status !== "loaded" || !name) return;

    const results = state.rows
      .filter((row) => labels[row.sample_id] !== undefined && labels[row.sample_id] !== "")
      .map((row) => ({
        sample_id: row.sample_id,
        label: Number(labels[row.sample_id]),
      }));

    if (results.length === 0) {
      setSubmitError("Enter at least one result before submitting.");
      return;
    }

    setSubmitError(null);
    setSubmitting(true);
    try {
      await submitResults(name, results);
      navigate(`/pro/sessions/${name}`);
    } catch (err) {
      setSubmitError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <h2 className={styles.title}>Recommended experiments</h2>
      <form onSubmit={handleSubmit}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Sample ID</th>
              <th>Uncertainty</th>
              <th>P(positive)</th>
              <th>Predicted</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {state.rows.map((row) => (
              <tr key={row.sample_id}>
                <td>{row.rank}</td>
                <td>{row.sample_id}</td>
                <td>{row.uncertainty_score.toFixed(3)}</td>
                <td>{row.p_positive.toFixed(3)}</td>
                <td>{row.predicted_class}</td>
                <td>
                  <label htmlFor={`label-${row.sample_id}`} className={styles.srOnly}>
                    Result for {row.sample_id}
                  </label>
                  <select
                    id={`label-${row.sample_id}`}
                    value={labels[row.sample_id] ?? ""}
                    onChange={(e) =>
                      setLabels((prev) => ({ ...prev, [row.sample_id]: e.target.value }))
                    }
                  >
                    <option value="">—</option>
                    <option value="0">0</option>
                    <option value="1">1</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit results"}
        </button>

        {submitError && <p className={styles.submitError}>{submitError}</p>}
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Write `ProRecommendationsPage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--pro-ink);
}

.loading,
.error {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  overflow: hidden;
  box-shadow: var(--pro-shadow-sm);
  font-size: 0.82rem;
  margin-bottom: 1rem;
}

.table th {
  text-align: left;
  padding: 0.6rem 0.8rem;
  color: var(--pro-ink-faint);
  font-weight: 600;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--pro-line);
}

.table td {
  padding: 0.55rem 0.8rem;
  border-bottom: 1px solid var(--pro-line-soft);
  font-family: var(--pro-font-mono);
  color: var(--pro-ink);
}

.table tbody tr:hover td {
  background: var(--pro-line-soft);
}

.table select {
  font-family: var(--pro-font-body);
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  background: var(--pro-surface);
  color: var(--pro-ink);
}

.srOnly {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.submit {
  display: inline-flex;
  align-items: center;
  padding: 0.6rem 1.3rem;
  border: none;
  border-radius: var(--pro-radius-sm);
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: var(--pro-shadow-btn);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.submit:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.35);
  transform: translateY(-1px);
}

.submit:disabled {
  opacity: 0.6;
  cursor: default;
}

.submitError {
  font-size: 0.8rem;
  color: var(--pro-neg-ink);
  background: var(--pro-neg-bg);
  border-radius: var(--pro-radius-sm);
  padding: 0.5rem 0.7rem;
  margin-top: 0.75rem;
}
```

- [ ] **Step 3: Write `ProRecommendationsPage.test.tsx`**

Adapted from `RecommendationsPage.test.tsx` — routes prefixed with `/pro`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProRecommendationsPage from "./ProRecommendationsPage";

function renderAtSession(name: string, { strict = false } = {}) {
  const tree = (
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/recommend`]}>
      <Routes>
        <Route path="/pro/sessions/:name/recommend" element={<ProRecommendationsPage />} />
        <Route path="/pro/sessions/:name" element={<div>Dashboard placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
  return render(strict ? <StrictMode>{tree}</StrictMode> : tree);
}

const sampleRows = [
  {
    rank: 1,
    sample_id: "pool_3",
    uncertainty_score: 0.98,
    p_positive: 0.51,
    predicted_class: "positive",
  },
  {
    rank: 2,
    sample_id: "pool_7",
    uncertainty_score: 0.95,
    p_positive: 0.49,
    predicted_class: "negative",
  },
];

describe("ProRecommendationsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the recommended batch once loaded", async () => {
    vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });

    renderAtSession("azm-project");

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });
    expect(screen.getByText("pool_7")).toBeInTheDocument();
  });

  it("submits only the rows with a selected result, then navigates to the dashboard", async () => {
    vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });
    const submitSpy = vi.spyOn(client, "submitResults").mockResolvedValue({
      round: 1,
      n_returned: 1,
      n_known: 21,
      n_pool: 1,
      accuracy: 0.9,
      round_cost: null,
      cumulative_cost: null,
      should_stop: false,
      stop_reason: "",
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/result for pool_3/i), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit results/i }));

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith("azm-project", [
        { sample_id: "pool_3", label: 1 },
      ]);
    });
    await waitFor(() => {
      expect(screen.getByText("Dashboard placeholder")).toBeInTheDocument();
    });
  });

  it("shows a validation message and does not submit when nothing is selected", async () => {
    vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });
    const submitSpy = vi.spyOn(client, "submitResults");

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /submit results/i }));

    expect(
      await screen.findByText(/enter at least one result/i)
    ).toBeInTheDocument();
    expect(submitSpy).not.toHaveBeenCalled();
  });

  it("fetches recommendations exactly once under StrictMode's double-invoked effects", async () => {
    const getSpy = vi.spyOn(client, "getRecommendations").mockResolvedValue({
      rows: sampleRows,
      should_stop: false,
      stop_reason: "",
    });

    renderAtSession("azm-project", { strict: true });

    await waitFor(() => {
      expect(screen.getByText("pool_3")).toBeInTheDocument();
    });

    expect(getSpy).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

Add the import and one nested `<Route>` under the `/sessions/:name` block in
`ProApp` (immediately after the `index` route added in Task 5):

```tsx
import ProRecommendationsPage from "./pro/pages/ProRecommendationsPage";
```

```tsx
          <Route path="recommend" element={<ProRecommendationsPage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProRecommendationsPage.test.tsx`
Expected: `4 passed`.

Run: `npm test -- --run`
Expected: `139 passed (139)` (135 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProRecommendationsPage.tsx frontend/src/pro/pages/ProRecommendationsPage.module.css \
  frontend/src/pro/pages/ProRecommendationsPage.test.tsx frontend/src/App.tsx
git commit -m "Add ProRecommendationsPage"
```

---

### Task 7: `ProHistoryPage`

**Files:**
- Create: `frontend/src/pro/pages/ProHistoryPage.tsx`
- Create: `frontend/src/pro/pages/ProHistoryPage.module.css`
- Create: `frontend/src/pro/pages/ProHistoryPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `exportHistory`/`getHistory`/`HistoryRow` from `../../api/client`
  (unchanged), `ProAccuracyChart` from Task 3.

- [ ] **Step 1: Write `ProHistoryPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { exportHistory, getHistory, type HistoryRow } from "../../api/client";
import ProAccuracyChart from "../components/ProAccuracyChart";
import styles from "./ProHistoryPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; history: HistoryRow[] };

export default function ProHistoryPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getHistory(name)
      .then((history) => {
        if (!cancelled) setState({ status: "loaded", history });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  async function handleExport() {
    if (!name) return;
    setExportError(null);
    try {
      const blob = await exportHistory(name);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name}_history.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError((err as Error).message);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <div className={styles.headerRow}>
        <h2 className={styles.title}>Round history</h2>
        <button onClick={handleExport} className={styles.exportButton}>
          Export CSV
        </button>
      </div>

      {exportError && <p className={styles.error}>{exportError}</p>}

      {state.history.length === 0 ? (
        <p className={styles.empty}>No rounds completed yet.</p>
      ) : (
        <>
          <ProAccuracyChart history={state.history} />
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Round</th>
                <th>Known</th>
                <th>Accuracy</th>
                <th>Round cost</th>
                <th>Cumulative cost</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {state.history.map((row) => (
                <tr key={row.round_number}>
                  <td>{row.round_number}</td>
                  <td>{row.n_known}</td>
                  <td>{row.accuracy !== null ? `${(row.accuracy * 100).toFixed(1)}%` : "—"}</td>
                  <td>{row.round_cost !== null ? row.round_cost.toFixed(2) : "—"}</td>
                  <td>{row.cumulative_cost !== null ? row.cumulative_cost.toFixed(2) : "—"}</td>
                  <td>{row.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ProHistoryPage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
  color: var(--pro-ink);
}

.headerRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.exportButton {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.9rem;
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  background: var(--pro-surface);
  color: var(--pro-accent);
  font-weight: 600;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.exportButton:hover {
  border-color: var(--pro-accent);
}

.loading,
.error,
.empty {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  overflow: hidden;
  box-shadow: var(--pro-shadow-sm);
  font-size: 0.8rem;
  margin-top: 1rem;
}

.table th {
  text-align: left;
  padding: 0.6rem 0.8rem;
  color: var(--pro-ink-faint);
  font-weight: 600;
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--pro-line);
}

.table td {
  padding: 0.55rem 0.8rem;
  border-bottom: 1px solid var(--pro-line-soft);
  font-family: var(--pro-font-mono);
  color: var(--pro-ink);
}

.table tbody tr:hover td {
  background: var(--pro-line-soft);
}
```

- [ ] **Step 3: Write `ProHistoryPage.test.tsx`**

Adapted from `HistoryPage.test.tsx` — routes prefixed with `/pro`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProHistoryPage from "./ProHistoryPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/history`]}>
      <Routes>
        <Route path="/pro/sessions/:name/history" element={<ProHistoryPage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleHistory = [
  {
    round_number: 1,
    n_known: 25,
    accuracy: 0.85,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-19T00:00:00Z",
  },
  {
    round_number: 2,
    n_known: 30,
    accuracy: 0.9,
    round_cost: null,
    cumulative_cost: null,
    created_at: "2026-07-20T00:00:00Z",
  },
];

describe("ProHistoryPage", () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the round table once loaded", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue(sampleHistory);

    renderAtSession("azm-project");

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("90.0%")).toBeInTheDocument();
  });

  it("shows an empty-state message instead of the table when there's no history", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("new-project");

    expect(await screen.findByText(/no rounds completed yet/i)).toBeInTheDocument();
  });

  it("triggers a CSV download when Export is clicked", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue(sampleHistory);
    const mockBlob = new Blob(["round_number,accuracy\n1,0.85\n"], { type: "text/csv" });
    vi.spyOn(client, "exportHistory").mockResolvedValue(mockBlob);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    await waitFor(() => {
      expect(client.exportHistory).toHaveBeenCalledWith("azm-project");
    });
    expect(URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
  });

  it("shows an error message when the export fails", async () => {
    vi.spyOn(client, "getHistory").mockResolvedValue(sampleHistory);
    vi.spyOn(client, "exportHistory").mockRejectedValue(new Error("export failed"));

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(await screen.findByText(/export failed/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

```tsx
import ProHistoryPage from "./pro/pages/ProHistoryPage";
```

```tsx
          <Route path="history" element={<ProHistoryPage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProHistoryPage.test.tsx`
Expected: `4 passed`.

Run: `npm test -- --run`
Expected: `143 passed (143)` (139 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProHistoryPage.tsx frontend/src/pro/pages/ProHistoryPage.module.css \
  frontend/src/pro/pages/ProHistoryPage.test.tsx frontend/src/App.tsx
git commit -m "Add ProHistoryPage"
```

---

### Task 8: `ProOverviewPage`

**Files:**
- Create: `frontend/src/pro/pages/ProOverviewPage.tsx`
- Create: `frontend/src/pro/pages/ProOverviewPage.module.css`
- Create: `frontend/src/pro/pages/ProOverviewPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getOverview`/`OverviewResponse` from `../../api/client` (unchanged).

- [ ] **Step 1: Write `ProOverviewPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getOverview, type OverviewResponse } from "../../api/client";
import styles from "./ProOverviewPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: OverviewResponse };

export default function ProOverviewPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getOverview(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;
  const maxPrevalence = Math.max(...data.top_prevalent_features.map((f) => f.prevalence), 0.0001);

  return (
    <div>
      <h2 className={styles.title}>Session overview</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_known}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_pool}</div>
          <div className={styles.statLabel}>Pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_features}</div>
          <div className={styles.statLabel}>Features</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.positive_rate !== null ? `${(data.positive_rate * 100).toFixed(1)}%` : "—"}
          </div>
          <div className={styles.statLabel}>
            Positive ({data.n_positive} / {data.n_positive + data.n_negative})
          </div>
        </div>
      </div>

      {data.top_prevalent_features.length > 0 && (
        <div className={styles.barCard}>
          <h4>Most prevalent features</h4>
          <ul className={styles.barList}>
            {data.top_prevalent_features.map((f) => (
              <li key={f.feature} className={styles.barRow}>
                <span className={styles.barLabel}>{f.feature}</span>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(f.prevalence / maxPrevalence) * 100}%` }}
                  />
                </div>
                <span className={styles.barValue}>{(f.prevalence * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ProOverviewPage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--pro-ink);
}

.loading,
.error {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.statRow {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1.25rem;
}

.stat {
  flex: 1;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 0.85rem 1rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--pro-shadow-md);
}

.statValue {
  font-family: var(--pro-font-mono);
  font-size: 1.3rem;
  font-weight: 600;
  background: linear-gradient(135deg, var(--pro-ink), var(--pro-accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.statLabel {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pro-ink-faint);
  margin-top: 0.25rem;
}

.barCard {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 1rem 1.1rem;
}

.barCard h4 {
  margin: 0 0 0.8rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.barList {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.barRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 3fr) 4ch;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.75rem;
}

.barLabel {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.barTrack {
  height: 6px;
  border-radius: 3px;
  background: var(--pro-line-soft);
  overflow: hidden;
}

.barFill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--pro-accent), var(--pro-accent-bright));
}

.barValue {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-faint);
  text-align: right;
}
```

- [ ] **Step 3: Write `ProOverviewPage.test.tsx`**

Adapted from `OverviewPage.test.tsx` — routes prefixed with `/pro`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProOverviewPage from "./ProOverviewPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/overview`]}>
      <Routes>
        <Route path="/pro/sessions/:name/overview" element={<ProOverviewPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProOverviewPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows class balance and feature counts once loaded", async () => {
    vi.spyOn(client, "getOverview").mockResolvedValue({
      n_known: 40, n_pool: 60, n_features: 30, n_positive: 11, n_negative: 29,
      positive_rate: 0.275, top_prevalent_features: [],
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("40")).toBeInTheDocument();
    });
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("27.5%")).toBeInTheDocument();
  });

  it("renders a bar per prevalent feature", async () => {
    vi.spyOn(client, "getOverview").mockResolvedValue({
      n_known: 40, n_pool: 60, n_features: 30, n_positive: 11, n_negative: 29,
      positive_rate: 0.275,
      top_prevalent_features: [
        { feature: "unitig_3", prevalence: 0.9 },
        { feature: "unitig_7", prevalence: 0.4 },
      ],
    });

    renderAtSession("azm-project");

    expect(await screen.findByText("unitig_3")).toBeInTheDocument();
    expect(screen.getByText("unitig_7")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getOverview").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

```tsx
import ProOverviewPage from "./pro/pages/ProOverviewPage";
```

```tsx
          <Route path="overview" element={<ProOverviewPage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProOverviewPage.test.tsx`
Expected: `3 passed`.

Run: `npm test -- --run`
Expected: `146 passed (146)` (143 + 3 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProOverviewPage.tsx frontend/src/pro/pages/ProOverviewPage.module.css \
  frontend/src/pro/pages/ProOverviewPage.test.tsx frontend/src/App.tsx
git commit -m "Add ProOverviewPage"
```

---

### Task 9: `ProExplainPage`

**Files:**
- Create: `frontend/src/pro/pages/ProExplainPage.tsx`
- Create: `frontend/src/pro/pages/ProExplainPage.module.css`
- Create: `frontend/src/pro/pages/ProExplainPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getFeatureImportance`/`FeatureImportanceResponse` from
  `../../api/client` (unchanged).

- [ ] **Step 1: Write `ProExplainPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getFeatureImportance, type FeatureImportanceResponse } from "../../api/client";
import styles from "./ProExplainPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: FeatureImportanceResponse };

export default function ProExplainPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getFeatureImportance(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;
  const maxImportance = Math.max(...data.features.map((f) => f.importance), 0.0001);

  return (
    <div>
      <h2 className={styles.title}>Feature importance</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.cv_accuracy_mean !== null
              ? `${(data.cv_accuracy_mean * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div className={styles.statLabel}>
            Cross-validated accuracy
            {data.cv_accuracy_std !== null && ` (± ${(data.cv_accuracy_std * 100).toFixed(1)}pp)`}
          </div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.total_features}</div>
          <div className={styles.statLabel}>Total features</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{data.n_known}</div>
          <div className={styles.statLabel}>Trained on</div>
        </div>
      </div>

      {data.features.length === 0 ? (
        <p className={styles.empty}>Not enough known samples yet to rank features.</p>
      ) : (
        <div className={styles.barCard}>
          <h4>Top predictive features</h4>
          <ul className={styles.barList}>
            {data.features.map((f) => (
              <li key={f.feature} className={styles.barRow}>
                <span className={styles.barRank}>#{f.rank}</span>
                <span className={styles.barLabel}>{f.feature}</span>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${(f.importance / maxImportance) * 100}%` }}
                  />
                </div>
                <span className={styles.barValue}>{f.importance.toFixed(4)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ProExplainPage.module.css`**

Same `.statRow`/`.stat`/`.statValue`/`.statLabel`/`.barCard`/`.barList`/
`.loading`/`.error`/`.empty` rules as `ProOverviewPage.module.css` (Task 8),
plus a `.barRank` rule and a 4-column `.barRow` grid (rank/label/track/value):

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--pro-ink);
}

.loading,
.error,
.empty {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.statRow {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1.25rem;
}

.stat {
  flex: 1;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 0.85rem 1rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--pro-shadow-md);
}

.statValue {
  font-family: var(--pro-font-mono);
  font-size: 1.3rem;
  font-weight: 600;
  background: linear-gradient(135deg, var(--pro-ink), var(--pro-accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.statLabel {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pro-ink-faint);
  margin-top: 0.25rem;
}

.barCard {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 1rem 1.1rem;
}

.barCard h4 {
  margin: 0 0 0.8rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.barList {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.barRow {
  display: grid;
  grid-template-columns: 2.5ch minmax(0, 1fr) minmax(0, 3fr) 6ch;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.75rem;
}

.barRank {
  font-family: var(--pro-font-mono);
  font-size: 0.68rem;
  color: var(--pro-ink-faint);
}

.barLabel {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.barTrack {
  height: 6px;
  border-radius: 3px;
  background: var(--pro-line-soft);
  overflow: hidden;
}

.barFill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--pro-accent), var(--pro-accent-bright));
}

.barValue {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-faint);
  text-align: right;
}
```

- [ ] **Step 3: Write `ProExplainPage.test.tsx`**

Adapted from `ExplainPage.test.tsx` — routes prefixed with `/pro`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProExplainPage from "./ProExplainPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/explain`]}>
      <Routes>
        <Route path="/pro/sessions/:name/explain" element={<ProExplainPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProExplainPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows cv accuracy and ranked features once loaded", async () => {
    vi.spyOn(client, "getFeatureImportance").mockResolvedValue({
      features: [
        { rank: 1, feature: "unitig_9", importance: 0.21, cumulative_importance: 0.21 },
      ],
      cv_accuracy_mean: 0.93, cv_accuracy_std: 0.02, total_features: 500, n_known: 40,
    });

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("93.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("unitig_9")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
  });

  it("shows an em dash for cv accuracy when it's null", async () => {
    vi.spyOn(client, "getFeatureImportance").mockResolvedValue({
      features: [{ rank: 1, feature: "unitig_1", importance: 0.5, cumulative_importance: 0.5 }],
      cv_accuracy_mean: null, cv_accuracy_std: null, total_features: 6, n_known: 5,
    });

    renderAtSession("azm-project");

    expect(await screen.findByText("—")).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getFeatureImportance").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

```tsx
import ProExplainPage from "./pro/pages/ProExplainPage";
```

```tsx
          <Route path="explain" element={<ProExplainPage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProExplainPage.test.tsx`
Expected: `3 passed`.

Run: `npm test -- --run`
Expected: `149 passed (149)` (146 + 3 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProExplainPage.tsx frontend/src/pro/pages/ProExplainPage.module.css \
  frontend/src/pro/pages/ProExplainPage.test.tsx frontend/src/App.tsx
git commit -m "Add ProExplainPage"
```

---

### Task 10: `ProComparePage`

**Files:**
- Create: `frontend/src/pro/pages/ProComparePage.tsx`
- Create: `frontend/src/pro/pages/ProComparePage.module.css`
- Create: `frontend/src/pro/pages/ProComparePage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getComparison`/`CompareResponse` from `../../api/client`
  (unchanged).

The classic `ComparePage.tsx` renders decorative `<span className="bracket ...">`
corner elements that come from a global, classic-only `.bracket` CSS class —
**do not carry these over**; Pro cards get their look entirely from
`var(--pro-shadow-sm)` on `.chartCard`, no classic global classes referenced
anywhere in `pro/`. This page keeps the classic page's defining behavior: it is
the one page that does **not** fetch on mount (button-triggered, since the
comparison trains several models and can take a few seconds).

- [ ] **Step 1: Write `ProComparePage.tsx`**

```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getComparison, type CompareResponse } from "../../api/client";
import styles from "./ProComparePage.module.css";

type RunState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: CompareResponse };

interface ComparePoint {
  size: number;
  al: number;
  random: number;
}

function toChartData(data: CompareResponse): ComparePoint[] {
  return data.known_pool_sizes.map((size, i) => ({
    size,
    al: data.al_accuracy[i] * 100,
    random: data.random_accuracy[i] * 100,
  }));
}

export default function ProComparePage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<RunState>({ status: "idle" });

  async function handleRun() {
    if (!name) return;
    setState({ status: "loading" });
    try {
      const data = await getComparison(name);
      setState({ status: "loaded", data });
    } catch (err) {
      setState({ status: "error", message: (err as Error).message });
    }
  }

  return (
    <div>
      <h2 className={styles.title}>Active learning vs. random sampling</h2>
      <p className={styles.intro}>
        Simulates both strategies on this session's own known data to show how much
        faster active learning reaches a given accuracy compared to random sampling.
        This trains several models and can take a few seconds.
      </p>

      <button type="button" onClick={handleRun} disabled={state.status === "loading"} className={styles.runButton}>
        {state.status === "loading" ? "Running…" : "Run comparison"}
      </button>

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && (
        <>
          <div className={styles.chartCard}>
            <div className={styles.chartHead}>
              <h4>Accuracy vs. known pool size</h4>
              <div className={styles.chartLegend}>
                <span className={styles.legendActual}>● active learning</span>
                <span className={styles.legendProjected}>┄ random</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={toChartData(state.data)} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--pro-line-soft)" />
                <XAxis
                  dataKey="size"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  stroke="var(--pro-ink-faint)"
                  tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
                  label={{
                    value: "Known pool size",
                    position: "insideBottom",
                    offset: -6,
                    fill: "var(--pro-ink-faint)",
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="var(--pro-ink-faint)"
                  tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
                  tickFormatter={(v: number) => `${Math.round(v)}%`}
                  label={{
                    value: "Accuracy",
                    angle: -90,
                    position: "insideLeft",
                    fill: "var(--pro-ink-faint)",
                  }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--pro-surface)",
                    border: "1px solid var(--pro-line)",
                    borderRadius: 6,
                    boxShadow: "var(--pro-shadow-md)",
                  }}
                  labelStyle={{ color: "var(--pro-ink)" }}
                  labelFormatter={(v: number) => `${v} known`}
                  formatter={(value: number, dataKey: string) => [
                    `${value.toFixed(1)}%`,
                    dataKey === "al" ? "Active learning" : "Random",
                  ]}
                />
                <Line type="monotone" dataKey="al" stroke="var(--pro-accent)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--pro-accent)" }} name="al" />
                <Line type="monotone" dataKey="random" stroke="var(--pro-ink-soft)" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3, fill: "var(--pro-ink-soft)" }} name="random" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className={styles.summary}>
            Active learning reached{" "}
            <strong className={styles.summaryValue}>
              {Math.abs(state.data.final_gap * 100).toFixed(1)} percentage points
            </strong>{" "}
            {state.data.final_gap >= 0 ? "higher" : "lower"} accuracy than random sampling at
            the same number of experiments, averaged over {state.data.runs} run
            {state.data.runs === 1 ? "" : "s"}.
          </p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ProComparePage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  color: var(--pro-ink);
}

.intro {
  font-size: 0.85rem;
  color: var(--pro-ink-soft);
  max-width: 640px;
  margin: 0 0 1rem 0;
}

.error {
  font-family: var(--pro-font-mono);
  color: var(--pro-neg-ink);
}

.runButton {
  display: inline-flex;
  align-items: center;
  padding: 0.6rem 1.3rem;
  border: none;
  border-radius: var(--pro-radius-sm);
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: var(--pro-shadow-btn);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
  margin-bottom: 1rem;
}

.runButton:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.35);
  transform: translateY(-1px);
}

.runButton:disabled {
  opacity: 0.6;
  cursor: default;
}

.chartCard {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}

.chartHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.4rem;
}

.chartHead h4 {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.chartLegend {
  display: flex;
  gap: 0.8rem;
  font-family: var(--pro-font-mono);
  font-size: 0.68rem;
}

.legendActual {
  color: var(--pro-accent);
}

.legendProjected {
  color: var(--pro-ink-soft);
}

.summary {
  font-size: 0.85rem;
  color: var(--pro-ink-soft);
}

.summaryValue {
  color: var(--pro-ink);
}
```

- [ ] **Step 3: Write `ProComparePage.test.tsx`**

Adapted from `ComparePage.test.tsx` — routes prefixed with `/pro`. Keeps the
"does not fetch on mount" assertion, since that's the behavior this page must
preserve:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProComparePage from "./ProComparePage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/compare`]}>
      <Routes>
        <Route path="/pro/sessions/:name/compare" element={<ProComparePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProComparePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch on mount", () => {
    const spy = vi.spyOn(client, "getComparison");

    renderAtSession("azm-project");

    expect(spy).not.toHaveBeenCalled();
  });

  it("fetches exactly once when the run button is clicked", async () => {
    const spy = vi.spyOn(client, "getComparison").mockResolvedValue({
      known_pool_sizes: [5, 7, 9],
      al_accuracy: [0.6, 0.75, 0.85],
      random_accuracy: [0.55, 0.6, 0.65],
      runs: 3,
      final_gap: 0.2,
    });

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledTimes(1);
    });
    expect(spy).toHaveBeenCalledWith("azm-project");
  });

  it("shows the final gap in plain language once loaded", async () => {
    vi.spyOn(client, "getComparison").mockResolvedValue({
      known_pool_sizes: [5, 7, 9],
      al_accuracy: [0.6, 0.75, 0.85],
      random_accuracy: [0.55, 0.6, 0.65],
      runs: 3,
      final_gap: 0.2,
    });

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    expect(await screen.findByText(/20\.0 percentage points/i)).toBeInTheDocument();
    expect(screen.getByText(/higher/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getComparison").mockRejectedValue(
      new Error("Need at least 20 known samples to compare strategies (have 10).")
    );

    renderAtSession("azm-project");
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    expect(await screen.findByText(/at least 20 known samples/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

```tsx
import ProComparePage from "./pro/pages/ProComparePage";
```

```tsx
          <Route path="compare" element={<ProComparePage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProComparePage.test.tsx`
Expected: `4 passed`.

Run: `npm test -- --run`
Expected: `153 passed (153)` (149 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProComparePage.tsx frontend/src/pro/pages/ProComparePage.module.css \
  frontend/src/pro/pages/ProComparePage.test.tsx frontend/src/App.tsx
git commit -m "Add ProComparePage"
```

---

### Task 11: `ProValidatePage`

**Files:**
- Create: `frontend/src/pro/pages/ProValidatePage.tsx`
- Create: `frontend/src/pro/pages/ProValidatePage.module.css`
- Create: `frontend/src/pro/pages/ProValidatePage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getValidation`/`ValidateResponse` from `../../api/client`
  (unchanged).

Confusion-matrix labels are copied character-for-character from the classic
page ("Correctly cleared sensitive strains", "False alarms (false positives)",
"Missed resistant strains (false negatives)", "Correctly caught resistant
strains") — these match `validate.py`'s own CLI wording and must not drift.

- [ ] **Step 1: Write `ProValidatePage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getValidation, type ValidateResponse } from "../../api/client";
import styles from "./ProValidatePage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: ValidateResponse };

export default function ProValidatePage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getValidation(name)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const { data } = state;

  return (
    <div>
      <h2 className={styles.title}>Holdout validation</h2>
      <p className={styles.intro}>
        Trained on {data.n_train} known samples, evaluated on {data.n_holdout} held-out
        samples the model never saw during training.
      </p>

      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.balanced_accuracy * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Balanced accuracy</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.precision * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Precision</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.recall * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>Recall</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{(data.f1 * 100).toFixed(1)}%</div>
          <div className={styles.statLabel}>F1</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {data.roc_auc !== null ? data.roc_auc.toFixed(3) : "—"}
          </div>
          <div className={styles.statLabel}>ROC-AUC</div>
        </div>
      </div>

      <div className={styles.matrixCard}>
        <h4>Confusion matrix</h4>
        <div className={styles.matrixGrid}>
          <div className={styles.matrixCell}>
            <div className={styles.matrixCount}>{data.tn}</div>
            <div className={styles.matrixLabel}>Correctly cleared sensitive strains</div>
          </div>
          <div className={`${styles.matrixCell} ${styles.matrixMiss}`}>
            <div className={styles.matrixCount}>{data.fp}</div>
            <div className={styles.matrixLabel}>False alarms (false positives)</div>
          </div>
          <div className={`${styles.matrixCell} ${styles.matrixMiss}`}>
            <div className={styles.matrixCount}>{data.fn}</div>
            <div className={styles.matrixLabel}>Missed resistant strains (false negatives)</div>
          </div>
          <div className={styles.matrixCell}>
            <div className={styles.matrixCount}>{data.tp}</div>
            <div className={styles.matrixLabel}>Correctly caught resistant strains</div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `ProValidatePage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 0.4rem 0;
  color: var(--pro-ink);
}

.intro {
  font-size: 0.85rem;
  color: var(--pro-ink-soft);
  max-width: 640px;
  margin: 0 0 1rem 0;
}

.loading,
.error {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.statRow {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin-bottom: 1.25rem;
}

.stat {
  flex: 1 1 140px;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 0.85rem 1rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--pro-shadow-md);
}

.statValue {
  font-family: var(--pro-font-mono);
  font-size: 1.3rem;
  font-weight: 600;
  background: linear-gradient(135deg, var(--pro-ink), var(--pro-accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.statLabel {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pro-ink-faint);
  margin-top: 0.25rem;
}

.matrixCard {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 1rem 1.1rem;
}

.matrixCard h4 {
  margin: 0 0 0.8rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.matrixGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
}

.matrixCell {
  background: var(--pro-pos-bg);
  border-radius: var(--pro-radius-sm);
  padding: 0.8rem 0.9rem;
}

.matrixMiss {
  background: var(--pro-neg-bg);
}

.matrixCount {
  font-family: var(--pro-font-mono);
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.matrixLabel {
  font-size: 0.72rem;
  color: var(--pro-ink-soft);
  margin-top: 0.2rem;
}
```

- [ ] **Step 3: Write `ProValidatePage.test.tsx`**

Adapted from `ValidatePage.test.tsx` — routes prefixed with `/pro`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProValidatePage from "./ProValidatePage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/validate`]}>
      <Routes>
        <Route path="/pro/sessions/:name/validate" element={<ProValidatePage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleResult = {
  n_train: 32, n_holdout: 8, n_holdout_resistant: 3, n_holdout_sensitive: 5,
  balanced_accuracy: 0.9, precision: 0.85, recall: 0.95, f1: 0.88,
  roc_auc: 0.97, tn: 5, fp: 0, fn: 0, tp: 3,
};

describe("ProValidatePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the five headline metrics once loaded", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue(sampleResult);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText("90.0%")).toBeInTheDocument();
    });
    expect(screen.getByText("85.0%")).toBeInTheDocument();
    expect(screen.getByText("95.0%")).toBeInTheDocument();
    expect(screen.getByText("0.970")).toBeInTheDocument();
  });

  it("shows an em dash for roc-auc when it's null", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue({ ...sampleResult, roc_auc: null });

    renderAtSession("azm-project");

    expect(await screen.findByText("—")).toBeInTheDocument();
  });

  it("shows all four confusion matrix cells", async () => {
    vi.spyOn(client, "getValidation").mockResolvedValue(sampleResult);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText(/correctly caught resistant/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/correctly cleared sensitive/i)).toBeInTheDocument();
    expect(screen.getByText(/false alarms/i)).toBeInTheDocument();
    expect(screen.getByText(/missed resistant/i)).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(client, "getValidation").mockRejectedValue(new Error("No session named 'x'."));

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

```tsx
import ProValidatePage from "./pro/pages/ProValidatePage";
```

```tsx
          <Route path="validate" element={<ProValidatePage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProValidatePage.test.tsx`
Expected: `4 passed`.

Run: `npm test -- --run`
Expected: `157 passed (157)` (153 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProValidatePage.tsx frontend/src/pro/pages/ProValidatePage.module.css \
  frontend/src/pro/pages/ProValidatePage.test.tsx frontend/src/App.tsx
git commit -m "Add ProValidatePage"
```

---

### Task 12: `ProSettingsPage`

**Files:**
- Create: `frontend/src/pro/pages/ProSettingsPage.tsx`
- Create: `frontend/src/pro/pages/ProSettingsPage.module.css`
- Create: `frontend/src/pro/pages/ProSettingsPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `deleteSession`/`getStatus`/`resetSession`/`updateSettings`/
  `StatusResponse` from `../../api/client` (unchanged).

Danger-zone buttons keep the classic page's native `window.confirm` gate before
calling `resetSession`/`deleteSession` — cancelling leaves the session
untouched, same as the classic page. Deleting navigates to `/pro` (not `/`).

- [ ] **Step 1: Write `ProSettingsPage.tsx`**

```tsx
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  deleteSession,
  getStatus,
  resetSession,
  updateSettings,
  type StatusResponse,
} from "../../api/client";
import styles from "./ProSettingsPage.module.css";

const MODEL_OPTIONS = [
  { value: "rf", label: "Random Forest" },
  { value: "gbm", label: "Gradient Boosting" },
  { value: "lr", label: "Logistic Regression" },
  { value: "svm", label: "SVM" },
];

const CALIBRATION_OPTIONS = [
  { value: "sigmoid", label: "Sigmoid" },
  { value: "isotonic", label: "Isotonic" },
];

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: StatusResponse };

export default function ProSettingsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const [patience, setPatience] = useState("3");
  const [minDelta, setMinDelta] = useState("0.005");
  const [costPerSample, setCostPerSample] = useState("");
  const [diversityWeight, setDiversityWeight] = useState("0");
  const [model, setModel] = useState("rf");
  const [calibrate, setCalibrate] = useState(false);
  const [calibrationMethod, setCalibrationMethod] = useState("sigmoid");

  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [dangerBusy, setDangerBusy] = useState(false);
  const [dangerError, setDangerError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getStatus(name)
      .then((data) => {
        if (cancelled) return;
        setState({ status: "loaded", data });
        setPatience(String(data.patience));
        setMinDelta(String(data.min_delta));
        setCostPerSample(data.cost_per_sample !== null ? String(data.cost_per_sample) : "");
        setDiversityWeight(String(data.diversity_weight));
        setModel(data.model);
        setCalibrate(data.calibrate);
        setCalibrationMethod(data.calibration_method);
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    if (!name) return;
    setSaveError(null);
    setSaveMessage(null);
    setSaving(true);
    try {
      const updated = await updateSettings(name, {
        patience: Number(patience),
        minDelta: Number(minDelta),
        costPerSample: costPerSample === "" ? undefined : Number(costPerSample),
        diversityWeight: Number(diversityWeight),
        model,
        calibrate,
        calibrationMethod,
      });
      setState({ status: "loaded", data: updated });
      setSaveMessage("Settings saved.");
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!name) return;
    if (!window.confirm(`Reset ${name}? This clears all round history but keeps known/pool samples.`)) {
      return;
    }
    setDangerError(null);
    setDangerBusy(true);
    try {
      await resetSession(name);
      const refreshed = await getStatus(name);
      setState({ status: "loaded", data: refreshed });
    } catch (err) {
      setDangerError((err as Error).message);
    } finally {
      setDangerBusy(false);
    }
  }

  async function handleDelete() {
    if (!name) return;
    if (!window.confirm(`Delete ${name}? This permanently removes the session and its data.`)) {
      return;
    }
    setDangerError(null);
    setDangerBusy(true);
    try {
      await deleteSession(name);
      navigate("/pro");
    } catch (err) {
      setDangerError((err as Error).message);
      setDangerBusy(false);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <h2 className={styles.title}>Settings</h2>
      <form onSubmit={handleSave} className={styles.form}>
        <div className={styles.field}>
          <label htmlFor="patience">Patience (rounds)</label>
          <input id="patience" type="number" min="1" value={patience} onChange={(e) => setPatience(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="minDelta">Min delta</label>
          <input id="minDelta" type="number" step="0.001" min="0" value={minDelta} onChange={(e) => setMinDelta(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="costPerSample">Cost per sample (blank = not tracked)</label>
          <input id="costPerSample" type="number" step="0.01" min="0" value={costPerSample} onChange={(e) => setCostPerSample(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="diversityWeight">Diversity weight</label>
          <input id="diversityWeight" type="number" step="0.05" min="0" max="1" value={diversityWeight} onChange={(e) => setDiversityWeight(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="model">Model</label>
          <select id="model" value={model} onChange={(e) => setModel(e.target.value)}>
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className={styles.checkboxField}>
          <label htmlFor="calibrate">
            <input id="calibrate" type="checkbox" checked={calibrate} onChange={(e) => setCalibrate(e.target.checked)} />
            {" "}Calibrate predictions
          </label>
        </div>
        {calibrate && (
          <div className={styles.field}>
            <label htmlFor="calibrationMethod">Calibration method</label>
            <select id="calibrationMethod" value={calibrationMethod} onChange={(e) => setCalibrationMethod(e.target.value)}>
              {CALIBRATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        )}

        <button type="submit" className={styles.submit} disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
        {saveMessage && <p className={styles.saveMessage}>{saveMessage}</p>}
        {saveError && <p className={styles.error}>{saveError}</p>}
      </form>

      <div className={styles.dangerZone}>
        <h3>Danger zone</h3>
        <button type="button" onClick={handleReset} disabled={dangerBusy} className={styles.dangerButton}>
          Reset session
        </button>
        <button type="button" onClick={handleDelete} disabled={dangerBusy} className={styles.dangerButton}>
          Delete session
        </button>
        {dangerError && <p className={styles.error}>{dangerError}</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `ProSettingsPage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--pro-ink);
}

.loading,
.error {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.form {
  max-width: 420px;
  margin-bottom: 2rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.field label {
  font-size: 0.8rem;
  color: var(--pro-ink-soft);
  font-weight: 600;
}

.field input,
.field select {
  font-family: var(--pro-font-body);
  font-size: 0.88rem;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  background: var(--pro-surface);
  color: var(--pro-ink);
  box-sizing: border-box;
  width: 100%;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--pro-accent);
}

.checkboxField {
  margin-bottom: 1rem;
  font-size: 0.85rem;
  color: var(--pro-ink-soft);
}

.checkboxField input {
  margin-right: 0.4rem;
}

.submit {
  display: inline-flex;
  align-items: center;
  padding: 0.6rem 1.3rem;
  border: none;
  border-radius: var(--pro-radius-sm);
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: var(--pro-shadow-btn);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.submit:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.35);
  transform: translateY(-1px);
}

.submit:disabled {
  opacity: 0.6;
  cursor: default;
}

.saveMessage {
  font-size: 0.8rem;
  color: var(--pro-pos-ink);
  margin-top: 0.6rem;
}

.dangerZone {
  border: 1px solid var(--pro-neg-bg);
  border-radius: var(--pro-radius-md);
  background: var(--pro-neg-bg);
  padding: 1rem 1.2rem;
  max-width: 420px;
}

.dangerZone h3 {
  margin: 0 0 0.7rem 0;
  font-size: 0.9rem;
  color: var(--pro-neg-ink);
}

.dangerButton {
  padding: 0.5rem 1rem;
  border: 1px solid var(--pro-neg-ink);
  border-radius: var(--pro-radius-sm);
  background: var(--pro-surface);
  color: var(--pro-neg-ink);
  font-weight: 600;
  font-size: 0.8rem;
  cursor: pointer;
  margin-right: 0.6rem;
  transition: background-color 0.15s ease;
}

.dangerButton:hover:not(:disabled) {
  background: var(--pro-neg-bg);
}

.dangerButton:disabled {
  opacity: 0.6;
  cursor: default;
}
```

- [ ] **Step 3: Write `ProSettingsPage.test.tsx`**

Adapted from `SettingsPage.test.tsx` — routes prefixed with `/pro`, the
post-delete placeholder route is `/pro` instead of `/`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProSettingsPage from "./ProSettingsPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/settings`]}>
      <Routes>
        <Route path="/pro/sessions/:name/settings" element={<ProSettingsPage />} />
        <Route path="/pro" element={<div>Session list placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleStatus = {
  name: "azm-project", current_round: 2, n_known: 45, n_pool: 55, n_pending: 0,
  latest_accuracy: 0.93, patience: 3, min_delta: 0.005, cost_per_sample: 1.5,
  total_cost: 15, diversity_weight: 0, model: "rf", calibrate: false,
  calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
};

describe("ProSettingsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("pre-fills the form with the session's current settings", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByLabelText(/patience/i)).toHaveValue(3);
    });
    expect(screen.getByLabelText(/min delta/i)).toHaveValue(0.005);
    expect(screen.getByLabelText(/cost per sample/i)).toHaveValue(1.5);
  });

  it("saves changed settings and shows a confirmation", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const updateSpy = vi.spyOn(client, "updateSettings").mockResolvedValue({ ...sampleStatus, patience: 7 });
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByLabelText(/patience/i)).toHaveValue(3);
    });
    fireEvent.change(screen.getByLabelText(/patience/i), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalled();
    });
    expect(await screen.findByText(/settings saved/i)).toBeInTheDocument();
  });

  it("asks for confirmation before resetting, and does not reset if cancelled", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const resetSpy = vi.spyOn(client, "resetSession");
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reset session/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /reset session/i }));

    expect(window.confirm).toHaveBeenCalled();
    expect(resetSpy).not.toHaveBeenCalled();
  });

  it("resets when confirmed", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const resetSpy = vi.spyOn(client, "resetSession").mockResolvedValue({ n_known: 45, n_pool: 55, rounds_cleared: 2 });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reset session/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /reset session/i }));

    await waitFor(() => {
      expect(resetSpy).toHaveBeenCalledWith("azm-project");
    });
  });

  it("asks for confirmation before deleting, and navigates away when confirmed", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    const deleteSpy = vi.spyOn(client, "deleteSession").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /delete session/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /delete session/i }));

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("azm-project");
    });
    expect(await screen.findByText("Session list placeholder")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

```tsx
import ProSettingsPage from "./pro/pages/ProSettingsPage";
```

```tsx
          <Route path="settings" element={<ProSettingsPage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProSettingsPage.test.tsx`
Expected: `5 passed`.

Run: `npm test -- --run`
Expected: `162 passed (162)` (157 + 5 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProSettingsPage.tsx frontend/src/pro/pages/ProSettingsPage.module.css \
  frontend/src/pro/pages/ProSettingsPage.test.tsx frontend/src/App.tsx
git commit -m "Add ProSettingsPage"
```

---

### Task 13: `ProBudgetPage`

**Files:**
- Create: `frontend/src/pro/pages/ProBudgetPage.tsx`
- Create: `frontend/src/pro/pages/ProBudgetPage.module.css`
- Create: `frontend/src/pro/pages/ProBudgetPage.test.tsx`
- Modify: `frontend/src/App.tsx` (both the route wiring and the conditional
  Budget nav link in `ProSessionLayout` already handle this — no `ProSessionLayout`
  change needed here since Task 5 already built the conditional link)

**Interfaces:**
- Consumes: `getHistory`/`getStatus`/`HistoryRow`/`StatusResponse` from
  `../../api/client`, `fitLinearTrend`/`projectCostForTarget`/`CostPoint` from
  `../../pages/costProjection`, `toBudgetChartData` from
  `../../pages/budgetChartData` — all unchanged, all reused verbatim (this is
  the page with the most non-presentational logic, and every bit of it is a
  pure function this task must not touch).

- [ ] **Step 1: Write `ProBudgetPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getHistory, getStatus, type HistoryRow, type StatusResponse } from "../../api/client";
import { fitLinearTrend, projectCostForTarget, type CostPoint } from "../../pages/costProjection";
import { toBudgetChartData } from "../../pages/budgetChartData";
import styles from "./ProBudgetPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; history: HistoryRow[]; sessionStatus: StatusResponse };

function historyToCostPoints(history: HistoryRow[]): CostPoint[] {
  return history
    .filter((row): row is HistoryRow & { accuracy: number; cumulative_cost: number } =>
      row.accuracy !== null && row.cumulative_cost !== null
    )
    .map((row) => ({ cost: row.cumulative_cost, accuracy: row.accuracy }));
}

export default function ProBudgetPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [targetPercent, setTargetPercent] = useState("95");

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    Promise.all([getHistory(name), getStatus(name)])
      .then(([history, sessionStatus]) => {
        if (!cancelled) setState({ status: "loaded", history, sessionStatus });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  const points = historyToCostPoints(state.history);
  const trend = fitLinearTrend(points);
  const currentCost = state.sessionStatus.total_cost ?? 0;
  const parsedTarget = Number(targetPercent) / 100;
  const projected =
    trend !== null && !Number.isNaN(parsedTarget)
      ? projectCostForTarget(trend, currentCost, parsedTarget)
      : null;
  const projectedTargetCost = projected !== null ? currentCost + projected : null;
  const chartData = toBudgetChartData(points, projectedTargetCost, parsedTarget);

  return (
    <div>
      <h2 className={styles.title}>Cost &amp; budget projection</h2>
      <div className={styles.statRow}>
        <div className={styles.stat}>
          <div className={styles.statValue}>${currentCost.toFixed(2)}</div>
          <div className={styles.statLabel}>Spent so far</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {state.sessionStatus.latest_accuracy !== null
              ? `${(state.sessionStatus.latest_accuracy * 100).toFixed(1)}%`
              : "—"}
          </div>
          <div className={styles.statLabel}>Current accuracy</div>
        </div>
      </div>

      {points.length < 2 ? (
        <p className={styles.empty}>
          Not enough completed rounds yet to project a trend — at least 2 rounds with
          both accuracy and cost recorded are needed.
        </p>
      ) : (
        <>
          <div className={styles.chartCard}>
            <div className={styles.chartHead}>
              <h4>Accuracy vs. cumulative cost</h4>
              <div className={styles.chartLegend}>
                <span className={styles.legendActual}>● actual</span>
                <span className={styles.legendProjected}>┄ projected</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--pro-line-soft)" />
                <XAxis
                  dataKey="cost"
                  type="number"
                  domain={[0, "dataMax"]}
                  stroke="var(--pro-ink-faint)"
                  tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
                  tickFormatter={(v: number) => `$${Math.round(v)}`}
                  label={{
                    value: "Cumulative cost",
                    position: "insideBottom",
                    offset: -6,
                    fill: "var(--pro-ink-faint)",
                  }}
                />
                <YAxis
                  domain={[0, 1]}
                  stroke="var(--pro-ink-faint)"
                  tick={{ fill: "var(--pro-ink-faint)", fontSize: 12, fontFamily: "var(--pro-font-mono)" }}
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                  label={{
                    value: "Accuracy",
                    angle: -90,
                    position: "insideLeft",
                    fill: "var(--pro-ink-faint)",
                  }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--pro-surface)",
                    border: "1px solid var(--pro-line)",
                    borderRadius: 6,
                    boxShadow: "var(--pro-shadow-md)",
                  }}
                  labelStyle={{ color: "var(--pro-ink)" }}
                  labelFormatter={(v: number) => `$${v.toFixed(2)}`}
                  formatter={(value: number, dataKey: string) => [
                    `${(value * 100).toFixed(1)}%`,
                    dataKey === "actual" ? "Accuracy" : "Projected",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="var(--pro-accent)"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "var(--pro-accent)" }}
                  activeDot={{ r: 5 }}
                  name="actual"
                />
                <Line
                  type="monotone"
                  dataKey="projected"
                  stroke="var(--pro-ink-soft)"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={{ r: 4, fill: "var(--pro-ink-soft)" }}
                  activeDot={{ r: 5 }}
                  connectNulls
                  name="projected"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.projectionPanel}>
            <div className={styles.targetField}>
              <label htmlFor="targetAccuracy">Target accuracy</label>
              <div className={styles.targetInputWrap}>
                <input
                  id="targetAccuracy"
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  value={targetPercent}
                  onChange={(e) => setTargetPercent(e.target.value)}
                />
                <span className={styles.targetSuffix}>%</span>
              </div>
            </div>

            <div className={styles.projectionResult}>
              {trend !== null && trend.slope <= 0 ? (
                <p className={styles.empty}>
                  Accuracy isn't trending upward with cost yet — projection isn't
                  meaningful until it is.
                </p>
              ) : projected !== null ? (
                <>
                  <div className={styles.projectionValue}>${projected.toFixed(2)}</div>
                  <div className={styles.projectionLabel}>
                    Projected additional spend to reach {targetPercent}%
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `ProBudgetPage.module.css`**

```css
.title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--pro-ink);
}

.loading,
.error,
.empty {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-soft);
}

.error {
  color: var(--pro-neg-ink);
}

.statRow {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1.25rem;
}

.stat {
  flex: 1;
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 0.85rem 1rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--pro-shadow-md);
}

.statValue {
  font-family: var(--pro-font-mono);
  font-size: 1.3rem;
  font-weight: 600;
  background: linear-gradient(135deg, var(--pro-ink), var(--pro-accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.statLabel {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pro-ink-faint);
  margin-top: 0.25rem;
}

.chartCard {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}

.chartHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.4rem;
}

.chartHead h4 {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--pro-ink);
}

.chartLegend {
  display: flex;
  gap: 0.8rem;
  font-family: var(--pro-font-mono);
  font-size: 0.68rem;
}

.legendActual {
  color: var(--pro-accent);
}

.legendProjected {
  color: var(--pro-ink-soft);
}

.projectionPanel {
  display: flex;
  gap: 1rem;
  align-items: stretch;
  flex-wrap: wrap;
}

.targetField {
  background: var(--pro-surface);
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-sm);
  padding: 0.9rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 160px;
}

.targetField label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pro-ink-faint);
}

.targetInputWrap {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.targetInputWrap input {
  font-family: var(--pro-font-mono);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--pro-ink);
  border: 1px solid var(--pro-line);
  border-radius: var(--pro-radius-sm);
  padding: 0.35rem 0.5rem;
  width: 4.5rem;
}

.targetInputWrap input:focus {
  outline: none;
  border-color: var(--pro-accent);
}

.targetSuffix {
  font-family: var(--pro-font-mono);
  color: var(--pro-ink-faint);
}

.projectionResult {
  flex: 1;
  background: linear-gradient(135deg, var(--pro-accent), var(--pro-accent-bright));
  border-radius: var(--pro-radius-md);
  box-shadow: var(--pro-shadow-btn);
  padding: 0.9rem 1.1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 220px;
  color: #ffffff;
}

.projectionResult .empty {
  color: #ffffff;
  font-family: var(--pro-font-body);
}

.projectionValue {
  font-family: var(--pro-font-mono);
  font-size: 1.6rem;
  font-weight: 700;
}

.projectionLabel {
  font-size: 0.75rem;
  opacity: 0.9;
  margin-top: 0.2rem;
}
```

- [ ] **Step 3: Write `ProBudgetPage.test.tsx`**

Adapted from `BudgetPage.test.tsx` — routes prefixed with `/pro`. The exact
dollar figures (`$12.22`/`$5.56`) come from `costProjection.ts`'s math on the
same input data, unchanged, so they must still match:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../../api/client";
import ProBudgetPage from "./ProBudgetPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/pro/sessions/${name}/budget`]}>
      <Routes>
        <Route path="/pro/sessions/:name/budget" element={<ProBudgetPage />} />
      </Routes>
    </MemoryRouter>
  );
}

const sampleStatus = {
  name: "azm-project", current_round: 3, n_known: 45, n_pool: 55, n_pending: 0,
  latest_accuracy: 0.85, patience: 3, min_delta: 0.005, cost_per_sample: 1,
  total_cost: 30, diversity_weight: 0, model: "rf", calibrate: false,
  calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
};

describe("ProBudgetPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an insufficient-data message with fewer than 2 costed rounds", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    vi.spyOn(client, "getHistory").mockResolvedValue([
      { round_number: 1, n_known: 25, accuracy: 0.7, round_cost: 10, cumulative_cost: 10, created_at: "2026-01-01" },
    ]);

    renderAtSession("azm-project");

    expect(await screen.findByText(/not enough completed rounds/i)).toBeInTheDocument();
  });

  it("shows a projection with 2+ costed rounds and an upward trend", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    vi.spyOn(client, "getHistory").mockResolvedValue([
      { round_number: 1, n_known: 25, accuracy: 0.7, round_cost: 10, cumulative_cost: 10, created_at: "2026-01-01" },
      { round_number: 2, n_known: 35, accuracy: 0.8, round_cost: 10, cumulative_cost: 20, created_at: "2026-01-02" },
      { round_number: 3, n_known: 45, accuracy: 0.85, round_cost: 10, cumulative_cost: 30, created_at: "2026-01-03" },
    ]);

    renderAtSession("azm-project");

    await waitFor(() => {
      expect(screen.getByText(/spent so far/i)).toBeInTheDocument();
    });
    expect(await screen.findByText(/projected additional spend/i)).toBeInTheDocument();
  });

  it("defaults the target-accuracy input to a whole-number percentage and recomputes the projection when it changes", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue(sampleStatus);
    vi.spyOn(client, "getHistory").mockResolvedValue([
      { round_number: 1, n_known: 25, accuracy: 0.7, round_cost: 10, cumulative_cost: 10, created_at: "2026-01-01" },
      { round_number: 2, n_known: 35, accuracy: 0.8, round_cost: 10, cumulative_cost: 20, created_at: "2026-01-02" },
      { round_number: 3, n_known: 45, accuracy: 0.85, round_cost: 10, cumulative_cost: 30, created_at: "2026-01-03" },
    ]);

    renderAtSession("azm-project");

    const input = await screen.findByLabelText(/target accuracy/i);
    expect(input).toHaveValue(95);
    expect(await screen.findByText(/reach 95%/i)).toBeInTheDocument();
    expect(await screen.findByText("$12.22")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "90" } });

    expect(await screen.findByText(/reach 90%/i)).toBeInTheDocument();
    expect(await screen.findByText("$5.56")).toBeInTheDocument();
  });

  it("shows an error message when a request fails", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("No session named 'x'."));
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Wire into `App.tsx`**

This finalizes `ProApp`'s `<Routes>` — every session-scoped page now has a
route:

```tsx
import ProBudgetPage from "./pro/pages/ProBudgetPage";
```

```tsx
          <Route path="budget" element={<ProBudgetPage />} />
```

- [ ] **Step 5: Run the new test and the full suite**

Run: `cd frontend && npx vitest run src/pro/pages/ProBudgetPage.test.tsx`
Expected: `4 passed`.

Run: `npm test -- --run`
Expected: `166 passed (166)` (162 + 4 new).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pro/pages/ProBudgetPage.tsx frontend/src/pro/pages/ProBudgetPage.module.css \
  frontend/src/pro/pages/ProBudgetPage.test.tsx frontend/src/App.tsx
git commit -m "Add ProBudgetPage"
```

---

### Task 14: Full-app verification + CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none (documentation + verification only).

- [ ] **Step 1: Run the full backend and frontend suites**

Run: `make test` (from the repo root) — Expected: `272 passed` (untouched by
this plan; confirms nothing in `acquireml/` regressed).

Run: `cd frontend && npm test -- --run` — Expected: `166 passed (166)`.

Run: `npx tsc --noEmit` — Expected: no errors.

Run: `npm run build` — Expected: a clean production build (Vite bundles both
`ClassicApp` and `ProApp`; this catches any import-path mistake that `tsc`
alone might miss under different module resolution).

- [ ] **Step 2: Manually verify the whole Pro app in the browser**

`npm run dev` + `make api`. Walk every Pro route end to end against a real
session:
- `/pro` — session list, sortable, "New session" link works
- `/pro/new` — create a session, lands back on `/pro`
- `/pro/sessions/<name>` through all nine nav pages (Dashboard, Recommendations,
  History, Overview, Explain, Compare, Validate, Settings, Budget) — confirm
  each renders real data, the sidebar's active-link gradient pill tracks the
  current page, and the Budget nav link only appears for a cost-tracked session
- Cmd+K opens `ProCommandPalette` from any Pro route and correctly excludes
  Budget for a non-cost-tracked session
- In parallel, spot-check 3–4 classic routes (`/`, `/sessions/<name>`,
  `/sessions/<name>/history`) still look and behave exactly as before —
  dark, electric blue, motion effects intact, completely unaffected by this
  plan

Stop both servers when done.

- [ ] **Step 3: Update CLAUDE.md**

Add a new paragraph after the existing "Web UI frontend" section (after the
sidebar/color-scheme redesign note) documenting the Pro theme: what it is, the
`/pro/*` route split in `App.tsx`, the `frontend/src/pro/` tree, what's reused
vs. new, the "Navy Instrument" name and its Inter/IBM Plex Mono + navy-gradient
identity, and the updated frontend test count (108 → 166). Follow the existing
prose style in that section — dense, specific, no marketing language.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Document the Pro theme in CLAUDE.md"
```

