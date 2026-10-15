"""Round 3 Python reference solutions. Try python_exercises.py first.

Standard library only. Each solution ends with a note on how you'd do the same thing with
pandas, which is what most teams use day to day.
"""
import csv
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


# P1 ---------------------------------------------------------------------------
def read_export(path):
    rows, filter_text = [], None
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for rec in reader:
            if not rec or not any(cell.strip() for cell in rec):
                continue                                   # blank line
            first = rec[0].strip()
            if first.startswith("Applied filters:"):
                filter_text = first[len("Applied filters:"):].strip()
                continue
            if first == "Total":
                continue
            rows.append(dict(zip(header, rec)))
    return rows, filter_text
# pandas: df = pd.read_csv(path, dtype=str, keep_default_na=False)
#         footer = df["account_id"].str.startswith("Applied filters") | (df["account_id"] == "Total")
#         df = df[~footer & (df["account_id"] != "")]
# dtype=str matters: without it pandas reads IDs as numbers and silently drops leading zeros.


# P2 ---------------------------------------------------------------------------
def as_of_check(rows, claimed_month):
    months = sorted({r["snapshot_month"] for r in rows})
    max_txn = max(r["last_txn_date"] for r in rows if r["last_txn_date"])
    return {
        "snapshot_months": months,
        "max_txn_date": max_txn,
        "is_current": months == [claimed_month] and max_txn.startswith(claimed_month),
    }
# max() on ISO date strings is safe because YYYY-MM-DD sorts in date order.
# pandas: df["snapshot_month"].unique(), df["last_txn_date"].max()


# P3 ---------------------------------------------------------------------------
def clean_id(value):
    return str(value).strip().zfill(8)


def fix_text(value):
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
# Clean text has no bytes that form valid multi-byte UTF-8 once re-encoded, so the round trip
# either fails (and we keep the original) or returns it unchanged. Damaged text gets repaired.
# The real fix is upstream: read the file with the right encoding in the first place.


EXCEL_EPOCH = date(1899, 12, 30)


def to_iso(value):
    value = (value or "").strip()
    if not value:
        return None
    if value.isdigit():
        return (EXCEL_EPOCH + timedelta(days=int(value))).isoformat()
    if "/" in value:
        month, day, year = (int(p) for p in value.split("/"))
        return date(year, month, day).isoformat()
    return date.fromisoformat(value).isoformat()
# pandas: pd.to_datetime(s, format="%m/%d/%Y", errors="coerce") for one format at a time;
#         pd.to_datetime(serials.astype(int), unit="D", origin="1899-12-30") for Excel numbers.


def clean_row(row):
    out = dict(row)
    out["account_id"] = clean_id(row["account_id"])
    out["dept_name"] = fix_text(row["dept_name"])
    out["discharge_date"] = to_iso(row["discharge_date"])
    return out


# P4 ---------------------------------------------------------------------------
def _same(a, b, tol=0.005):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return (a or "") == (b or "")


def reconcile(left, right, key, fields):
    lmap = {r[key]: r for r in left}
    rmap = {r[key]: r for r in right}
    both = lmap.keys() & rmap.keys()
    mismatches = {f: sum(1 for k in both if not _same(lmap[k][f], rmap[k][f])) for f in fields}
    return {
        "only_left": len(lmap.keys() - rmap.keys()),
        "only_right": len(rmap.keys() - lmap.keys()),
        "matched": len(both),
        "mismatches": mismatches,
    }
# Watch for duplicate keys: a dict keeps only the last row per key. In real work, count
# duplicates first (len(left) vs len(lmap)) and stop if they differ.
# pandas: m = left.merge(right, on=key, how="outer", indicator=True, suffixes=("_l", "_r"))
#         m["_merge"].value_counts() gives left_only / right_only / both in one line.


# P5 ---------------------------------------------------------------------------
def stack_daily(folder):
    latest = {}
    for path in sorted(Path(folder).glob("census_*.csv")):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                k = (r["snapshot_taken"][:10], r["unit"])
                if k not in latest or r["snapshot_taken"] > latest[k]["snapshot_taken"]:
                    latest[k] = r
    rows = [{"census_day": day, "unit": unit,
             "occupied_beds": int(r["occupied_beds"]), "staffed_beds": int(r["staffed_beds"]),
             "snapshot_taken": r["snapshot_taken"]}
            for (day, unit), r in sorted(latest.items())]
    days = sorted({r["census_day"] for r in rows})
    have = set(days)
    d, end, missing = date.fromisoformat(days[0]), date.fromisoformat(days[-1]), []
    while d <= end:
        if d.isoformat() not in have:
            missing.append(d.isoformat())
        d += timedelta(days=1)
    return rows, missing
# pandas: df = pd.concat(pd.read_csv(p).assign(source_file=p.name) for p in folder.glob("census_*.csv"))
#         df["census_day"] = df["snapshot_taken"].str[:10]
#         df = df.sort_values("snapshot_taken").drop_duplicates(["census_day", "unit"], keep="last")
#         missing = pd.date_range(min_day, max_day).difference(pd.to_datetime(df["census_day"].unique()))


# P6 ---------------------------------------------------------------------------
def balance_breaks(rows, tolerance=0.005):
    bad = []
    for r in rows:
        expected = float(r["total_charges"]) - float(r["total_payments"]) - float(r["total_adjustments"])
        if abs(float(r["balance"]) - expected) > tolerance:
            bad.append(r["account_id"])
    return sorted(bad)
# pandas: diff = df.balance - (df.total_charges - df.total_payments - df.total_adjustments)
#         df.loc[diff.abs() > 0.005, "account_id"]
