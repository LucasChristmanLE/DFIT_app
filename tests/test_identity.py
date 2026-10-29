"""Tests for the pure identity helpers (operator, API number, job date)."""
import datetime as dt

import numpy as np
import pytest

from dfit_tool import identity as idn


def test_seed_list_shape():
    assert idn.SEED_OPERATORS[0] == "Abraxas Petroleum Corp"
    assert idn.SEED_OPERATORS[-1] == "Williams"
    assert len(set(idn.SEED_OPERATORS)) == len(idn.SEED_OPERATORS)


@pytest.mark.parametrize("name,key", [
    ("Helis Oil & Gas", "helis oil and gas"),
    ("B-32 Exploration", "b 32 exploration"),
    ("Impact E&P", "impact e and p"),
    ("  Black   Hills ", "black hills"),
])
def test_operator_key(name, key):
    assert idn.operator_key(name) == key


@pytest.mark.parametrize("name,core", [
    ("Extraction Oil and Gas", "extraction"),
    ("Whiting Oil & Gas Corp", "whiting"),
    ("Edge Energy II", "edge energy ii"),
    ("Edge Energy", "edge"),
    ("Impact E&P", "impact"),
    ("Shell", "shell"),
    ("Black Hills", "black hills"),
    ("Energy", "energy"),
])
def test_operator_core(name, core):
    assert idn.operator_core(name) == core


def test_known_operators_seed_survives_dedupe():
    known = idn.known_operators()
    assert sorted(known, key=str.casefold) == known
    assert set(known) == set(idn.SEED_OPERATORS)


def test_known_operators_extra_dedupes_and_skips_junk():
    known = idn.known_operators(
        ["PDC Energy", " Brand New Operator ", "", None, float("nan"), "civitas"])
    assert "PDC Energy" not in known
    assert "PDC" in known
    assert "Brand New Operator" in known
    assert "civitas" not in known
    assert len(known) == len(idn.SEED_OPERATORS) + 1


@pytest.mark.parametrize("text,want", [
    ("civitas", "Civitas Resources"),
    ("Extraction Oil & Gas", "Extraction Oil and Gas"),
    ("Fifth Creek Energy", "Fifth Creek"),
    ("PDC Energy", "PDC"),
    ("Synergy Resources", "Synergy"),
    ("Whiting Oil & Gas Corp", "Whiting Oil and Gas"),
    ("Zavanna LLC", "Zavanna"),
    ("Kiwetinohk", "Kiwetinohk Energy"),
    ("Laredo", "Laredo Petroleum"),
    ("APC", "Anadarko Petroleum"),
    ("Vermilion", "Vermillion"),
    ("Edge Energy II", "Edge Energy II"),
    ("edge energy", "Edge Energy"),
    ("  Brand New Operator ", "Brand New Operator"),
    ("   ", ""),
])
def test_canonical_operator(text, want):
    assert idn.canonical_operator(text, idn.known_operators()) == want


def test_alias_needs_target_in_known():
    assert idn.canonical_operator("APC", ["Shell"]) == "APC"


def test_filter_operators():
    known = ["Helis Oil & Gas", "Shell", "Black Hills"]
    assert idn.filter_operators(known, "") == known
    assert idn.filter_operators(known, "heli") == ["Helis Oil & Gas"]
    assert idn.filter_operators(known, "oil &") == ["Helis Oil & Gas"]
    assert idn.filter_operators(known, "zzz") == []


KNOWN = idn.known_operators()


def test_suggest_dbs_folder_alias():
    p = r"C:\DFIT Organized\DJ\APC Badger 11N-3HZ\Badger 11N-3HZ Final.dbs"
    assert idn.suggest_operator(p, KNOWN) == ("Anadarko Petroleum", "APC Badger 11N-3HZ")


def test_suggest_shallowest_wins():
    p = r"C:\DFIT Data\WPX Energy\Williams 12-3H\x.csv"
    assert idn.suggest_operator(p, KNOWN) == ("WPX Energy", "WPX Energy")


def test_suggest_onedrive_not_liberty():
    p = (r"C:\Users\Someone\OneDrive - Liberty Oilfield Services\Documents"
         r"\DFIT Project\Akbary 36-3H\x.csv")
    assert idn.suggest_operator(p, KNOWN) is None


def test_suggest_top_reaches_far_folder():
    p = r"C:\DFIT Data\Civitas\Well 1\Data\Final\Raw\x.csv"
    assert idn.suggest_operator(p, KNOWN) is None
    got = idn.suggest_operator(p, KNOWN, top=r"C:\DFIT Data\Civitas")
    assert got == ("Civitas Resources", "Civitas")


def test_suggest_top_forward_slashes_and_case():
    p = "c:/dfit data/Civitas/Well 1/Data/Final/x.csv"
    got = idn.suggest_operator(p, KNOWN, top=r"C:\DFIT Data\Civitas")
    assert got == ("Civitas Resources", "Civitas")


def test_suggest_ampersand_folder():
    p = r"C:\DFIT Data\Extraction Oil & Gas\Well\x.csv"
    assert idn.suggest_operator(p, KNOWN)[0] == "Extraction Oil and Gas"


def test_suggest_longest_match_wins():
    p = r"C:\DFIT Data\Edge Energy II\Well\x.csv"
    assert idn.suggest_operator(p, KNOWN)[0] == "Edge Energy II"


def test_suggest_from_filename_only():
    p = r"C:\x\y\Anadarko BBKB 25E-3HZ DFIT Merged.dbs"
    assert idn.suggest_operator(p, KNOWN) == (
        "Anadarko Petroleum", "Anadarko BBKB 25E-3HZ DFIT Merged")


def test_suggest_alias_prefix_folder():
    p = r"C:\data\Crestone Echeverria D Well\x.csv"
    assert idn.suggest_operator(p, KNOWN)[0] == "Crestone Peak"


def test_suggest_tie_skips_component():
    known = ["Alpha Energy", "Alpha Oil"]
    assert idn.suggest_operator(r"C:\a\Alpha 1\x.csv", known) is None


def test_suggest_learned_operator():
    known = idn.known_operators(["Brand New Operator"])
    p = r"C:\data\Brand New Operator\w\x.csv"
    assert idn.suggest_operator(p, known)[0] == "Brand New Operator"


@pytest.mark.parametrize("text,want", [
    ("05-123-45678", "0512345678"),
    ("0512345678", "0512345678"),
    ("512345678", "0512345678"),
    ("49-005-62791-00-00", "4900562791"),
    ("05-123-45678-00", "0512345678"),
    (" 05.123.45678 ", "0512345678"),
    (512345678, "0512345678"),
    ("12345", None),
    ("abc", None),
    ("05-123-4567A", None),
    ("", None),
    ("  ", None),
    (None, None),
])
def test_normalize_api(text, want):
    assert idn.normalize_api(text) == want


@pytest.mark.parametrize("text,want", [
    ("2019-05-04", "2019-05-04"),
    ("2019-5-4", "2019-05-04"),
    ("5/4/2019", "2019-05-04"),
    ("05/04/2019", "2019-05-04"),
    (" 12/31/2020 ", "2020-12-31"),
    ("13/40/2020", None),
    ("2020-02-30", None),
    ("5/4/19", None),
    ("hello", None),
    ("", None),
    (None, None),
])
def test_parse_job_date(text, want):
    assert idn.parse_job_date(text) == want


def test_job_date_from_data_basic_and_midnight():
    start = dt.datetime(2019, 5, 4, 23, 0, 0)
    assert idn.job_date_from_data(start, [0.0, 7200.0], 1) == "2019-05-05"
    assert idn.job_date_from_data(start, [0.0, 7200.0], 0) == "2019-05-04"


def test_job_date_from_data_fallbacks():
    start = dt.datetime(2019, 5, 4, 23, 0, 0)
    assert idn.job_date_from_data(None, [0.0], 0) is None
    assert idn.job_date_from_data(start, [0.0, 7200.0], None) == "2019-05-04"
    assert idn.job_date_from_data(start, [0.0, 7200.0], 5) == "2019-05-04"
    assert idn.job_date_from_data(start, [0.0, 7200.0], -1) == "2019-05-04"
    assert idn.job_date_from_data(start, [0.0, float("nan")], 1) == "2019-05-04"


def test_job_date_from_data_numpy():
    start = dt.datetime(2019, 5, 4, 23, 0, 0)
    t = np.array([0.0, 3600.0, 7200.0])
    assert idn.job_date_from_data(start, t, np.int64(2)) == "2019-05-05"


# Review: a one-word core ("rockies", "true", "liberty") is a common place or well word, so it
# never matches path text; the folders that relied on one have explicit aliases.
@pytest.mark.parametrize("path", [
    r"C:\DFIT Data\Rockies\Foo\well.csv",
    r"C:\x\True Vertical\a.csv",
    r"C:\x\Liberty DFITs\Pad\b.csv",
])
def test_one_word_core_never_matches_a_path(path):
    assert idn.suggest_operator(path, idn.known_operators()) is None


@pytest.mark.parametrize("folder, expected", [
    ("Civitas", "Civitas Resources"),
    ("Kiwetinohk", "Kiwetinohk Energy"),
    ("Laredo", "Laredo Petroleum"),
    ("Rockies Resources", "Rockies Resources"),
    ("Fifth Creek Energy", "Fifth Creek"),
])
def test_operator_folders_still_match(folder, expected):
    hit = idn.suggest_operator(rf"C:\DFIT Data\{folder}\Well\x.csv", idn.known_operators())
    assert hit is not None and hit[0] == expected


# --------------------------------------------------------------------------------------------------
# API entry mask: dashes inserted as digits are typed or pasted
# --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text, expected", [
    ("", ""),
    ("0", "0"),
    ("05", "05"),
    ("051", "05-1"),
    ("05123", "05-123"),
    ("051234", "05-123-4"),
    ("0512345678", "05-123-45678"),
    ("051234567800", "05-123-45678-00"),
    ("05123456780000", "05-123-45678-00-00"),
    ("0512345678000099", "05-123-45678-00-00"),  # past 14 digits is dropped
    ("API: 05 123 45678", "05-123-45678"),  # pasted with a label and spaces
    ("05-123-45678", "05-123-45678"),
])
def test_format_api(text, expected):
    assert idn.format_api(text) == expected


def test_format_api_edit_typing_past_a_group_moves_over_the_dash():
    # "05|" + "1" typed -> "05-1|"
    assert idn.format_api_edit("05", "051", 3) == ("05-1", 4)


def test_format_api_edit_typing_in_the_middle_keeps_the_cursor_after_the_digit():
    # "05-1|23" + "9" -> digits 0519 23 -> "05-192-3", cursor after the 9
    assert idn.format_api_edit("05-123", "05-1923", 5) == ("05-192-3", 5)


def test_format_api_edit_paste_puts_the_cursor_at_the_end():
    assert idn.format_api_edit("", "05-123-45678", 12) == ("05-123-45678", 12)
    assert idn.format_api_edit("", "0512345678", 10) == ("05-123-45678", 12)


def test_format_api_edit_backspace_over_a_dash_removes_the_digit_before_it():
    # "05-|123", BackSpace deletes only the dash -> take the "5" with it
    assert idn.format_api_edit("05-123", "05123", 2, key="BackSpace") == ("01-23", 1)


def test_format_api_edit_delete_over_a_dash_removes_the_digit_after_it():
    # "05|-123", Delete deletes only the dash -> take the "1" with it
    assert idn.format_api_edit("05-123", "05123", 2, key="Delete") == ("05-23", 2)


def test_format_api_edit_backspace_on_a_digit_reflows():
    # "05-12|3" BackSpace -> "05-13", cursor after the 1
    assert idn.format_api_edit("05-123", "05-13", 4, key="BackSpace") == ("05-13", 4)


def test_format_api_edit_trailing_dash_left_by_backspace_is_dropped():
    # "05-1|" BackSpace -> "05-" -> "05", cursor at the end
    assert idn.format_api_edit("05-1", "05-", 3, key="BackSpace") == ("05", 2)


def test_format_api_edit_cursor_at_start():
    assert idn.format_api_edit("", "05", 0) == ("05", 0)


def test_nine_digits_starting_with_zero_is_incomplete_not_padded():
    # Excel drops the 0 of "05", so a mangled API starts with 5; a 9-digit "05..." is unfinished.
    assert idn.normalize_api("05-123-4567") is None
    assert idn.normalize_api("512345678") == "0512345678"


# --------------------------------------------------------------------------------------------------
# Job date entry mask: YYYY-MM-DD dashes as digits are typed; M/D/YYYY passes through
# --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text, expected", [
    ("", ""),
    ("2019", "2019"),
    ("20190", "2019-0"),
    ("201905", "2019-05"),
    ("20190504", "2019-05-04"),
    ("201905041", "2019-05-04"),  # past 8 digits is dropped
])
def test_format_job_date(text, expected):
    assert idn.format_job_date(text) == expected


def test_date_edit_typing_inserts_dashes():
    assert idn.format_job_date_edit("2019", "20190", 5) == ("2019-0", 6)
    assert idn.format_job_date_edit("2019-05", "2019-050", 8) == ("2019-05-0", 9)


def test_date_edit_typing_a_day_digit_is_not_padded_early():
    # "2019-01" + "1": the day is unfinished, not 2019-01-01.
    assert idn.format_job_date_edit("2019-01", "2019-011", 8) == ("2019-01-1", 9)


def test_date_edit_separator_pads_a_one_digit_month_and_day():
    assert idn.format_job_date_edit("2019-5", "2019-5-", 7, key="minus") == ("2019-05", 7)
    assert idn.format_job_date_edit("2019-05-4", "2019-05-4-", 10, key="minus") == (
        "2019-05-04", 10)


def test_date_edit_separator_after_a_full_group_does_nothing():
    assert idn.format_job_date_edit("2019", "2019-", 5, key="minus") == ("2019", 4)


@pytest.mark.parametrize("pasted", ["2019-5-4", "5/4/2019", "2019-05-04"])
def test_date_edit_paste_of_a_full_date_becomes_iso(pasted):
    assert idn.format_job_date_edit("", pasted, len(pasted), key="v") == ("2019-05-04", 10)


def test_date_edit_slash_typing_is_left_as_typed():
    assert idn.format_job_date_edit("5/4", "5/4/", 4, key="slash") == ("5/4/", 4)
    assert idn.format_job_date_edit("5/4/201", "5/4/2019", 8) == ("5/4/2019", 8)


def test_date_edit_backspace_over_dash_removes_the_digit_before_it():
    assert idn.format_job_date_edit("2019-05", "201905", 4, key="BackSpace") == ("2010-5", 3)
