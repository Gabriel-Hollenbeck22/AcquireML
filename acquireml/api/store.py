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
    """Return the .db path for a session name (does not check existence).

    ``name`` is the trust boundary between client input and the filesystem
    (the FastAPI layer wires a client-supplied URL path parameter straight
    into this function), so it must be a safe bare identifier — no path
    separators, no absolute paths, no ``..`` traversal. ``Path(name).name``
    strips any directory components and normalizes traversal segments, so
    comparing it back against ``name`` catches both cases.
    """
    if Path(name).name != name:
        raise ValueError(f"invalid session name: {name!r}")
    return base_dir / f"{name}.db"


def session_exists(name: str, base_dir: Path = SESSIONS_DIR) -> bool:
    return session_path(name, base_dir=base_dir).exists()


def list_session_names(base_dir: Path = SESSIONS_DIR) -> list[str]:
    """Return all known session names, sorted alphabetically."""
    if not base_dir.exists():
        return []
    return sorted(p.stem for p in base_dir.glob("*.db"))
