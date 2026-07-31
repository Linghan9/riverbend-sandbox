"""
Load the raw Riverbend CSVs into a SQLite database, AS-IS.

Note what this does NOT do: it does not clean anything. Everything lands
as TEXT, warts intact. That is deliberate — you will write the cleaning
layer yourself in `src/clean.py` (Exercise 3) and materialize tidy tables.

Usage:
    python src/build_db.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "riverbend.db"

# (filename, table_name, separator, encoding)
FILES = [
    ("providers.csv", "raw_providers", ",", "utf-8"),
    ("patients.csv", "raw_patients", ",", "utf-8"),
    ("encounters.csv", "raw_encounters", ",", "utf-8"),
    ("labs.csv", "raw_labs", ";", "latin-1"),
    ("billing.csv", "raw_billing", ",", "utf-8"),
    ("encounter_snapshot_2024_06.csv", "raw_snapshot_202406", ",", "utf-8"),
    ("encounter_snapshot_2024_12.csv", "raw_snapshot_202412", ";", "latin-1"),
]


def main():
    if DB.exists():
        DB.unlink()

    con = sqlite3.connect(DB)
    try:
        for fname, table, sep, enc in FILES:
            df = pd.read_csv(RAW / fname, sep=sep, encoding=enc, dtype=str, keep_default_na=False)
            df.to_sql(table, con, if_exists="replace", index=False)
            print(f"  {table:24s} {len(df):>8,} rows  x {len(df.columns)} cols")

        con.execute("CREATE INDEX idx_enc_patient ON raw_encounters(patient_id)")
        con.execute("CREATE INDEX idx_labs_enc ON raw_labs(encounter_id)")
        con.execute("CREATE INDEX idx_bill_enc ON raw_billing(encounter_id)")
        con.commit()
    finally:
        con.close()

    print(f"\nDatabase written to {DB}")
    print("Open it in VS Code with the SQLite Viewer extension, or run:")
    print(f"  sqlite3 {DB}")


if __name__ == "__main__":
    main()
