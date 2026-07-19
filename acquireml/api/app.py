"""app.py — FastAPI app for the AcquireML web UI backend.

A thin HTTP wrapper around acquireml.session.Session. No session/model
logic lives here — every endpoint just translates an HTTP request into a
Session method call and its return dict into a Pydantic response model.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from acquireml.api import store
from acquireml.api.schemas import SessionSummary, StatusResponse
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
