# Web UI Frontend — Dashboard, Recommendations, History — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the frontend's session lifecycle by adding the three
pages deferred from Phase 1: Dashboard, Recommendations, History —
letting a researcher go from "session exists" to "see progress, submit
lab results, review/export history" entirely in the browser.

**Architecture:** Three new session-scoped routes nested under a shared
`SessionLayout` (nav header + `<Outlet />`), mirroring the backend's own
`/sessions/{name}/...` URL shape. `frontend/src/api/client.ts` (existing
file) gains five functions for the backend endpoints Phase 1 didn't need
yet. A shared `AccuracyChart` component (Recharts) is used by both
Dashboard and History, backed by pure, independently-testable data-shaping
functions rather than testing chart rendering directly (jsdom can't do
real layout, so Recharts' `ResponsiveContainer` needs care in tests).

**Tech Stack:** Adds one new dependency, `recharts`, to the existing
React/TypeScript/Vite/Vitest stack from Phase 1. No other new dependencies.

## Global Constraints

- No changes to the backend (`acquireml/api/`) — pure frontend consumer
  of already-built, already-tested endpoints.
- `frontend/src/api/client.ts` remains the ONLY file that calls `fetch`
  or constructs a backend URL — every new page goes through it.
- New TypeScript interfaces (`StatusResponse`, `HistoryRow`,
  `RecommendResponse`, `RecommendRow`, `ResultRow`, `UpdateResponse`)
  must exactly mirror `acquireml/api/schemas.py`'s equivalents — field
  names, types, and nullability (`| None` → `| null`).
- Routing: `/sessions/:name` (Dashboard), `/sessions/:name/recommend`
  (Recommendations), `/sessions/:name/history` (History), nested under a
  shared `SessionLayout` via React Router's `<Outlet />` pattern — not
  three independent top-level routes that each reimplement navigation.
- No polling/auto-refresh anywhere — each page fetches once on mount,
  same request-per-navigation model Phase 1 already established.
- All Phase 1 tests (12) and the backend's tests (221) must stay green
  throughout — this plan only adds files and extends `client.ts`/`App.tsx`/
  `SessionListPage.tsx`, never rewrites existing page logic.
- Every component gets at least one test verifying real rendered behavior
  (React Testing Library queries), not implementation details.

---

### Task 1: Extend the API client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: nothing new — extends the existing `API_BASE_URL` and
  `parseErrorDetail` already in the file.
- Produces: `getStatus(name: string): Promise<StatusResponse>`,
  `getHistory(name: string): Promise<HistoryRow[]>`,
  `getRecommendations(name: string, batchSize?: number): Promise<RecommendResponse>`,
  `submitResults(name: string, results: ResultRow[]): Promise<UpdateResponse>`,
  `exportHistory(name: string): Promise<Blob>` — plus the TypeScript
  interfaces `StatusResponse`, `HistoryRow`, `RecommendRow`,
  `RecommendResponse`, `ResultRow`, `UpdateResponse`. Task 3 imports
  `getStatus`/`getHistory`/`StatusResponse`/`HistoryRow`; Task 4 imports
  `getRecommendations`/`submitResults`/`RecommendRow`/`ResultRow`; Task 5
  imports `getHistory`/`exportHistory`/`HistoryRow`; Task 2 imports only
  `HistoryRow` (the chart component takes history data, not session name).

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/api/client.test.ts` (append — the existing
`listSessions`/`createSession` describe blocks stay as they are):

```typescript
describe("getStatus", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions/{name}/status", async () => {
    const mockStatus = {
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
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    });

    const result = await getStatus("azm-project");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/status");
    expect(result).toEqual(mockStatus);
  });

  it("throws with the response detail on a 404", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "No session named 'nope'." }),
    });

    await expect(getStatus("nope")).rejects.toThrow("No session named 'nope'.");
  });
});

describe("getHistory", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions/{name}/history", async () => {
    const mockHistory = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHistory,
    });

    const result = await getHistory("azm-project");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/history");
    expect(result).toEqual(mockHistory);
  });
});

describe("getRecommendations", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions/{name}/recommend with no batch_size by default", async () => {
    const mockResponse = { rows: [], should_stop: false, stop_reason: "" };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    await getRecommendations("azm-project");

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/sessions/azm-project/recommend");
  });

  it("includes batch_size in the query string when provided", async () => {
    const mockResponse = { rows: [], should_stop: false, stop_reason: "" };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    await getRecommendations("azm-project", 5);

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toBe("http://localhost:8000/sessions/azm-project/recommend?batch_size=5");
  });
});

describe("submitResults", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts JSON results to /sessions/{name}/update", async () => {
    const mockResponse = {
      round: 1,
      n_returned: 2,
      n_known: 22,
      n_pool: 18,
      accuracy: 0.9,
      round_cost: null,
      cumulative_cost: null,
      should_stop: false,
      stop_reason: "",
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const results = [
      { sample_id: "pool_1", label: 1 },
      { sample_id: "pool_2", label: 0 },
    ];
    const result = await submitResults("azm-project", results);

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results }),
    });
    expect(result).toEqual(mockResponse);
  });

  it("throws with the response detail on a 400 (no matching results)", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "No pending samples matched in the results file." }),
    });

    await expect(submitResults("azm-project", [])).rejects.toThrow(
      "No pending samples matched"
    );
  });
});

describe("exportHistory", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the CSV and returns it as a Blob", async () => {
    const mockBlob = new Blob(["round_number,accuracy\n1,0.9\n"], { type: "text/csv" });
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      blob: async () => mockBlob,
    });

    const result = await exportHistory("azm-project");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions/azm-project/export");
    expect(result).toBe(mockBlob);
  });
});
```

Add the new imports to the top of the test file (alongside the existing
`import { createSession, listSessions } from "./client";`):

```typescript
import {
  createSession,
  exportHistory,
  getHistory,
  getRecommendations,
  getStatus,
  listSessions,
  submitResults,
} from "./client";
```

Note: error-path tests are written for `getStatus` and `submitResults`
only, not all five functions — `parseErrorDetail` is one shared function
already fully tested (success and failure) in the existing
`listSessions`/`createSession` tests above; re-testing the identical
shared error path five more times would be redundant, not more thorough.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — `getStatus`, `getHistory`, etc. are not exported from
`./client` yet.

- [ ] **Step 3: Add the new interfaces and functions to `frontend/src/api/client.ts`**

Add these interfaces after the existing `CreateSessionInput` interface:

```typescript
export interface StatusResponse {
  name: string | null;
  current_round: number;
  n_known: number;
  n_pool: number;
  n_pending: number;
  latest_accuracy: number | null;
  patience: number;
  min_delta: number;
  cost_per_sample: number | null;
  total_cost: number | null;
  diversity_weight: number;
  model: string;
  calibrate: boolean;
  calibration_method: string;
  should_stop: boolean;
  stop_reason: string;
  created_at: string | null;
}

export interface HistoryRow {
  round_number: number;
  n_known: number;
  accuracy: number | null;
  round_cost: number | null;
  cumulative_cost: number | null;
  created_at: string;
}

export interface RecommendRow {
  rank: number;
  sample_id: string;
  uncertainty_score: number;
  p_positive: number;
  predicted_class: string;
}

export interface RecommendResponse {
  rows: RecommendRow[];
  should_stop: boolean;
  stop_reason: string;
}

export interface ResultRow {
  sample_id: string;
  label: number;
}

export interface UpdateResponse {
  round: number;
  n_returned: number;
  n_known: number;
  n_pool: number;
  accuracy: number;
  round_cost: number | null;
  cumulative_cost: number | null;
  should_stop: boolean;
  stop_reason: string;
}
```

Add these functions at the end of the file:

```typescript
export async function getStatus(name: string): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/status`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getHistory(name: string): Promise<HistoryRow[]> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/history`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function getRecommendations(
  name: string,
  batchSize?: number
): Promise<RecommendResponse> {
  const url = new URL(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/recommend`);
  if (batchSize !== undefined) {
    url.searchParams.set("batch_size", String(batchSize));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function submitResults(
  name: string,
  results: ResultRow[]
): Promise<UpdateResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ results }),
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function exportHistory(name: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/export`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.blob();
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `client.test.ts` — 12 passed (4 pre-existing: listSessions×2, createSession×2 + 8 new: getStatus×2, getHistory×1, getRecommendations×2, submitResults×2, exportHistory×1).

- [ ] **Step 5: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "Extend API client: getStatus, getHistory, getRecommendations, submitResults, exportHistory"
```

---

### Task 2: Recharts + shared AccuracyChart component

**Files:**
- Modify: `frontend/package.json` (add `recharts` dependency)
- Modify: `frontend/src/test-setup.ts` (add a `ResizeObserver` stub —
  jsdom has no native `ResizeObserver`, which Recharts' `ResponsiveContainer`
  requires; without a stub, rendering any Recharts component in a test
  throws)
- Create: `frontend/src/components/chartData.ts`
- Create: `frontend/src/components/chartData.test.ts`
- Create: `frontend/src/components/AccuracyChart.tsx`
- Create: `frontend/src/components/AccuracyChart.test.tsx`

**Interfaces:**
- Consumes: `HistoryRow` from `frontend/src/api/client.ts` (Task 1).
- Produces: `historyToChartData(history: HistoryRow[]): ChartPoint[]`,
  `historyHasCost(history: HistoryRow[]): boolean`, and the default-exported
  `AccuracyChart` component (`{ history: HistoryRow[] }` props). Tasks 3
  and 5 both import `AccuracyChart` and render it with a `HistoryRow[]`
  they already fetched — the component does its own data-shaping
  internally via the two functions above, callers never call those
  functions themselves.

- [ ] **Step 1: Add `recharts` to `frontend/package.json`**

In the `dependencies` object, add (keeping alphabetical order):

```json
    "react-router-dom": "^6.26.0",
    "recharts": "^2.12.0"
```

(i.e. the `dependencies` block becomes `react`, `react-dom`,
`react-router-dom`, `recharts` in that order)

- [ ] **Step 2: Install it**

Run: `cd frontend && npm install`
Expected: installs `recharts` and its transitive dependencies (`d3-*`
packages) cleanly.

- [ ] **Step 3: Write the failing tests for the pure data-shaping functions**

Create `frontend/src/components/chartData.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { historyHasCost, historyToChartData } from "./chartData";
import type { HistoryRow } from "../api/client";

describe("historyToChartData", () => {
  it("maps round_number to round and scales accuracy to a percentage", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];

    expect(historyToChartData(history)).toEqual([
      { round: 1, accuracy: 90, cost: null },
    ]);
  });

  it("passes through a null accuracy as null rather than scaling it", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 10,
        accuracy: null,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];

    expect(historyToChartData(history)[0].accuracy).toBeNull();
  });

  it("carries cumulative_cost through as cost", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: 150,
        cumulative_cost: 150,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];

    expect(historyToChartData(history)[0].cost).toBe(150);
  });

  it("returns an empty array for empty history", () => {
    expect(historyToChartData([])).toEqual([]);
  });
});

describe("historyHasCost", () => {
  it("returns false when no round has a cumulative_cost", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ];
    expect(historyHasCost(history)).toBe(false);
  });

  it("returns true when at least one round has a cumulative_cost", () => {
    const history: HistoryRow[] = [
      {
        round_number: 1,
        n_known: 25,
        accuracy: 0.9,
        round_cost: null,
        cumulative_cost: null,
        created_at: "2026-07-19T00:00:00Z",
      },
      {
        round_number: 2,
        n_known: 30,
        accuracy: 0.92,
        round_cost: 150,
        cumulative_cost: 300,
        created_at: "2026-07-20T00:00:00Z",
      },
    ];
    expect(historyHasCost(history)).toBe(true);
  });

  it("returns false for empty history", () => {
    expect(historyHasCost([])).toBe(false);
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — module `./chartData` not found.

- [ ] **Step 5: Implement `frontend/src/components/chartData.ts`**

```typescript
import type { HistoryRow } from "../api/client";

export interface ChartPoint {
  round: number;
  accuracy: number | null;
  cost: number | null;
}

export function historyToChartData(history: HistoryRow[]): ChartPoint[] {
  return history.map((row) => ({
    round: row.round_number,
    accuracy: row.accuracy !== null ? row.accuracy * 100 : null,
    cost: row.cumulative_cost,
  }));
}

export function historyHasCost(history: HistoryRow[]): boolean {
  return history.some((row) => row.cumulative_cost !== null);
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `chartData.test.ts` — 7 passed.

- [ ] **Step 7: Add the ResizeObserver stub to `frontend/src/test-setup.ts`**

Replace the file's contents:

```typescript
import "@testing-library/jest-dom/vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== "undefined" && !window.ResizeObserver) {
  window.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}
```

- [ ] **Step 8: Write the failing test for `AccuracyChart`**

Create `frontend/src/components/AccuracyChart.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AccuracyChart from "./AccuracyChart";
import type { HistoryRow } from "../api/client";

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

describe("AccuracyChart", () => {
  it("renders without crashing given real history data", () => {
    const { container } = render(<AccuracyChart history={sampleHistory} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });

  it("renders without crashing given empty history", () => {
    const { container } = render(<AccuracyChart history={[]} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });
});
```

This is intentionally a light-touch smoke test, per the design spec's own
testing approach for charts — jsdom does not perform real layout, so
`ResponsiveContainer` reports a zero-size container and Recharts may not
render its full internal SVG tree (axes, lines) in this environment. The
correctness that matters (the round/accuracy/cost mapping) is already
fully covered by `chartData.test.ts`'s pure-function tests above, which
don't depend on jsdom's layout limitations at all.

- [ ] **Step 9: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — module `./AccuracyChart` not found.

- [ ] **Step 10: Implement `frontend/src/components/AccuracyChart.tsx`**

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

interface AccuracyChartProps {
  history: HistoryRow[];
}

export default function AccuracyChart({ history }: AccuracyChartProps) {
  const data = historyToChartData(history);
  const hasCost = historyHasCost(history);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
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
            background: "var(--paper-raised)",
            border: "1px solid var(--line)",
            borderRadius: 4,
          }}
          labelStyle={{ color: "var(--ink)" }}
        />
        <Line
          yAxisId="accuracy"
          type="monotone"
          dataKey="accuracy"
          stroke="var(--accent)"
          strokeWidth={2}
          dot={{ fill: "var(--accent)" }}
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
  );
}
```

Colors reference the Noir & Gold CSS custom properties directly
(`var(--accent)`, `var(--brass)`, etc.) rather than a separate chart
palette — SVG `stroke`/`fill` attributes resolve CSS custom properties
from the DOM the same way inline styles do, since `tokens.css` defines
them on `:root`.

- [ ] **Step 11: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `AccuracyChart.test.tsx` — 2 passed, `chartData.test.ts` — 7
passed, plus all Phase 1 and Task 1 tests still passing.

- [ ] **Step 12: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 13: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/test-setup.ts frontend/src/components/
git commit -m "Add Recharts and a shared AccuracyChart component"
```

---

### Task 3: SessionLayout, DashboardPage, and routing

**Files:**
- Create: `frontend/src/components/SessionLayout.tsx`
- Create: `frontend/src/components/SessionLayout.module.css`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/pages/DashboardPage.test.tsx`
- Create: `frontend/src/pages/DashboardPage.module.css`
- Modify: `frontend/src/App.tsx` (add nested session routes)
- Modify: `frontend/src/pages/SessionListPage.tsx` (make session cards
  clickable links into the dashboard)
- Modify: `frontend/src/pages/SessionListPage.test.tsx` (the existing
  tests query session cards by text content, which still works once
  they're links — but one assertion needs updating, see Step 6)

**Interfaces:**
- Consumes: `getStatus`, `getHistory`, `StatusResponse`, `HistoryRow`
  (Task 1); `AccuracyChart` (Task 2).
- Produces: `SessionLayout` (no props — reads `:name` via `useParams`),
  `DashboardPage` (no props — same). Neither is imported by name
  elsewhere; they're wired into `App.tsx`'s route tree directly.

- [ ] **Step 1: Write the failing tests for `DashboardPage`**

Create `frontend/src/pages/DashboardPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import DashboardPage from "./DashboardPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}`]}>
      <Routes>
        <Route path="/sessions/:name" element={<DashboardPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("DashboardPage", () => {
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

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("93.0%")).toBeInTheDocument();
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

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — module `./DashboardPage` not found.

- [ ] **Step 3: Create `frontend/src/components/SessionLayout.module.css`**

```css
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--line);
}

.sessionName {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--ink);
}

.nav {
  display: flex;
  gap: 1.2rem;
}

.nav a {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  text-decoration: none;
  color: var(--ink-faint);
}

.nav a:hover {
  color: var(--accent);
}
```

- [ ] **Step 4: Implement `frontend/src/components/SessionLayout.tsx`**

```tsx
import { Link, Outlet, useParams } from "react-router-dom";
import styles from "./SessionLayout.module.css";

export default function SessionLayout() {
  const { name } = useParams<{ name: string }>();

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.sessionName}>{name}</div>
        <nav className={styles.nav}>
          <Link to={`/sessions/${name}`}>Dashboard</Link>
          <Link to={`/sessions/${name}/recommend`}>Recommendations</Link>
          <Link to={`/sessions/${name}/history`}>History</Link>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/src/pages/DashboardPage.module.css`**

```css
.loading,
.error,
.empty {
  font-family: var(--font-mono);
  color: var(--ink-soft);
}

.error {
  color: var(--red-data);
}

.stopBanner {
  background: var(--paper-raised);
  border-left: 3px solid var(--brass);
  padding: 0.9rem 1.1rem;
  margin-bottom: 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--ink);
}

.statRow {
  display: flex;
  gap: 2.2rem;
  margin-bottom: 2rem;
}

.stat {
  display: flex;
  flex-direction: column;
}

.statValue {
  font-family: var(--font-display);
  font-size: 1.8rem;
  color: var(--ink);
}

.statLabel {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
  margin-top: 0.2rem;
}
```

- [ ] **Step 6: Implement `frontend/src/pages/DashboardPage.tsx`**

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
          <div className={styles.statValue}>{sessionStatus.current_round}</div>
          <div className={styles.statLabel}>Round</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{sessionStatus.n_known}</div>
          <div className={styles.statLabel}>Known</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>{sessionStatus.n_pool}</div>
          <div className={styles.statLabel}>In pool</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statValue}>
            {sessionStatus.latest_accuracy !== null
              ? `${(sessionStatus.latest_accuracy * 100).toFixed(1)}%`
              : "—"}
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

- [ ] **Step 7: Wire the nested routes in `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="recommend" element={<div>Recommendations (coming in Task 4)</div>} />
          <Route path="history" element={<div>History (coming in Task 5)</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 8: Make session cards in `SessionListPage` clickable links**

In `frontend/src/pages/SessionListPage.tsx`, change the import line:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionSummary } from "../api/client";
import styles from "./SessionListPage.module.css";
```

(unchanged — `Link` is already imported for the "New session" link)

Change the session card rendering from a `<div>` to a `<Link>`:

```tsx
      {state.status === "loaded" &&
        state.sessions.map((session) => (
          <Link
            key={session.name}
            to={`/sessions/${session.name}`}
            className={styles.sessionCard}
          >
            <div className={styles.sessionName}>{session.name}</div>
            <div className={styles.sessionMeta}>
              Round {session.current_round} · {session.n_known} known ·{" "}
              {session.n_pool} in pool
              {session.latest_accuracy !== null &&
                ` · ${(session.latest_accuracy * 100).toFixed(1)}% accuracy`}
            </div>
          </Link>
        ))}
```

In `frontend/src/pages/SessionListPage.module.css`, the existing
`.sessionCard` rule was styled for a `<div>` — add `text-decoration: none`
and `color: inherit` so it doesn't pick up default link styling:

```css
.sessionCard {
  display: block;
  padding: 1.2rem 1.4rem;
  margin-bottom: 0.8rem;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  border-radius: 4px;
  text-decoration: none;
  color: inherit;
}
```

(this replaces the existing `.sessionCard` rule — same properties, plus
the two new lines)

- [ ] **Step 9: Update `frontend/src/pages/SessionListPage.test.tsx`**

The existing tests query cards by text content (`screen.getByText("azm-project")`),
which still passes once the card is a `<Link>` instead of a `<div>` — no
test changes needed. Confirm this by running the suite in the next step
rather than editing the file.

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `DashboardPage.test.tsx` — 4 passed, `SessionListPage.test.tsx`
— 4 passed (unmodified, still passing), plus everything from Tasks 1-2.

- [ ] **Step 11: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 12: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/SessionLayout.tsx frontend/src/components/SessionLayout.module.css frontend/src/pages/DashboardPage.tsx frontend/src/pages/DashboardPage.test.tsx frontend/src/pages/DashboardPage.module.css frontend/src/pages/SessionListPage.tsx frontend/src/pages/SessionListPage.module.css
git commit -m "Add SessionLayout, DashboardPage, and session-scoped routing"
```

---

### Task 4: RecommendationsPage

**Files:**
- Create: `frontend/src/pages/RecommendationsPage.tsx`
- Create: `frontend/src/pages/RecommendationsPage.test.tsx`
- Create: `frontend/src/pages/RecommendationsPage.module.css`
- Modify: `frontend/src/App.tsx` (wire the real `/recommend` route)

**Interfaces:**
- Consumes: `getRecommendations`, `submitResults`, `RecommendRow`,
  `ResultRow` from `frontend/src/api/client.ts` (Task 1).
- Produces: `RecommendationsPage` — fetches the current batch on mount,
  collects a 0/1/blank result per row via a `<select>`, submits only the
  rows with a selected result, navigates to `/sessions/:name` (the
  dashboard) on success so the researcher immediately sees updated
  accuracy.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/RecommendationsPage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import RecommendationsPage from "./RecommendationsPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/recommend`]}>
      <Routes>
        <Route path="/sessions/:name/recommend" element={<RecommendationsPage />} />
        <Route path="/sessions/:name" element={<div>Dashboard placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
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

describe("RecommendationsPage", () => {
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
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — module `./RecommendationsPage` not found.

- [ ] **Step 3: Create `frontend/src/pages/RecommendationsPage.module.css`**

```css
.loading,
.error {
  font-family: var(--font-mono);
  color: var(--ink-soft);
}

.error {
  color: var(--red-data);
}

.table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0;
  font-size: 0.9rem;
}

.table th,
.table td {
  text-align: left;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--line);
}

.table th {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.table select {
  background: var(--paper-raised);
  border: 1px solid var(--line);
  color: var(--ink);
  padding: 0.3rem 0.5rem;
  border-radius: 3px;
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
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--paper);
  background: var(--accent);
  border: none;
  padding: 0.75rem 1.4rem;
  border-radius: 3px;
  cursor: pointer;
}

.submit:hover {
  background: var(--accent-bright);
}

.submitError {
  color: var(--red-data);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  margin-top: 1rem;
}
```

- [ ] **Step 4: Implement `frontend/src/pages/RecommendationsPage.tsx`**

```tsx
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getRecommendations,
  submitResults,
  type RecommendRow,
} from "../api/client";
import styles from "./RecommendationsPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; rows: RecommendRow[] };

export default function RecommendationsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getRecommendations(name)
      .then((response) => {
        if (!cancelled) setState({ status: "loaded", rows: response.rows });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
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
      navigate(`/sessions/${name}`);
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
      <h2>Recommended experiments</h2>
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

- [ ] **Step 5: Wire the real route in `frontend/src/App.tsx`**

Replace the placeholder route:

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="recommend" element={<RecommendationsPage />} />
          <Route path="history" element={<div>History (coming in Task 5)</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `RecommendationsPage.test.tsx` — 3 passed, plus everything
from Tasks 1-3.

- [ ] **Step 7: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/RecommendationsPage.tsx frontend/src/pages/RecommendationsPage.test.tsx frontend/src/pages/RecommendationsPage.module.css
git commit -m "Add RecommendationsPage and wire the /recommend route"
```

---

### Task 5: HistoryPage

**Files:**
- Create: `frontend/src/pages/HistoryPage.tsx`
- Create: `frontend/src/pages/HistoryPage.test.tsx`
- Create: `frontend/src/pages/HistoryPage.module.css`
- Modify: `frontend/src/App.tsx` (wire the real `/history` route)

**Interfaces:**
- Consumes: `getHistory`, `exportHistory`, `HistoryRow` from
  `frontend/src/api/client.ts` (Task 1); `AccuracyChart` (Task 2).
- Produces: `HistoryPage` — full round table + the shared chart + an
  export-to-CSV button that triggers a browser file download from the
  `Blob` `exportHistory` returns.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/HistoryPage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import HistoryPage from "./HistoryPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/history`]}>
      <Routes>
        <Route path="/sessions/:name/history" element={<HistoryPage />} />
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

describe("HistoryPage", () => {
  beforeEach(() => {
    // jsdom has no real implementation of createObjectURL/revokeObjectURL —
    // stub them so the export button's click handler doesn't throw.
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

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — module `./HistoryPage` not found.

- [ ] **Step 3: Create `frontend/src/pages/HistoryPage.module.css`**

```css
.loading,
.error,
.empty {
  font-family: var(--font-mono);
  color: var(--ink-soft);
}

.error {
  color: var(--red-data);
}

.headerRow {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1rem;
}

.exportButton {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--ink);
  background: transparent;
  border: 1px solid var(--line-strong);
  padding: 0.5rem 0.9rem;
  border-radius: 3px;
  cursor: pointer;
}

.exportButton:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1.5rem;
  font-size: 0.9rem;
}

.table th,
.table td {
  text-align: left;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid var(--line);
}

.table th {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
```

- [ ] **Step 4: Implement `frontend/src/pages/HistoryPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { exportHistory, getHistory, type HistoryRow } from "../api/client";
import AccuracyChart from "../components/AccuracyChart";
import styles from "./HistoryPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; history: HistoryRow[] };

export default function HistoryPage() {
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
        <h2>Round history</h2>
        <button onClick={handleExport} className={styles.exportButton}>
          Export CSV
        </button>
      </div>

      {exportError && <p className={styles.error}>{exportError}</p>}

      {state.history.length === 0 ? (
        <p className={styles.empty}>No rounds completed yet.</p>
      ) : (
        <>
          <AccuracyChart history={state.history} />
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

- [ ] **Step 5: Wire the real route in `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="recommend" element={<RecommendationsPage />} />
          <Route path="history" element={<HistoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `HistoryPage.test.tsx` — 4 passed, plus everything from Tasks
1-4 (App's own smoke test may need re-checking — it renders `/` only,
unaffected by these route changes).

- [ ] **Step 7: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/HistoryPage.tsx frontend/src/pages/HistoryPage.test.tsx frontend/src/pages/HistoryPage.module.css
git commit -m "Add HistoryPage and wire the /history route"
```

---

### Task 6: End-to-end verification + docs

**Files:**
- Modify: `CLAUDE.md`
- No new tests — this task verifies the complete session lifecycle works
  end-to-end (create → recommend → submit results → dashboard/history
  reflect it → export) against the real backend in a real browser, the
  same way Phase 1's final task did.

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd frontend && npm test`
Expected: all tests pass — roughly 12 (Phase 1) + 8 (Task 1) + 9 (Task
2: 7 chartData + 2 AccuracyChart) + 4 (Task 3) + 3 (Task 4) + 4 (Task 5)
= approximately 40 total. Confirm the actual printed count rather than
assuming this estimate is exact.

- [ ] **Step 2: Run the backend test suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: 221 passed (this plan touches nothing under `acquireml/`).

- [ ] **Step 3: Manually verify the complete lifecycle in a real browser**

Clear any existing local sessions first: `rm -rf ~/.acquireml/sessions`

In one terminal: `make api` (backend on :8000)
In another: `cd frontend && npm run dev` (frontend on :5173)

Drive through the full loop:
1. Create a session with a labeled CSV and an unlabeled pool CSV (both
   required this time, unlike Phase 1's verification — the pool is what
   makes `recommend` work).
2. From the session list, click into the new session — lands on the
   Dashboard, shows Round 0, correct known/pool counts, "No rounds
   completed yet" instead of a chart.
3. Click "Recommendations" — shows a ranked batch. Select 0/1 for a few
   rows, leave others blank, submit.
4. Confirm it navigates back to the Dashboard and now shows Round 1,
   an updated accuracy stat, and a chart with one data point.
5. Click "History" — shows the same round in a table, plus the chart.
   Click "Export CSV" — confirm a file downloads.

If anything fails, treat it as a real bug to root-cause (per
systematic-debugging), not something to patch around — this is the
first time these three pages are exercised against the real backend
rather than mocked tests.

- [ ] **Step 4: Clean up test artifacts**

`rm -rf ~/.acquireml/sessions`, remove any test CSV files created for
this verification, stop both dev servers.

- [ ] **Step 5: Update CLAUDE.md**

In the existing "**Web UI frontend**" paragraph (added by Phase 1, under
"## Session Module Design"), update the sentence describing current
scope:

Find:
```
Currently covers session list + creation
(`SessionListPage`, `NewSessionPage`) — dashboard, recommendations, and
history are a follow-up plan.
```

Replace with:
```
Covers the full session lifecycle: list, create, dashboard
(`DashboardPage`, with an interactive accuracy/cost chart via Recharts),
recommendations with inline results-entry (`RecommendationsPage`), and
history with CSV export (`HistoryPage`). Session-scoped pages live under
`/sessions/:name` (nested routes via `SessionLayout`), mirroring the
backend's own URL structure.
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "Document the completed web UI frontend session lifecycle in CLAUDE.md"
```

- [ ] **Step 7: Report readiness**

Summarize for the user: final test counts (frontend + backend), confirmation
the full manual lifecycle (create → recommend → submit → dashboard/history
update → export) worked end-to-end against the real backend, and that
the web UI's originally-planned 5 pages are now all complete.
