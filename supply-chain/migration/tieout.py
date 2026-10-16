"""
Tie the new pipeline out to the old Tableau dashboard.

legacy_tableau_kpis.csv holds the numbers the Tableau dashboard showed for 2025, signed
off by the supply chain director before it was retired. They are the target. This
script reads the same KPIs from your views in migration.db and compares them at the
grain listed, row by row.

It tells you WHAT doesn't tie. Finding WHY is your job.

Usage (from the supply-chain folder, after load_extract.py):
    python migration/tieout.py            summary plus the first few differences per KPI
    python migration/tieout.py K4         every difference for one KPI
"""

import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "migration.db"
LEGACY = HERE / "legacy_tableau_kpis.csv"
TOLERANCE = 0.005

KPIS = {
    "K1": ("Spend by vendor company", "company",
           "SELECT company_name, spend FROM v_spend_by_company"),
    "K2": ("Invoice lines by match status", "status",
           "SELECT match_status, lines FROM v_match_summary"),
    "K3": ("Knee replacement cost per case by surgeon, Jul-Dec", "surgeon",
           "SELECT surgeon_name, avg_cost_per_case FROM v_tka_cost_by_surgeon"),
    "K4": ("Supply cost per completed case by procedure", "procedure",
           "SELECT procedure_code, avg_cost_per_case FROM v_cost_per_case_by_procedure"),
    "K5": ("Invoice spend by category group", "category group",
           "SELECT category_group, spend FROM v_spend_by_category_group"),
    "K6": ("Invoice spend by criticality tier", "tier",
           "SELECT criticality, spend FROM v_spend_by_criticality"),
    "K7": ("Scheduled cases at risk from a backorder", "item",
           "SELECT item_on_backorder, cases_at_risk FROM v_backorder_risk"),
    "K8": ("Low-stock runs (3+ days)", "location | item | first day",
           "SELECT location_id || ' | ' || description || ' | ' || first_day, days_low FROM v_low_stock_runs"),
}


def legacy():
    out = {}
    with open(LEGACY, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["kpi"], {})[r["key"]] = float(r["value"])
    return out


def fmt(v):
    if v is None:
        return "(missing)"
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"


def compare(expected, actual):
    diffs = []
    for key in sorted(set(expected) | set(actual), key=lambda k: (k is None, str(k))):
        e, a = expected.get(key), actual.get(key)
        if e is None or a is None or abs(e - a) > TOLERANCE:
            diffs.append((key, e, a))
    return diffs


def main():
    if not DB.exists():
        raise SystemExit("migration.db not found. Run migration/load_extract.py first.")
    only = sys.argv[1].upper() if len(sys.argv) > 1 else None
    target = legacy()
    con = sqlite3.connect(DB)
    passed = 0
    for kpi, (title, grain, sql) in KPIS.items():
        if only and kpi != only:
            continue
        try:
            actual = {}
            for key, value in con.execute(sql):
                actual[key] = (actual.get(key) or 0) + (value or 0)
        except sqlite3.Error as e:
            print(f"{kpi}  ERROR  {title}: {e}\n")
            continue
        diffs = compare(target[kpi], actual)
        if not diffs:
            passed += 1
            print(f"{kpi}  PASS   {title} ({len(target[kpi])} rows tie)")
            continue
        print(f"{kpi}  FAIL   {title}: {len(diffs)} of {len(set(target[kpi]) | set(actual))} rows don't tie")
        print(f"       {'by ' + grain:<52} {'Tableau':>15} {'new pipeline':>15}")
        limit = None if only else 6
        for key, e, a in diffs[:limit]:
            label = "(blank)" if key is None else str(key)
            print(f"       {label[:52]:<52} {fmt(e):>15} {fmt(a):>15}")
        if limit and len(diffs) > limit:
            print(f"       ... {len(diffs) - limit} more. Run: python migration/tieout.py {kpi}")
        print()
    con.close()
    if not only:
        print(f"\n{passed} of {len(KPIS)} KPIs tie out to Tableau.")
        if passed == len(KPIS):
            print("Every page ties. Write up your casebook entries before you celebrate.")


if __name__ == "__main__":
    main()
