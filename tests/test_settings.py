"""Unit tests for settings.py: the per-user settings file. Every test passes an explicit path so
the real %APPDATA% is never touched."""

from __future__ import annotations

import json

from dfit_tool import settings


def test_roundtrip(tmp_path):
    path = str(tmp_path / "sub" / "settings.json")
    settings.save_settings({"log_path": "C:/logs/a.csv"}, path)
    assert settings.load_settings(path) == {"log_path": "C:/logs/a.csv"}


def test_missing_file_returns_empty(tmp_path):
    assert settings.load_settings(str(tmp_path / "nope.json")) == {}


def test_empty_file_returns_empty(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("")
    assert settings.load_settings(str(p)) == {}


def test_corrupt_file_returns_empty(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{not json")
    assert settings.load_settings(str(p)) == {}


def test_non_dict_json_returns_empty(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("[1, 2]")
    assert settings.load_settings(str(p)) == {}


def test_unknown_keys_preserved(tmp_path):
    path = str(tmp_path / "s.json")
    settings.save_settings({"log_path": None, "future_key": 3}, path)
    assert settings.load_settings(path) == {"log_path": None, "future_key": 3}


def test_save_leaves_no_temp_files(tmp_path):
    path = tmp_path / "s.json"
    settings.save_settings({"a": 1}, str(path))
    assert [p.name for p in tmp_path.iterdir()] == ["s.json"]
    assert json.loads(path.read_text()) == {"a": 1}


def test_settings_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert settings.settings_path() == str(tmp_path / "DFIT Tool" / "settings.json")
