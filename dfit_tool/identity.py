"""Pure helpers for a test's identity: operator at test, API number (or Alberta UWI), and job date.

Stdlib only, no ``dfit_tool`` imports, no Tkinter. ``model.compute_all`` calls the API and date
helpers to validate what was recorded; ``ui`` calls the operator helpers for suggestions and the
type-ahead list.
"""

from __future__ import annotations

import datetime as _dt
import math
import ntpath
import re
from typing import Iterable, Optional, Sequence

# First block: operators in the 2024 summary workbook's "Original Data" sheet (spelling kept,
# e.g. "Vermillion"). Second block: operator folders in C:\DFIT Data that the summary lacks.
SEED_OPERATORS: tuple[str, ...] = (
    "Abraxas Petroleum Corp", "Advance Energy Partners", "Anadarko Petroleum", "Apache",
    "Ballard Petroleum", "Birch Resources", "Black Hills", "Bonanza Creek", "Boomtown Oil",
    "Catamount Energy Partners", "Centennial Resources", "Civitas Resources", "Clear Creek",
    "Continental Resources", "Crescent Point", "Crestone Peak", "DJR", "Devon Energy", "EOG",
    "Edge Energy", "Edge Energy II", "Elk Mesa", "Emerald Oil", "Extraction Oil and Gas",
    "Fifth Creek", "Fulcrum Energy", "GMT Exploration", "Great Western", "Halcon Resources",
    "Hat Creek Resources", "Helis Oil & Gas", "Hess", "Highlands Natural Resources",
    "Impact E&P", "Kiwetinohk Energy", "Koch Exploration", "Koda Resources",
    "Laredo Petroleum", "Leucrotta Exploration", "Liberty Resources", "Lucero Energy",
    "Mallard Exploration", "Nickel Road Operating", "Noble Energy", "North Peak",
    "North Plains Energy", "North Silo", "Occidental Petroleum", "PDC", "Paramount Resources",
    "Permian Resources", "Red Willow", "Rockies Resources", "SM Energy", "Samson Exploration",
    "Sandpoint Resources", "Shell", "Strathcona Resources", "Synergy", "Talisman Energy",
    "Tap Rock Resources", "Vermillion", "Vesta Energy", "WPX Energy", "Ward Petroleum",
    "Wave Petroleum", "Whiting Oil and Gas", "Zavanna",
    "ARC Resources", "Aspect Energy", "B-32 Exploration", "Bright Rock", "Conoco Phillips",
    "Cygnet", "Enduring Resources", "Kinney Oil", "Laramie Energy", "Lonestar Operating",
    "Phoenix Energy", "Roost Resources", "Tamboran", "True Oil", "Williams",
)

# Normalized alias -> seed name. Applies only when the target is in the known list in use.
OPERATOR_ALIASES: dict[str, str] = {
    "apc": "Anadarko Petroleum",
    "anadarko": "Anadarko Petroleum",
    "oxy": "Occidental Petroleum",
    "crestone": "Crestone Peak",
    "vermilion": "Vermillion",
    # Operator folders named by a one-word core, which paths never match on its own.
    "civitas": "Civitas Resources",
    "kiwetinohk": "Kiwetinohk Energy",
    "laredo": "Laredo Petroleum",
}

_GENERIC_TOKENS = frozenset({
    "corp", "corporation", "inc", "llc", "ltd", "co", "company", "energy", "resources",
    "petroleum", "oil", "gas", "and", "exploration", "operating", "partners",
})
_GENERIC_PHRASE = ("e", "and", "p")

# Company-name noise in OneDrive/user paths that must never suggest Liberty Resources.
_PATH_NOISE_RE = re.compile(r"(?:^| )(?:liberty oilfield services|liberty energy|liberty os)(?= |$)")

_API_LENGTHS_TRUNCATED = (12, 14)
_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_US_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_PATH_PARENTS_WITHOUT_TOP = 4


def operator_key(name: str) -> str:
    """Casefolded name with `&` as "and", other punctuation as spaces, whitespace collapsed."""
    s = name.casefold().replace("&", " and ")
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return " ".join(s.split())


def operator_core(name: str) -> str:
    """`operator_key` with trailing generic words removed; never fewer than one word."""
    toks = operator_key(name).split()
    while len(toks) > 1:
        if len(toks) > len(_GENERIC_PHRASE) and tuple(toks[-3:]) == _GENERIC_PHRASE:
            del toks[-3:]
        elif toks[-1] in _GENERIC_TOKENS:
            toks.pop()
        else:
            break
    return " ".join(toks)


def known_operators(extra: Iterable[object] = ()) -> list[str]:
    """Seed operators plus `extra` names (non-str, blank, and duplicate entries are skipped).

    An entry duplicates an earlier one when its key or core equals the other's key or core, so
    the seed spelling wins. Sorted case-insensitively."""
    kept: list[str] = []
    seen: set[str] = set()
    for item in list(SEED_OPERATORS) + list(extra):
        if not isinstance(item, str):
            continue
        name = item.strip()
        if not operator_key(name):
            continue
        ids = {operator_key(name), operator_core(name)}
        if ids & seen:
            continue
        kept.append(name)
        seen |= ids
    return sorted(kept, key=str.casefold)


def canonical_operator(text: str, known: Iterable[str]) -> str:
    """The known spelling that `text` names (by key, core, or alias), else `text` stripped."""
    s = text.strip() if isinstance(text, str) else ""
    if not operator_key(s):
        return ""
    names = list(known)
    by_key: dict[str, str] = {}
    by_core: dict[str, str] = {}
    for n in names:
        by_key.setdefault(operator_key(n), n)
        by_core.setdefault(operator_core(n), n)
    cands = [operator_key(s), operator_core(s)]
    target = OPERATOR_ALIASES.get(operator_key(s))
    if target is not None and operator_key(target) in by_key:
        cands.append(operator_key(target))
    for c in cands:
        if c in by_key:
            return by_key[c]
        if c in by_core:
            return by_core[c]
    return s


def filter_operators(known: Iterable[str], typed: str) -> list[str]:
    """Type-ahead filter: names whose key contains the typed key, order preserved."""
    names = list(known)
    tk = operator_key(typed or "")
    if not tk:
        return names
    return [n for n in names if tk in operator_key(n)]


def _phrases_by_operator(known: Iterable[str]) -> dict[str, set[str]]:
    """Each known operator's match phrases: its key, its core when that is two or more words,
    and aliases pointing at it. A one-word core ("rockies", "true", "liberty") is a common place
    or well word, so it never matches path text alone; a one-word key ("Williams") still does."""
    out: dict[str, set[str]] = {}
    for n in known:
        core = operator_core(n)
        phrases = {operator_key(n)} | ({core} if " " in core else set())
        for alias, target in OPERATOR_ALIASES.items():
            if operator_key(target) == operator_key(n):
                phrases.add(alias)
        phrases.discard("")
        if phrases:
            out[n] = phrases
    return out


def _path_components(path: str, top: Optional[str]) -> list[str]:
    """Shallowest-first folder names to search, with the file stem last."""
    p = ntpath.normpath(path)
    stem = ntpath.splitext(ntpath.basename(p))[0]
    dirs: Optional[list[str]] = None
    if top:
        t = ntpath.normpath(top)
        tn, pn = ntpath.normcase(t), ntpath.normcase(p)
        if pn.startswith(tn.rstrip("\\") + "\\"):
            rel = p[len(t.rstrip("\\")) + 1:]
            between = [d for d in ntpath.dirname(rel).split("\\") if d]
            dirs = [ntpath.basename(t.rstrip("\\"))] + between
    if dirs is None:
        parent = ntpath.splitdrive(ntpath.dirname(p))[1]
        dirs = [d for d in parent.split("\\") if d][-_PATH_PARENTS_WITHOUT_TOP:]
    return dirs + [stem]


def suggest_operator(path: str, known: Iterable[str],
                     top: Optional[str] = None) -> Optional[tuple[str, str]]:
    """`(operator, component text)` for the shallowest path component naming a known operator.

    Components are `top`'s folder plus the folders under it when `path` is inside `top`, else
    the last four parent folders; the file stem is last. Within a component the longest match
    wins and a tie between two operators skips that component."""
    phrases = _phrases_by_operator(known)
    for comp in _path_components(path, top):
        ckey = _PATH_NOISE_RE.sub("", operator_key(comp)).strip()
        if not ckey:
            continue
        padded = f" {ckey} "
        best_len, best = 0, set()
        for name, ps in phrases.items():
            hit = max((len(ph) for ph in ps if f" {ph} " in padded), default=0)
            if hit > best_len:
                best_len, best = hit, {name}
            elif hit and hit == best_len:
                best.add(name)
        if len(best) == 1:
            return next(iter(best)), comp
    return None


def normalize_api(text: object) -> Optional[str]:
    """10-digit US API number, else an Alberta UWI in ST37 form (`normalize_uwi`), else None.

    API: accepts dashes/spaces/dots, 9 digits not starting with 0 (Excel dropped the leading 0;
    a 9-digit "05..." is unfinished), and 12 or 14 digits (well-bore and event suffixes are
    cut)."""
    return _normalize_us_api(text) or normalize_uwi(text)


# Dominion Land Survey UWI, whitespace removed and uppercased: an optional prefix (the 16-
# character form's survey-system "1" plus the 2-character location exception), LSD-section-
# township-range, W + meridian, an optional event sequence.
_UWI_RE = re.compile(r"^(?:1?(?P<le>[0-9A-Z]{2})/)?(?P<lsd>\d{1,2})-(?P<sec>\d{1,2})-"
                     r"(?P<twp>\d{1,3})-(?P<rge>\d{1,2})W(?P<mer>\d)(?:/0?(?P<ev>\d))?$")
_UWI_RANGES = {"lsd": (1, 16), "sec": (1, 36), "twp": (1, 126), "rge": (1, 30), "mer": (4, 6)}


def normalize_uwi(text: object) -> Optional[str]:
    """Alberta UWI in AER ST37 `Well_UWI` form, `00/14-22-065-16W5/0`, or None.

    Accepts the 16-character form (`100/14-22-065-16W5/00`), the short form with no location
    exception or event (`14-22-065-16W5`, which gets `00/` and `/0`), unpadded parts, any
    whitespace, and a lowercase `w`. A part out of range (LSD 1-16, section 1-36, township 1-126,
    range 1-30, meridian W4-W6) is invalid, as is a 2-digit event not starting with 0."""
    if not isinstance(text, str):
        return None
    m = _UWI_RE.match(re.sub(r"\s+", "", text).upper())
    if m is None:
        return None
    n = {k: int(m[k]) for k in _UWI_RANGES}
    if any(not lo <= n[k] <= hi for k, (lo, hi) in _UWI_RANGES.items()):
        return None
    return (f"{m['le'] or '00'}/{n['lsd']:02d}-{n['sec']:02d}-{n['twp']:03d}-{n['rge']:02d}"
            f"W{n['mer']}/{m['ev'] or '0'}")


def _normalize_us_api(text: object) -> Optional[str]:
    if text is None:
        return None
    if isinstance(text, float):
        if not math.isfinite(text) or not text.is_integer():
            return None
        text = int(text)
    s = re.sub(r"[\s.\-]+", "", str(text))
    if not s.isascii() or not s.isdigit():
        return None
    if len(s) == 10:
        return s
    if len(s) == 9:
        return None if s.startswith("0") else "0" + s
    if len(s) in _API_LENGTHS_TRUNCATED:
        return s[:10]
    return None


# Display groups: an API is state-county-well, then the 2-digit sidetrack and event codes.
_API_GROUPS = (2, 3, 5, 2, 2)
_DATE_GROUPS = (4, 2, 2)
# A separator typed after one digit of the month (5 digits before the cursor) or of the day
# (7) zero-pads it, so "2019-5-" reads "2019-05".
_DATE_PAD_AT = (5, 7)
_SEPARATOR_KEYS = frozenset({"minus", "period", "space", "slash"})


def _digits(text: object) -> str:
    return re.sub(r"\D", "", str(text or ""))


def _group(digits: str, groups: tuple[int, ...]) -> str:
    """`digits` (cut to the groups' total) joined with dashes at the group boundaries."""
    digits = digits[:sum(groups)]
    parts, i = [], 0
    for size in groups:
        if i >= len(digits):
            break
        parts.append(digits[i:i + size])
        i += size
    return "-".join(parts)


def _mask_edit(prev: str, text: str, cursor: int, key: Optional[str],
               groups: tuple[int, ...], pad_at: tuple[int, ...] = ()) -> tuple[str, int]:
    """Shared entry mask: regroup the digits of `text` and keep the cursor just after the same
    digit it followed. A BackSpace or Delete that removed only a dash also removes the digit
    beside it, so the key never seems to do nothing. A separator key typed with `pad_at` digits
    before the cursor zero-pads the one-digit group it closes."""
    before = len(_digits(text[:cursor]))
    digits = _digits(text)
    if (key in ("BackSpace", "Delete") and len(text) < len(prev)
            and digits == _digits(prev)):
        if key == "BackSpace" and before > 0:
            digits = digits[:before - 1] + digits[before:]
            before -= 1
        elif key == "Delete" and before < len(digits):
            digits = digits[:before] + digits[before + 1:]
    if key in _SEPARATOR_KEYS and before in pad_at:
        digits = digits[:before - 1] + "0" + digits[before - 1:]
        before += 1
    new = _group(digits, groups)
    before = min(before, len(_digits(new)))
    pos, seen = 0, 0
    while seen < before:
        if new[pos].isdigit():
            seen += 1
        pos += 1
    return new, pos


def format_api(text: object) -> str:
    """The digits of `text` (at most 14) grouped as `SS-CCC-WWWWW-SS-EE` for display. Anything
    but digits is dropped, so a pasted "API: 05 123 45678" reads "05-123-45678"."""
    return _group(_digits(text), _API_GROUPS)


def format_api_edit(prev: str, text: str, cursor: int,
                    key: Optional[str] = None) -> tuple[str, int]:
    """Reformat the API entry after an edit: `prev` is the formatted text before it, `text` and
    `cursor` the entry after it, `key` the keysym that made it (if any). Returns the new text and
    cursor index (see `_mask_edit`). A UWI being typed or pasted (`_is_uwi_edit`) is left as
    typed; the commit normalizes it."""
    if _is_uwi_edit(prev, text, cursor, key):
        head = text[:cursor]
        if (head.endswith("/") and len(text) == len(prev) + 1 and prev == format_api(prev)
                and len(_digits(head)) <= 3):
            # "100" was masked "10-0" before the "/" showed it was a UWI prefix.
            head = head.replace("-", "")
            return head + text[cursor:], len(head)
        return text, cursor
    return _mask_edit(prev, text, cursor, key, _API_GROUPS)


# Digit counts an API dash follows (the boundaries of _API_GROUPS).
_API_DASH_AT = frozenset(sum(_API_GROUPS[:i]) for i in range(1, len(_API_GROUPS)))


def _is_uwi_edit(prev: str, text: str, cursor: int, key: Optional[str]) -> bool:
    """Whether the API entry holds a UWI in progress: a `/` or a meridian (`16W5`); a letter or a
    `-` typed where an API has no dash (`14-22-`, `1-`); or an edit to text already left as
    typed that still has a separator or letter. A pasted "API: 05 123 45678" or
    "05-123-45678 Weld" stays an API."""
    if "/" in text or re.search(r"\d\s*[Ww]\s*\d", text):
        return True
    inserted = len(text) == len(prev) + 1 and 0 < cursor <= len(text)
    if inserted and text[cursor - 1].isalpha():
        return True
    if (key == "minus" and inserted and text[cursor - 1] == "-"
            and len(_digits(text[:cursor])) not in _API_DASH_AT):
        return True
    return prev != format_api(prev) and bool(re.search(r"[-A-Za-z]", text))


def format_job_date(text: object) -> str:
    """The digits of `text` (at most 8) grouped as `YYYY-MM-DD`."""
    return _group(_digits(text), _DATE_GROUPS)


def format_job_date_edit(prev: str, text: str, cursor: int,
                         key: Optional[str] = None) -> tuple[str, int]:
    """Reformat the job date entry after an edit (arguments as `format_api_edit`). A paste or
    other multi-character insert that is already a full date (`2019-5-4`, `5/4/2019`) becomes
    ISO at once. Text with a `/` is M/D/YYYY being typed and is left alone (the commit converts
    it). Otherwise the digits are masked as `YYYY-MM-DD`."""
    if len(text) - len(prev) > 1 and re.search(r"\D", text):
        iso = parse_job_date(text)
        if iso is not None:
            return iso, len(iso)
    if "/" in text:
        return text, cursor
    return _mask_edit(prev, text, cursor, key, _DATE_GROUPS, _DATE_PAD_AT)


def parse_job_date(text: object) -> Optional[str]:
    """ISO `YYYY-MM-DD` from `YYYY-M-D` or `M/D/YYYY`, or None when not a real calendar date."""
    if text is None:
        return None
    s = str(text).strip()
    m = _ISO_DATE_RE.match(s)
    if m:
        y, mo, d = (int(g) for g in m.groups())
    else:
        m = _US_DATE_RE.match(s)
        if not m:
            return None
        mo, d, y = (int(g) for g in m.groups())
    try:
        return _dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


def job_date_from_data(start_time: Optional[_dt.datetime], t_s: Sequence[float],
                       shutin_idx: Optional[int]) -> Optional[str]:
    """Calendar date of shut-in (else of the first sample) as ISO text; None without a start."""
    if start_time is None:
        return None
    offset = 0.0
    if shutin_idx is not None and 0 <= int(shutin_idx) < len(t_s):
        v = float(t_s[int(shutin_idx)])
        if math.isfinite(v):
            offset = v
    return (start_time + _dt.timedelta(seconds=offset)).date().isoformat()
