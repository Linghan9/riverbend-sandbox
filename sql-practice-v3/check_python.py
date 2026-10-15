"""Check the Round 3 Python exercises against known answers.

Usage:
  python check_python.py              checks your python_exercises.py
  python check_python.py --solutions  checks the reference solutions (to see what passing looks like)

The answers in data/expected.json come from how the data was built, not from the solutions,
so the checker tests values, not just shapes.
"""
import csv
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
EXPECTED = json.loads((DATA / "expected.json").read_text(encoding="utf-8"))

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass


def load_rows(path):
    """The checker's own loader, so every exercise can be checked on its own."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    return [r for r in rows if r["account_id"] and r["account_id"] != "Total"
            and not r["account_id"].startswith("Applied filters")]


def run(name, fn):
    try:
        problems = fn()
    except NotImplementedError:
        print(f"  {name}: not started")
        return None
    except Exception as e:                                  # show the error, keep going
        print(f"  {name}: ERROR  {type(e).__name__}: {e}")
        return False
    if problems:
        print(f"  {name}: FAIL")
        for p in problems:
            print(f"      - {p}")
        return False
    print(f"  {name}: PASS")
    return True


def main():
    mod_name = "python_solutions" if "--solutions" in sys.argv else "python_exercises"
    m = importlib.import_module(mod_name)
    print(f"Checking {mod_name}.py\n")
    first = load_rows(DATA / "extract_first.csv")
    second = load_rows(DATA / "extract_second.csv")
    source = load_rows(DATA / "source_report.csv")

    def p1():
        e, out = EXPECTED["P1"], []
        for label in ("first", "second"):
            rows, flt = m.read_export(DATA / f"extract_{label}.csv")
            if len(rows) != e[f"{label}_rows"]:
                out.append(f"{label}: got {len(rows)} rows, expected {e[f'{label}_rows']}")
            if flt != e[f"{label}_filter"]:
                out.append(f"{label}: got filter {flt!r}, expected {e[f'{label}_filter']!r}")
            if rows and rows[0]["account_id"] != rows[0]["account_id"].strip():
                out.append(f"{label}: account_id has stray spaces")
        return out

    def p2():
        e, out = EXPECTED["P2"], []
        for label, rows in (("first", first), ("second", second)):
            got = m.as_of_check(rows, "2026-10")
            if got != e[label]:
                out.append(f"{label}: got {got}, expected {e[label]}")
        return out

    def p3():
        e, out = EXPECTED["P3"], []
        for fname, cases in e["examples"].items():
            fn = getattr(m, fname)
            for given, want in cases:
                got = fn(given)
                if got != want:
                    out.append(f"{fname}({given!r}) returned {got!r}, expected {want!r}")
        if not out:
            src = {r["account_id"]: r for r in source}
            ok = 0
            for r in second:
                c = m.clean_row(r)
                s = src.get(c["account_id"])
                if s and c["dept_name"] == s["dept_name"] and (c["discharge_date"] or "") == s["discharge_date"]:
                    ok += 1
            if ok != e["rows_matching_source"]:
                out.append(f"after clean_row, {ok} rows match the source; expected {e['rows_matching_source']}")
        return out

    def p4():
        e, out = EXPECTED["P4"], []
        fields = ["dept_name", "balance", "account_status"]
        got = m.reconcile(second, source, "account_id", fields)
        if got != e["raw"]:
            out.append(f"raw files: got {got}, expected {e['raw']}")
        if hasattr(m, "clean_row"):
            try:
                cleaned = [m.clean_row(r) for r in second]
            except NotImplementedError:
                cleaned = None
            if cleaned is not None:
                got2 = m.reconcile(cleaned, source, "account_id", fields)
                if got2 != e["cleaned"]:
                    out.append(f"after clean_row: got {got2}, expected {e['cleaned']}")
        return out

    def p5():
        e, out = EXPECTED["P5"], []
        rows, missing = m.stack_daily(DATA / "daily_census")
        if len(rows) != e["rows"]:
            out.append(f"got {len(rows)} rows, expected {e['rows']}")
        if missing != e["missing_days"]:
            out.append(f"got missing days {missing}, expected {e['missing_days']}")
        occ = sum(r["occupied_beds"] for r in rows if r["census_day"] == "2026-10-07")
        if occ != e["occupied_on_2026-10-07"]:
            out.append(f"2026-10-07 occupied beds total {occ}, expected {e['occupied_on_2026-10-07']} "
                       "(did you keep the latest refresh?)")
        return out

    def p6():
        got = m.balance_breaks(first)
        want = EXPECTED["P6"]["break_ids"]
        return [] if got == want else [f"got {got}, expected {want}"]

    results = [run(n, f) for n, f in
               [("P1 read_export", p1), ("P2 as_of_check", p2), ("P3 cleaning", p3),
                ("P4 reconcile", p4), ("P5 stack_daily", p5), ("P6 balance_breaks", p6)]]
    passed = sum(1 for r in results if r)
    print(f"\n{passed} of {len(results)} passing")


if __name__ == "__main__":
    main()
