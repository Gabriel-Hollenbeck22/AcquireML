# Web UI Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI backend that wraps `acquireml.session.Session` so a
future React frontend (and anything else) can drive the full session
lifecycle — create, recommend, update, status, history, reset, export,
delete — over local HTTP instead of the CLI.

**Architecture:** A new `acquireml/api/` package with three files:
`store.py` (resolves session names to `.db` paths under a fixed app-data
directory — the one piece designed to stay isolated for an easy future
pivot to hosted/multi-user), `schemas.py` (Pydantic request/response models
mirroring `Session`'s existing dict shapes exactly), and `app.py` (the
FastAPI app, a `get_session` dependency that 404s on unknown sessions, and
the endpoints themselves). No changes to `session.py` — this is a second,
independent consumer of the same class the CLI already uses.

**Tech Stack:** FastAPI, Pydantic v2, uvicorn (dev server), httpx (FastAPI
`TestClient`'s transport, dev-only dependency), python-multipart (required
by FastAPI for file-upload form parsing).

## Global Constraints

- No changes to `acquireml/session.py`, `acquireml/generic_loader.py`, or
  any other existing module — the API is a thin wrapper, not a rewrite.
- Local, single-machine tool: no auth, no multi-user, per the design spec.
- Sessions live at `~/.acquireml/sessions/<name>.db`, auto-discovered —
  no path ever comes from the client except the session `name`.
- `Session` raises `FileExistsError` (duplicate session), `RuntimeError`
  (business-rule conflicts: empty pool, unresolved pending samples, no
  matching results), and `ValueError` (bad input: unknown model choice,
  missing CSV columns) — these map to HTTP 409, 409, and 400 respectively,
  via global exception handlers (Task 3), not per-endpoint try/except.
- "Session not found" (unknown `name` in the URL) is not something
  `Session` itself raises (its constructor just wraps a path). Checked
  explicitly via a `get_session` FastAPI dependency (Task 3) that 404s
  before any endpoint body runs, mirroring the existing
  `sess.db_path.exists()` check in `acquireml/session_cli.py`.
- All 179 existing tests must stay green throughout — this plan only adds
  files, it never touches existing ones.

---

### Task 1: Dependencies + session store module

**Files:**
- Modify: `pyproject.toml` (add dependencies)
- Create: `acquireml/api/__init__.py`
- Create: `acquireml/api/store.py`
- Test: `tests/test_api_store.py`

**Interfaces:**
- Produces: `SESSIONS_DIR: Path`, `ensure_sessions_dir(base_dir: Path = SESSIONS_DIR) -> Path`,
  `session_path(name: str, base_dir: Path = SESSIONS_DIR) -> Path`,
  `session_exists(name: str, base_dir: Path = SESSIONS_DIR) -> bool`,
  `list_session_names(base_dir: Path = SESSIONS_DIR) -> list[str]`.
  Every function takes an optional `base_dir` so tests never touch the
  real `~/.acquireml/sessions/` directory.

- [ ] **Step 1: Add new dependencies to `pyproject.toml`**

In `pyproject.toml`, update the `dependencies` and `dev` optional-dependencies lists:

```toml
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
    "scikit-learn>=1.3",
    "rich>=13.0",
    "matplotlib>=3.7",
    "openpyxl>=3.1",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "httpx>=0.27",
]
```

- [ ] **Step 2: Install the new dependencies**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pip install -e ".[dev]"`
Expected: installs fastapi, uvicorn, python-multipart, httpx alongside the existing deps with no errors.

- [ ] **Step 3: Write the failing tests**

Create `tests/test_api_store.py`:

```python
"""Tests for acquireml/api/store.py — session file discovery/resolution."""
from __future__ import annotations

from pathlib import Path

from acquireml.api.store import (
    ensure_sessions_dir,
    session_exists,
    session_path,
    list_session_names,
)


def test_ensure_sessions_dir_creates_it(tmp_path):
    base = tmp_path / "sessions"
    assert not base.exists()
    result = ensure_sessions_dir(base_dir=base)
    assert result == base
    assert base.exists()
    assert base.is_dir()


def test_ensure_sessions_dir_idempotent(tmp_path):
    base = tmp_path / "sessions"
    ensure_sessions_dir(base_dir=base)
    ensure_sessions_dir(base_dir=base)  # must not raise on second call
    assert base.exists()


def test_session_path_appends_db_extension(tmp_path):
    base = tmp_path / "sessions"
    assert session_path("azm-project", base_dir=base) == base / "azm-project.db"


def test_session_exists_false_for_missing(tmp_path):
    base = tmp_path / "sessions"
    assert session_exists("nope", base_dir=base) is False


def test_session_exists_true_after_creation(tmp_path):
    base = tmp_path / "sessions"
    ensure_sessions_dir(base_dir=base)
    (base / "azm-project.db").touch()
    assert session_exists("azm-project", base_dir=base) is True


def test_list_session_names_empty_when_dir_missing(tmp_path):
    base = tmp_path / "sessions"
    assert list_session_names(base_dir=base) == []


def test_list_session_names_returns_stems_sorted(tmp_path):
    base = tmp_path / "sessions"
    ensure_sessions_dir(base_dir=base)
    (base / "cip-project.db").touch()
    (base / "azm-project.db").touch()
    assert list_session_names(base_dir=base) == ["azm-project", "cip-project"]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'acquireml.api'`

- [ ] **Step 5: Create the package and implement `store.py`**

Create `acquireml/api/__init__.py` (empty file).

Create `acquireml/api/store.py`:

```python
"""store.py — resolves session names to local .db paths.

Kept isolated from the rest of the API deliberately: this is the one
piece of the backend that would need to grow if the app ever moved from
"one local sessions folder" to "one folder per hosted user." Every other
module only ever learns a session's path through this file.
"""
from __future__ import annotations

from pathlib import Path

SESSIONS_DIR = Path.home() / ".acquireml" / "sessions"


def ensure_sessions_dir(base_dir: Path = SESSIONS_DIR) -> Path:
    """Create the sessions directory if it doesn't exist yet. Returns it."""
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def session_path(name: str, base_dir: Path = SESSIONS_DIR) -> Path:
    """Return the .db path for a session name (does not check existence)."""
    return base_dir / f"{name}.db"


def session_exists(name: str, base_dir: Path = SESSIONS_DIR) -> bool:
    return session_path(name, base_dir=base_dir).exists()


def list_session_names(base_dir: Path = SESSIONS_DIR) -> list[str]:
    """Return all known session names, sorted alphabetically."""
    if not base_dir.exists():
        return []
    return sorted(p.stem for p in base_dir.glob("*.db"))
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_store.py -v`
Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml acquireml/api/__init__.py acquireml/api/store.py tests/test_api_store.py
git commit -m "Add FastAPI deps and session store module for web UI backend"
```

---

### Task 2: Pydantic schemas

**Files:**
- Create: `acquireml/api/schemas.py`
- Test: `tests/test_api_schemas.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `SessionSummary`, `SessionCreateResponse`, `StatusResponse`,
  `HistoryRow`, `RecommendRow`, `RecommendResponse`, `ResultRow`,
  `UpdateRequest`, `UpdateResponse`, `ResetResponse` — all Pydantic
  `BaseModel` subclasses. Field names and types below are exact; Task 3+
  construct these by explicit field-by-field mapping from `Session`'s
  dict returns (not `Model(**a_dict)`), so extra keys in those dicts
  (like `report_path` on `update()`'s return) are simply never read.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api_schemas.py`:

```python
"""Tests for acquireml/api/schemas.py — API request/response shapes."""
from __future__ import annotations

from acquireml.api.schemas import (
    HistoryRow,
    RecommendResponse,
    RecommendRow,
    ResetResponse,
    ResultRow,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
    UpdateRequest,
    UpdateResponse,
)


def test_session_summary_round_trips():
    s = SessionSummary(
        name="azm-project", current_round=2, n_known=45,
        n_pool=55, n_pending=0, latest_accuracy=0.93,
    )
    assert s.model_dump()["name"] == "azm-project"


def test_session_summary_allows_null_accuracy():
    s = SessionSummary(
        name="new-project", current_round=0, n_known=20,
        n_pool=30, n_pending=0, latest_accuracy=None,
    )
    assert s.latest_accuracy is None


def test_session_create_response_round_trips():
    r = SessionCreateResponse(
        name="azm-project", n_known=20, n_pool=30, label_col="outcome",
        patience=3, min_delta=0.005, cost_per_sample=None,
        diversity_weight=0.0, model="rf", calibrate=False,
        calibration_method="sigmoid",
    )
    assert r.n_known == 20


def test_status_response_round_trips():
    r = StatusResponse(
        name="azm-project", current_round=2, n_known=45, n_pool=55,
        n_pending=0, latest_accuracy=0.93, patience=3, min_delta=0.005,
        cost_per_sample=None, total_cost=None, diversity_weight=0.0,
        model="rf", calibrate=False, calibration_method="sigmoid",
        should_stop=False, stop_reason="", created_at="2026-07-19T00:00:00Z",
    )
    assert r.should_stop is False


def test_history_row_round_trips():
    r = HistoryRow(
        round_number=1, n_known=20, accuracy=0.9,
        round_cost=None, cumulative_cost=None, created_at="2026-07-19T00:00:00Z",
    )
    assert r.round_number == 1


def test_recommend_response_round_trips():
    row = RecommendRow(
        rank=1, sample_id="pool_3", uncertainty_score=0.98,
        p_positive=0.51, predicted_class="positive",
    )
    resp = RecommendResponse(rows=[row], should_stop=False, stop_reason="")
    assert resp.rows[0].sample_id == "pool_3"


def test_update_request_parses_results_list():
    req = UpdateRequest(results=[ResultRow(sample_id="pool_3", label=1)])
    assert req.results[0].label == 1


def test_update_response_round_trips():
    r = UpdateResponse(
        round=1, n_returned=5, n_known=25, n_pool=25, accuracy=0.9,
        round_cost=None, cumulative_cost=None, should_stop=False, stop_reason="",
    )
    assert r.n_returned == 5


def test_reset_response_round_trips():
    r = ResetResponse(n_known=20, n_pool=30, rounds_cleared=2)
    assert r.rounds_cleared == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'acquireml.api.schemas'`

- [ ] **Step 3: Implement `schemas.py`**

Create `acquireml/api/schemas.py`:

```python
"""schemas.py — Pydantic request/response models for the web UI API.

Field names and types mirror acquireml.session.Session's existing dict
returns exactly. Nothing here changes session.py's behavior — this is
just the API's data contract.
"""
from __future__ import annotations

from pydantic import BaseModel


class SessionSummary(BaseModel):
    """One row in the GET /sessions list."""
    name: str
    current_round: int
    n_known: int
    n_pool: int
    n_pending: int
    latest_accuracy: float | None


class SessionCreateResponse(BaseModel):
    """Response for POST /sessions — mirrors Session.init()'s return."""
    name: str
    n_known: int
    n_pool: int
    label_col: str
    patience: int
    min_delta: float
    cost_per_sample: float | None
    diversity_weight: float
    model: str
    calibrate: bool
    calibration_method: str


class StatusResponse(BaseModel):
    """Response for GET /sessions/{name}/status — mirrors Session.status()."""
    name: str | None
    current_round: int
    n_known: int
    n_pool: int
    n_pending: int
    latest_accuracy: float | None
    patience: int
    min_delta: float
    cost_per_sample: float | None
    total_cost: float | None
    diversity_weight: float
    model: str
    calibrate: bool
    calibration_method: str
    should_stop: bool
    stop_reason: str
    created_at: str | None


class HistoryRow(BaseModel):
    """One row in GET /sessions/{name}/history — mirrors Session.history()."""
    round_number: int
    n_known: int
    accuracy: float | None
    round_cost: float | None
    cumulative_cost: float | None
    created_at: str


class RecommendRow(BaseModel):
    """One row in GET /sessions/{name}/recommend."""
    rank: int
    sample_id: str
    uncertainty_score: float
    p_positive: float
    predicted_class: str


class RecommendResponse(BaseModel):
    rows: list[RecommendRow]
    should_stop: bool
    stop_reason: str


class ResultRow(BaseModel):
    """One lab result submitted back via POST /sessions/{name}/update."""
    sample_id: str
    label: int


class UpdateRequest(BaseModel):
    results: list[ResultRow]


class UpdateResponse(BaseModel):
    """Mirrors Session.update()'s return, minus report_path (unused by the
    web UI, which renders its own interactive charts instead of the
    CLI's static PNG)."""
    round: int
    n_returned: int
    n_known: int
    n_pool: int
    accuracy: float
    round_cost: float | None
    cumulative_cost: float | None
    should_stop: bool
    stop_reason: str


class ResetResponse(BaseModel):
    """Mirrors Session.reset()'s return."""
    n_known: int
    n_pool: int
    rounds_cleared: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_schemas.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/schemas.py tests/test_api_schemas.py
git commit -m "Add Pydantic schemas for the web UI API"
```

---

### Task 3: FastAPI app skeleton, error mapping, GET /sessions

**Files:**
- Create: `acquireml/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `store.list_session_names`, `store.session_path`,
  `store.session_exists`, `store.SESSIONS_DIR` (Task 1);
  `schemas.SessionSummary` (Task 2); `acquireml.session.Session`.
- Produces: `app: FastAPI` (importable as `acquireml.api.app:app`, the
  target uvicorn will run). A `get_session(name: str) -> Session`
  dependency that later tasks reuse via `Depends(get_session)` — it
  404s if the session doesn't exist, otherwise returns an open `Session`
  pointed at that name's `.db` file. Global exception handlers for
  `FileExistsError` (409), `RuntimeError` (409), `ValueError` (400).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api_app.py`:

```python
"""Tests for acquireml/api/app.py — FastAPI app wiring and GET /sessions."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import acquireml.api.app as api_app
from acquireml.session import Session


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient wired to a throwaway sessions directory."""
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setattr(api_app.store, "SESSIONS_DIR", sessions_dir)
    return TestClient(api_app.app)


@pytest.fixture()
def labeled_csv(tmp_path):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        rng.integers(0, 2, size=(20, 10)).astype(int),
        index=[f"known_{i}" for i in range(20)],
        columns=[f"f{j}" for j in range(10)],
    )
    df["outcome"] = (df["f0"] | df["f1"]).astype(int)
    p = tmp_path / "labeled.csv"
    df.to_csv(p)
    return p


def test_list_sessions_empty(client):
    resp = client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_returns_summary(client, tmp_path, labeled_csv, monkeypatch):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    Session(sessions_dir / "azm-project.db").init(
        labeled_csv, label_col="outcome", name="azm-project",
    )
    resp = client.get("/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "azm-project"
    assert body[0]["n_known"] == 20
    assert body[0]["current_round"] == 0
    assert body[0]["latest_accuracy"] is None


def test_get_unknown_session_status_404s(client):
    resp = client.get("/sessions/nope/status")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'acquireml.api.app'`

- [ ] **Step 3: Implement `app.py`**

Create `acquireml/api/app.py`:

```python
"""app.py — FastAPI app for the AcquireML web UI backend.

A thin HTTP wrapper around acquireml.session.Session. No session/model
logic lives here — every endpoint just translates an HTTP request into a
Session method call and its return dict into a Pydantic response model.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from acquireml.api import store
from acquireml.api.schemas import SessionSummary
from acquireml.session import Session

app = FastAPI(title="AcquireML Web UI API")

# The React dev server (Vite) runs on a different port than uvicorn; the
# browser enforces CORS between them. Local-only tool, so allowing the
# standard Vite dev ports is enough — no production/hosted origin exists yet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FileExistsError)
def _handle_file_exists(request, exc: FileExistsError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
def _handle_runtime_error(request, exc: RuntimeError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValueError)
def _handle_value_error(request, exc: ValueError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def get_session(name: str) -> Session:
    """FastAPI dependency: 404s if `name` has no session file, otherwise
    returns an open Session pointed at it. Reused by every
    /sessions/{name}/... endpoint from Task 4 onward."""
    if not store.session_exists(name, base_dir=store.SESSIONS_DIR):
        raise HTTPException(status_code=404, detail=f"No session named {name!r}.")
    return Session(store.session_path(name, base_dir=store.SESSIONS_DIR))


@app.get("/sessions", response_model=list[SessionSummary])
def list_sessions() -> list[SessionSummary]:
    summaries = []
    for name in store.list_session_names(base_dir=store.SESSIONS_DIR):
        with Session(store.session_path(name, base_dir=store.SESSIONS_DIR)) as sess:
            s = sess.status()
            summaries.append(SessionSummary(
                name=s["name"] or name,
                current_round=s["current_round"],
                n_known=s["n_known"],
                n_pool=s["n_pool"],
                n_pending=s["n_pending"],
                latest_accuracy=s["latest_accuracy"],
            ))
    return summaries


@app.get("/sessions/{name}/status", response_model=SessionSummary)
def get_status(sess: Session = Depends(get_session)) -> SessionSummary:
    with sess:
        s = sess.status()
        return SessionSummary(
            name=s["name"] or "",
            current_round=s["current_round"],
            n_known=s["n_known"],
            n_pool=s["n_pool"],
            n_pending=s["n_pending"],
            latest_accuracy=s["latest_accuracy"],
        )
```

Note: `get_status` above returns `SessionSummary` (not the full
`StatusResponse`) only as a placeholder to make Task 3's own test pass —
Task 5 replaces this with the real `StatusResponse` version. This keeps
Task 3 focused on app wiring + `GET /sessions` + the 404 dependency, which
is exactly what its tests check.

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/app.py tests/test_api_app.py
git commit -m "Add FastAPI app skeleton with error mapping and GET /sessions"
```

---

### Task 4: POST /sessions (create)

**Files:**
- Modify: `acquireml/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `schemas.SessionCreateResponse` (Task 2), `store.session_path`
  (Task 1), `Session.init` (existing).
- Produces: `POST /sessions` accepting `multipart/form-data` with a
  required `labeled_file` upload and optional `pool_file` upload, plus
  form fields `name`, `label_col`, `model`, `patience`, `min_delta`,
  `cost_per_sample`, `diversity_weight`, `calibrate`, `calibration_method`.
  Returns 201 + `SessionCreateResponse` on success, 409 on duplicate name,
  400 on invalid `model`/`calibration_method`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api_app.py`:

```python
def test_create_session_success(client, labeled_csv):
    with open(labeled_csv, "rb") as f:
        resp = client.post(
            "/sessions",
            data={"name": "azm-project", "label_col": "outcome"},
            files={"labeled_file": ("labeled.csv", f, "text/csv")},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "azm-project"
    assert body["n_known"] == 20
    assert body["n_pool"] == 0
    assert body["model"] == "rf"


def test_create_session_with_pool_file(client, labeled_csv, tmp_path):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(7)
    pool_df = pd.DataFrame(
        rng.integers(0, 2, size=(30, 10)).astype(int),
        index=[f"pool_{i}" for i in range(30)],
        columns=[f"f{j}" for j in range(10)],
    )
    pool_csv = tmp_path / "pool.csv"
    pool_df.to_csv(pool_csv)

    with open(labeled_csv, "rb") as lf, open(pool_csv, "rb") as pf:
        resp = client.post(
            "/sessions",
            data={"name": "azm-project", "label_col": "outcome"},
            files={
                "labeled_file": ("labeled.csv", lf, "text/csv"),
                "pool_file": ("pool.csv", pf, "text/csv"),
            },
        )
    assert resp.status_code == 201
    assert resp.json()["n_pool"] == 30


def test_create_session_duplicate_name_409s(client, labeled_csv):
    with open(labeled_csv, "rb") as f:
        client.post(
            "/sessions",
            data={"name": "azm-project", "label_col": "outcome"},
            files={"labeled_file": ("labeled.csv", f, "text/csv")},
        )
    with open(labeled_csv, "rb") as f:
        resp = client.post(
            "/sessions",
            data={"name": "azm-project", "label_col": "outcome"},
            files={"labeled_file": ("labeled.csv", f, "text/csv")},
        )
    assert resp.status_code == 409


def test_create_session_invalid_model_400s(client, labeled_csv):
    with open(labeled_csv, "rb") as f:
        resp = client.post(
            "/sessions",
            data={"name": "azm-project", "label_col": "outcome", "model": "not-a-model"},
            files={"labeled_file": ("labeled.csv", f, "text/csv")},
        )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k create_session -v`
Expected: FAIL with 404 (no such route yet)

- [ ] **Step 3: Implement `POST /sessions`**

In `acquireml/api/app.py`, add near the top of the imports:

```python
import tempfile
import uuid
from pathlib import Path

from fastapi import File, Form, UploadFile
```

Add this helper function and endpoint after `get_session`:

```python
def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    """Save an uploaded file to disk, preserving its extension (the
    loaders dispatch on extension, so this must survive the upload)."""
    suffix = Path(upload.filename or "").suffix or ".csv"
    dest = dest_dir / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(upload.file.read())
    return dest


@app.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session(
    name: str = Form(...),
    label_col: str = Form(...),
    labeled_file: UploadFile = File(...),
    pool_file: UploadFile | None = File(None),
    model: str = Form("rf"),
    patience: int = Form(3),
    min_delta: float = Form(0.005),
    cost_per_sample: float | None = Form(None),
    diversity_weight: float = Form(0.0),
    calibrate: bool = Form(False),
    calibration_method: str = Form("sigmoid"),
) -> SessionCreateResponse:
    store.ensure_sessions_dir(base_dir=store.SESSIONS_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        labeled_path = _save_upload(labeled_file, tmp_dir)
        pool_path = _save_upload(pool_file, tmp_dir) if pool_file else None

        with Session(store.session_path(name, base_dir=store.SESSIONS_DIR)) as sess:
            summary = sess.init(
                data_path=labeled_path,
                label_col=label_col,
                pool_path=pool_path,
                name=name,
                patience=patience,
                min_delta=min_delta,
                cost_per_sample=cost_per_sample,
                diversity_weight=diversity_weight,
                model=model,
                calibrate=calibrate,
                calibration_method=calibration_method,
            )

    return SessionCreateResponse(
        name=summary["name"],
        n_known=summary["n_known"],
        n_pool=summary["n_pool"],
        label_col=summary["label_col"],
        patience=summary["patience"],
        min_delta=summary["min_delta"],
        cost_per_sample=summary["cost_per_sample"],
        diversity_weight=summary["diversity_weight"],
        model=summary["model"],
        calibrate=summary["calibrate"],
        calibration_method=summary["calibration_method"],
    )
```

Add `SessionCreateResponse` to the existing schemas import line:

```python
from acquireml.api.schemas import SessionCreateResponse, SessionSummary
```

Note: `Session.init` reads `data_path`/`pool_path` from disk immediately
(inside the `with` block, before the `TemporaryDirectory` is cleaned up),
so the temp files are guaranteed to still exist when they're needed —
`GenericLoader.load()` runs synchronously inside `sess.init(...)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/app.py tests/test_api_app.py
git commit -m "Add POST /sessions (create session from uploaded files)"
```

---

### Task 5: GET /sessions/{name}/status (full) and /history

**Files:**
- Modify: `acquireml/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `schemas.StatusResponse`, `schemas.HistoryRow` (Task 2),
  `get_session` dependency (Task 3).
- Produces: `GET /sessions/{name}/status` returning the full
  `StatusResponse` (replacing Task 3's placeholder), and
  `GET /sessions/{name}/history` returning `list[HistoryRow]`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api_app.py`:

```python
def _create_session(client, labeled_csv, name="azm-project"):
    with open(labeled_csv, "rb") as f:
        client.post(
            "/sessions",
            data={"name": name, "label_col": "outcome"},
            files={"labeled_file": ("labeled.csv", f, "text/csv")},
        )


def test_get_status_full_fields(client, labeled_csv):
    _create_session(client, labeled_csv)
    resp = client.get("/sessions/azm-project/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "azm-project"
    assert body["patience"] == 3
    assert body["min_delta"] == 0.005
    assert body["should_stop"] is False
    assert body["created_at"] is not None


def test_get_history_empty_for_new_session(client, labeled_csv):
    _create_session(client, labeled_csv)
    resp = client.get("/sessions/azm-project/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_history_404s_for_unknown_session(client):
    resp = client.get("/sessions/nope/history")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k "status_full or history" -v`
Expected: `test_get_status_full_fields` FAILs (missing fields like `patience`
on the placeholder `SessionSummary` response), `test_get_history*` FAIL
with 404 route-not-found.

- [ ] **Step 3: Replace the placeholder status endpoint and add history**

In `acquireml/api/app.py`, update the schemas import:

```python
from acquireml.api.schemas import (
    HistoryRow,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
)
```

Replace the existing `get_status` function entirely with:

```python
@app.get("/sessions/{name}/status", response_model=StatusResponse)
def get_status(sess: Session = Depends(get_session)) -> StatusResponse:
    with sess:
        s = sess.status()
        return StatusResponse(
            name=s["name"],
            current_round=s["current_round"],
            n_known=s["n_known"],
            n_pool=s["n_pool"],
            n_pending=s["n_pending"],
            latest_accuracy=s["latest_accuracy"],
            patience=s["patience"],
            min_delta=s["min_delta"],
            cost_per_sample=s["cost_per_sample"],
            total_cost=s["total_cost"],
            diversity_weight=s["diversity_weight"],
            model=s["model"],
            calibrate=s["calibrate"],
            calibration_method=s["calibration_method"],
            should_stop=s["should_stop"],
            stop_reason=s["stop_reason"],
            created_at=s["created_at"],
        )


@app.get("/sessions/{name}/history", response_model=list[HistoryRow])
def get_history(sess: Session = Depends(get_session)) -> list[HistoryRow]:
    with sess:
        return [HistoryRow(**row) for row in sess.history()]
```

`HistoryRow(**row)` is safe here (unlike the other responses) because
`Session.history()`'s dict keys are already an exact 1:1 match with
`HistoryRow`'s fields — there's no extra key like `update()`'s
`report_path` to worry about.

Also update `list_sessions` to use the now-real status fields the same
way it already did (no change needed there — it already only reads the
fields `SessionSummary` needs).

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/app.py tests/test_api_app.py
git commit -m "Add full status response and GET /sessions/{name}/history"
```

---

### Task 6: GET /sessions/{name}/recommend

**Files:**
- Modify: `acquireml/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `schemas.RecommendResponse`, `schemas.RecommendRow` (Task 2),
  `get_session` dependency (Task 3), `Session.recommend` (existing).
- Produces: `GET /sessions/{name}/recommend?batch_size=N`, default
  `batch_size=10`. 409 if the pool is empty or pending results are
  unresolved (via the `RuntimeError` global handler from Task 3).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api_app.py`:

```python
def _create_session_with_pool(client, labeled_csv, tmp_path, name="azm-project"):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(7)
    pool_df = pd.DataFrame(
        rng.integers(0, 2, size=(30, 10)).astype(int),
        index=[f"pool_{i}" for i in range(30)],
        columns=[f"f{j}" for j in range(10)],
    )
    pool_csv = tmp_path / "pool.csv"
    pool_df.to_csv(pool_csv)
    with open(labeled_csv, "rb") as lf, open(pool_csv, "rb") as pf:
        client.post(
            "/sessions",
            data={"name": name, "label_col": "outcome"},
            files={
                "labeled_file": ("labeled.csv", lf, "text/csv"),
                "pool_file": ("pool.csv", pf, "text/csv"),
            },
        )


def test_recommend_returns_batch(client, labeled_csv, tmp_path):
    _create_session_with_pool(client, labeled_csv, tmp_path)
    resp = client.get("/sessions/azm-project/recommend?batch_size=5")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rows"]) == 5
    assert set(body["rows"][0].keys()) == {
        "rank", "sample_id", "uncertainty_score", "p_positive", "predicted_class",
    }
    assert "should_stop" in body


def test_recommend_empty_pool_409s(client, labeled_csv):
    _create_session(client, labeled_csv)  # no pool file uploaded
    resp = client.get("/sessions/azm-project/recommend")
    assert resp.status_code == 409


def test_recommend_pending_unresolved_409s(client, labeled_csv, tmp_path):
    _create_session_with_pool(client, labeled_csv, tmp_path)
    client.get("/sessions/azm-project/recommend?batch_size=5")
    resp = client.get("/sessions/azm-project/recommend?batch_size=5")
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k recommend -v`
Expected: FAIL with 404 (no such route yet)

- [ ] **Step 3: Implement the endpoint**

In `acquireml/api/app.py`, update the schemas import:

```python
from acquireml.api.schemas import (
    HistoryRow,
    RecommendResponse,
    RecommendRow,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
)
```

Add:

```python
@app.get("/sessions/{name}/recommend", response_model=RecommendResponse)
def recommend(batch_size: int = 10, sess: Session = Depends(get_session)) -> RecommendResponse:
    with sess:
        df = sess.recommend(batch_size=batch_size)
        rows = [
            RecommendRow(
                rank=int(row.rank),
                sample_id=str(row.sample_id),
                uncertainty_score=float(row.uncertainty_score),
                p_positive=float(row.p_positive),
                predicted_class=row.predicted_class,
            )
            for row in df.itertuples()
        ]
        return RecommendResponse(
            rows=rows,
            should_stop=bool(df.attrs.get("should_stop", False)),
            stop_reason=df.attrs.get("stop_reason", ""),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/app.py tests/test_api_app.py
git commit -m "Add GET /sessions/{name}/recommend"
```

---

### Task 7: POST /sessions/{name}/update

**Files:**
- Modify: `acquireml/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `schemas.UpdateRequest`, `schemas.UpdateResponse` (Task 2),
  `get_session` dependency (Task 3), `Session.update` (existing, takes a
  CSV path — this endpoint writes the JSON body to a temp CSV first).
- Produces: `POST /sessions/{name}/update` accepting a JSON body
  `{"results": [{"sample_id": "...", "label": 0|1}, ...]}`. 400 if no
  submitted `sample_id` matches a pending sample (via the `ValueError`
  global handler).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api_app.py`:

```python
def test_update_submits_results_and_retrains(client, labeled_csv, tmp_path):
    _create_session_with_pool(client, labeled_csv, tmp_path)
    rec = client.get("/sessions/azm-project/recommend?batch_size=5").json()
    results = [
        {"sample_id": row["sample_id"], "label": i % 2}
        for i, row in enumerate(rec["rows"])
    ]
    resp = client.post("/sessions/azm-project/update", json={"results": results})
    assert resp.status_code == 200
    body = resp.json()
    assert body["round"] == 1
    assert body["n_returned"] == 5
    assert body["n_known"] == 25
    assert 0.0 <= body["accuracy"] <= 1.0


def test_update_no_matching_results_400s(client, labeled_csv, tmp_path):
    _create_session_with_pool(client, labeled_csv, tmp_path)
    client.get("/sessions/azm-project/recommend?batch_size=5")
    resp = client.post(
        "/sessions/azm-project/update",
        json={"results": [{"sample_id": "not_a_real_id", "label": 1}]},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k update -v`
Expected: FAIL with 404 (no such route yet)

- [ ] **Step 3: Implement the endpoint**

In `acquireml/api/app.py`, update the schemas import:

```python
from acquireml.api.schemas import (
    HistoryRow,
    RecommendResponse,
    RecommendRow,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
    UpdateRequest,
    UpdateResponse,
)
```

Add:

```python
import pandas as pd


@app.post("/sessions/{name}/update", response_model=UpdateResponse)
def update(body: UpdateRequest, sess: Session = Depends(get_session)) -> UpdateResponse:
    with sess:
        with tempfile.TemporaryDirectory() as tmp:
            results_path = Path(tmp) / "results.csv"
            pd.DataFrame(
                [{"sample_id": r.sample_id, "label": r.label} for r in body.results]
            ).to_csv(results_path, index=False)
            result = sess.update(results_path)

        return UpdateResponse(
            round=result["round"],
            n_returned=result["n_returned"],
            n_known=result["n_known"],
            n_pool=result["n_pool"],
            accuracy=result["accuracy"],
            round_cost=result["round_cost"],
            cumulative_cost=result["cumulative_cost"],
            should_stop=result["should_stop"],
            stop_reason=result["stop_reason"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/app.py tests/test_api_app.py
git commit -m "Add POST /sessions/{name}/update"
```

---

### Task 8: reset, export, delete

**Files:**
- Modify: `acquireml/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `schemas.ResetResponse` (Task 2), `get_session` dependency
  (Task 3), `Session.reset`, `Session.export` (existing).
- Produces: `POST /sessions/{name}/reset` → `ResetResponse`.
  `GET /sessions/{name}/export` → CSV file download
  (`Content-Type: text/csv`). `DELETE /sessions/{name}` → 204 No Content,
  removes the `.db` file (and its round-report PNG, if one exists —
  `Session.update` always writes one via `_generate_report`, so it would
  otherwise be orphaned).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api_app.py`:

```python
def test_reset_clears_rounds(client, labeled_csv, tmp_path):
    _create_session_with_pool(client, labeled_csv, tmp_path)
    rec = client.get("/sessions/azm-project/recommend?batch_size=5").json()
    results = [{"sample_id": r["sample_id"], "label": 0} for r in rec["rows"]]
    client.post("/sessions/azm-project/update", json={"results": results})

    resp = client.post("/sessions/azm-project/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rounds_cleared"] == 1

    status = client.get("/sessions/azm-project/status").json()
    assert status["current_round"] == 0


def test_export_returns_csv(client, labeled_csv):
    _create_session(client, labeled_csv)
    resp = client.get("/sessions/azm-project/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "round_number" in resp.text


def test_delete_removes_session(client, labeled_csv):
    _create_session(client, labeled_csv)
    resp = client.delete("/sessions/azm-project")
    assert resp.status_code == 204

    resp = client.get("/sessions/azm-project/status")
    assert resp.status_code == 404


def test_delete_unknown_session_404s(client):
    resp = client.delete("/sessions/nope")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -k "reset or export or delete" -v`
Expected: FAIL with 404 (no such routes yet)

- [ ] **Step 3: Implement the three endpoints**

In `acquireml/api/app.py`, update the schemas import to add `ResetResponse`:

```python
from acquireml.api.schemas import (
    HistoryRow,
    RecommendResponse,
    RecommendRow,
    ResetResponse,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
    UpdateRequest,
    UpdateResponse,
)
```

Add near the top of the imports:

```python
from fastapi import Response
```

Add the three endpoints:

```python
@app.post("/sessions/{name}/reset", response_model=ResetResponse)
def reset(sess: Session = Depends(get_session)) -> ResetResponse:
    with sess:
        result = sess.reset()
        return ResetResponse(
            n_known=result["n_known"],
            n_pool=result["n_pool"],
            rounds_cleared=result["rounds_cleared"],
        )


@app.get("/sessions/{name}/export")
def export(name: str, sess: Session = Depends(get_session)) -> Response:
    # Read the CSV into memory rather than streaming it from disk with
    # FileResponse: FileResponse reads lazily as it streams, but the
    # TemporaryDirectory below deletes its contents as soon as the `with`
    # block exits, which happens before streaming would finish. Reading
    # the bytes up front avoids that race entirely.
    with sess:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / f"{name}_history.csv"
            sess.export(out_path)
            csv_bytes = out_path.read_bytes()
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}_history.csv"'},
    )


@app.delete("/sessions/{name}", status_code=204)
def delete_session(name: str, sess: Session = Depends(get_session)) -> Response:
    sess.close()
    db_path = store.session_path(name, base_dir=store.SESSIONS_DIR)
    db_path.unlink(missing_ok=True)
    report_path = db_path.with_name(f"{db_path.stem}_report.png")
    report_path.unlink(missing_ok=True)
    return Response(status_code=204)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest tests/test_api_app.py -v`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add acquireml/api/app.py tests/test_api_app.py
git commit -m "Add session reset, export, and delete endpoints"
```

---

### Task 9: Dev-run wiring, docs, full verification

**Files:**
- Modify: `Makefile`
- Modify: `CLAUDE.md`
- No new tests — this task wires up how a human runs the server and
  confirms the whole suite (existing + new) is green together.

- [ ] **Step 1: Add a Makefile target to run the API dev server**

In `Makefile`, the `.PHONY` line currently reads:

```makefile
.PHONY: install run compare compare-cip explore explain recommend test clean
```

Change it to add `api` (leave the rest of the line exactly as-is, including
that `validate` is already absent from it — that's pre-existing and out of
scope here):

```makefile
.PHONY: install run compare compare-cip explore explain recommend test clean api
```

Then add a new target, matching the existing `## name      — description`
comment style used above every other target:

```makefile
## api          — run the web UI backend API (dev server, auto-reload)
api:
	$(PYTHON) -m uvicorn acquireml.api.app:app --reload --port 8000
```

- [ ] **Step 2: Manually verify the server boots**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m uvicorn acquireml.api.app:app --port 8000 &`
Then: `curl -s http://localhost:8000/sessions`
Expected: `[]` (empty list, no sessions created against the real
`~/.acquireml/sessions/` yet)
Then stop the server: `kill %1` (or find and kill the uvicorn process)

- [ ] **Step 3: Update CLAUDE.md**

Add a new subsection under "## Session Module Design" (after the existing
"Session workflow for a researcher" numbered list) documenting the new
API:

```markdown
**Web UI backend** (`acquireml/api/`): a FastAPI app exposing the same
session lifecycle over local HTTP, for the in-progress React frontend.
`store.py` resolves session names to `~/.acquireml/sessions/<name>.db`
(auto-discovered, no path ever comes from the client). `schemas.py`
mirrors `Session`'s existing dict returns as Pydantic models. `app.py` is
a thin translation layer — no session/model logic lives here. Run with
`make api` (or `uvicorn acquireml.api.app:app --reload`).
```

- [ ] **Step 4: Run the full test suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest -q`
Expected: all existing tests (179) plus this plan's new tests
(7 store + 9 schemas + 19 app = 35) pass — 214 total, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add Makefile CLAUDE.md
git commit -m "Add make api target and document the web UI backend in CLAUDE.md"
```

- [ ] **Step 6: Report readiness**

Summarize for the user: total new test count, confirmation the full
suite passes, and that the backend is ready for the frontend plan (which
should be written next, now that the exact response shapes are real
and tested rather than speculative).
