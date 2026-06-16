"""Tests for round_report.py — round-by-round accuracy/cost chart."""
from __future__ import annotations

from pathlib import Path

from acquireml.round_report import generate_round_report


def test_generates_png(tmp_path: Path):
    history = [
        {"round_number": 1, "accuracy": 0.7, "cumulative_cost": None},
        {"round_number": 2, "accuracy": 0.8, "cumulative_cost": None},
    ]
    out = tmp_path / "report.png"
    result = generate_round_report(history, out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_handles_empty_history(tmp_path: Path):
    out = tmp_path / "empty.png"
    generate_round_report([], out)
    assert out.exists()


def test_skips_rounds_without_accuracy(tmp_path: Path):
    history = [
        {"round_number": 1, "accuracy": None, "cumulative_cost": None},
        {"round_number": 2, "accuracy": 0.9, "cumulative_cost": None},
    ]
    out = tmp_path / "partial.png"
    generate_round_report(history, out)
    assert out.exists()


def test_renders_with_cost_data(tmp_path: Path):
    history = [
        {"round_number": 1, "accuracy": 0.6, "cumulative_cost": 100.0},
        {"round_number": 2, "accuracy": 0.75, "cumulative_cost": 200.0},
    ]
    out = tmp_path / "cost.png"
    generate_round_report(history, out, session_name="my_proj")
    assert out.exists()


def test_returns_path_object(tmp_path: Path):
    out = tmp_path / "result.png"
    result = generate_round_report([{"round_number": 1, "accuracy": 0.5}], out)
    assert isinstance(result, Path)
