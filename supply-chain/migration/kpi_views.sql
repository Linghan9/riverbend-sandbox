-- REPORT LAYER: the views the new Power BI pages sit on.
-- load_extract.py runs this file after loading the tables, so a fix here takes effect
-- on the next load. This plays the role of the semantic model: measures and the tables
-- built on top of the data.
--
-- tieout.py reads these views by name and by column, so when you fix one, keep its
-- name and its output columns.


-- Page 1. Spend by vendor company. Duplicate vendor records roll up to one company.
DROP VIEW IF EXISTS v_spend_by_company;
CREATE VIEW v_spend_by_company AS
WITH company AS (
  SELECT vendor_id,
         FIRST_VALUE(vendor_name) OVER (PARTITION BY tax_id ORDER BY vendor_id) AS company_name
  FROM vendor
)
SELECT c.company_name,
       ROUND(SUM(i.line_amount), 2) AS spend,
       ROUND(100.0 * SUM(i.line_amount) / SUM(SUM(i.line_amount)) OVER (), 1) AS pct_of_total
FROM invoice_line i
JOIN company c ON c.vendor_id = i.vendor_id
GROUP BY c.company_name;


-- Page 2. Three-way match status for every invoice line, and the summary by status.
DROP VIEW IF EXISTS v_invoice_match;
CREATE VIEW v_invoice_match AS
WITH rcv AS (
  SELECT po_number, po_line, SUM(qty_received) AS qty_received
  FROM receipt GROUP BY po_number, po_line
)
SELECT i.invoice_number, i.invoice_line, i.vendor_id, i.invoice_date,
       CASE
         WHEN i.po_number IS NULL THEN 'No PO'
         WHEN i.unit_price <> p.unit_price THEN 'Price exception'
         WHEN i.qty_invoiced > r.qty_received THEN 'Quantity exception'
         ELSE 'Matched'
       END AS match_status
FROM invoice_line i
LEFT JOIN po_line p ON p.po_number = i.po_number AND p.po_line = i.po_line
LEFT JOIN rcv r ON r.po_number = i.po_number AND r.po_line = i.po_line;

DROP VIEW IF EXISTS v_match_summary;
CREATE VIEW v_match_summary AS
SELECT match_status,
       COUNT(*) AS lines,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM v_invoice_match
GROUP BY match_status;


-- Fact table for the clinical pages: one row per supply line on a completed case,
-- cost already in EACH (contract price on the case date if there is one, else list).
DROP VIEW IF EXISTS v_fact_case_supply;
CREATE VIEW v_fact_case_supply AS
SELECT u.usage_id,
       sc.case_id, sc.case_date, sc.procedure_code,
       s.surgeon_name,
       u.item_id, im.category,
       u.qty_used AS qty_each,
       COALESCE(c.contract_price, im.list_price) / im.units_per_uom AS unit_cost_each,
       u.qty_used * COALESCE(c.contract_price, im.list_price) / im.units_per_uom AS extended_cost,
       u.wasted_flag
FROM case_supply_usage u
JOIN surgical_case sc ON sc.case_id = u.case_id AND sc.case_status = 'Completed'
JOIN surgeon s ON s.surgeon_id = sc.surgeon_id
JOIN item_master im ON im.item_id = u.item_id
LEFT JOIN contract_price c ON c.item_id = u.item_id
                          AND sc.case_date BETWEEN c.effective_start AND c.effective_end;


-- Page 3. Knee replacement cost per case by surgeon, July to December.
DROP VIEW IF EXISTS v_tka_cost_by_surgeon;
CREATE VIEW v_tka_cost_by_surgeon AS
SELECT surgeon_name,
       COUNT(DISTINCT case_id) AS cases,
       ROUND(SUM(extended_cost) / COUNT(DISTINCT case_id), 2) AS avg_cost_per_case
FROM v_fact_case_supply
WHERE procedure_code = 'TKA' AND case_date >= '2025-07-01'
GROUP BY surgeon_name;


-- Page 4. Supply cost per completed case, by procedure, for the full year.
DROP VIEW IF EXISTS v_cost_per_case_by_procedure;
CREATE VIEW v_cost_per_case_by_procedure AS
WITH volume(procedure_code, cases) AS (
  -- Case volume by procedure, from the Tableau "Case Volume" sheet
  VALUES ('TKA', 429), ('THA', 236), ('PPM', 212), ('ICD', 93), ('ABL', 230)
)
SELECT f.procedure_code,
       v.cases,
       ROUND(SUM(f.extended_cost) / v.cases, 2) AS avg_cost_per_case
FROM v_fact_case_supply f
JOIN volume v ON v.procedure_code = f.procedure_code
GROUP BY f.procedure_code, v.cases;


-- Page 5. Invoice spend by category group (the new Power BI category hierarchy).
DROP VIEW IF EXISTS v_spend_by_category_group;
CREATE VIEW v_spend_by_category_group AS
SELECT m.category_group,
       ROUND(SUM(i.line_amount), 2) AS spend
FROM invoice_line i
JOIN item_master im ON im.item_id = i.item_id
JOIN category_map m ON m.category = im.category
GROUP BY m.category_group;


-- Page 6. Invoice spend by criticality tier, on the new risk scale (3 = most critical).
DROP VIEW IF EXISTS v_spend_by_criticality;
CREATE VIEW v_spend_by_criticality AS
SELECT CASE im.criticality_code
         WHEN '3' THEN 'Critical'
         WHEN '2' THEN 'Important'
         WHEN '1' THEN 'Routine'
       END AS criticality,
       ROUND(SUM(i.line_amount), 2) AS spend
FROM invoice_line i
JOIN item_master im ON im.item_id = i.item_id
GROUP BY 1;


-- Page 7. Scheduled cases at risk from an open backorder on a critical item,
-- 2025-12-16 to 2025-12-29, counted per item.
DROP VIEW IF EXISTS v_backorder_risk;
CREATE VIEW v_backorder_risk AS
SELECT im.description AS item_on_backorder,
       COUNT(*) AS cases_at_risk
FROM surgical_case sc
JOIN preference_card pc ON pc.surgeon_id = sc.surgeon_id AND pc.procedure_code = sc.procedure_code
JOIN backorder b ON b.item_id = pc.item_id AND b.resolved_date IS NULL
JOIN item_master im ON im.item_id = pc.item_id
WHERE sc.case_status = 'Scheduled'
  AND sc.case_date BETWEEN '2025-12-16' AND '2025-12-29'
  AND sc.case_date < b.expected_release_date
  AND im.criticality_code = '3'
GROUP BY im.description;


-- Page 8. Runs of 3 or more consecutive calendar days at or below the reorder point.
DROP VIEW IF EXISTS v_low_stock_runs;
CREATE VIEW v_low_stock_runs AS
WITH low AS (
  SELECT location_id, item_id, snapshot_date,
         CAST(julianday(snapshot_date) AS INTEGER)
           - ROW_NUMBER() OVER (PARTITION BY location_id, item_id ORDER BY snapshot_date) AS grp
  FROM inventory_snapshot
  WHERE on_hand_qty <= reorder_point
)
SELECT l.location_id,
       im.description,
       MIN(l.snapshot_date) AS first_day,
       MAX(l.snapshot_date) AS last_day,
       COUNT(*) AS days_low
FROM low l
JOIN item_master im ON im.item_id = l.item_id
GROUP BY l.location_id, im.description, l.grp
HAVING COUNT(*) >= 3;
