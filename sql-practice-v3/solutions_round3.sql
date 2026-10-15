-- ROUND 3 SOLUTIONS. Try questions_round3.sql first.
-- Written for SQLite. Notes show the SQL Server and Oracle versions where they differ.


-- ============================================================================
-- Part A. The monthly extract
-- ============================================================================

-- Q21. Rows that aren't accounts, and the filter each export used.
-- A report export carries a totals row and a filters line at the bottom. Imported as-is,
-- they become "accounts" and inflate every count and sum. The filters line is also evidence:
-- it tells you which view of the report the file came from.
SELECT 'first' AS file, account_id, balance
FROM acct_extract_first
WHERE account_id NOT GLOB '[0-9]*' OR dept_name IS NULL
UNION ALL
SELECT 'second', account_id, balance
FROM acct_extract_second
WHERE account_id NOT GLOB '[0-9]*' OR dept_name IS NULL;
-- SQL Server: account_id NOT LIKE '[0-9]%'.  Oracle: NOT REGEXP_LIKE(account_id, '^[0-9]').


-- Q22. Is the first file really this month's? Let the data answer.
-- Never trust the file name or the email. Look inside: the snapshot month the rows carry,
-- the latest transaction date, and the row count.
SELECT 'first' AS file,
       GROUP_CONCAT(DISTINCT snapshot_month) AS snapshot_months,
       MAX(last_txn_date) AS latest_txn,
       COUNT(*) AS accounts
FROM acct_extract_first
WHERE account_id GLOB '[0-9]*'
UNION ALL
SELECT 'second',
       GROUP_CONCAT(DISTINCT snapshot_month),
       MAX(last_txn_date),
       COUNT(*)
FROM acct_extract_second
WHERE account_id GLOB '[0-9]*';
-- MAX works on these dates only because they are ISO text (YYYY-MM-DD), which sorts like a date.
-- On MM/DD/YYYY text, MAX would pick 12/01 over 10/31. Convert first.
-- SQL Server: STRING_AGG(DISTINCT ...) isn't allowed; use a subquery with DISTINCT, then STRING_AGG.
-- Oracle: LISTAGG(DISTINCT snapshot_month, ',').


-- Q23. Test the first file against its own arithmetic.
-- balance should equal charges - payments - adjustments. Compare with a tolerance,
-- because money stored as floating point can be off by a fraction of a cent.
SELECT account_id,
       total_charges, total_payments, total_adjustments, balance,
       ROUND(total_charges - total_payments - total_adjustments, 2) AS expected_balance,
       ROUND(balance - (total_charges - total_payments - total_adjustments), 2) AS difference
FROM acct_extract_first
WHERE account_id GLOB '[0-9]*'
  AND ABS(balance - (total_charges - total_payments - total_adjustments)) > 0.005
ORDER BY account_id;
-- Without the account filter the Total row fails too, which is a nice tell that the totals
-- were added up from broken rows.


-- Q24. Reconcile the second file to the source report.

-- (a) Join on the ID exactly as delivered.
SELECT COUNT(*) AS matched_as_is
FROM acct_source s
JOIN acct_extract_second e ON e.account_id = s.account_id;

-- Why the gap: some IDs passed through a spreadsheet that treated them as numbers,
-- so 00412035 became 412035. Look at them:
SELECT account_id, LENGTH(account_id) AS len
FROM acct_extract_second
WHERE account_id GLOB '[0-9]*' AND LENGTH(account_id) <> 8
LIMIT 5;

-- (b) Normalize the key, then check both directions.
WITH e AS (
  SELECT printf('%08d', CAST(account_id AS INTEGER)) AS account_id
  FROM acct_extract_second
  WHERE account_id GLOB '[0-9]*'
)
SELECT
  (SELECT COUNT(*) FROM acct_source s JOIN e ON e.account_id = s.account_id) AS matched,
  (SELECT COUNT(*) FROM acct_source s WHERE s.account_id NOT IN (SELECT account_id FROM e)) AS only_in_source,
  (SELECT COUNT(*) FROM e WHERE e.account_id NOT IN (SELECT account_id FROM acct_source)) AS only_in_extract;
-- SQL Server: RIGHT('00000000' + account_id, 8).  Oracle: LPAD(account_id, 8, '0').
-- Newer SQLite (3.39+), SQL Server and Oracle can also do this with one FULL OUTER JOIN.

-- (c) Field by field on the matched rows.
WITH e AS (
  SELECT printf('%08d', CAST(account_id AS INTEGER)) AS account_id,
         dept_name, account_status, balance
  FROM acct_extract_second
  WHERE account_id GLOB '[0-9]*'
)
SELECT SUM(e.dept_name <> s.dept_name)           AS dept_name_diffs,
       SUM(e.account_status <> s.account_status) AS status_diffs,
       SUM(ABS(e.balance - s.balance) > 0.005)   AS balance_diffs
FROM acct_source s
JOIN e ON e.account_id = s.account_id;

-- What do the differing names look like?
SELECT DISTINCT e.dept_name AS extract_name, s.dept_name AS source_name
FROM acct_extract_second e
JOIN acct_source s ON s.account_id = printf('%08d', CAST(e.account_id AS INTEGER))
WHERE e.dept_name <> s.dept_name;

-- The en dash (–) was saved as UTF-8 and read back as Windows-1252, so it turned into "â€“".
-- Fix it and compare again. char() builds the characters from their code points, which keeps
-- this file safe to open in any editor.
WITH e AS (
  SELECT printf('%08d', CAST(account_id AS INTEGER)) AS account_id,
         REPLACE(dept_name, char(226, 8364, 8220), char(8211)) AS dept_name,
         account_status, balance
  FROM acct_extract_second
  WHERE account_id GLOB '[0-9]*'
)
SELECT SUM(e.dept_name <> s.dept_name)           AS dept_name_diffs,
       SUM(e.account_status <> s.account_status) AS status_diffs,
       SUM(ABS(e.balance - s.balance) > 0.005)   AS balance_diffs
FROM acct_source s
JOIN e ON e.account_id = s.account_id;
-- SQL Server: NCHAR(8211). Oracle: UNISTR('\2013'). Better still, fix the encoding where the file is read.


-- Q25. Accounts that were open last month and are simply gone this month.
-- Closed accounts dropping out can be normal (a purge rule). Open or billed accounts
-- vanishing is not: ask the source team before you publish.
SELECT m.account_id, m.dept_name, m.account_status, m.balance
FROM acct_last_month m
LEFT JOIN acct_source s ON s.account_id = m.account_id
WHERE s.account_id IS NULL
  AND m.account_status IN ('Open', 'Billed')
ORDER BY m.balance DESC;

-- (b) Everything that dropped out, by last month's status.
SELECT m.account_status, COUNT(*) AS dropped
FROM acct_last_month m
LEFT JOIN acct_source s ON s.account_id = m.account_id
WHERE s.account_id IS NULL
GROUP BY m.account_status
ORDER BY dropped DESC;


-- ============================================================================
-- Part B. The daily snapshot archive
-- ============================================================================

-- Q26. One row per day per unit: keep the latest refresh.
-- Two days were refreshed twice. Stacking every file as-is double-counts those days.
WITH ranked AS (
  SELECT c.*,
         date(snapshot_taken) AS census_day,
         ROW_NUMBER() OVER (PARTITION BY date(snapshot_taken), unit
                            ORDER BY snapshot_taken DESC) AS rn
  FROM census_daily_raw c
)
SELECT census_day, unit, occupied_beds, staffed_beds, snapshot_taken
FROM ranked
WHERE rn = 1
ORDER BY census_day, unit;
-- SQL Server: CAST(snapshot_taken AS date). Oracle: TRUNC(snapshot_taken).


-- Q27. Which days have no snapshot at all?
-- Build the full calendar from the data's own range, then anti-join.
WITH RECURSIVE bounds AS (
  SELECT MIN(date(snapshot_taken)) AS lo, MAX(date(snapshot_taken)) AS hi
  FROM census_daily_raw
),
days(d) AS (
  SELECT lo FROM bounds
  UNION ALL
  SELECT date(d, '+1 day') FROM days, bounds WHERE d < hi
)
SELECT d AS missing_day
FROM days
WHERE d NOT IN (SELECT date(snapshot_taken) FROM census_daily_raw);
-- A daily snapshot that never ran can't be recreated later if the source keeps only today.
-- That's why you check for gaps every week, not at year end.
-- SQL Server: WITH (no RECURSIVE keyword) and DATEADD(day, 1, d). Oracle: CONNECT BY LEVEL or a recursive WITH.


-- Q28. Hospital-wide occupancy by day, with the change from the previous snapshot.
WITH ranked AS (
  SELECT c.*,
         date(snapshot_taken) AS census_day,
         ROW_NUMBER() OVER (PARTITION BY date(snapshot_taken), unit
                            ORDER BY snapshot_taken DESC) AS rn
  FROM census_daily_raw c
),
daily AS (
  SELECT census_day,
         SUM(occupied_beds) AS occupied,
         SUM(staffed_beds) AS staffed
  FROM ranked
  WHERE rn = 1
  GROUP BY census_day
)
SELECT census_day,
       occupied,
       ROUND(100.0 * occupied / staffed, 1) AS occupancy_pct,
       occupied - LAG(occupied) OVER (ORDER BY census_day) AS change,
       CAST(julianday(census_day) - julianday(LAG(census_day) OVER (ORDER BY census_day)) AS INTEGER) AS days_since_prev
FROM daily
ORDER BY census_day;
-- Look at 2026-10-13: days_since_prev is 2. LAG returns the previous ROW, not the previous DAY,
-- so that "change" covers two days. Label it, or join to a calendar so the gap shows as a gap.
-- Also note 100.0: integer / integer would truncate to a whole number in SQLite and SQL Server.


-- ============================================================================
-- Part C. A small star schema
-- ============================================================================

-- Q29. Budget vs actual by department for July–September 2026.
-- The two facts sit at different grains: 3 budget lines and 5 GL lines per department-month.
-- Total each fact to the same grain first, then join.
WITH b AS (
  SELECT dept_key, SUM(amount) AS budget
  FROM fact_budget_month
  WHERE month_key BETWEEN '2026-07' AND '2026-09'
  GROUP BY dept_key
),
a AS (
  SELECT dept_key, SUM(amount) AS actual
  FROM fact_actual_month
  WHERE month_key BETWEEN '2026-07' AND '2026-09'
  GROUP BY dept_key
)
SELECT d.dept_name,
       d.service_line,
       ROUND(b.budget, 2) AS budget,
       ROUND(a.actual, 2) AS actual,
       ROUND(a.actual - b.budget, 2) AS variance,
       ROUND(100.0 * a.actual / b.budget, 1) AS pct_of_budget
FROM dim_department d
JOIN b ON b.dept_key = d.dept_key
JOIN a ON a.dept_key = d.dept_key
ORDER BY pct_of_budget DESC;

-- (b) The trap: join the facts row to row, then sum.
SELECT ROUND(SUM(b.amount), 2) AS naive_budget,
       (SELECT ROUND(SUM(amount), 2) FROM fact_budget_month) AS true_budget,
       ROUND(SUM(b.amount) / (SELECT SUM(amount) FROM fact_budget_month), 2) AS inflation
FROM fact_budget_month b
JOIN fact_actual_month a
  ON a.dept_key = b.dept_key AND a.month_key = b.month_key;
-- Every budget line matches 5 actual lines, so the budget comes out 5x too high.
-- Same family of bug as a join that turns about 5 rows into 85.


-- ============================================================================
-- Part D. Finding your way in a new warehouse
-- ============================================================================

-- Q30. Search the catalog.
-- (a) Every table that carries a hospital account ID.
SELECT schema_name, table_name
FROM warehouse_catalog
WHERE column_name = 'HSP_ACCOUNT_ID'
ORDER BY schema_name, table_name;

-- (b) Drop backup and old copies. The obvious version has a bug:
SELECT schema_name, table_name
FROM warehouse_catalog
WHERE column_name = 'HSP_ACCOUNT_ID'
  AND table_name NOT LIKE '%_OLD%'
  AND table_name NOT LIKE '%_BKP%';
-- In LIKE, "_" means "any one character", so '%_OLD%' also matches ACCT_HOLD ("H" + "OLD").
-- Escape the underscore:
SELECT schema_name, table_name
FROM warehouse_catalog
WHERE column_name = 'HSP_ACCOUNT_ID'
  AND table_name NOT LIKE '%\_OLD%' ESCAPE '\'
  AND table_name NOT LIKE '%\_BKP%' ESCAPE '\'
ORDER BY schema_name, table_name;
-- SQL Server also accepts '%[_]OLD%'.

-- (c) Tables that have a patient ID and at least one date or time column.
SELECT schema_name, table_name
FROM warehouse_catalog
GROUP BY schema_name, table_name
HAVING SUM(column_name = 'PAT_ID') > 0
   AND SUM(data_type = 'DATETIME') > 0
ORDER BY table_name;
-- SQL Server: SUM(CASE WHEN column_name = 'PAT_ID' THEN 1 ELSE 0 END) > 0.

-- (d) Bonus: the same search on this database's own catalog.
SELECT m.name AS table_name, p.name AS column_name, p.type
FROM sqlite_master m, pragma_table_info(m.name) p
WHERE m.type = 'table' AND p.name LIKE '%dept%'
ORDER BY m.name;
-- The real-world versions:
--   SQL Server:  SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE COLUMN_NAME LIKE '%ACCOUNT%';
--   Oracle:      SELECT owner, table_name FROM all_tab_columns WHERE column_name LIKE '%ACCOUNT%';
