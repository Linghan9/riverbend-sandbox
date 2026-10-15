"""Round 3 practice data (added in v3). All data is made up; fixed seed, so every rebuild is identical.

Round 3 mirrors problems from real reporting work:
  - a monthly extract that arrives stale, with report-export junk rows at the bottom
  - a file that fails its own arithmetic
  - account IDs that lost their leading zeros, and a corrupted dash character
  - accounts that vanish between monthly files
  - a daily archive of raw snapshot files, with a missed day and same-day re-refreshes
  - a small star schema where two facts sit at different grains
  - a warehouse catalog to search, the way you'd find tables in a new data warehouse

It writes the tables into practice.db (next to this script) and the Python exercise files into data/.
It only drops and rebuilds its own tables, so you can also run it next to another practice.db
to add these tables without touching the rest.

Usage:  python build_round3.py
"""
import csv
import json
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 3030
HERE = Path(__file__).resolve().parent
DB = HERE / "practice.db"
DATA = HERE / "data"

ROUND3_TABLES = ["acct_extract_first", "acct_extract_second", "acct_source", "acct_last_month",
                 "census_daily_raw", "dim_department", "dim_month", "fact_budget_month",
                 "fact_actual_month", "warehouse_catalog"]

EN_DASH = "–"
MOJIBAKE_DASH = EN_DASH.encode("utf-8").decode("cp1252")  # what a mis-decoded en dash looks like

DEPTS = [
    (1, f"Cardiology {EN_DASH} Inpatient", "Heart & Vascular"),
    (2, f"Cardiology {EN_DASH} Outpatient", "Heart & Vascular"),
    (3, "General Surgery", "Surgical Services"),
    (4, "Orthopedics", "Surgical Services"),
    (5, "Emergency Medicine", "Emergency"),
    (6, "Internal Medicine", "Medicine"),
    (7, "Pediatrics", "Women & Children"),
    (8, "Obstetrics", "Women & Children"),
]
PAYERS = ["Medicare", "Medicaid", "Commercial", "Self-pay"]
ACCT_COLS = ["account_id", "dept_name", "payer", "admit_date", "discharge_date", "account_status",
             "total_charges", "total_payments", "total_adjustments", "balance", "last_txn_date",
             "snapshot_month"]

SEP_END = date(2026, 9, 30)
STALE_CUTOFF = date(2026, 9, 25)
OCT_DATA_END = date(2026, 10, 13)


def iso(d):
    return d.isoformat() if d else None


def rand_date(rng, start, end):
    return start + timedelta(days=rng.randint(0, (end - start).days))


def money(cents):
    return round(cents / 100, 2)


def make_account(rng, acct_id, admit_lo, admit_hi, as_of):
    """One hospital account as it stands on `as_of`. Amounts are kept in cents so balances add up exactly."""
    dept = rng.choice(DEPTS)
    admit = rand_date(rng, admit_lo, admit_hi)
    los = rng.choice([0, 0, 1, 2, 3, 4, 5, 7, 10])
    disch = admit + timedelta(days=los)
    if disch > as_of:
        disch = None
    charges = rng.randint(80_000, 6_000_000)
    age = (as_of - admit).days
    if disch is None or age < 10:
        status = "Open"
    elif age < 45:
        status = rng.choice(["Open", "Billed", "Billed", "Billed"])
    else:
        status = rng.choice(["Billed", "Closed", "Closed"])
    if status == "Open":
        pay, adj = 0, rng.choice([0, 0, rng.randint(0, charges // 20)])
    elif status == "Billed":
        pay = rng.randint(0, charges // 2)
        adj = rng.randint(0, charges // 4)
    else:
        adj = rng.randint(charges // 10, charges // 2)
        pay = charges - adj
    last_txn = min(as_of, (disch or admit) + timedelta(days=rng.randint(0, 40)))
    return {
        "account_id": acct_id, "dept_id": dept[0], "dept_name": dept[1], "payer": rng.choice(PAYERS),
        "admit": admit, "disch": disch, "status": status,
        "charges": charges, "pay": pay, "adj": adj, "last_txn": last_txn,
    }


def advance_to_october(rng, a):
    """Carry a September account forward to the October snapshot."""
    b = dict(a)
    if b["disch"] is None and rng.random() < 0.7:
        b["disch"] = min(OCT_DATA_END, b["admit"] + timedelta(days=rng.randint(1, 12)))
        if b["disch"] < b["admit"]:
            b["disch"] = b["admit"]
    remaining = b["charges"] - b["pay"] - b["adj"]
    if b["status"] == "Open" and b["disch"] is not None and rng.random() < 0.6:
        b["status"] = "Billed"
        b["pay"] += rng.randint(0, remaining // 3)
        b["last_txn"] = rand_date(rng, date(2026, 10, 1), OCT_DATA_END)
    elif b["status"] == "Billed":
        roll = rng.random()
        if roll < 0.25:
            b["status"] = "Closed"
            b["pay"] += remaining
            b["last_txn"] = rand_date(rng, date(2026, 10, 1), OCT_DATA_END)
        elif roll < 0.7:
            b["pay"] += rng.randint(0, remaining // 2)
            b["last_txn"] = rand_date(rng, date(2026, 10, 1), OCT_DATA_END)
    return b


def to_row(a, snapshot_month, last_txn_cap=None):
    last_txn = a["last_txn"] if last_txn_cap is None else min(a["last_txn"], last_txn_cap)
    return {
        "account_id": a["account_id"], "dept_name": a["dept_name"], "payer": a["payer"],
        "admit_date": iso(a["admit"]), "discharge_date": iso(a["disch"]),
        "account_status": a["status"], "total_charges": money(a["charges"]),
        "total_payments": money(a["pay"]), "total_adjustments": money(a["adj"]),
        "balance": money(a["charges"] - a["pay"] - a["adj"]),
        "last_txn_date": iso(last_txn), "snapshot_month": snapshot_month,
    }


def footer_rows(rows, filter_text):
    total = {c: None for c in ACCT_COLS}
    total["account_id"] = "Total"
    for c in ["total_charges", "total_payments", "total_adjustments", "balance"]:
        total[c] = round(sum(r[c] for r in rows), 2)
    flt = {c: None for c in ACCT_COLS}
    flt["account_id"] = f"Applied filters: {filter_text}"
    return [total, flt]


def excel_serial(d):
    return str((d - date(1899, 12, 30)).days)


def build_accounts(rng):
    ids = rng.sample(range(100_000, 1_000_000), 2_200)
    ids = [f"{n:08d}" for n in ids]
    it = iter(ids)

    # September final file (last month)
    sep = [make_account(rng, next(it), date(2026, 5, 1), SEP_END, SEP_END) for _ in range(1_980)]

    # October: 30 closed accounts purge normally, 5 open/billed accounts vanish (planted), 55 new
    closed = [a for a in sep if a["status"] == "Closed"]
    active = [a for a in sep if a["status"] in ("Open", "Billed")]
    purged = set(a["account_id"] for a in rng.sample(closed, 30))
    vanished = set(a["account_id"] for a in rng.sample(active, 5))
    carried = [advance_to_october(rng, a) for a in sep
               if a["account_id"] not in purged and a["account_id"] not in vanished]
    new = [make_account(rng, next(it), date(2026, 10, 1), date(2026, 10, 12), OCT_DATA_END)
           for _ in range(2_000 - len(carried))]
    october = sorted(carried + new, key=lambda a: a["account_id"])

    # Stale first file: the September view as of 9/25 (accounts admitted by then)
    stale = [a for a in sep if a["admit"] <= STALE_CUTOFF]
    first_rows = [to_row(a, "2026-09", STALE_CUTOFF) for a in stale]
    # Planted: 6 rows whose balance no longer equals charges - payments - adjustments
    breaks = rng.sample(range(len(first_rows)), 6)
    break_ids = []
    for i in breaks:
        first_rows[i]["balance"] = round(first_rows[i]["balance"] + rng.choice([-1, 1]) * rng.randint(5_000, 90_000) / 100, 2)
        break_ids.append(first_rows[i]["account_id"])

    sep_rows = [to_row(a, "2026-09") for a in sep]
    source_rows = [to_row(a, "2026-10") for a in october]

    # Second file: the right October data, with formatting damage
    second_rows = [dict(r) for r in source_rows]
    stripped = set(r["account_id"] for r in rng.sample(second_rows, 59))
    for r in second_rows:
        if r["account_id"] in stripped:
            r["account_id"] = str(int(r["account_id"]))
        r["dept_name"] = r["dept_name"].replace(EN_DASH, MOJIBAKE_DASH)
        if r["discharge_date"]:
            d = date.fromisoformat(r["discharge_date"])
            roll = rng.random()
            if roll < 0.10:
                r["discharge_date"] = d.strftime("%m/%d/%Y")
            elif roll < 0.13:
                r["discharge_date"] = excel_serial(d)

    first_all = first_rows + footer_rows(first_rows, "Snapshot is CURRENT")
    second_all = second_rows + footer_rows(second_rows, "Report month is October 2026")

    truth = {
        "first_rows": len(first_rows), "second_rows": len(second_rows),
        "break_ids": sorted(break_ids), "stripped_ids": sorted(stripped),
        "vanished_ids": sorted(vanished), "purged_count": len(purged),
        "dash_rows": sum(1 for r in source_rows if EN_DASH in r["dept_name"]),
        "dash_rows_matched_raw": sum(1 for r in source_rows
                                     if EN_DASH in r["dept_name"] and r["account_id"] not in stripped),
        "reformatted_dates": sum(1 for r in second_rows
                                 if r["discharge_date"] and "-" not in r["discharge_date"]),
        "first_total_balance": round(sum(r["balance"] for r in first_rows), 2),
    }
    return first_all, second_all, source_rows, sep_rows, truth


UNITS = [("4 North", 32), ("4 South", 32), ("5 North", 28), ("ICU", 20), ("Step-Down", 16), ("Pediatrics", 24)]
CENSUS_START, CENSUS_END = date(2026, 9, 28), date(2026, 10, 13)
MISSED_DAY = date(2026, 10, 12)        # the refresh never ran that day
RE_REFRESH_DAYS = [date(2026, 10, 1), date(2026, 10, 7)]   # workbook reopened, refreshed twice


def build_census(rng):
    rows = []
    d = CENSUS_START
    while d <= CENSUS_END:
        if d != MISSED_DAY:
            times = [datetime(d.year, d.month, d.day, 6, rng.randint(0, 20), rng.randint(0, 59))]
            if d in RE_REFRESH_DAYS:
                times.append(datetime(d.year, d.month, d.day, 14, rng.randint(0, 59), rng.randint(0, 59)))
            for t in times:
                fname = f"census_{t:%Y-%m-%d_%H%M}.csv"
                for unit, staffed in UNITS:
                    occ = rng.randint(int(staffed * 0.6), staffed)
                    rows.append({"snapshot_taken": t.strftime("%Y-%m-%d %H:%M:%S"), "unit": unit,
                                 "occupied_beds": occ, "staffed_beds": staffed, "source_file": fname})
        d += timedelta(days=1)
    return rows


def build_star(rng):
    months = [("2026-07", "2026-07-01"), ("2026-08", "2026-08-01"), ("2026-09", "2026-09-01")]
    budget, actual = [], []
    for dept_key, _, _ in DEPTS:
        base = rng.randint(300_000, 1_200_000)
        for mk, _ in months:
            for btype, share in [("Labor", 0.62), ("Supplies", 0.28), ("Other", 0.10)]:
                budget.append((dept_key, mk, btype, round(base * share, 2)))
            spend = base * rng.uniform(0.9, 1.12)
            weights = [rng.uniform(0.5, 1.5) for _ in range(5)]
            for gl, w in zip(["5100 Salaries", "5200 Benefits", "6100 Med Supplies", "6200 Drugs", "7100 Services"], weights):
                actual.append((dept_key, mk, gl, round(spend * w / sum(weights), 2)))
    return months, budget, actual


CATALOG = {
    ("CLARITY", "PATIENT"): ["PAT_ID", "PAT_MRN_ID", "PAT_NAME", "BIRTH_DATE", "ZIP"],
    ("CLARITY", "PAT_ENC"): ["PAT_ENC_CSN_ID", "PAT_ID", "CONTACT_DATE", "DEPARTMENT_ID", "VISIT_PROV_ID", "ENC_TYPE_C"],
    ("CLARITY", "PAT_ENC_HSP"): ["PAT_ENC_CSN_ID", "PAT_ID", "HSP_ACCOUNT_ID", "HOSP_ADMSN_TIME", "HOSP_DISCH_TIME", "ADT_PAT_CLASS_C", "DEPARTMENT_ID"],
    ("CLARITY", "HSP_ACCOUNT"): ["HSP_ACCOUNT_ID", "PAT_ID", "PRIM_ENC_CSN_ID", "ACCT_BILLSTS_HA_C", "TOT_CHGS", "TOT_PMTS", "TOT_ADJ", "TOT_ACCT_BAL", "DISCH_DATE_TIME"],
    ("CLARITY", "HSP_TRANSACTIONS"): ["TX_ID", "HSP_ACCOUNT_ID", "TX_POST_DATE", "TX_AMOUNT", "TX_TYPE_HA_C"],
    ("CLARITY", "CLARITY_DEP"): ["DEPARTMENT_ID", "DEPARTMENT_NAME", "SERV_AREA_ID"],
    ("CLARITY", "CLARITY_SER"): ["PROV_ID", "PROV_NAME", "PROV_TYPE"],
    ("CLARITY", "ZC_ACCT_BILLSTS_HA"): ["ACCT_BILLSTS_HA_C", "NAME"],
    ("REPORTING", "HSP_ACCOUNT_BKP_2024"): ["HSP_ACCOUNT_ID", "PAT_ID", "TOT_ACCT_BAL"],
    ("REPORTING", "RPT_AR_AGING"): ["HSP_ACCOUNT_ID", "AGING_BUCKET", "BALANCE", "AS_OF_DATE"],
    ("REPORTING", "ACCT_HOLD"): ["HSP_ACCOUNT_ID", "HOLD_REASON", "HOLD_DATE"],
    ("REPORTING", "X_ENC_SUMMARY_OLD"): ["PAT_ENC_CSN_ID", "PAT_ID", "HSP_ACCOUNT_ID"],
}


def data_type(col):
    if col.endswith(("_DATE", "_TIME")) or col in ("BIRTH_DATE", "CONTACT_DATE", "AS_OF_DATE"):
        return "DATETIME"
    if col.startswith("TOT_") or col in ("TX_AMOUNT", "BALANCE"):
        return "NUMERIC(18,2)"
    if col.endswith(("_ID", "_C")):
        return "VARCHAR(18)"
    return "VARCHAR(254)"


def write_export_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ACCT_COLS)
        data_rows = [r for r in rows if r["account_id"] != "Total" and not str(r["account_id"]).startswith("Applied")]
        footer = [r for r in rows if r not in data_rows]
        for r in data_rows:
            w.writerow(["" if r[c] is None else r[c] for c in ACCT_COLS])
        w.writerow([])
        total = footer[0]
        w.writerow(["" if total[c] is None else total[c] for c in ACCT_COLS])
        w.writerow([footer[1]["account_id"]])


def write_plain_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ACCT_COLS)
        for r in rows:
            w.writerow(["" if r[c] is None else r[c] for c in ACCT_COLS])


def main():
    rng = random.Random(SEED)
    first, second, source, sep, truth = build_accounts(rng)
    census = build_census(rng)
    months, budget, actual = build_star(rng)

    con = sqlite3.connect(DB)
    for t in ROUND3_TABLES:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    acct_ddl = """(account_id TEXT, dept_name TEXT, payer TEXT, admit_date TEXT, discharge_date TEXT,
                   account_status TEXT, total_charges REAL, total_payments REAL, total_adjustments REAL,
                   balance REAL, last_txn_date TEXT, snapshot_month TEXT)"""
    for name, rows in [("acct_extract_first", first), ("acct_extract_second", second),
                       ("acct_source", source), ("acct_last_month", sep)]:
        con.execute(f"CREATE TABLE {name} {acct_ddl}")
        con.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(ACCT_COLS))})",
                        [[r[c] for c in ACCT_COLS] for r in rows])

    con.execute("""CREATE TABLE census_daily_raw (snapshot_taken TEXT, unit TEXT, occupied_beds INTEGER,
                   staffed_beds INTEGER, source_file TEXT)""")
    con.executemany("INSERT INTO census_daily_raw VALUES (?,?,?,?,?)",
                    [(r["snapshot_taken"], r["unit"], r["occupied_beds"], r["staffed_beds"], r["source_file"]) for r in census])

    con.execute("CREATE TABLE dim_department (dept_key INTEGER PRIMARY KEY, dept_name TEXT, service_line TEXT)")
    con.executemany("INSERT INTO dim_department VALUES (?,?,?)", DEPTS)
    con.execute("CREATE TABLE dim_month (month_key TEXT PRIMARY KEY, month_start TEXT)")
    con.executemany("INSERT INTO dim_month VALUES (?,?)", months)
    con.execute("CREATE TABLE fact_budget_month (dept_key INTEGER, month_key TEXT, budget_type TEXT, amount REAL)")
    con.executemany("INSERT INTO fact_budget_month VALUES (?,?,?,?)", budget)
    con.execute("CREATE TABLE fact_actual_month (dept_key INTEGER, month_key TEXT, gl_account TEXT, amount REAL)")
    con.executemany("INSERT INTO fact_actual_month VALUES (?,?,?,?)", actual)

    con.execute("""CREATE TABLE warehouse_catalog (schema_name TEXT, table_name TEXT, column_name TEXT,
                   data_type TEXT, column_order INTEGER)""")
    con.executemany("INSERT INTO warehouse_catalog VALUES (?,?,?,?,?)",
                    [(s, t, c, data_type(c), i + 1) for (s, t), cols in CATALOG.items() for i, c in enumerate(cols)])
    con.commit()
    con.close()

    # Python exercise files
    DATA.mkdir(exist_ok=True)
    census_dir = DATA / "daily_census"
    census_dir.mkdir(exist_ok=True)
    for old in census_dir.glob("census_*.csv"):
        old.unlink()
    write_export_csv(DATA / "extract_first.csv", first)
    write_export_csv(DATA / "extract_second.csv", second)
    write_plain_csv(DATA / "source_report.csv", source)
    by_file = {}
    for r in census:
        by_file.setdefault(r["source_file"], []).append(r)
    for fname, rows in by_file.items():
        with (census_dir / fname).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["snapshot_taken", "unit", "occupied_beds", "staffed_beds"])
            for r in rows:
                w.writerow([r["snapshot_taken"], r["unit"], r["occupied_beds"], r["staffed_beds"]])

    # Answer key for check_python.py, taken from how the data was built (not from any solution code)
    latest = {}
    for r in census:
        k = (r["snapshot_taken"][:10], r["unit"])
        if k not in latest or r["snapshot_taken"] > latest[k]["snapshot_taken"]:
            latest[k] = r
    occupied_by_day = {}
    for (day, _), r in latest.items():
        occupied_by_day[day] = occupied_by_day.get(day, 0) + r["occupied_beds"]
    expected = {
        "P1": {"first_rows": truth["first_rows"], "first_filter": "Snapshot is CURRENT",
               "second_rows": truth["second_rows"], "second_filter": "Report month is October 2026"},
        "P2": {"first": {"snapshot_months": ["2026-09"], "max_txn_date": STALE_CUTOFF.isoformat(), "is_current": False},
               "second": {"snapshot_months": ["2026-10"],
                          "max_txn_date": max(r["last_txn_date"] for r in source), "is_current": True}},
        "P3": {"examples": {"clean_id": [["412035", "00412035"], ["00412035", "00412035"], [" 731 ", "00000731"]],
                            "fix_text": [[f"Cardiology {MOJIBAKE_DASH} Inpatient", f"Cardiology {EN_DASH} Inpatient"],
                                         ["General Surgery", "General Surgery"]],
                            "to_iso": [["2026-10-03", "2026-10-03"], ["10/03/2026", "2026-10-03"],
                                       [excel_serial(date(2026, 10, 3)), "2026-10-03"], ["", None]]},
               "rows_matching_source": truth["second_rows"]},
        "P4": {"raw": {"only_left": len(truth["stripped_ids"]), "only_right": len(truth["stripped_ids"]),
                       "matched": truth["second_rows"] - len(truth["stripped_ids"]),
                       "mismatches": {"dept_name": truth["dash_rows_matched_raw"], "balance": 0, "account_status": 0}},
               "cleaned": {"only_left": 0, "only_right": 0, "matched": truth["second_rows"],
                           "mismatches": {"dept_name": 0, "balance": 0, "account_status": 0}}},
        "P5": {"rows": len(latest), "missing_days": [MISSED_DAY.isoformat()],
               "occupied_on_2026-10-07": occupied_by_day["2026-10-07"]},
        "P6": {"break_ids": truth["break_ids"]},
    }
    (DATA / "expected.json").write_text(json.dumps(expected, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Round 3 tables written to {DB.name}; Python files written to data/.")
    print(json.dumps({k: v for k, v in truth.items() if not k.endswith("_ids")}, indent=2))


if __name__ == "__main__":
    main()
