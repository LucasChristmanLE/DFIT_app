"""Test identity (API, operator at test, job date) through compute_all, the log, and results."""

from __future__ import annotations

import json
import os

from dfit_tool import store, summary
from dfit_tool.model import PickState, compute_all
from tests.helpers import injection_state, make_testdata


def _state(**kw):
    td = make_testdata()
    st = injection_state(td)
    for k, v in kw.items():
        setattr(st, k, v)
    return st, td


def _log_row(tmp_path, st, td):
    res = compute_all(st, td)
    entry = store.TestEntry(test_id="well1", folder=str(tmp_path))
    return store.build_log_row(entry, os.path.join(str(tmp_path), "well1.csv"), str(tmp_path),
                               st, td, res)


def test_log_columns_end_with_identity():
    assert store.LOG_COLUMNS[-3:] == ["api", "operator_at_test", "job_date"]


def test_valid_identity_is_normalized_and_logged(tmp_path):
    st, td = _state(api="05-123-45678", operator_at_test="Anadarko Petroleum",
                    job_date="5/4/2019")
    res = compute_all(st, td)
    assert res.api == "0512345678"
    assert res.job_date == "2019-05-04"
    assert not any("API" in n or "Job date" in n or "Identity" in n for n in res.notes)
    row = _log_row(tmp_path, st, td)
    assert row["api"] == "0512345678"
    assert row["operator_at_test"] == "Anadarko Petroleum"
    assert row["job_date"] == "2019-05-04"


def test_invalid_api_and_date_are_noted_not_logged(tmp_path):
    st, td = _state(api="12345", operator_at_test="X", job_date="2020-02-30")
    res = compute_all(st, td)
    assert res.api is None and res.job_date is None
    assert any(n.startswith("API '12345'") for n in res.notes)
    assert any(n.startswith("Job date '2020-02-30'") for n in res.notes)
    assert all(len(n) <= 90 for n in res.notes)
    row = _log_row(tmp_path, st, td)
    assert row["api"] is None and row["job_date"] is None


def test_alberta_uwi_is_normalized_and_logged(tmp_path):
    st, td = _state(api="14-22-065-16W5", operator_at_test="GMT Exploration",
                    job_date="2022-01-15")
    res = compute_all(st, td)
    assert res.api == "00/14-22-065-16W5/0"
    assert not any("API" in n for n in res.notes)
    assert _log_row(tmp_path, st, td)["api"] == "00/14-22-065-16W5/0"


def test_invalid_uwi_is_noted_not_logged(tmp_path):
    st, td = _state(api="14-37-065-16W5", operator_at_test="X", job_date="2022-01-15")
    res = compute_all(st, td)
    assert res.api is None
    assert "API '14-37-065-16W5' is not a 10-digit API or an Alberta UWI; not logged" in res.notes
    assert _log_row(tmp_path, st, td)["api"] is None


def test_uwi_round_trips_through_log_file(tmp_path):
    st, td = _state(api="00/14-22-065-16W5/0", job_date="2022-01-15")
    path = str(tmp_path / "dfit_log.csv")
    log = store.upsert_log_row(store.load_log_file(path), _log_row(tmp_path, st, td))
    store.save_log_file(path, log)
    assert store.load_log_file(path).loc[0, "api"] == "00/14-22-065-16W5/0"


def test_uwi_shows_in_expanded_results():
    st, td = _state(api="00/14-22-065-16W5/0", job_date="2022-01-15")
    res = compute_all(st, td)
    rows = [row for sec in summary.summary_sections(st, res) for row in sec.rows]
    assert ["API / UWI", "00/14-22-065-16W5/0"] in rows


def test_blank_identity_gives_one_note():
    st, td = _state()
    res = compute_all(st, td)
    blank = [n for n in res.notes if n.startswith("Identity blank")]
    assert blank == ["Identity blank: operator, API, job date"]


def test_api_keeps_leading_zero_through_log_file(tmp_path):
    st, td = _state(api="0512345678", job_date="2019-05-04")
    path = str(tmp_path / "dfit_log.csv")
    log = store.upsert_log_row(store.load_log_file(path), _log_row(tmp_path, st, td))
    store.save_log_file(path, log)
    back = store.load_log_file(path)
    assert back.loc[0, "api"] == "0512345678"
    assert back.loc[0, "job_date"] == "2019-05-04"


def test_identity_round_trips_through_picks_json(tmp_path):
    st = PickState(api="0512345678", operator_at_test="Civitas Resources", job_date="2021-01-02")
    p = str(tmp_path / "p.json")
    st.to_json(p)
    back = PickState.from_json(p)
    assert (back.api, back.operator_at_test, back.job_date) == (
        "0512345678", "Civitas Resources", "2021-01-02")


def test_old_save_without_identity_loads_blank(tmp_path):
    p = tmp_path / "old.json"
    p.write_text(json.dumps({"well_name": "W"}))
    back = PickState.from_json(str(p))
    assert (back.api, back.operator_at_test, back.job_date) == ("", "", "")


def test_inputs_section_lists_identity_first():
    st, td = _state(api="0512345678", operator_at_test="PDC", job_date="2019-05-04")
    res = compute_all(st, td)
    sec = next(s for s in summary.summary_sections(st, res) if s.title == "Inputs and data")
    assert sec.rows[:3] == [["operator", "PDC"], ["API / UWI", "0512345678"],
                            ["job date", "2019-05-04"]]


def test_null_identity_in_foreign_json_decodes_blank(tmp_path):
    p = tmp_path / "foreign.json"
    p.write_text(json.dumps({"operator_at_test": None, "api": 512345678, "job_date": None}))
    back = PickState.from_json(str(p))
    assert (back.operator_at_test, back.api, back.job_date) == ("", "512345678", "")
