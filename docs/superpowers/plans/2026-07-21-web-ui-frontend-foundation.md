# Web UI Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the React frontend's toolchain, visual identity, and typed
API client, then build the first two real pages — the session list and the
new-session creation form — against the now-real, tested backend API. This
is the first of (at least) two frontend plans; Dashboard, Recommendations,
and History are deferred to a follow-up plan once this phase is real and
demoable, mirroring how the backend was split into "get the API real" before
the frontend was ever planned in detail.

**Architecture:** A new `frontend/` directory (sibling to `acquireml/`) —
Vite + React + TypeScript, no server-side rendering, talks to the FastAPI
backend (`acquireml/api/app.py`, already built) over local HTTP at
`http://localhost:8000`. `src/api/client.ts` is the single place that knows
the backend's URL and response shapes — every page imports typed functions
from it, never calls `fetch` directly. `src/styles/tokens.css` carries the
exact Noir & Gold design tokens already established for the landing page
(`docs/index.html`), so the app is visually continuous with it. `react-router-dom`
provides two routes: `/` (session list) and `/new` (creation form).

**Tech Stack:** React 18, TypeScript 5, Vite 5 (dev server + bundler),
react-router-dom 6 (routing), Vitest + React Testing Library + jsdom
(component tests — the frontend's equivalent of pytest). No CSS framework —
plain CSS + CSS Modules, reusing the existing Noir & Gold token system
rather than introducing Tailwind or a component library. No HTTP client
library — native `fetch`, wrapped in one typed module, is sufficient at
this scope (avoids an unneeded axios dependency).

## Global Constraints

- The backend (`acquireml/api/app.py`, already built and merged to `main`)
  is not touched by this plan — this is a pure frontend consumer.
- `src/api/client.ts` is the only file that constructs a URL or calls
  `fetch` — every page/component goes through its exported functions. This
  mirrors the backend's own `store.py` trust-boundary pattern: one place
  that owns "how do we reach the backend," everything else consumes it.
- Response shapes in `client.ts`'s TypeScript types must exactly match the
  backend's Pydantic schemas (`acquireml/api/schemas.py`) — field names,
  optionality (`| null` for Python's `Optional`/`| None` fields), and
  types. Cross-check against the real schema file, not against memory of
  what it "should" be.
- Design tokens in `frontend/src/styles/tokens.css` must exactly match the
  Noir & Gold values already committed in `docs/index.html` — same hex
  values for `--paper`, `--ink`, `--accent`, `--brass`, etc. This is a
  continuation of an existing visual identity, not a fresh design pass.
- `frontend/node_modules/` and `frontend/dist/` must be gitignored —
  neither should ever be committed.
- Every component gets at least one test verifying real rendered behavior
  (React Testing Library queries against rendered output), not
  implementation details (no snapshot tests, no testing internal state
  directly).

---

### Task 1: Vite + React + TypeScript scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/.gitignore`
- Modify: `.gitignore` (repo root — only if `frontend/` needs an entry beyond its own `.gitignore`; it doesn't, since `frontend/.gitignore` covers `frontend/node_modules/` and `frontend/dist/` on its own. No repo-root change needed — confirmed in Step 6 below.)

**Interfaces:**
- Produces: a working `npm run dev` (Vite dev server), `npm run build`
  (production bundle), `npm test` (Vitest) — later tasks add to `App.tsx`
  and add new files under `src/`, but the toolchain itself doesn't change
  after this task.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "acquireml-web-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Create `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
```

- [ ] **Step 5: Create `frontend/src/test-setup.ts`**

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 6: Create `frontend/.gitignore`**

```
node_modules/
dist/
```

No change to the repo-root `.gitignore` is needed — `frontend/.gitignore`
covers everything under `frontend/` on its own; git applies `.gitignore`
files relative to the directory they live in.

- [ ] **Step 7: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AcquireML</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 8: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 9: Create `frontend/src/App.tsx`** (minimal placeholder — Task 4 replaces this with real routing)

```tsx
export default function App() {
  return <div>AcquireML</div>;
}
```

- [ ] **Step 10: Write the failing smoke test**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders without crashing", () => {
    render(<App />);
    expect(screen.getByText("AcquireML")).toBeInTheDocument();
  });
});
```

- [ ] **Step 11: Install dependencies**

Run: `cd frontend && npm install`
Expected: installs cleanly, creates `frontend/node_modules/` and
`frontend/package-lock.json`.

- [ ] **Step 12: Run the test to verify it passes**

Run: `cd frontend && npm test`
Expected: `App.test.tsx` — 1 passed.

- [ ] **Step 13: Verify the dev server boots**

Run: `cd frontend && npm run dev` (in the background — e.g. append `&` or
run in a separate terminal), then `curl -s http://localhost:5173/ | grep -o "AcquireML"`
Expected: prints `AcquireML` (confirms the Vite dev server serves the
page and the React app mounts). Stop the dev server afterward.

- [ ] **Step 14: Commit**

```bash
git add frontend/
git commit -m "Scaffold frontend: Vite + React + TypeScript + Vitest"
```

---

### Task 2: Design tokens — Noir & Gold, ported from the landing page

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/global.css`
- Modify: `frontend/index.html` (add Google Fonts link)
- Modify: `frontend/src/main.tsx` (import global.css)

**Interfaces:**
- Produces: CSS custom properties (`--paper`, `--paper-raised`, `--ink`,
  `--ink-soft`, `--ink-faint`, `--accent`, `--accent-bright`, `--brass`,
  `--red-data`, `--line`, `--line-strong`) available globally to every
  component from Task 4 onward, plus base typography/reset rules.

- [ ] **Step 1: Add the Google Fonts link to `frontend/index.html`**

Update the `<head>`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Cormorant:wght@600;700&family=Manrope:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />
    <title>AcquireML</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

This is a normal `<link>` tag pulling from Google's CDN — unlike the
static landing page (`docs/index.html`), which had to inline fonts as
base64 data URIs because it's served through a strict-CSP artifact
renderer, a real app has no such restriction, so there's no reason to
carry that complexity here.

- [ ] **Step 2: Create `frontend/src/styles/tokens.css`**

Exact same values as `docs/index.html`'s Noir & Gold theme — do not
invent new ones:

```css
:root {
  --paper: #14110e;
  --paper-raised: #1e1913;
  --ink: #ede6d6;
  --ink-soft: #b7ac94;
  --ink-faint: #8a8069;
  --accent: #c9a24b;
  --accent-bright: #e0bd6c;
  --brass: #9c7a3e;
  --red-data: #a6534c;
  --line: #332c21;
  --line-strong: #4a4030;
  --shadow: 0 4px 24px rgba(0, 0, 0, 0.45);

  --font-display: "Cormorant", Georgia, serif;
  --font-body: "Manrope", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", monospace;
}
```

- [ ] **Step 3: Create `frontend/src/styles/global.css`**

```css
@import "./tokens.css";

* {
  box-sizing: border-box;
}

html {
  -webkit-text-size-adjust: 100%;
}

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

h1,
h2,
h3 {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--ink);
}

a {
  color: var(--accent);
}

button {
  font-family: var(--font-mono);
}
```

- [ ] **Step 4: Import `global.css` in `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 5: Verify the existing test still passes**

Run: `cd frontend && npm test`
Expected: `App.test.tsx` — 1 passed (CSS changes don't affect this test,
confirming nothing broke).

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/src/styles/ frontend/src/main.tsx
git commit -m "Add Noir & Gold design tokens, ported from the landing page"
```

---

### Task 3: Typed API client

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `API_BASE_URL: string`, and typed async functions —
  `listSessions(): Promise<SessionSummary[]>`,
  `createSession(input: CreateSessionInput): Promise<SessionCreateResponse>`
  — plus the TypeScript interfaces `SessionSummary` and
  `SessionCreateResponse`, `CreateSessionInput`. Task 4 imports
  `listSessions`/`SessionSummary`; Task 5 imports `createSession`/
  `CreateSessionInput`/`SessionCreateResponse`. Later frontend plans
  (status/history/recommend/update/reset/export/delete) extend this same
  file with more functions — nothing about its shape needs to change for
  that, it's additive.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/api/client.test.ts`:

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createSession, listSessions } from "./client";

describe("listSessions", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches from /sessions and returns parsed JSON", async () => {
    const mockSessions = [
      {
        name: "azm-project",
        current_round: 2,
        n_known: 45,
        n_pool: 55,
        n_pending: 0,
        latest_accuracy: 0.93,
      },
    ];
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessions,
    });

    const result = await listSessions();

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/sessions");
    expect(result).toEqual(mockSessions);
  });

  it("throws with the response detail when the request fails", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "something broke" }),
    });

    await expect(listSessions()).rejects.toThrow("something broke");
  });
});

describe("createSession", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts multipart form data to /sessions", async () => {
    const mockResponse = {
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
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const labeledFile = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
    const result = await createSession({
      name: "azm-project",
      labelCol: "outcome",
      labeledFile,
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("http://localhost:8000/sessions");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect(result).toEqual(mockResponse);
  });

  it("throws with the response detail on a 409 (duplicate name)", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Session already exists at ..." }),
    });

    const labeledFile = new File(["a,b\n1,2"], "labeled.csv", { type: "text/csv" });
    await expect(
      createSession({ name: "azm-project", labelCol: "outcome", labeledFile })
    ).rejects.toThrow("Session already exists at ...");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL with a module-not-found error for `./client`.

- [ ] **Step 3: Implement `frontend/src/api/client.ts`**

Field names and types below mirror `acquireml/api/schemas.py` exactly —
cross-check against that file if anything looks ambiguous.

```typescript
export const API_BASE_URL = "http://localhost:8000";

export interface SessionSummary {
  name: string;
  current_round: number;
  n_known: number;
  n_pool: number;
  n_pending: number;
  latest_accuracy: number | null;
}

export interface SessionCreateResponse {
  name: string;
  n_known: number;
  n_pool: number;
  label_col: string;
  patience: number;
  min_delta: number;
  cost_per_sample: number | null;
  diversity_weight: number;
  model: string;
  calibrate: boolean;
  calibration_method: string;
}

export interface CreateSessionInput {
  name: string;
  labelCol: string;
  labeledFile: File;
  poolFile?: File;
  model?: string;
  patience?: number;
  minDelta?: number;
  costPerSample?: number;
  diversityWeight?: number;
  calibrate?: boolean;
  calibrationMethod?: string;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
  } catch {
    // response body wasn't JSON — fall through to the generic message
  }
  return `Request failed with status ${response.status}`;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const response = await fetch(`${API_BASE_URL}/sessions`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function createSession(
  input: CreateSessionInput
): Promise<SessionCreateResponse> {
  const form = new FormData();
  form.set("name", input.name);
  form.set("label_col", input.labelCol);
  form.set("labeled_file", input.labeledFile);
  if (input.poolFile) form.set("pool_file", input.poolFile);
  if (input.model) form.set("model", input.model);
  if (input.patience !== undefined) form.set("patience", String(input.patience));
  if (input.minDelta !== undefined) form.set("min_delta", String(input.minDelta));
  if (input.costPerSample !== undefined) form.set("cost_per_sample", String(input.costPerSample));
  if (input.diversityWeight !== undefined) form.set("diversity_weight", String(input.diversityWeight));
  if (input.calibrate !== undefined) form.set("calibrate", String(input.calibrate));
  if (input.calibrationMethod) form.set("calibration_method", input.calibrationMethod);

  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}
```

Note: `fetch` with a `FormData` body must NOT have a `Content-Type`
header set manually — the browser sets it automatically, including the
multipart boundary string. This is why `createSession` never sets one;
setting it explicitly is a common mistake that breaks multipart uploads.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `client.test.ts` — 4 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/
git commit -m "Add typed API client: listSessions, createSession"
```

---

### Task 4: Routing shell + SessionListPage

**Files:**
- Modify: `frontend/src/App.tsx` (replace placeholder with real routing)
- Modify: `frontend/src/App.test.tsx` (update for the new App shape)
- Create: `frontend/src/pages/SessionListPage.tsx`
- Create: `frontend/src/pages/SessionListPage.test.tsx`
- Create: `frontend/src/pages/SessionListPage.module.css`

**Interfaces:**
- Consumes: `listSessions`, `SessionSummary` from `frontend/src/api/client.ts` (Task 3).
- Produces: `App` renders a `BrowserRouter` with two routes:
  `/` → `SessionListPage`, `/new` → a placeholder until Task 5 replaces
  it with the real `NewSessionPage`. `SessionListPage` is a named export
  reused as-is once Task 5 wires the real route.

- [ ] **Step 1: Add `react-router-dom`'s testing utilities are already installed — write the failing tests**

Create `frontend/src/pages/SessionListPage.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import SessionListPage from "./SessionListPage";

describe("SessionListPage", () => {
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
        <SessionListPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("azm-project")).toBeInTheDocument();
    });
    expect(screen.getByText(/round 2/i)).toBeInTheDocument();
    expect(screen.getByText(/93/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no sessions", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);

    render(
      <MemoryRouter>
        <SessionListPage />
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
        <SessionListPage />
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
        <SessionListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /new session/i })).toHaveAttribute(
        "href",
        "/new"
      );
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL with a module-not-found error for `./SessionListPage`.

- [ ] **Step 3: Create `frontend/src/pages/SessionListPage.module.css`**

```css
.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 3rem 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2rem;
}

.newLink {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  text-decoration: none;
  color: var(--paper);
  background: var(--accent);
  padding: 0.6rem 1rem;
  border-radius: 3px;
}

.newLink:hover {
  background: var(--accent-bright);
}

.sessionCard {
  display: block;
  padding: 1.2rem 1.4rem;
  margin-bottom: 0.8rem;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  border-radius: 4px;
}

.sessionName {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--ink);
}

.sessionMeta {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--ink-faint);
  margin-top: 0.3rem;
}

.empty,
.error,
.loading {
  font-family: var(--font-mono);
  color: var(--ink-soft);
}

.error {
  color: var(--red-data);
}
```

- [ ] **Step 4: Implement `frontend/src/pages/SessionListPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionSummary } from "../api/client";
import styles from "./SessionListPage.module.css";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; sessions: SessionSummary[] };

export default function SessionListPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

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
        <Link to="/new" className={styles.newLink}>
          New session
        </Link>
      </div>

      {state.status === "loading" && <p className={styles.loading}>Loading…</p>}

      {state.status === "error" && <p className={styles.error}>{state.message}</p>}

      {state.status === "loaded" && state.sessions.length === 0 && (
        <p className={styles.empty}>No sessions yet — create one to get started.</p>
      )}

      {state.status === "loaded" &&
        state.sessions.map((session) => (
          <div key={session.name} className={styles.sessionCard}>
            <div className={styles.sessionName}>{session.name}</div>
            <div className={styles.sessionMeta}>
              Round {session.current_round} · {session.n_known} known ·{" "}
              {session.n_pool} in pool
              {session.latest_accuracy !== null &&
                ` · ${(session.latest_accuracy * 100).toFixed(1)}% accuracy`}
            </div>
          </div>
        ))}
    </div>
  );
}
```

- [ ] **Step 5: Replace `frontend/src/App.tsx` with real routing**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<div>New session (coming in Task 5)</div>} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Update `frontend/src/App.test.tsx`** (the old test asserted on placeholder text that no longer exists)

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as client from "./api/client";
import App from "./App";

describe("App", () => {
  it("renders the session list at the root route", async () => {
    vi.spyOn(client, "listSessions").mockResolvedValue([]);
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `SessionListPage.test.tsx` — 4 passed, `App.test.tsx` — 1 passed.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/pages/
git commit -m "Add routing shell and SessionListPage"
```

---

### Task 5: NewSessionPage

**Files:**
- Modify: `frontend/src/App.tsx` (wire the real `/new` route)
- Create: `frontend/src/pages/NewSessionPage.tsx`
- Create: `frontend/src/pages/NewSessionPage.test.tsx`
- Create: `frontend/src/pages/NewSessionPage.module.css`

**Interfaces:**
- Consumes: `createSession`, `CreateSessionInput` from
  `frontend/src/api/client.ts` (Task 3).
- Produces: `NewSessionPage`, a form that collects a session name, label
  column, a required labeled-data file, an optional pool file, and
  submits via `createSession`. On success, navigates to `/` (the session
  list) — the dashboard it would ideally navigate to instead doesn't
  exist until the next frontend plan.

  Deliberate scope trim: this form does NOT expose the advanced config
  fields `createSession`/`CreateSessionInput` already support (`model`,
  `patience`, `minDelta`, `costPerSample`, `diversityWeight`,
  `calibrate`, `calibrationMethod`) — they're left unset, so the backend
  applies its own defaults (`rf`, patience 3, min_delta 0.005, no cost
  tracking, no diversity, no calibration), exactly matching what
  `acquireml session init` defaults to on the CLI. Exposing them is a
  reasonable next addition, but keeping the first form to only what's
  required to create a working session keeps this task reviewable on its
  own. Not an oversight — `CreateSessionInput` already has the fields
  ready for whenever a form field is added for each.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/NewSessionPage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import NewSessionPage from "./NewSessionPage";

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

describe("NewSessionPage", () => {
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
        <NewSessionPage />
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
        <NewSessionPage />
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
        <NewSessionPage />
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

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL with a module-not-found error for `./NewSessionPage`.

- [ ] **Step 3: Create `frontend/src/pages/NewSessionPage.module.css`**

```css
.container {
  max-width: 560px;
  margin: 0 auto;
  padding: 3rem 2rem;
}

.field {
  margin-bottom: 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field label {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.field input[type="text"],
.field input[type="file"] {
  background: var(--paper-raised);
  border: 1px solid var(--line);
  color: var(--ink);
  padding: 0.6rem 0.8rem;
  border-radius: 3px;
  font-family: var(--font-body);
  font-size: 0.95rem;
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

.validationError {
  color: var(--red-data);
  font-size: 0.85rem;
  margin-top: 0.3rem;
}

.submitError {
  color: var(--red-data);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  margin-top: 1rem;
}
```

- [ ] **Step 4: Implement `frontend/src/pages/NewSessionPage.tsx`**

```tsx
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createSession } from "../api/client";
import styles from "./NewSessionPage.module.css";

export default function NewSessionPage() {
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
      navigate("/");
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
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="labelCol">Label column</label>
          <input
            id="labelCol"
            type="text"
            value={labelCol}
            onChange={(e) => setLabelCol(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="labeledFile">Labeled data file</label>
          <input
            id="labeledFile"
            type="file"
            onChange={(e) => setLabeledFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="poolFile">Unlabeled pool file (optional)</label>
          <input
            id="poolFile"
            type="file"
            onChange={(e) => setPoolFile(e.target.files?.[0] ?? null)}
          />
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

- [ ] **Step 5: Wire the real route in `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: `NewSessionPage.test.tsx` — 3 passed, plus all prior test
files still passing.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/NewSessionPage.tsx frontend/src/pages/NewSessionPage.test.tsx frontend/src/pages/NewSessionPage.module.css
git commit -m "Add NewSessionPage and wire the /new route"
```

---

### Task 6: End-to-end manual verification + docs

**Files:**
- Modify: `CLAUDE.md`
- No new tests — this task verifies the frontend and backend actually
  work together end-to-end (not just each side's own mocked tests) and
  documents how to run both.

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd frontend && npm test`
Expected: all frontend tests pass (App, SessionListPage, NewSessionPage,
client — roughly 12-13 tests total across the 4 files added in this plan).

- [ ] **Step 2: Run the backend test suite (confirm nothing regressed there)**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: 221 passed (this plan touches nothing under `acquireml/`, so
this is a sanity check, not expected to change).

- [ ] **Step 3: Manually verify the frontend and backend talk to each other**

In one terminal: `make api` (starts the backend on port 8000)
In another terminal: `cd frontend && npm run dev` (starts the frontend
dev server, typically port 5173)

Open `http://localhost:5173` in a browser. Expected: "No sessions yet"
(assuming a fresh `~/.acquireml/sessions/`). Click "New session," fill
in a name, label column, and a small CSV file, submit. Expected:
redirected to `/`, and the new session now appears in the list with
"Round 0" and the correct known-sample count.

If this manual check fails (e.g. a CORS error in the browser console),
check that the backend's CORS middleware in `acquireml/api/app.py`
allows `http://localhost:5173` — it already should, from the backend
plan's Task 3, but confirm rather than assume.

- [ ] **Step 4: Update CLAUDE.md**

Add a new subsection right after the existing "**Web UI backend**"
paragraph (added by the backend plan, under "## Session Module Design"):

```markdown

**Web UI frontend** (`frontend/`): React + TypeScript + Vite, talking to
the backend at `http://localhost:8000`. `src/api/client.ts` is the sole
place that knows the backend's URL and response shapes. `src/styles/tokens.css`
carries the same Noir & Gold design tokens as the landing page
(`docs/index.html`). Currently covers session list + creation
(`SessionListPage`, `NewSessionPage`) — dashboard, recommendations, and
history are a follow-up plan. Run with `npm run dev` from `frontend/`
(needs the backend running too — see `make api`). Test with `npm test`
from `frontend/`.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "Document the web UI frontend in CLAUDE.md"
```

- [ ] **Step 6: Report readiness**

Summarize for the user: frontend test count, confirmation the backend
suite is still green, confirmation the manual end-to-end check passed
(session list + creation actually work against the real backend in a
browser), and that dashboard/recommendations/history are the natural
next frontend plan once this one is reviewed.
