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
