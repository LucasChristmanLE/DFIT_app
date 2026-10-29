"""DfitApp identity wiring, bound onto duck-typed stand-ins (no Tk)."""

from __future__ import annotations

import datetime as dt
import types

import numpy as np

from dfit_tool import identity, ui
from dfit_tool.model import PickState
from dfit_tool.ui import DfitApp

PATH = r"C:\DFIT Organized\DJ\APC Badger 11N-3HZ\Badger 11N-3HZ Final.dbs"


class _Var:
    def __init__(self, value=""):
        self.value = value

    def set(self, v):
        self.value = v

    def get(self):
        return self.value


def _app(state, start_time=dt.datetime(2019, 5, 4, 23, 0)):
    app = types.SimpleNamespace(
        td=types.SimpleNamespace(path=PATH, start_time=start_time,
                                 t_s=np.arange(0.0, 10000.0, 1.0)),
        state=state, folder_root=None, _known_operators=identity.known_operators(),
        _identity_lines=[], _identity_filled=False, _identity_committed=None, var_operator=_Var(), var_api=_Var(),
        var_job_date=_Var(), cmb_operator={}, refresh_calls=[])
    app.refresh = lambda: app.refresh_calls.append(1)
    app._fill_identity_blanks = types.MethodType(DfitApp._fill_identity_blanks, app)
    app._commit_identity = types.MethodType(DfitApp._commit_identity, app)
    return app


def test_fill_blanks_from_path_and_shutin_timestamp():
    app = _app(PickState(shutin_idx=7200))
    app._fill_identity_blanks()
    assert app.state.operator_at_test == "Anadarko Petroleum"
    assert app.state.job_date == "2019-05-05"  # 23:00 + 2 h at shut-in crosses midnight
    assert app.var_operator.get() == "Anadarko Petroleum"
    assert app.var_job_date.get() == "2019-05-05"
    assert len(app._identity_lines) == 2


def test_fill_never_overwrites_a_saved_value():
    app = _app(PickState(shutin_idx=0, operator_at_test="Occidental Petroleum",
                         job_date="2019-01-01"))
    app._fill_identity_blanks()
    assert app.state.operator_at_test == "Occidental Petroleum"
    assert app.state.job_date == "2019-01-01"
    assert app._identity_lines == []


def test_no_wall_clock_leaves_job_date_blank():
    app = _app(PickState(shutin_idx=0), start_time=None)
    app._fill_identity_blanks()
    assert app.state.job_date == ""


def test_commit_snaps_operator_and_normalizes_valid_entries():
    app = _app(PickState())
    app.var_operator.set(" civitas ")
    app.var_api.set("05-123-45678")
    app.var_job_date.set("5/4/2019")
    app._commit_identity()
    assert app.var_operator.get() == "Civitas Resources"
    assert app.var_api.get() == "0512345678"
    assert app.var_job_date.get() == "2019-05-04"
    assert (app.state.operator_at_test, app.state.api, app.state.job_date) == (
        "Civitas Resources", "0512345678", "2019-05-04")


def test_commit_keeps_invalid_text_for_the_note():
    app = _app(PickState())
    app.var_api.set("12345")
    app.var_job_date.set("someday")
    app._commit_identity()
    assert app.state.api == "12345"
    assert app.state.job_date == "someday"


def test_fill_runs_once_per_load():
    # A cleared suggestion stays cleared on the next Overview visit, and no line repeats.
    app = _app(PickState(shutin_idx=0))
    app._fill_identity_blanks()
    app.state.operator_at_test = ""
    app._fill_identity_blanks()
    assert app.state.operator_at_test == ""
    assert len(app._identity_lines) == 2


def test_nan_shutin_time_is_labeled_data_start():
    app = _app(PickState(shutin_idx=5))
    app.td.t_s[5] = np.nan
    app._fill_identity_blanks()
    assert app.state.job_date == "2019-05-04"
    assert app._identity_lines[-1].endswith("[data timestamp at data start]")


def test_commit_refreshes_only_on_change_and_restores_full_list():
    app = _app(PickState())
    app.cmb_operator["values"] = ["Apache"]
    app.var_operator.set("apache")
    app._commit_identity()
    assert app.refresh_calls == [1]
    assert app.cmb_operator["values"] == app._known_operators
    app._commit_identity()
    assert app.refresh_calls == [1]


def test_sync_stores_canonical_identity_without_touching_widgets():
    # Finish/Next sync without a focus-out: the log still gets the list's spelling.
    stub = types.SimpleNamespace(td=None, state=PickState(),
                                 _known_operators=identity.known_operators())
    for name, val in [("var_surface", ""), ("var_rate", ""), ("var_volume", ""),
                      ("var_bhp", "Calculated"), ("var_surface_unit", "auto"),
                      ("var_bhp_unit", "auto"), ("var_rate_unit", "auto"),
                      ("var_volume_unit", "auto"), ("var_density", ""),
                      ("var_density_fallback", False), ("var_tvd", ""), ("var_well", ""),
                      ("var_formation", ""), ("var_operator", "oxy"),
                      ("var_api", "05-123-45678"), ("var_job_date", "5/4/2019"),
                      ("var_alpha", "1.0"), ("var_step", "30")]:
        setattr(stub, name, _Var(val))
    DfitApp._sync_state_from_widgets(stub)
    assert (stub.state.operator_at_test, stub.state.api, stub.state.job_date) == (
        "Occidental Petroleum", "0512345678", "2019-05-04")
    assert stub.var_operator.get() == "oxy"


def test_commit_refreshes_after_a_mid_edit_sync_stored_the_value():
    # The state already holds the typed value (a sync ran mid-edit); the panel has not seen it.
    app = _app(PickState())
    app._fill_identity_blanks()
    app.var_api.set("12345")
    app.state.api = "12345"
    app._commit_identity()
    assert app.refresh_calls == [1]


class _MaskEntry:
    def __init__(self, cursor):
        self.cursor = cursor

    def bind(self, *a, **kw):
        pass

    def index(self, _what):
        return self.cursor

    def icursor(self, pos):
        self.cursor = pos


class _MaskVar(_Var):
    def trace_add(self, *a):
        pass


def _mask(edit, prev, text, cursor, key=None):
    m = ui._EntryMask(None, _MaskEntry(cursor), _MaskVar(text), edit)
    m.prev, m.key, m.pending = prev, key, True
    m.apply()
    return m


def test_api_entry_reformats_and_places_cursor():
    m = _mask(identity.format_api_edit, "05-12", "05-123", 6)
    assert (m.var.get(), m.entry.cursor) == ("05-123", 6)
    m = _mask(identity.format_api_edit, "05-123", "05-1234", 7)
    assert (m.var.get(), m.entry.cursor) == ("05-123-4", 8)
    assert m.prev == "05-123-4" and m.key is None and m.pending is False


def test_api_entry_paste_with_label():
    m = _mask(identity.format_api_edit, "", "API# 0512345678", 15, key="v")
    assert (m.var.get(), m.entry.cursor) == ("05-123-45678", 12)


def test_api_entry_backspace_over_dash():
    m = _mask(identity.format_api_edit, "05-123", "05123", 2, key="BackSpace")
    assert (m.var.get(), m.entry.cursor) == ("01-23", 1)


def test_job_date_entry_masks_and_converts_a_paste():
    m = _mask(identity.format_job_date_edit, "2019", "20190", 5)
    assert (m.var.get(), m.entry.cursor) == ("2019-0", 6)
    m = _mask(identity.format_job_date_edit, "", "5/4/2019", 8, key="v")
    assert (m.var.get(), m.entry.cursor) == ("2019-05-04", 10)
