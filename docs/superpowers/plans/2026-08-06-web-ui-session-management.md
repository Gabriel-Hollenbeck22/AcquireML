# Web UI Session Management & Portfolio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Session Settings page (edit/reset/delete), turn the flat session list into a sortable Portfolio view, add a Cost & Budget projection page, and add a Cmd+K command palette — completing Phase 4 of the web UI.

**Architecture:** One new backend endpoint (`PATCH /sessions/{name}/settings`) backed by a new `Session.update_settings()` method, following the exact validation/persistence pattern `Session.init()` already uses. Everything else is frontend-only: two new routes (`/sessions/:name/settings`, `/sessions/:name/budget`) under the existing `SessionLayout`, an upgraded `SessionListPage`, and a new `CommandPalette` mounted once in `AppShell`. Pure logic (sorting, cost projection, command filtering) is factored into standalone, independently-tested files, matching the `chartData.ts` precedent from the visual overhaul phase.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest (backend). React 18, TypeScript 5 (strict), Vite 5, Vitest 2 + React Testing Library 16, React Router 6 (backend/frontend as established in prior phases).

## Global Constraints

- Backend test suite (`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q` from repo root) must report 221 passed before this plan's backend work starts, and grow by exactly the new tests each backend task adds — no existing test may be modified to make this plan's work pass.
- Frontend test suite (`npm test -- --run` from `frontend/`) must report 47 passed before this plan's frontend work starts, and grow by exactly the new tests each frontend task adds.
- `npx tsc --noEmit` (from `frontend/`) must stay clean throughout.
- New backend fields follow the exact snake_case-in-Python / camelCase-in-TypeScript mirroring discipline already established: Pydantic schema field names match `Session` dict keys exactly; `client.ts` interfaces use camelCase and each function maps camelCase input to the snake_case wire format before sending.
- No changes to Phases 1-3's existing pages' data/interaction logic beyond what's explicitly listed in a task below (e.g. `SessionLayout` gaining a status fetch is in-scope; `DashboardPage`'s internals are not).
- Every destructive action (reset, delete) must go through a `window.confirm` before calling its endpoint — no destructive action fires on a single click.
- Every task's `git add` must be scoped to the exact files that task changed — never `git add -A` / `git add .`. (Prior phases on this project had real incidents where an unscoped add swept in unrelated leftover files; this constraint is not boilerplate.)
- Per `CLAUDE.md`: before the final task reports done, the dev server must be run and every new/changed page clicked through in a real browser — this is not optional polish.

---

### Task 1: Backend — `Session.update_settings()`

**Files:**
- Modify: `acquireml/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Produces: `Session.update_settings(patience: Optional[int] = None, min_delta: Optional[float] = None, cost_per_sample: Optional[float] = None, diversity_weight: Optional[float] = None, model: Optional[str] = None, calibrate: Optional[bool] = None, calibration_method: Optional[str] = None) -> dict` — returns `self.status()`'s full dict (Task 2's endpoint relies on this exact return shape to build its `StatusResponse`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_session.py`, in a new `# ── update_settings ──` section placed after the existing `# ── reset ──` section (i.e. near the end of the file, following the file's existing section-comment convention):

```python
# ── update_settings ──────────────────────────────────────────────────────────

def test_update_settings_changes_patience(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", patience=3)

    result = sess.update_settings(patience=5)

    assert result["patience"] == 5
    assert sess.status()["patience"] == 5
    sess.close()


def test_update_settings_changes_multiple_fields_at_once(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome")

    result = sess.update_settings(min_delta=0.01, cost_per_sample=2.5, diversity_weight=0.3)

    assert result["min_delta"] == 0.01
    assert result["cost_per_sample"] == 2.5
    assert result["diversity_weight"] == 0.3
    sess.close()


def test_update_settings_leaves_unspecified_fields_unchanged(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", patience=3, min_delta=0.005)

    sess.update_settings(patience=7)

    # min_delta wasn't in this call, so it should still be the init() value
    assert sess.status()["min_delta"] == 0.005
    sess.close()


def test_update_settings_changes_model(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", model="rf")

    result = sess.update_settings(model="gbm")

    assert result["model"] == "gbm"
    sess.close()


def test_update_settings_rejects_unknown_model(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome")

    with pytest.raises(ValueError, match="Unknown model"):
        sess.update_settings(model="not_a_real_model")
    sess.close()


def test_update_settings_rejects_unknown_calibration_method(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome")

    with pytest.raises(ValueError, match="Unknown calibration method"):
        sess.update_settings(calibration_method="platt")
    sess.close()


def test_update_settings_rejects_invalid_before_applying_valid(tmp_path, labeled_csv):
    """A call mixing a valid and an invalid field should apply nothing —
    not partially update patience and then raise on the bad model name."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", patience=3)

    with pytest.raises(ValueError, match="Unknown model"):
        sess.update_settings(patience=99, model="not_a_real_model")

    assert sess.status()["patience"] == 3
    sess.close()


def test_update_settings_changes_calibrate_flag(tmp_path, labeled_csv):
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", calibrate=False)

    result = sess.update_settings(calibrate=True)

    assert result["calibrate"] is True
    sess.close()


def test_update_settings_no_args_is_a_noop(tmp_path, labeled_csv):
    """Calling with no arguments changes nothing and doesn't raise."""
    db = tmp_path / "s.db"
    sess = Session(db)
    sess.init(labeled_csv, label_col="outcome", patience=3)

    result = sess.update_settings()

    assert result["patience"] == 3
    sess.close()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k update_settings -v`
Expected: FAIL — `AttributeError: 'Session' object has no attribute 'update_settings'` on every test.

- [ ] **Step 3: Implement `update_settings`**

In `acquireml/session.py`, add this method immediately after `init()` (i.e. after the closing of `init()`'s method body, before `def recommend(`):

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
    (same shape as `status()`'s return).

    Validates before applying anything: an invalid `model` or
    `calibration_method` raises before any field (including valid ones
    passed in the same call) is written to meta.
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

Note the two validation `if` statements both run before any `_set_meta` call — this is what makes `test_update_settings_rejects_invalid_before_applying_valid` pass; do not reorder validation and mutation.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_session.py -k update_settings -v`
Expected: `9 passed`.

- [ ] **Step 5: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: `230 passed` (221 + 9 new).

- [ ] **Step 6: Commit**

```bash
git add acquireml/session.py tests/test_session.py
git commit -m "Add Session.update_settings() for in-place settings edits"
```

---

### Task 2: Backend — `PATCH /sessions/{name}/settings` endpoint

**Files:**
- Modify: `acquireml/api/schemas.py`
- Modify: `acquireml/api/app.py`
- Test: `tests/test_api_schemas.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `Session.update_settings(**kwargs) -> dict` from Task 1.
- Produces: `PATCH /sessions/{name}/settings` — request body `UpdateSettingsRequest`, response `StatusResponse` (reused from the existing schema, not a new type). This is the endpoint Task 3's frontend client function calls.

- [ ] **Step 1: Add the `UpdateSettingsRequest` schema**

In `acquireml/api/schemas.py`, add after the existing `ResetResponse` class (end of file):

```python
class UpdateSettingsRequest(BaseModel):
    """Body for PATCH /sessions/{name}/settings. All fields optional —
    only provided (non-None) ones are changed."""
    patience: int | None = None
    min_delta: float | None = None
    cost_per_sample: float | None = None
    diversity_weight: float | None = None
    model: str | None = None
    calibrate: bool | None = None
    calibration_method: str | None = None
```

- [ ] **Step 2: Write the schema test**

Add to `tests/test_api_schemas.py` (find the existing test file's pattern — it constructs each schema class with sample data and asserts field values; follow that exact pattern for the new class):

```python
def test_update_settings_request_all_fields_optional():
    body = UpdateSettingsRequest()
    assert body.patience is None
    assert body.model_dump(exclude_none=True) == {}


def test_update_settings_request_accepts_partial_fields():
    body = UpdateSettingsRequest(patience=5, cost_per_sample=2.5)
    assert body.model_dump(exclude_none=True) == {"patience": 5, "cost_per_sample": 2.5}
```

Add `UpdateSettingsRequest` to that file's existing `from acquireml.api.schemas import (...)` import list at the top.

- [ ] **Step 3: Run the schema tests**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_schemas.py -k update_settings -v`
Expected: `2 passed`.

- [ ] **Step 4: Add the endpoint**

In `acquireml/api/app.py`, add immediately after the existing `reset` endpoint (`@app.post("/sessions/{name}/reset", ...)`), before `@app.get("/sessions/{name}/export")`:

```python
@app.patch("/sessions/{name}/settings", response_model=StatusResponse)
def update_settings(
    body: UpdateSettingsRequest, sess: Session = Depends(get_session)
) -> StatusResponse:
    with sess:
        result = sess.update_settings(**body.model_dump(exclude_none=True))
        return StatusResponse(**result)
```

Add `UpdateSettingsRequest` to `app.py`'s existing `from acquireml.api.schemas import (...)` import list at the top of the file (find the existing multi-line import and add this name to it, matching its current formatting).

- [ ] **Step 5: Write the endpoint tests**

Add to `tests/test_api_app.py`, after `test_reset_clears_rounds` (reuse the file's existing `_create_session` / `client` / `labeled_csv` fixtures — do not redefine them):

```python
def test_update_settings_changes_patience(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.patch("/sessions/azm-project/settings", json={"patience": 7})
    assert resp.status_code == 200
    assert resp.json()["patience"] == 7

    status = client.get("/sessions/azm-project/status").json()
    assert status["patience"] == 7


def test_update_settings_partial_body_leaves_other_fields(client, labeled_csv):
    _create_session(client, labeled_csv)

    client.patch("/sessions/azm-project/settings", json={"min_delta": 0.02})

    status = client.get("/sessions/azm-project/status").json()
    assert status["min_delta"] == 0.02
    assert status["patience"] == 3  # untouched, still the init() default


def test_update_settings_rejects_unknown_model(client, labeled_csv):
    _create_session(client, labeled_csv)

    resp = client.patch("/sessions/azm-project/settings", json={"model": "not_a_real_model"})
    assert resp.status_code == 400


def test_update_settings_unknown_session_404s(client):
    resp = client.patch("/sessions/nope/settings", json={"patience": 5})
    assert resp.status_code == 404
```

- [ ] **Step 6: Run the endpoint tests**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k update_settings -v`
Expected: `4 passed`.

- [ ] **Step 7: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: `236 passed` (230 from Task 1 + 6 new: 2 schema + 4 endpoint).

- [ ] **Step 8: Commit**

```bash
git add acquireml/api/schemas.py acquireml/api/app.py tests/test_api_schemas.py tests/test_api_app.py
git commit -m "Add PATCH /sessions/{name}/settings endpoint"
```

---

### Task 3: Frontend — API client additions

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: `PATCH /sessions/{name}/settings` and existing `POST /sessions/{name}/reset`, `DELETE /sessions/{name}` endpoints (reset/delete endpoints already exist and are already tested server-side; this task only adds the missing client-side wrappers for them, following the exact pattern already used for every other endpoint in this file).
- Produces: `updateSettings(name, input: UpdateSettingsInput): Promise<StatusResponse>`, `resetSession(name): Promise<ResetResponse>`, `deleteSession(name): Promise<void>`, and the `ResetResponse`/`UpdateSettingsInput` TypeScript interfaces — Task 4's `SettingsPage` imports all three functions directly from `client.ts`.

- [ ] **Step 1: Add the `ResetResponse` interface and the three functions**

In `frontend/src/api/client.ts`, add the interface near the other response interfaces (e.g. right after `UpdateResponse`):

```typescript
export interface ResetResponse {
  n_known: number;
  n_pool: number;
  rounds_cleared: number;
}

export interface UpdateSettingsInput {
  patience?: number;
  minDelta?: number;
  costPerSample?: number;
  diversityWeight?: number;
  model?: string;
  calibrate?: boolean;
  calibrationMethod?: string;
}
```

Add the three functions after `exportHistory` (the last function currently in the file):

```typescript
export async function updateSettings(
  name: string,
  input: UpdateSettingsInput
): Promise<StatusResponse> {
  const body: Record<string, string | number | boolean> = {};
  if (input.patience !== undefined) body.patience = input.patience;
  if (input.minDelta !== undefined) body.min_delta = input.minDelta;
  if (input.costPerSample !== undefined) body.cost_per_sample = input.costPerSample;
  if (input.diversityWeight !== undefined) body.diversity_weight = input.diversityWeight;
  if (input.model !== undefined) body.model = input.model;
  if (input.calibrate !== undefined) body.calibrate = input.calibrate;
  if (input.calibrationMethod !== undefined) body.calibration_method = input.calibrationMethod;

  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function resetSession(name: string): Promise<ResetResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}/reset`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function deleteSession(name: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
}
```

Note `deleteSession` returns `Promise<void>` and does not call `response.json()` — the backend's `DELETE` endpoint returns `204 No Content` with an empty body (confirmed by the existing `test_delete_removes_session` backend test asserting `status_code == 204`), so calling `.json()` on it would throw on the empty body.

- [ ] **Step 2: Write the tests**

Find `frontend/src/api/client.test.ts` and follow its existing pattern exactly (each test mocks global `fetch` via `vi.fn()`, asserts the request URL/method/body, and asserts the parsed response). Add:

```typescript
describe("updateSettings", () => {
  it("sends only the provided fields as snake_case JSON", async () => {
    const mockResponse = { name: "proj", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.9, patience: 7, min_delta: 0.005, cost_per_sample: null, total_cost: null, diversity_weight: 0, model: "rf", calibrate: false, calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await updateSettings("proj", { patience: 7 });

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/sessions/proj/settings`,
      expect.objectContaining({
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patience: 7 }),
      })
    );
    expect(result).toEqual(mockResponse);
  });

  it("throws with the parsed error detail on failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Unknown model 'bad'." }),
    });

    await expect(updateSettings("proj", { model: "bad" })).rejects.toThrow("Unknown model 'bad'.");
  });
});

describe("resetSession", () => {
  it("posts to the reset endpoint and returns the parsed response", async () => {
    const mockResponse = { n_known: 20, n_pool: 30, rounds_cleared: 2 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await resetSession("proj");

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/sessions/proj/reset`,
      expect.objectContaining({ method: "POST" })
    );
    expect(result).toEqual(mockResponse);
  });
});

describe("deleteSession", () => {
  it("sends a DELETE request and resolves without parsing a body", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true });

    await expect(deleteSession("proj")).resolves.toBeUndefined();

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/sessions/proj`,
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("throws with the parsed error detail on failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "No session named 'proj'." }),
    });

    await expect(deleteSession("proj")).rejects.toThrow("No session named 'proj'.");
  });
});
```

Add `updateSettings`, `resetSession`, `deleteSession` to this test file's existing import line from `./client`.

- [ ] **Step 3: Run the new tests**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: all tests in the file pass, including the 6 new ones above.

- [ ] **Step 4: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `52 passed (52)` (47 + 5 new — the brief's Step 2 code contains 5 `it(...)` blocks, not 6; verify against the actual count in the test file rather than this number if anything looks off).

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "Add updateSettings, resetSession, deleteSession to the API client"
```

---

### Task 4: Frontend — `SettingsPage` + route + nav link

**Files:**
- Create: `frontend/src/pages/SettingsPage.tsx`
- Create: `frontend/src/pages/SettingsPage.module.css`
- Create: `frontend/src/pages/SettingsPage.test.tsx`
- Modify: `frontend/src/components/SessionLayout.tsx`
- Modify: `frontend/src/components/SessionLayout.module.css`
- Modify: `frontend/src/components/SessionLayout.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getStatus`, `updateSettings`, `resetSession`, `deleteSession` from `client.ts` (Task 3). `MODEL_CHOICES`/`CALIBRATION_METHODS`-equivalent hardcoded arrays (the frontend has no shared source for these — mirror the backend's `("rf", "gbm", "lr", "svm")` and `("sigmoid", "isotonic")` as local constants in `SettingsPage.tsx`, matching how `NewSessionPage`... — check `NewSessionPage.tsx` first: if it already hardcodes a model list for its own form, reuse the exact same literal values for consistency, but do not import across page files — each page owns its own copy, matching this codebase's existing pattern of no cross-page imports between pages).
- Produces: nothing later tasks in this plan depend on directly, except that `SessionLayout` gains a `getStatus` fetch this task introduces, which Task 6 (Budget's conditional nav link) builds on directly — read Task 6's brief before starting Task 6 to see exactly how it extends the code this task writes.

**Design note on `SessionLayout`'s new fetch:** `SessionLayout` currently renders synchronously — no loading state, just `{name}` from `useParams`. This task adds a `getStatus(name)` fetch on mount so the nav can decide whether to show a "Settings" link (always) — wait, re-read the design spec: Settings is **always** shown regardless of status; only **Budget** (Task 6) is conditional on `cost_per_sample`. So this task's `SessionLayout` change fetches status **in preparation for** Task 6's conditional link, but Task 4 itself only needs to add the unconditional "Settings" nav link — the status fetch could be deferred to Task 6 instead. **Resolution: add the status fetch in this task anyway** (not Task 6), because `SettingsPage` itself will fetch status independently for its own form data regardless — but `SessionLayout`'s fetch is a separate, smaller one (just for the nav's conditional Budget link) and doing it now means Task 6 only has to read a value that's already there, not restructure `SessionLayout` a second time. `SessionLayout` should NOT block rendering `<Outlet />` on this fetch — the nav's Budget link simply appears once the fetch resolves (or never, if `cost_per_sample` is null); Dashboard/Recommendations/History/Settings must all be immediately clickable with no spinner gating them.

- [ ] **Step 1: Write the failing `SessionLayout` test additions**

Read the current `frontend/src/components/SessionLayout.test.tsx` in full first (it already has 3 tests from the visual overhaul phase — mono label, active-link tests). Add two new tests to it, reusing its existing `renderAt` helper:

```typescript
describe("SessionLayout settings/budget nav", () => {
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

    renderAt("/sessions/azm-project");

    expect(await screen.findByRole("link", { name: "Settings" })).toBeInTheDocument();
  });

  it("does not show a Budget link when cost_per_sample is null", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      name: "azm-project", current_round: 1, n_known: 10, n_pool: 5, n_pending: 0,
      latest_accuracy: 0.9, patience: 3, min_delta: 0.005, cost_per_sample: null,
      total_cost: null, diversity_weight: 0, model: "rf", calibrate: false,
      calibration_method: "sigmoid", should_stop: false, stop_reason: "", created_at: null,
    });

    renderAt("/sessions/azm-project");

    await screen.findByRole("link", { name: "Settings" }); // wait for the fetch to resolve
    expect(screen.queryByRole("link", { name: "Budget" })).not.toBeInTheDocument();
  });
});
```

This test file needs `import * as client from "../api/client";` added if not already present (check first — other test files in this project already follow this `vi.spyOn(client, ...)` pattern, `SessionLayout.test.tsx` may not need it yet since it currently renders synchronously with no fetch).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/SessionLayout.test.tsx`
Expected: FAIL — no "Settings" link exists yet, `getStatus` is never called.

- [ ] **Step 3: Update `SessionLayout.tsx`**

```tsx
import { useEffect, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { getStatus, type StatusResponse } from "../api/client";
import styles from "./SessionLayout.module.css";

export default function SessionLayout() {
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
          <NavLink
            to={`/sessions/${name}/settings`}
            className={({ isActive }) => (isActive ? styles.active : undefined)}
          >
            Settings
          </NavLink>
          {status?.cost_per_sample !== null && status?.cost_per_sample !== undefined && (
            <NavLink
              to={`/sessions/${name}/budget`}
              className={({ isActive }) => (isActive ? styles.active : undefined)}
            >
              Budget
            </NavLink>
          )}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Run the `SessionLayout` tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/SessionLayout.test.tsx`
Expected: `5 passed` (3 existing + 2 new).

- [ ] **Step 5: Check `NewSessionPage.tsx` for an existing model-choices list**

Run: `grep -n "rf\|gbm\|sigmoid\|isotonic" frontend/src/pages/NewSessionPage.tsx`

If it already has a model/calibration-method `<select>` with hardcoded options, copy its exact option values and labels verbatim into `SettingsPage.tsx` for consistency (same wording researchers already see when creating a session). If `NewSessionPage.tsx` has no such controls (it may only expose the fields the visual overhaul phase's spec described — check what actually exists, don't assume), use these literal values in `SettingsPage.tsx`: models `rf` ("Random Forest"), `gbm` ("Gradient Boosting"), `lr` ("Logistic Regression"), `svm` ("SVM"); calibration methods `sigmoid` ("Sigmoid"), `isotonic` ("Isotonic").

- [ ] **Step 6: Write `SettingsPage.tsx`**

```tsx
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  deleteSession,
  getStatus,
  resetSession,
  updateSettings,
  type StatusResponse,
} from "../api/client";
import styles from "./SettingsPage.module.css";

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

export default function SettingsPage() {
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
      navigate("/");
    } catch (err) {
      setDangerError((err as Error).message);
      setDangerBusy(false);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <h2>Settings</h2>
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
        <div className={styles.field}>
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

- [ ] **Step 7: Write `SettingsPage.module.css`**

Follow the exact token/spacing conventions already established in `NewSessionPage.module.css` and `RecommendationsPage.module.css` (read both first — this page's `.form`/`.field`/`.submit` classes should look visually consistent with those, reusing `var(--font-mono)` for labels, `var(--paper-raised)`/`var(--line)` for inputs, `var(--accent-deep)`/`var(--accent)` for the submit button per the visual-overhaul phase's token rename). Add a `.dangerZone` class bordered in `var(--red-data)` with reduced-emphasis spacing (a `border-top` separator, `margin-top`, distinct from the form above it), and `.dangerButton` styled as an outlined (not filled) button using `var(--red-data)` for its border/text, consistent with how `HistoryPage.module.css`'s `.exportButton` is an outlined secondary action (same pattern, different color).

- [ ] **Step 8: Write `SettingsPage.test.tsx`**

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import SettingsPage from "./SettingsPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/settings`]}>
      <Routes>
        <Route path="/sessions/:name/settings" element={<SettingsPage />} />
        <Route path="/" element={<div>Session list placeholder</div>} />
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

describe("SettingsPage", () => {
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

- [ ] **Step 9: Run the `SettingsPage` tests**

Run: `cd frontend && npx vitest run src/pages/SettingsPage.test.tsx`
Expected: `5 passed`.

- [ ] **Step 10: Wire the route into `App.tsx`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";

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
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
```

(The `budget` route is added in Task 6, not here — do not add it now.)

- [ ] **Step 11: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: `59 passed (59)` — 52 from Task 3's actual end state (corrected from this plan's original miscounted "53" — Task 3's brief had 5 new tests, not 6), plus exactly the new `it(...)` blocks this task added: 2 in Step 1 (`SessionLayout`'s new nav tests) + 5 in Step 8 (`SettingsPage.test.tsx`). Verify the actual reported number matches 59 rather than trusting this arithmetic blindly — if it doesn't, something in the diff added or removed a test this plan didn't account for, and that's worth investigating before moving on.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 12: Manually verify in the browser**

`npm run dev` (frontend) + `make api` (backend, repo root, separate terminal). Open a session (use `acquireml demo --init` if needed), click "Settings" in the nav, confirm the form pre-fills with real values, change patience and save, confirm the success message appears and the value persists on reload. Click "Reset session" and confirm a browser confirm dialog appears before anything happens; cancel it. Do NOT actually click through a real delete during this check (it's destructive and this session may be reused by later tasks) — just confirm the confirm-dialog appears, then cancel. Stop both servers when done.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx frontend/src/pages/SettingsPage.module.css \
  frontend/src/pages/SettingsPage.test.tsx frontend/src/components/SessionLayout.tsx \
  frontend/src/components/SessionLayout.module.css frontend/src/components/SessionLayout.test.tsx \
  frontend/src/App.tsx
git commit -m "Add SettingsPage: edit settings, reset, delete"
```

---

### Task 5: Frontend — Portfolio-ify `SessionListPage`

**Files:**
- Create: `frontend/src/pages/sessionSort.ts`
- Create: `frontend/src/pages/sessionSort.test.ts`
- Modify: `frontend/src/pages/SessionListPage.tsx`
- Modify: `frontend/src/pages/SessionListPage.module.css`
- Modify: `frontend/src/pages/SessionListPage.test.tsx`

**Interfaces:**
- Produces: `sortSessions(sessions: SessionSummary[], by: SortKey): SessionSummary[]` where `type SortKey = "name" | "round" | "accuracy" | "known"` — pure function, does not mutate its input array.

- [ ] **Step 1: Write the failing test for `sortSessions`**

Create `frontend/src/pages/sessionSort.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { sortSessions } from "./sessionSort";
import type { SessionSummary } from "../api/client";

const sessions: SessionSummary[] = [
  { name: "beta", current_round: 3, n_known: 20, n_pool: 5, n_pending: 0, latest_accuracy: 0.8 },
  { name: "alpha", current_round: 1, n_known: 50, n_pool: 5, n_pending: 0, latest_accuracy: null },
  { name: "gamma", current_round: 5, n_known: 10, n_pool: 5, n_pending: 0, latest_accuracy: 0.95 },
];

describe("sortSessions", () => {
  it("sorts by name alphabetically", () => {
    expect(sortSessions(sessions, "name").map((s) => s.name)).toEqual(["alpha", "beta", "gamma"]);
  });

  it("sorts by round descending", () => {
    expect(sortSessions(sessions, "round").map((s) => s.name)).toEqual(["gamma", "beta", "alpha"]);
  });

  it("sorts by known count descending", () => {
    expect(sortSessions(sessions, "known").map((s) => s.name)).toEqual(["alpha", "beta", "gamma"]);
  });

  it("sorts by accuracy descending, with null accuracy sorted last regardless of direction", () => {
    expect(sortSessions(sessions, "accuracy").map((s) => s.name)).toEqual(["gamma", "beta", "alpha"]);
  });

  it("does not mutate the input array", () => {
    const original = [...sessions];
    sortSessions(sessions, "name");
    expect(sessions).toEqual(original);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/sessionSort.test.ts`
Expected: FAIL — module `./sessionSort` doesn't exist.

- [ ] **Step 3: Implement `sessionSort.ts`**

```typescript
import type { SessionSummary } from "../api/client";

export type SortKey = "name" | "round" | "accuracy" | "known";

export function sortSessions(sessions: SessionSummary[], by: SortKey): SessionSummary[] {
  const copy = [...sessions];
  switch (by) {
    case "name":
      return copy.sort((a, b) => a.name.localeCompare(b.name));
    case "round":
      return copy.sort((a, b) => b.current_round - a.current_round);
    case "known":
      return copy.sort((a, b) => b.n_known - a.n_known);
    case "accuracy":
      return copy.sort((a, b) => {
        if (a.latest_accuracy === null && b.latest_accuracy === null) return 0;
        if (a.latest_accuracy === null) return 1;
        if (b.latest_accuracy === null) return -1;
        return b.latest_accuracy - a.latest_accuracy;
      });
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/sessionSort.test.ts`
Expected: `5 passed`.

- [ ] **Step 5: Update `SessionListPage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionSummary } from "../api/client";
import { sortSessions, type SortKey } from "./sessionSort";
import styles from "./SessionListPage.module.css";

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

export default function SessionListPage() {
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
        <Link to="/new" className={styles.newLink}>
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

      {state.status === "loaded" &&
        sortSessions(state.sessions, sortBy).map((session) => (
          <Link
            key={session.name}
            to={`/sessions/${session.name}`}
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
  );
}
```

- [ ] **Step 6: Update `SessionListPage.module.css`**

Add `.sortRow` (a small flex row above the cards, `label` in `var(--font-mono)` matching other form labels in this app, `select` styled consistently with `SettingsPage`'s selects from Task 4), `.statRow`/`.stat`/`.statValue`/`.statLabel` (reuse the exact visual pattern already established in `DashboardPage.module.css`'s `.statRow`/`.stat`/`.statValue`/`.statLabel` from the visual-overhaul phase — same spacing/sizing scaled down slightly since these sit inside a card rather than being the page's headline stats; e.g. `font-size: 1.1rem` instead of Dashboard's `1.5rem` for `.statValue`), and `.highAccuracy` (a `color: var(--accent)` + subtle `background: rgba(224, 189, 108, 0.12)` chip, `border-radius: 4px`, `padding: 0 4px` — small enough to read as a highlight, not a badge). Remove the now-unused `.sessionMeta` rule (the old single-line prose format it styled is gone from the JSX above) — confirm via `grep -n sessionMeta` across `frontend/src/` that nothing else references it before deleting.

- [ ] **Step 7: Update `SessionListPage.test.tsx`**

Read the existing test file first — it currently asserts on the old prose-line format (e.g. `screen.getByText(/round 2/i)` or similar single-line text). Update any assertion that checked the old `.sessionMeta` prose line to instead check the new stat values render as separate elements (e.g. `screen.getByText("2")` scoped appropriately, or check for the accuracy percentage text directly, following this project's established RTL query patterns from `DashboardPage.test.tsx`). Add one new test:

```typescript
it("sorts sessions when the sort dropdown changes", async () => {
  vi.spyOn(client, "listSessions").mockResolvedValue([
    { name: "zeta", current_round: 1, n_known: 5, n_pool: 5, n_pending: 0, latest_accuracy: null },
    { name: "alpha", current_round: 1, n_known: 5, n_pool: 5, n_pending: 0, latest_accuracy: null },
  ]);
  render(
    <MemoryRouter>
      <SessionListPage />
    </MemoryRouter>
  );

  const links = await screen.findAllByRole("link", { name: /zeta|alpha/ });
  // default sort is "name" — alpha should come before zeta
  expect(links[0]).toHaveTextContent("alpha");
});
```

(Adjust the exact query to match however this test file already queries session card links — check the existing "renders session cards" test for the established pattern before adding this one, to stay consistent rather than introducing a new querying style.)

- [ ] **Step 8: Run the `SessionListPage` tests**

Run: `cd frontend && npx vitest run src/pages/SessionListPage.test.tsx`
Expected: all pass (existing tests updated + 1 new).

- [ ] **Step 9: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: previous count (59, from Task 4) + 5 (`sessionSort.test.ts`) + 1 (`SessionListPage`'s new sort test) = `65 passed (65)`. As in Task 4, verify this against the actual reported number rather than trusting the arithmetic blindly — the exact baseline depends on Task 4's real final count.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 10: Manually verify in the browser**

`npm run dev` + `make api`. On the session list, confirm each card now shows four small stats instead of one prose line, high-accuracy sessions (>=90%) show a highlighted accuracy chip, and changing the "Sort by" dropdown reorders the cards. Stop both servers when done.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/pages/sessionSort.ts frontend/src/pages/sessionSort.test.ts \
  frontend/src/pages/SessionListPage.tsx frontend/src/pages/SessionListPage.module.css \
  frontend/src/pages/SessionListPage.test.tsx
git commit -m "Turn the session list into a sortable portfolio view"
```

---

### Task 6: Frontend — `BudgetPage`

**Files:**
- Create: `frontend/src/pages/costProjection.ts`
- Create: `frontend/src/pages/costProjection.test.ts`
- Create: `frontend/src/pages/BudgetPage.tsx`
- Create: `frontend/src/pages/BudgetPage.module.css`
- Create: `frontend/src/pages/BudgetPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getHistory`, `getStatus` from `client.ts`. `SessionLayout`'s conditional "Budget" nav link (already added in Task 4) — this task does not need to touch `SessionLayout.tsx` again, only add the route it links to.
- Produces: `fitLinearTrend(points: {cost: number; accuracy: number}[]): {slope: number; intercept: number} | null` (returns `null` when fewer than 2 points), `projectCostForTarget(trend: {slope, intercept}, currentCost: number, targetAccuracy: number): number | null` (returns `null` when the trend's slope is `<= 0`, since a flat-or-declining accuracy-vs-cost trend cannot be projected forward to a higher target — this is the "insufficient/bad data" case the design spec calls out).

- [ ] **Step 1: Write the failing tests for `costProjection.ts`**

Create `frontend/src/pages/costProjection.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { fitLinearTrend, projectCostForTarget } from "./costProjection";

describe("fitLinearTrend", () => {
  it("returns null with fewer than 2 points", () => {
    expect(fitLinearTrend([])).toBeNull();
    expect(fitLinearTrend([{ cost: 10, accuracy: 0.8 }])).toBeNull();
  });

  it("fits an exact line through collinear points", () => {
    // accuracy = 0.5 + 0.01 * cost
    const points = [
      { cost: 0, accuracy: 0.5 },
      { cost: 10, accuracy: 0.6 },
      { cost: 20, accuracy: 0.7 },
    ];
    const trend = fitLinearTrend(points);
    expect(trend).not.toBeNull();
    expect(trend!.slope).toBeCloseTo(0.01, 5);
    expect(trend!.intercept).toBeCloseTo(0.5, 5);
  });
});

describe("projectCostForTarget", () => {
  it("projects additional cost needed to reach a target accuracy", () => {
    // accuracy = 0.5 + 0.01 * cost → to reach 0.9, need cost = 40
    const trend = { slope: 0.01, intercept: 0.5 };
    const result = projectCostForTarget(trend, 20, 0.9);
    expect(result).toBeCloseTo(20, 5); // 40 total - 20 already spent = 20 more
  });

  it("returns null when the trend is flat or declining", () => {
    expect(projectCostForTarget({ slope: 0, intercept: 0.8 }, 10, 0.9)).toBeNull();
    expect(projectCostForTarget({ slope: -0.01, intercept: 0.9 }, 10, 0.95)).toBeNull();
  });

  it("returns 0 (or negative-clamped-to-0) when the target is already met", () => {
    const trend = { slope: 0.01, intercept: 0.5 };
    // at cost=20, projected accuracy = 0.7, target 0.6 is already exceeded
    const result = projectCostForTarget(trend, 20, 0.6);
    expect(result).toBe(0);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/pages/costProjection.test.ts`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement `costProjection.ts`**

```typescript
export interface CostPoint {
  cost: number;
  accuracy: number;
}

export interface LinearTrend {
  slope: number;
  intercept: number;
}

/** Ordinary least-squares fit of accuracy as a function of cumulative cost. */
export function fitLinearTrend(points: CostPoint[]): LinearTrend | null {
  const n = points.length;
  if (n < 2) return null;

  const sumX = points.reduce((acc, p) => acc + p.cost, 0);
  const sumY = points.reduce((acc, p) => acc + p.accuracy, 0);
  const meanX = sumX / n;
  const meanY = sumY / n;

  let numerator = 0;
  let denominator = 0;
  for (const p of points) {
    numerator += (p.cost - meanX) * (p.accuracy - meanY);
    denominator += (p.cost - meanX) ** 2;
  }
  if (denominator === 0) return null; // all points at the same cost — no meaningful slope

  const slope = numerator / denominator;
  const intercept = meanY - slope * meanX;
  return { slope, intercept };
}

/**
 * Additional cost (beyond currentCost) needed to reach targetAccuracy,
 * based on a fitted linear trend. Returns null if the trend can't reach
 * the target (flat or declining slope) — never returns a negative
 * "additional cost beyond what's already met" value below 0.
 */
export function projectCostForTarget(
  trend: LinearTrend,
  currentCost: number,
  targetAccuracy: number
): number | null {
  if (trend.slope <= 0) return null;
  const totalCostForTarget = (targetAccuracy - trend.intercept) / trend.slope;
  const additional = totalCostForTarget - currentCost;
  return Math.max(0, additional);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/costProjection.test.ts`
Expected: `6 passed`.

- [ ] **Step 5: Write `BudgetPage.tsx`**

```tsx
import { useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { getHistory, getStatus, type HistoryRow, type StatusResponse } from "../api/client";
import { fitLinearTrend, projectCostForTarget, type CostPoint } from "./costProjection";
import styles from "./BudgetPage.module.css";

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

export default function BudgetPage() {
  const { name } = useParams<{ name: string }>();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [targetAccuracy, setTargetAccuracy] = useState("0.95");

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
  const parsedTarget = Number(targetAccuracy);
  const projected =
    trend !== null && !Number.isNaN(parsedTarget)
      ? projectCostForTarget(trend, currentCost, parsedTarget)
      : null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    // state derives targetAccuracy reactively — nothing to do beyond
    // preventing the native form submit/page reload.
  }

  return (
    <div>
      <h2>Cost &amp; budget projection</h2>
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
          <svg viewBox="0 0 400 200" width="100%" height="200" className={styles.chart}>
            <BudgetChartBody points={points} trend={trend} currentCost={currentCost} projectedCost={projected} targetAccuracy={parsedTarget} />
          </svg>

          <form onSubmit={handleSubmit} className={styles.form}>
            <label htmlFor="targetAccuracy">Target accuracy</label>
            <input
              id="targetAccuracy"
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={targetAccuracy}
              onChange={(e) => setTargetAccuracy(e.target.value)}
            />
          </form>

          {trend !== null && trend.slope <= 0 && (
            <p className={styles.empty}>
              Accuracy isn't trending upward with cost yet — projection isn't meaningful
              until it is.
            </p>
          )}
          {projected !== null && (
            <p className={styles.projection}>
              Projected additional spend to reach {(parsedTarget * 100).toFixed(0)}%:{" "}
              <strong>${projected.toFixed(2)}</strong>
            </p>
          )}
        </>
      )}
    </div>
  );
}

function BudgetChartBody({
  points,
  trend,
  currentCost,
  projectedCost,
  targetAccuracy,
}: {
  points: CostPoint[];
  trend: ReturnType<typeof fitLinearTrend>;
  currentCost: number;
  projectedCost: number | null;
  targetAccuracy: number;
}) {
  const maxCost = Math.max(...points.map((p) => p.cost), currentCost + (projectedCost ?? 0));
  const xScale = (cost: number) => 20 + (cost / (maxCost || 1)) * 360;
  const yScale = (accuracy: number) => 180 - accuracy * 160;

  const realPath = points.map((p) => `${xScale(p.cost)},${yScale(p.accuracy)}`).join(" ");

  const projectedTargetCost =
    projectedCost !== null ? currentCost + projectedCost : null;

  return (
    <>
      <polyline points={realPath} fill="none" stroke="var(--accent)" strokeWidth={2} />
      {points.map((p, i) => (
        <circle key={i} cx={xScale(p.cost)} cy={yScale(p.accuracy)} r={3} fill="var(--accent)" />
      ))}
      {trend !== null && projectedTargetCost !== null && (
        <>
          <line
            x1={xScale(currentCost)}
            y1={yScale(trend.slope * currentCost + trend.intercept)}
            x2={xScale(projectedTargetCost)}
            y2={yScale(targetAccuracy)}
            stroke="var(--brass)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
          <circle cx={xScale(projectedTargetCost)} cy={yScale(targetAccuracy)} r={4} fill="var(--brass)" />
        </>
      )}
    </>
  );
}
```

- [ ] **Step 6: Write `BudgetPage.module.css`**

Follow the visual pattern already established: `.statRow`/`.stat`/`.statValue`/`.statLabel` reuse the same styling as `DashboardPage.module.css` (import the same visual language — card background `var(--paper-raised)`, border `var(--line)`, hover lock-on treatment is optional here since these aren't interactive, plain display is fine). `.chart` gets a card wrapper matching `AccuracyChart.module.css`'s `.card` (background/border/padding, but this task creates its own standalone card rather than importing that CSS module — copy the visual values, don't import cross-component). `.form` reuses the label/input styling from `SettingsPage.module.css` (Task 4) for consistency. `.empty` and `.error` reuse `var(--ink-soft)`/`var(--red-data)` per the app-wide convention. `.projection` should be visually emphasized (larger font, `var(--accent)` for the dollar figure via a nested `strong` selector).

- [ ] **Step 7: Write `BudgetPage.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import BudgetPage from "./BudgetPage";

function renderAtSession(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${name}/budget`]}>
      <Routes>
        <Route path="/sessions/:name/budget" element={<BudgetPage />} />
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

describe("BudgetPage", () => {
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

  it("shows an error message when a request fails", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("No session named 'x'."));
    vi.spyOn(client, "getHistory").mockResolvedValue([]);

    renderAtSession("x");

    expect(await screen.findByText(/no session named/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Run the `BudgetPage` tests**

Run: `cd frontend && npx vitest run src/pages/BudgetPage.test.tsx`
Expected: `3 passed`.

- [ ] **Step 9: Wire the `budget` route into `App.tsx`**

Add `import BudgetPage from "./pages/BudgetPage";` and, inside the `/sessions/:name` route's children, add `<Route path="budget" element={<BudgetPage />} />` after the `settings` route added in Task 4.

- [ ] **Step 10: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: previous count (65, from Task 5) + 5 (`costProjection.test.ts` — its Step 1 code contains 5 `it(...)` blocks, not 6 as earlier drafts of this plan estimated) + 3 (`BudgetPage.test.tsx`) = `73 passed (73)`. Verify against the actual reported total.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 11: Manually verify in the browser**

`npm run dev` + `make api`. Use (or create) a session with `cost_per_sample` set and at least 2 completed rounds — if you don't have one handy, create a fresh session through the UI with a cost-per-sample value set, then run Recommend→submit twice. Confirm the "Budget" nav link appears (it shouldn't for cost-less sessions — spot check by opening a session with no cost tracking and confirming the link is absent). On the Budget page, confirm the chart renders, changing the target-accuracy input updates the projection text, and setting an already-met target shows a `$0.00` projection rather than a negative number. Stop both servers when done.

- [ ] **Step 12: Commit**

```bash
git add frontend/src/pages/costProjection.ts frontend/src/pages/costProjection.test.ts \
  frontend/src/pages/BudgetPage.tsx frontend/src/pages/BudgetPage.module.css \
  frontend/src/pages/BudgetPage.test.tsx frontend/src/App.tsx
git commit -m "Add BudgetPage: cost/accuracy trend and target-accuracy projection"
```

---

### Task 7: Frontend — Command palette (Cmd+K)

**Files:**
- Create: `frontend/src/components/commandFilter.ts`
- Create: `frontend/src/components/commandFilter.test.ts`
- Create: `frontend/src/components/CommandPalette.tsx`
- Create: `frontend/src/components/CommandPalette.module.css`
- Create: `frontend/src/components/CommandPalette.test.tsx`
- Modify: `frontend/src/components/AppShell.tsx`
- Modify: `frontend/src/components/AppShell.module.css`

**Interfaces:**
- Produces: `filterCommands(commands: Command[], query: string): Command[]` where `interface Command { id: string; label: string; action: () => void }` — pure function, case-insensitive substring match, matches sorted before non-matches are excluded (not just filtered — order matters for keyboard navigation, earlier substring match position sorts first).

- [ ] **Step 1: Write the failing tests for `commandFilter.ts`**

Create `frontend/src/components/commandFilter.test.ts`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { filterCommands, type Command } from "./commandFilter";

function makeCommands(labels: string[]): Command[] {
  return labels.map((label, i) => ({ id: String(i), label, action: vi.fn() }));
}

describe("filterCommands", () => {
  it("returns all commands when the query is empty", () => {
    const commands = makeCommands(["Dashboard", "History", "Settings"]);
    expect(filterCommands(commands, "")).toHaveLength(3);
  });

  it("filters case-insensitively by substring", () => {
    const commands = makeCommands(["Dashboard", "History", "Settings"]);
    expect(filterCommands(commands, "hist").map((c) => c.label)).toEqual(["History"]);
    expect(filterCommands(commands, "DASH").map((c) => c.label)).toEqual(["Dashboard"]);
  });

  it("excludes commands with no match", () => {
    const commands = makeCommands(["Dashboard", "History"]);
    expect(filterCommands(commands, "budget")).toHaveLength(0);
  });

  it("sorts earlier substring matches before later ones", () => {
    const commands = makeCommands(["My Dashboard", "Dashboard Overview"]);
    // "Dashboard" appears at index 3 in "My Dashboard" but index 0 in "Dashboard Overview"
    expect(filterCommands(commands, "dashboard").map((c) => c.label)).toEqual([
      "Dashboard Overview",
      "My Dashboard",
    ]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/components/commandFilter.test.ts`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement `commandFilter.ts`**

```typescript
export interface Command {
  id: string;
  label: string;
  action: () => void;
}

export function filterCommands(commands: Command[], query: string): Command[] {
  const trimmed = query.trim().toLowerCase();
  if (trimmed === "") return commands;

  return commands
    .map((cmd) => ({ cmd, index: cmd.label.toLowerCase().indexOf(trimmed) }))
    .filter(({ index }) => index !== -1)
    .sort((a, b) => a.index - b.index)
    .map(({ cmd }) => cmd);
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/components/commandFilter.test.ts`
Expected: `4 passed`.

- [ ] **Step 5: Write `CommandPalette.tsx`**

```tsx
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { listSessions } from "../api/client";
import { filterCommands, type Command } from "./commandFilter";
import styles from "./CommandPalette.module.css";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [sessionNames, setSessionNames] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelectedIndex(0);
    listSessions()
      .then((sessions) => setSessionNames(sessions.map((s) => s.name)))
      .catch(() => setSessionNames([]));
  }, [open]);

  const currentSessionName = useMemo(() => {
    const match = location.pathname.match(/^\/sessions\/([^/]+)/);
    return match ? match[1] : null;
  }, [location.pathname]);

  const commands = useMemo<Command[]>(() => {
    const go = (path: string) => () => {
      navigate(path);
      onClose();
    };
    const list: Command[] = [
      { id: "new-session", label: "New session", action: go("/new") },
      ...sessionNames.map((name) => ({
        id: `go-${name}`,
        label: `Go to session: ${name}`,
        action: go(`/sessions/${name}`),
      })),
    ];
    if (currentSessionName) {
      list.push(
        { id: "cur-dashboard", label: "Dashboard", action: go(`/sessions/${currentSessionName}`) },
        { id: "cur-recommend", label: "Recommendations", action: go(`/sessions/${currentSessionName}/recommend`) },
        { id: "cur-history", label: "History", action: go(`/sessions/${currentSessionName}/history`) },
        { id: "cur-settings", label: "Settings", action: go(`/sessions/${currentSessionName}/settings`) },
        { id: "cur-budget", label: "Budget", action: go(`/sessions/${currentSessionName}/budget`) }
      );
    }
    return list;
  }, [sessionNames, currentSessionName, navigate, onClose]);

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

- [ ] **Step 6: Write `CommandPalette.module.css`**

`.backdrop`: fixed, full-viewport, `background: rgba(0, 0, 0, 0.6)`, centers its child, `z-index: 100` (comfortably above `AppShell.module.css`'s existing values — only `.content` sets one, at `z-index: 1`, so `100` is unambiguously on top). `.palette`: `var(--paper-raised)` background, `var(--line-strong)` border, `var(--shadow)` token, rounded corners, a fixed max-width (e.g. `480px`) centered near the top third of the viewport (not dead-center — matches how command palettes conventionally sit slightly above center). `.input`: full-width, `var(--font-body)`, no border (the palette's own border is enough framing), larger font size than normal body text (e.g. `1.1rem`) since it's the primary input. `.list`: scrollable if long (`max-height`, `overflow-y: auto`), each `li` padded and clickable (`cursor: pointer`). `.selected`: `background: var(--paper)` or similar to visually distinguish the keyboard-selected row from unselected ones. `.noResults`: `var(--ink-faint)`, no hover/pointer styling since it's not clickable.

- [ ] **Step 7: Write `CommandPalette.test.tsx`**

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import CommandPalette from "./CommandPalette";

describe("CommandPalette", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <MemoryRouter>
        <CommandPalette open={false} onClose={vi.fn()} />
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
        <CommandPalette open={true} onClose={vi.fn()} />
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
        <CommandPalette open={true} onClose={vi.fn()} />
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
        <CommandPalette open={true} onClose={onClose} />
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
        <CommandPalette open={true} onClose={onClose} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/jump to/i)).toBeInTheDocument();
    });
    fireEvent.click(container.firstChild as Element);

    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 8: Run the `CommandPalette` tests**

Run: `cd frontend && npx vitest run src/components/CommandPalette.test.tsx`
Expected: `5 passed`.

- [ ] **Step 9: Wire `CommandPalette` into `AppShell.tsx`**

```tsx
import { useEffect, useState, type ReactNode } from "react";
import { useCursorGlow } from "../hooks/useCursorGlow";
import CommandPalette from "./CommandPalette";
import styles from "./AppShell.module.css";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { onMouseMove } = useCursorGlow();
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
    <div className={styles.shell} onMouseMove={onMouseMove}>
      <div className={styles.scan} />
      <div className={styles.content}>{children}</div>
      <button
        type="button"
        className={styles.paletteHint}
        onClick={() => setPaletteOpen(true)}
        aria-label="Open command palette"
      >
        ⌘K
      </button>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
```

Note: `CommandPalette` uses `useNavigate`/`useLocation` internally, which requires a Router context — since `AppShell` is already rendered inside `<BrowserRouter>` in `App.tsx` (confirm this is still true — `AppShell` wraps `<Routes>`, and `BrowserRouter` wraps `AppShell`), this works without any prop threading.

- [ ] **Step 10: Add `.paletteHint` to `AppShell.module.css`**

A small fixed-position chip (e.g. `position: fixed; bottom: 16px; right: 16px;`), `var(--paper-raised)` background, `var(--line-strong)` border, `var(--font-mono)`, `var(--ink-faint)` text that brightens to `var(--accent)` on hover, `cursor: pointer`, `z-index: 10` — above `.content`'s `z-index: 1` so the chip is always clickable, below `CommandPalette`'s `.backdrop` at `z-index: 100` so the palette overlays it when open.

- [ ] **Step 11: Update `AppShell.test.tsx` if it exists**

Check `frontend/src/components/AppShell.test.tsx` — if the visual-overhaul phase created one, confirm it still passes given the new button/CommandPalette addition (it likely only checked that children render, which is unaffected). If it doesn't exist, no action needed — `App.test.tsx` already renders `AppShell` as part of the full app and will exercise this.

- [ ] **Step 12: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test -- --run`
Expected: previous count (from Task 6) + 4 (`commandFilter.test.ts`) + 5 (`CommandPalette.test.tsx`) = 9 new. Verify against the actual reported total — note `App.test.tsx`'s existing single test (rendering the full app at `/`) must still pass with `CommandPalette` mounted; if `listSessions` isn't mocked in that test and `CommandPalette` fetches it unconditionally on open (it doesn't — it only fetches when `open` becomes `true`, and `paletteOpen` defaults to `false`), this should not be an issue, but confirm `npm test -- --run` is clean, not just this file in isolation.

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 13: Manually verify in the browser**

`npm run dev` + `make api`. On any page, press Cmd+K (or Ctrl+K on non-Mac) and confirm the palette opens with a text input focused. Type part of a session name and confirm it filters. Press Escape and confirm it closes. Click the "⌘K" hint chip in the corner and confirm it also opens the palette. Navigate into a session, open the palette, and confirm session-scoped commands (Dashboard/Recommendations/History/Settings/Budget) appear. Use arrow keys + Enter to navigate to one and confirm it actually navigates. Stop both servers when done.

- [ ] **Step 14: Commit**

```bash
git add frontend/src/components/commandFilter.ts frontend/src/components/commandFilter.test.ts \
  frontend/src/components/CommandPalette.tsx frontend/src/components/CommandPalette.module.css \
  frontend/src/components/CommandPalette.test.tsx frontend/src/components/AppShell.tsx \
  frontend/src/components/AppShell.module.css
git commit -m "Add Cmd+K command palette for session/page navigation"
```

---

### Task 8: Full regression pass, browser walkthrough, docs

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run the full frontend suite**

Run: `cd frontend && npm test -- --run`
Expected: passes cleanly. Record the exact total reported — this is the real number to use in Step 5's docs update, not any number estimated earlier in this plan.

- [ ] **Step 2: Run the typecheck and production build**

Run: `cd frontend && npm run build`
Expected: succeeds.

- [ ] **Step 3: Run the full backend suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q` (from repo root)
Expected: `236 passed` (per Task 2's Step 7 — confirm this is still accurate; it should be, since no backend work happens after Task 2).

- [ ] **Step 4: Full browser walkthrough of everything this plan added**

`npm run dev` + `make api`. Using a real or `acquireml demo --init` session:
- Session list: confirm the sortable portfolio view (Task 5) — cards show four stats, sorting works, high-accuracy chip appears where applicable.
- Settings page: edit and save a value, confirm it persists; open the reset/delete confirms and cancel both (do not actually delete the session you're using for the rest of this walkthrough).
- Budget page: on a session with cost tracking and 2+ rounds, confirm the projection renders and responds to the target-accuracy input; on a session without cost tracking, confirm the "Budget" nav link is absent entirely.
- Command palette: Cmd+K / Ctrl+K opens it, typing filters, arrow keys + Enter navigate, Escape and backdrop-click both close it.
- Spot-check that nothing from Phases 1-3 regressed: Dashboard, Recommendations (full create→recommend→submit→dashboard-update lifecycle), History + CSV export all still work exactly as before.

Stop both servers when done.

- [ ] **Step 5: Update `CLAUDE.md`**

Find the existing "**Web UI frontend**" paragraph (search for that exact heading text) and extend it (do not replace its existing content) with a description of what this phase added: the Settings page (edit/reset/delete, backed by the new `PATCH /sessions/{name}/settings` endpoint), the Portfolio-ified session list (sortable, per-session stat cards), the Budget page (cost/accuracy trend projection, conditionally shown), and the Cmd+K command palette. Update the frontend test count to the real number recorded in Step 1. Also find the "**Web UI backend**" paragraph and add one sentence noting the new settings endpoint, matching that paragraph's existing terse style. Update the backend test count (`221` → `236`) everywhere in `CLAUDE.md` it currently appears (the "Common commands" section's `make test` comment, the Repository Structure `tests/` line if it enumerates test file names — check whether `test_session.py`/`test_api_app.py`/`test_api_schemas.py` are already listed there, in which case no new file names need adding since this phase only added tests to existing files, not new test files).

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "Document Phase 4 (settings, portfolio, budget, command palette) in CLAUDE.md"
```
