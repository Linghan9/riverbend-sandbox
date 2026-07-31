"""
The spec for src/clean.py.

Read these before implementing. They are not an afterthought — they are
the requirements document, written in a language the computer can check.
Run with:  pytest -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.clean import (  # noqa: E402
    normalize_department,
    normalize_sex,
    normalize_zip,
    parse_currency,
    parse_flexible_date,
    parse_lab_value,
)


class TestParseFlexibleDate:
    @pytest.mark.parametrize(
        "raw",
        ["2024-03-15", "03/15/2024", "15-MAR-2024", "15-Mar-2024", " 2024-03-15 "],
    )
    def test_all_formats_agree(self, raw):
        assert parse_flexible_date(raw) == pd.Timestamp("2024-03-15")

    @pytest.mark.parametrize("raw", ["", None, "not a date", "0000-00-00", "  "])
    def test_junk_returns_nat(self, raw):
        assert pd.isna(parse_flexible_date(raw))

    def test_us_format_is_month_first(self):
        # 04/07/2024 is April 7th, not July 4th. Getting this backwards is
        # the single most common silent bug in date parsing.
        assert parse_flexible_date("04/07/2024") == pd.Timestamp("2024-04-07")


class TestNormalizeDepartment:
    @pytest.mark.parametrize(
        "raw",
        ["Cardiology", "cardiology", "CARDIOLOGY", " Cardiology", "Cardiology ", "Cardio"],
    )
    def test_cardiology_variants(self, raw):
        assert normalize_department(raw) == "Cardiology"

    @pytest.mark.parametrize(
        "raw",
        ["General Medicine", "general medicine", "Gen Med", "GENERAL MEDICINE",
         "Gen. Medicine", "General  Medicine"],
    )
    def test_general_medicine_variants(self, raw):
        assert normalize_department(raw) == "General Medicine"

    @pytest.mark.parametrize("raw", ["Emergency", "ED", "ER", "Emergency Dept", "emergency"])
    def test_emergency_variants(self, raw):
        assert normalize_department(raw) == "Emergency"

    @pytest.mark.parametrize("raw", ["Nephrology", "Nephro", "Renal", "NEPHROLOGY"])
    def test_nephrology_variants(self, raw):
        assert normalize_department(raw) == "Nephrology"

    @pytest.mark.parametrize("raw", ["Orthopedics", "Ortho", "Orthopaedics"])
    def test_orthopedics_variants(self, raw):
        assert normalize_department(raw) == "Orthopedics"

    @pytest.mark.parametrize("raw", ["Pulmonology", "Pulm", "Pulmonary"])
    def test_pulmonology_variants(self, raw):
        assert normalize_department(raw) == "Pulmonology"

    @pytest.mark.parametrize("raw", ["", None, "Dermatology", "???"])
    def test_unknown_returns_none(self, raw):
        assert normalize_department(raw) is None


class TestNormalizeSex:
    @pytest.mark.parametrize("raw", ["M", "m", "Male", "MALE", "1"])
    def test_male(self, raw):
        assert normalize_sex(raw) == "M"

    @pytest.mark.parametrize("raw", ["F", "f", "Female", "FEMALE", "2"])
    def test_female(self, raw):
        assert normalize_sex(raw) == "F"

    @pytest.mark.parametrize("raw", ["U", "", None, "X", "Unknown"])
    def test_unknown(self, raw):
        assert normalize_sex(raw) is None


class TestParseCurrency:
    def test_dollar_sign_and_commas(self):
        assert parse_currency("$1,234.56") == pytest.approx(1234.56)

    def test_commas_only(self):
        assert parse_currency("1,234.56") == pytest.approx(1234.56)

    def test_plain(self):
        assert parse_currency("42.00") == pytest.approx(42.0)

    def test_negative_is_preserved(self):
        assert parse_currency("-45.00") == pytest.approx(-45.0)

    def test_negative_with_symbol(self):
        assert parse_currency("-$1,200.00") == pytest.approx(-1200.0)

    @pytest.mark.parametrize("raw", ["", None, "N/A"])
    def test_junk_is_none(self, raw):
        assert parse_currency(raw) is None


class TestParseLabValue:
    def test_plain_number(self):
        val, censored = parse_lab_value("7.20")
        assert val == pytest.approx(7.20)
        assert censored is False

    def test_unit_suffix_is_stripped(self):
        val, censored = parse_lab_value("7.20 mmol/L")
        assert val == pytest.approx(7.20)
        assert censored is False

    def test_censored_below_detection(self):
        val, censored = parse_lab_value("<0.01")
        assert val == pytest.approx(0.01)
        assert censored is True

    def test_censored_above(self):
        val, censored = parse_lab_value(">1000")
        assert val == pytest.approx(1000.0)
        assert censored is True

    @pytest.mark.parametrize("raw", ["SEE NOTE", "", None, "CANCELLED"])
    def test_non_numeric(self, raw):
        val, censored = parse_lab_value(raw)
        assert val is None
        assert censored is False


class TestNormalizeZip:
    def test_plain(self):
        assert normalize_zip("23060") == "23060"

    def test_leading_space(self):
        assert normalize_zip(" 23060") == "23060"

    def test_plus_four_is_truncated(self):
        assert normalize_zip("23060-1234") == "23060"

    @pytest.mark.parametrize("raw", ["2306", "", None, "ABCDE", "230601"])
    def test_invalid(self, raw):
        assert normalize_zip(raw) is None
