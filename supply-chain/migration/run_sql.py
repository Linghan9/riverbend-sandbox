"""Run SQL against migration.db (the new pipeline's output) and print the results.

Usage (from the supply-chain folder):
  python migration/run_sql.py "SELECT * FROM v_match_summary"
  python migration/run_sql.py my_checks.sql
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import run_sql as base  # noqa: E402  (supply-chain/run_sql.py)

base.DB = HERE / "migration.db"

if __name__ == "__main__":
    if not base.DB.exists():
        raise SystemExit("migration.db not found. Run migration/load_extract.py first.")
    base.main()
