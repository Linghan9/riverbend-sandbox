-- ROUND 3: the problems from real extract and reporting work, in a hospital setting.
-- Write your answers below each question (or in a new file) and run:
--     python run_sql.py my_answers.sql
-- Check solutions_round3.sql only after you've tried. Say your approach out loud first.
--
-- Tables for this round:
--   acct_extract_first    an "October" hospital account extract another team emailed you
--   acct_extract_second   the corrected October extract they sent later
--   acct_source           the source report's own October export (the trusted reference)
--   acct_last_month       last month's final file (September)
--   census_daily_raw      a daily archive of raw bed-census snapshots, stacked from files
--   dim_department, dim_month, fact_budget_month, fact_actual_month   a small star schema
--   warehouse_catalog     the column catalog of a hospital data warehouse (Epic-style names)
--
-- Account columns: account_id, dept_name, payer, admit_date, discharge_date, account_status,
--   total_charges, total_payments, total_adjustments, balance, last_txn_date, snapshot_month


-- ============================================================================
-- Part A. The monthly extract
-- ============================================================================

-- Q21. When you export a report, the bottom of the file often has two extra lines
--      that aren't data: a "Total" row and an "Applied filters: ..." line that says
--      which filter the report had on. Both extract tables were loaded straight from
--      exports like that, so each table has these 2 fake rows.
--      Find them in both tables (hint: real account IDs are all numbers), then read
--      what each "Applied filters" line says.                (expect 4 rows)


-- Q22. The first file was sent as "the October extract." Using only the data inside it,
--      show each file's snapshot month(s), latest transaction date and account count.
--      Leave out the non-account rows. Is the first file October?
--                                                            (expect 2 rows)


-- Q23. Test the first file against its own arithmetic: balance should equal
--      total_charges - total_payments - total_adjustments. List the accounts that fail,
--      with the expected balance and the difference.
--                                                            (expect 6 rows)


-- Q24. Reconcile the second extract to acct_source on account_id.
--      (a) Join on account_id exactly as delivered. How many source accounts match?
--                                                            (expect 1,941)
--      (b) Find out why the rest don't, fix the key, and count matched, only-in-source
--          and only-in-extract.                              (expect 2,000 / 0 / 0)
--      (c) On the matched rows, count differences in dept_name, account_status and balance.
--          One field disagrees on 525 rows. Find out why and fix it until all three are 0.


-- Q25. (a) Which accounts were Open or Billed last month but don't appear in this month's
--          source at all?                                    (expect 5 rows)
--      (b) Count every account that dropped out, by last month's status.
--                                                            (expect 3 rows)


-- ============================================================================
-- Part B. The daily snapshot archive
-- ============================================================================

-- Q26. census_daily_raw stacks every snapshot file. Some days were refreshed twice.
--      Return one row per day per unit, keeping the latest refresh.
--                                                            (expect 90 rows)


-- Q27. Which calendar days between the first and last snapshot have no snapshot at all?
--      Don't hard-code the date range.                       (expect 1 row)


-- Q28. Hospital-wide occupied beds by day (from your Q26 result), occupancy %, the change
--      from the previous snapshot, and the number of days since the previous snapshot.
--      What's misleading about the last row?                 (expect 15 rows)


-- ============================================================================
-- Part C. A small star schema
-- ============================================================================

-- Q29. (a) Budget vs actual by department for July–September 2026: budget, actual,
--          variance and % of budget, highest % first.        (expect 8 rows)
--      (b) Join the two fact tables row to row on dept_key and month_key and sum the
--          budget. How far off is it, and why?               (expect 1 row)


-- ============================================================================
-- Part D. Finding your way in a new warehouse
-- ============================================================================

-- Q30. Use warehouse_catalog the way you'd use the catalog views on day one in an unfamiliar warehouse.
--      (a) Which tables carry HSP_ACCOUNT_ID?                (expect 7 rows)
--      (b) Same, without backup or old copies (names with _BKP or _OLD).
--          Check your answer carefully.                      (expect 5 rows)
--      (c) Which tables have PAT_ID and at least one DATETIME column?
--                                                            (expect 4 rows)
--      (d) Bonus: list every column in THIS database with "dept" in its name.
--                                                            (expect 8 rows)
