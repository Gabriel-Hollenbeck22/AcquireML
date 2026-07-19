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
