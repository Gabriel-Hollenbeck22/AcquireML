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


def test_session_path_rejects_path_traversal(tmp_path):
    base = tmp_path / "sessions"
    try:
        session_path("../../etc/passwd", base_dir=base)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_session_path_rejects_absolute_path(tmp_path):
    base = tmp_path / "sessions"
    try:
        session_path("/etc/passwd", base_dir=base)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_session_path_accepts_normal_name(tmp_path):
    base = tmp_path / "sessions"
    assert session_path("azm-project", base_dir=base) == base / "azm-project.db"


def test_session_exists_rejects_path_traversal(tmp_path):
    base = tmp_path / "sessions"
    try:
        session_exists("../../etc/passwd", base_dir=base)
        assert False, "expected ValueError"
    except ValueError:
        pass
