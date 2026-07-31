"""
Reference solution for Exercise 3.

Don't read this until you've made a real attempt. Reading a solution
produces a strong feeling of understanding and very little actual
understanding. The feeling is the problem — it's why people re-watch
tutorials for a year and can't write anything from a blank file.

Compare, don't copy. If yours differs and passes, yours may well be better.
"""

from __future__ import annotations

import re

import pandas as pd

_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y")

# Canonical name -> the variants that map to it, lowercased and space-collapsed.
_DEPT_MAP: dict[str, str] = {}
for canonical, variants in {
    "Cardiology": ["cardiology", "cardio"],
    "General Medicine": ["general medicine", "gen med", "gen. medicine"],
    "Orthopedics": ["orthopedics", "ortho", "orthopaedics"],
    "Pulmonology": ["pulmonology", "pulm", "pulmonary"],
    "Nephrology": ["nephrology", "nephro", "renal"],
    "Emergency": ["emergency", "ed", "er", "emergency dept"],
}.items():
    for v in variants:
        _DEPT_MAP[v] = canonical

_MALE = {"m", "male", "1"}
_FEMALE = {"f", "female", "2"}


def _squash(value: str | None) -> str:
    """Trim, collapse internal runs of whitespace, lowercase."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def parse_flexible_date(value: str | None) -> pd.Timestamp:
    s = "" if value is None else str(value).strip()
    if not s:
        return pd.NaT
    for fmt in _DATE_FORMATS:
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT


def normalize_department(value: str | None) -> str | None:
    key = _squash(value).rstrip(".")
    return _DEPT_MAP.get(key)


def normalize_sex(value: str | None) -> str | None:
    key = _squash(value)
    if key in _MALE:
        return "M"
    if key in _FEMALE:
        return "F"
    # Assumption inherited from the legacy registration system: 1=M, 2=F.
    # Recorded here because it is an assumption, not a fact.
    return None


def parse_currency(value: str | None) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    negative = s.startswith("-")
    s = s.lstrip("-").lstrip("$").strip()
    if not s:
        return None
    try:
        amount = float(s)
    except ValueError:
        return None
    return -amount if negative else amount


def parse_lab_value(value: str | None) -> tuple[float | None, bool]:
    if value is None:
        return (None, False)
    s = str(value).strip()
    if not s:
        return (None, False)

    censored = s.startswith("<") or s.startswith(">")
    if censored:
        s = s[1:].strip()

    # Grab the leading number, discarding any trailing unit text.
    match = re.match(r"^[-+]?\d*\.?\d+", s)
    if not match:
        return (None, False)
    try:
        return (float(match.group()), censored)
    except ValueError:
        return (None, False)


def normalize_zip(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip().split("-")[0].strip()
    return s if re.fullmatch(r"\d{5}", s) else None
