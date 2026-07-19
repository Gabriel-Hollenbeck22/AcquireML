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
