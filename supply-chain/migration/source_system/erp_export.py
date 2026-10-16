"""
The new ERP's nightly export job. Treat this file as a black box.

In real life you never see this code. You get the files it drops in a folder,
and whatever is in them is what you have to work with. So: run it, don't read
it. Reading it is the same as reading the answer key.

Usage (from the supply-chain folder, after build_supply_chain.py):
    python migration/source_system/erp_export.py
"""

import csv
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_DB = HERE.parent.parent / "supply_chain.db"
OUT = HERE.parent / "extract"

TABLES = ["location", "vendor", "item_master", "contract_price", "surgeon", "procedure",
          "preference_card", "surgical_case", "case_supply_usage", "po_line", "receipt",
          "invoice_line", "inventory_snapshot", "backorder"]

HEADERS = {
    "vendor": {"tax_id": "TIN"},
    "invoice_line": {"unit_price": "unit_cost"},
}

TIER = {"Ortho Implant": "1", "Cardiac Implant": "1", "EP Catheter": "1",
        "Surgical Supply": "2", "Cardiac Supply": "2", "Med-Surg Commodity": "3"}


def rows_of(con, table):
    cur = con.execute(f"SELECT * FROM {table}")
    cols = [c[0] for c in cur.description]
    return cols, [list(r) for r in cur.fetchall()]


def main():
    if not SOURCE_DB.exists():
        raise SystemExit("supply_chain.db not found. Run build_supply_chain.py first.")
    OUT.mkdir(exist_ok=True)
    con = sqlite3.connect(SOURCE_DB)
    for table in TABLES:
        cols, rows = rows_of(con, table)

        if table == "item_master":
            c_cat, c_mfr, c_desc = cols.index("category"), cols.index("manufacturer"), cols.index("description")
            cols = cols + ["criticality_code"]
            for r in rows:
                r.append(TIER[r[c_cat]])
                if r[c_cat] == "Med-Surg Commodity" and (r[c_mfr] == "Bluegate" or r[c_desc] == r[c_desc].upper()):
                    r[c_cat] = "Med/Surg Commodity"

        if table in ("surgeon",):
            c_id = cols.index("surgeon_id")
            for r in rows:
                r[c_id] = r[c_id][:3] + "-" + r[c_id][3:]

        cols = [HEADERS.get(table, {}).get(c, c) for c in cols]
        with open(OUT / f"{table}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(["" if v is None else v for v in r] for r in rows)
        print(f"  exported {table:20s} {len(rows):>7,} rows")
    con.close()
    print(f"\nExtract written to {OUT}")


if __name__ == "__main__":
    main()
