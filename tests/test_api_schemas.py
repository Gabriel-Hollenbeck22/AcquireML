"""Tests for acquireml/api/schemas.py — API request/response shapes."""
from __future__ import annotations

from acquireml.api.schemas import (
    FeatureImportanceResponse,
    FeatureImportanceRow,
    HistoryRow,
    OverviewResponse,
    PrevalentFeatureRow,
    RecommendResponse,
    RecommendRow,
    ResetResponse,
    ResultRow,
    SessionCreateResponse,
    SessionSummary,
    StatusResponse,
    UpdateRequest,
    UpdateResponse,
    UpdateSettingsRequest,
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


def test_update_settings_request_all_fields_optional():
    body = UpdateSettingsRequest()
    assert body.patience is None
    assert body.model_dump(exclude_none=True) == {}


def test_update_settings_request_accepts_partial_fields():
    body = UpdateSettingsRequest(patience=5, cost_per_sample=2.5)
    assert body.model_dump(exclude_none=True) == {"patience": 5, "cost_per_sample": 2.5}


def test_feature_importance_response_shape():
    body = FeatureImportanceResponse(
        features=[
            FeatureImportanceRow(rank=1, feature="unitig_3", importance=0.42, cumulative_importance=0.42),
        ],
        cv_accuracy_mean=0.91,
        cv_accuracy_std=0.03,
        total_features=500,
        n_known=40,
    )
    assert body.features[0].feature == "unitig_3"
    assert body.cv_accuracy_mean == 0.91


def test_feature_importance_response_allows_null_cv():
    body = FeatureImportanceResponse(
        features=[], cv_accuracy_mean=None, cv_accuracy_std=None,
        total_features=10, n_known=3,
    )
    assert body.cv_accuracy_mean is None


def test_overview_response_shape():
    body = OverviewResponse(
        n_known=40, n_pool=60, n_features=30,
        n_positive=11, n_negative=29, positive_rate=0.275,
        top_prevalent_features=[PrevalentFeatureRow(feature="unitig_7", prevalence=0.9)],
    )
    assert body.n_known == 40
    assert body.top_prevalent_features[0].prevalence == 0.9
