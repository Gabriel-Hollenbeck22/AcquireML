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


def test_get_status_full_fields(client, tmp_path, labeled_csv, monkeypatch):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    Session(sessions_dir / "azm-project.db").init(
        labeled_csv, label_col="outcome", name="azm-project",
    )
    resp = client.get("/sessions/azm-project/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "azm-project"
    assert body["patience"] == 3
    assert body["min_delta"] == 0.005
    assert body["should_stop"] is False
    assert body["created_at"] is not None


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


def _create_session(client, labeled_csv, name="azm-project"):
    with open(labeled_csv, "rb") as f:
        client.post(
            "/sessions",
            data={"name": name, "label_col": "outcome"},
            files={"labeled_file": ("labeled.csv", f, "text/csv")},
        )


def test_get_history_empty_for_new_session(client, labeled_csv):
    _create_session(client, labeled_csv)
    resp = client.get("/sessions/azm-project/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_history_404s_for_unknown_session(client):
    resp = client.get("/sessions/nope/history")
    assert resp.status_code == 404


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
