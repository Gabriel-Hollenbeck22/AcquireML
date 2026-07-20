"""app.py — FastAPI app for the AcquireML web UI backend.

A thin HTTP wrapper around acquireml.session.Session. No session/model
logic lives here — every endpoint just translates an HTTP request into a
Session method call and its return dict into a Pydantic response model.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from acquireml.api import store
from acquireml.api.schemas import (
    HistoryRow,
    RecommendResponse,
    RecommendRow,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
)
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


def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    """Save an uploaded file to disk, preserving its extension (the
    loaders dispatch on extension, so this must survive the upload).

    Saved under the sessions directory (not a temp dir) because Session
    does not persist feature data in its .db file — every subsequent
    call (recommend, update, ...) reloads X from the resolved path
    stored in session meta, so the file must outlive this request.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
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
    # Resolve (and validate) the session's .db path before touching disk —
    # session_path() rejects unsafe names (path separators, "..") and we
    # want that check to run before any upload is written.
    db_path = store.session_path(name, base_dir=store.SESSIONS_DIR)
    data_dir = store.SESSIONS_DIR / f"{name}_data"
    labeled_path = _save_upload(labeled_file, data_dir)
    pool_path = _save_upload(pool_file, data_dir) if pool_file else None

    try:
        with Session(db_path) as sess:
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
    except Exception:
        # init() failed (duplicate name, invalid model, ...) — the uploads
        # we just wrote are orphaned (no session record points to them), so
        # remove exactly those files before re-raising unchanged. NOTE:
        # data_dir is shared by name, so on a duplicate-name retry it may
        # already contain files from a prior *successful* init() — must not
        # rmtree() the whole directory, only unlink what this request wrote.
        labeled_path.unlink(missing_ok=True)
        if pool_path is not None:
            pool_path.unlink(missing_ok=True)
        try:
            data_dir.rmdir()  # no-op (raises, caught) if not empty
        except OSError:
            pass
        raise

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


@app.get("/sessions/{name}/history", response_model=list[HistoryRow])
def get_history(sess: Session = Depends(get_session)) -> list[HistoryRow]:
    with sess:
        return [HistoryRow(**row) for row in sess.history()]


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
