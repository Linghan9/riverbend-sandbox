"""
The new pipeline: load the ERP extract into migration.db and build the report views.

This is the part you own. It plays the role Power Query plays in Power BI: read the
source files, shape them, apply the new standards, hand clean tables to the report
layer (kpi_views.sql). Debug it the way you'd debug a real refresh.

Usage (from the supply-chain folder):
    python migration/load_extract.py

Standard library only.
"""

import csv
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACT = HERE / "extract"
DB = HERE / "migration.db"
VIEWS = HERE / "kpi_views.sql"
CATEGORY_MAP = HERE / "category_map.csv"

# Columns per table, from the data source spec the Tableau workbook was built on.
COLUMNS = {
    "location": ["location_id", "location_name", "department"],
    "vendor": ["vendor_id", "vendor_name", "vendor_type", "tax_id"],
    "item_master": ["item_id", "description", "manufacturer", "mfr_catalog_no", "category",
                    "purchase_uom", "units_per_uom", "list_price", "is_implant", "active_flag",
                    "criticality_code"],
    "contract_price": ["contract_id", "vendor_id", "item_id", "contract_price", "purchase_uom",
                       "effective_start", "effective_end", "gpo_name"],
    "surgeon": ["surgeon_id", "surgeon_name", "specialty", "service_line"],
    "procedure": ["procedure_code", "procedure_name", "service_line"],
    "preference_card": ["card_line_id", "surgeon_id", "procedure_code", "item_id", "default_qty",
                        "last_updated"],
    "surgical_case": ["case_id", "case_date", "surgeon_id", "procedure_code", "location_id",
                      "case_status"],
    "case_supply_usage": ["usage_id", "case_id", "item_id", "qty_used", "uom_recorded", "wasted_flag"],
    "po_line": ["po_number", "po_line", "po_date", "vendor_id", "item_id", "qty_ordered",
                "purchase_uom", "unit_price", "ship_to_location", "po_type"],
    "receipt": ["receipt_id", "po_number", "po_line", "received_date", "qty_received"],
    "invoice_line": ["invoice_number", "invoice_line", "vendor_id", "invoice_date", "po_number",
                     "po_line", "item_id", "qty_invoiced", "unit_price", "line_amount"],
    "inventory_snapshot": ["snapshot_date", "location_id", "item_id", "on_hand_qty", "par_level",
                           "reorder_point", "stock_uom"],
    "backorder": ["backorder_id", "vendor_id", "item_id", "reported_date", "expected_release_date",
                  "resolved_date", "substitute_item_id"],
}

# Column types. Anything not listed loads as TEXT.
TYPES = {"units_per_uom": "INTEGER", "list_price": "REAL", "is_implant": "INTEGER",
         "contract_price": "REAL", "default_qty": "INTEGER", "qty_used": "INTEGER",
         "po_line": "INTEGER", "qty_ordered": "INTEGER", "unit_price": "REAL", "qty_received": "INTEGER",
         "invoice_line": "INTEGER", "qty_invoiced": "INTEGER", "line_amount": "REAL"}


def load_table(con, name, cols):
    path = EXTRACT / f"{name}.csv"
    with open(path, encoding="utf-8", newline="") as f:
        rows = [[(r.get(c) or None) for c in cols] for r in csv.DictReader(f)]
    coldefs = ", ".join(f"{c} {TYPES.get(c, 'TEXT')}" for c in cols)
    con.execute(f"CREATE TABLE {name} ({coldefs})")
    con.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(cols))})", rows)
    return len(rows)


def apply_standards(con):
    # The health system's new enterprise risk scale runs the other way from the old ERP:
    # 3 is now the most critical tier and 1 the least. Convert the codes.
    con.execute("UPDATE item_master SET criticality_code = REPLACE(criticality_code, '1', '3')")
    con.execute("UPDATE item_master SET criticality_code = REPLACE(criticality_code, '3', '1')")


def load_category_map(con):
    with open(CATEGORY_MAP, encoding="utf-8", newline="") as f:
        rows = [(r["category"], r["category_group"]) for r in csv.DictReader(f)]
    con.execute("CREATE TABLE category_map (category TEXT, category_group TEXT)")
    con.executemany("INSERT INTO category_map VALUES (?, ?)", rows)
    return len(rows)


def main():
    if not EXTRACT.exists():
        raise SystemExit("No extract found. Run migration/source_system/erp_export.py first.")
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    for name, cols in COLUMNS.items():
        print(f"  loaded {name:20s} {load_table(con, name, cols):>7,} rows")
    print(f"  loaded {'category_map':20s} {load_category_map(con):>7,} rows")
    apply_standards(con)
    con.executescript(VIEWS.read_text(encoding="utf-8"))
    con.commit()
    views = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name")]
    con.close()
    print(f"\nmigration.db built with {len(views)} report views: {', '.join(views)}")


if __name__ == "__main__":
    main()
