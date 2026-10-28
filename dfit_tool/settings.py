"""Per-user app settings (``settings.json``), kept outside the repo and OneDrive.

Stdlib only, no ``dfit_tool`` imports, no Tkinter. Reading never raises: a missing, empty, or
corrupt file is an empty dict. One key today: ``"log_path"`` (absolute path of the results log
CSV, absent or None = the per-folder ``dfit_log.csv`` default). Unknown keys round-trip.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Optional


def settings_path() -> str:
    """`%APPDATA%\\DFIT Tool\\settings.json`, or `~/.dfit_tool/settings.json` without APPDATA."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "DFIT Tool", "settings.json")
    return os.path.join(os.path.expanduser("~"), ".dfit_tool", "settings.json")


def load_settings(path: Optional[str] = None) -> dict:
    """The settings dict at `path` (default `settings_path()`); `{}` when the file is missing,
    empty, unreadable, or not a JSON object. Never raises."""
    try:
        with open(path or settings_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(data: dict, path: Optional[str] = None) -> None:
    """Write `data` to `path` (default `settings_path()`) atomically (temp file + os.replace),
    creating the directory if needed."""
    path = path or settings_path()
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=folder, prefix=".settings_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
