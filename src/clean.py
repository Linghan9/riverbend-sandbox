"""
Cleaning primitives for the Riverbend data.

These are stubs. You implement them. `tests/test_clean.py` is the spec —
read it before you write anything, then make it green.

Keep every function pure: input in, value out, no file reads, no globals.
Pure functions are trivially testable, and that is not a coincidence.
"""

from __future__ import annotations

import pandas as pd


def parse_flexible_date(value: str | None) -> pd.Timestamp:
    """
    Parse a date that may arrive in any of three formats:

        2024-03-15      ISO
        03/15/2024      US
        15-MAR-2024     Oracle-style

    Blank, None, or unparseable input returns pd.NaT.
    Do not use a bare pd.to_datetime with no format — it will silently
    guess wrong on ambiguous values and you will not notice for weeks.
    """
    s = "" if value is None else str(value).strip()
    if not s:
        return pd.NaT
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT


_DEPT_MAP = {
        "cardiology": "Cardiology",
        "cardio": "Cardiology",
        "gen med": "General Medicine",
        "general Med": "General Medicine",
        "orthopedics": "Orthopedics",
        "orthopaedics": "Orthopedics",
        "ortho": "Orthopedics",
        "pulmonology": "Pulmonology",
        "pulmonary": "Pulmonology",
        "pulm": "Pulmonology",
        "pULMONOLOGY": "Pulmonology",
        "nephrology": "Nephrology",
        "nephro": "Nephrology",
        "renal": "Nephrology",
        "emergency": "Emergency",
        "ed": "Emergency",
        "er": "Emergency",
        "emergency dept": "Emergency",
        "emergency department": "Emergency",
        "general  medicine": "General Medicine",
        "gen med": "General Medicine",
        "general medicine": "General Medicine",
        "gen. medicine": "General Medicine"
    }

def normalize_department(value: str | None) -> str | None:

    d = "" if value is None else " ".join(str(value).split()).lower()
    if not d:
        return None 
    return _DEPT_MAP.get(d.lower())

        
    """
    Collapse the department spelling variants to a canonical name.

    Canonical set:
        Cardiology, General Medicine, Orthopedics,
        Pulmonology, Nephrology, Emergency

    Handles case, leading/trailing/internal whitespace, and abbreviations
    ("Cardio", "Gen Med", "ED", "ER", "Renal", "Orthopaedics", ...).
    Unrecognized input returns None — never guess.
    """
    raise NotImplementedError


def normalize_sex(value: str | None) -> str | None:
    """
    Map the eight observed codes to "M", "F", or None.

    "M", "Male", "1"   -> "M"
    "F", "Female", "2" -> "F"
    "U", "", None      -> None

    Note: "1"/"2" is an assumption inherited from a legacy system. Write a
    comment recording that it is an assumption. Undocumented assumptions
    are how analyses quietly become wrong.
    """
    raise NotImplementedError


def parse_currency(value: str | None) -> float | None:
    """
    "$1,234.56" -> 1234.56
    "1,234.56"  -> 1234.56
    "-45.00"    -> -45.0
    ""          -> None

    Negative values are real (adjustments). Do not clip them to zero.
    """
    raise NotImplementedError


def parse_lab_value(value: str | None) -> tuple[float | None, bool]:
    """
    Return (numeric_value, was_censored).

    "7.20"          -> (7.20, False)
    "7.20 mmol/L"   -> (7.20, False)
    "<0.01"         -> (0.01, True)
    "SEE NOTE"      -> (None, False)
    ""              -> (None, False)

    Censored values ("below the limit of detection") are not missing and
    are not equal to the threshold either. Flagging them is the whole
    point — how you later handle them is a statistical decision, and you
    cannot make it if you have thrown the information away here.
    """
    raise NotImplementedError


def normalize_zip(value: str | None) -> str | None:
    """
    "23060"      -> "23060"
    " 23060"     -> "23060"
    "23060-1234" -> "23060"
    "2306"       -> None      (four digits is not a zip code)
    ""           -> None
    """
    raise NotImplementedError
