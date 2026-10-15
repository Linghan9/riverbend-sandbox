# SQL and Python practice: extracts, snapshots and warehouses

A made-up hospital dataset for practicing the SQL and Python behind everyday reporting work. Everything here is fake, and the data is deliberately broken in realistic ways.

Each exercise is a problem that turns up when you work from other teams' extracts: a "monthly" file that is actually last month's, export junk rows, a file that fails its own arithmetic, IDs that lost their leading zeros, a corrupted dash character, records that vanish between months, a daily snapshot archive with gaps and duplicates, a star schema with two facts at different grains, and finding your way in an unfamiliar warehouse.

## Start here

The data is generated, not stored in git (same rule as the rest of this repo). Build it first:

```
cd sql-practice-v3
python build_round3.py
```

That creates `practice.db` and the CSV files in `data/`. The fixed seed makes every rebuild identical. Standard library only: no `pip install` needed.

## What's inside

| File | What it is |
| --- | --- |
| `build_round3.py` | Generates `practice.db` and `data/` |
| `questions_round3.sql` | 10 SQL questions (Q21–Q30) with expected row counts |
| `solutions_round3.sql` | Answer key, with SQL Server and Oracle notes |
| `python_exercises.py` | Six Python exercises (P1–P6) to fill in |
| `check_python.py` | Checks your Python answers against known values |
| `python_solutions.py` | Python answer key, with the pandas version of each |
| `run_sql.py` | Runs a query or a `.sql` file and prints a table |

| SQL | What it practices | Python |
| --- | --- | --- |
| Q21 | Junk rows from a report export | P1 |
| Q22 | Proving an extract is (or isn't) current | P2 |
| Q23 | Testing a file against its own arithmetic | P6 |
| Q24 | Reconciling: keys that lost zeros, a corrupted dash | P3, P4 |
| Q25 | Records that vanished between months | |
| Q26–Q28 | Daily snapshot archive: duplicates, missed days, LAG | P5 |
| Q29 | Star schema: two facts at different grains | |
| Q30 | Searching a warehouse catalog, and the LIKE underscore trap | |

## Running it

```
python run_sql.py "SELECT * FROM dim_department"
python run_sql.py my_answers.sql
python check_python.py
python check_python.py --solutions
```

The checker tests values, not just shapes, so a wrong number that looks right still fails. On Windows, use `py` if `python` isn't recognized.

## Notes

- Q30's warehouse catalog uses Epic Clarity-style table and column names. The lists are simplified for practice; Epic documents the real tables at open.epic.com.
- Dates are stored as ISO text (`YYYY-MM-DD`), which sorts correctly. That's why `MAX()` works on them, and why it wouldn't on `MM/DD/YYYY`.

## Dialect notes

| Task | SQLite | SQL Server | Oracle |
| --- | --- | --- | --- |
| Pad an ID to 8 digits | `printf('%08d', id)` | `RIGHT('00000000' + id, 8)` | `LPAD(id, 8, '0')` |
| Date part of a timestamp | `date(ts)` | `CAST(ts AS date)` | `TRUNC(ts)` |
| Add a day | `date(d, '+1 day')` | `DATEADD(day, 1, d)` | `d + 1` |
| Recursive CTE | `WITH RECURSIVE` | `WITH` | `WITH` |
| Column catalog | `pragma_table_info` | `INFORMATION_SCHEMA.COLUMNS` | `ALL_TAB_COLUMNS` |
| List distinct values | `GROUP_CONCAT(DISTINCT x)` | `STRING_AGG(x, ',')` | `LISTAGG(DISTINCT x, ',')` |
