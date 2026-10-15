-- SUPPLY CHAIN SOLUTIONS. Try questions_supply_chain.sql first.
-- Written for SQLite. Notes show the SQL Server and Oracle versions where they differ.


-- ============================================================================
-- Part A. Clean master data first
-- ============================================================================

-- S1. Duplicate items: one manufacturer catalog number, more than one item ID.
-- The catalog number is the manufacturer's identity for the product; the item ID is ours.
SELECT mfr_catalog_no,
       COUNT(*) AS records,
       GROUP_CONCAT(item_id, ', ') AS item_ids,
       GROUP_CONCAT(description, ' | ') AS descriptions
FROM item_master
GROUP BY mfr_catalog_no
HAVING COUNT(*) > 1
ORDER BY mfr_catalog_no;
-- SQL Server: STRING_AGG(item_id, ', '). Oracle: LISTAGG(item_id, ', ').


-- S2. Duplicate vendors. Names don't match reliably ("Dist." vs "Distribution"),
-- but a tax ID identifies one legal company.
SELECT tax_id,
       COUNT(*) AS records,
       GROUP_CONCAT(vendor_id, ', ') AS vendor_ids,
       GROUP_CONCAT(vendor_name, ' | ') AS vendor_names
FROM vendor
GROUP BY tax_id
HAVING COUNT(*) > 1
ORDER BY tax_id;


-- S3. Invoice spend by real vendor, largest first, with each vendor's share and the running share.
WITH master AS (            -- one master vendor per tax ID: the lowest vendor_id
  SELECT tax_id, MIN(vendor_id) AS master_id FROM vendor GROUP BY tax_id
),
spend AS (
  SELECT m.master_id, SUM(i.line_amount) AS spend
  FROM invoice_line i
  JOIN vendor v ON v.vendor_id = i.vendor_id
  JOIN master m ON m.tax_id = v.tax_id
  GROUP BY m.master_id
)
SELECT v.vendor_name,
       ROUND(s.spend, 2) AS spend,
       ROUND(100.0 * s.spend / SUM(s.spend) OVER (), 1) AS pct_of_total,
       ROUND(100.0 * SUM(s.spend) OVER (ORDER BY s.spend DESC) / SUM(s.spend) OVER (), 1) AS cumulative_pct
FROM spend s
JOIN vendor v ON v.vendor_id = s.master_id
ORDER BY s.spend DESC;
-- A few implant vendors carry most of the money. That's why value analysis starts with implants.


-- S4. Off-contract purchases.
-- (a) A PO line is on contract when the same vendor and item have a contract in effect on the PO date.
SELECT COUNT(*) AS off_contract_lines,
       ROUND(SUM(p.qty_ordered * p.unit_price), 2) AS off_contract_spend
FROM po_line p
WHERE NOT EXISTS (
  SELECT 1 FROM contract_price c
  WHERE c.vendor_id = p.vendor_id
    AND c.item_id = p.item_id
    AND p.po_date BETWEEN c.effective_start AND c.effective_end
);

-- (b) Where it comes from.
SELECT p.vendor_id, v.vendor_name, i.description,
       COUNT(*) AS lines,
       ROUND(SUM(p.qty_ordered * p.unit_price), 2) AS spend
FROM po_line p
JOIN vendor v ON v.vendor_id = p.vendor_id
JOIN item_master i ON i.item_id = p.item_id
WHERE NOT EXISTS (
  SELECT 1 FROM contract_price c
  WHERE c.vendor_id = p.vendor_id AND c.item_id = p.item_id
    AND p.po_date BETWEEN c.effective_start AND c.effective_end
)
GROUP BY p.vendor_id, v.vendor_name, i.description
ORDER BY spend DESC;
-- Part of (a) isn't really off contract: the duplicate vendor and item records from S1 and S2
-- never got contracts attached. The real leakage is Apex implants after the contract ended
-- on June 30, and the Bluegate purchases made during a backorder.

-- (c) Same test, after resolving duplicates to their master vendor (tax ID) and master item
-- (catalog number).
WITH vmaster AS (
  SELECT v.vendor_id, (SELECT MIN(v2.vendor_id) FROM vendor v2 WHERE v2.tax_id = v.tax_id) AS master_id
  FROM vendor v
),
imaster AS (
  SELECT i.item_id, (SELECT MIN(i2.item_id) FROM item_master i2 WHERE i2.mfr_catalog_no = i.mfr_catalog_no) AS master_id
  FROM item_master i
)
SELECT COUNT(*) AS off_contract_lines,
       ROUND(SUM(p.qty_ordered * p.unit_price), 2) AS off_contract_spend
FROM po_line p
JOIN vmaster vm ON vm.vendor_id = p.vendor_id
JOIN imaster im ON im.item_id = p.item_id
WHERE NOT EXISTS (
  SELECT 1 FROM contract_price c
  WHERE c.vendor_id = vm.master_id AND c.item_id = im.master_id
    AND p.po_date BETWEEN c.effective_start AND c.effective_end
);


-- ============================================================================
-- Part B. Procure-to-pay
-- ============================================================================

-- S5. Invoices billed above the contract price that governed the order (the price on the PO date).
SELECT i.vendor_id, im.description,
       substr(p.po_date, 1, 7) AS po_month,
       COUNT(*) AS lines,
       c.contract_price,
       MAX(i.unit_price) AS invoiced_price,
       ROUND(SUM(i.qty_invoiced * (i.unit_price - c.contract_price)), 2) AS overbilled
FROM invoice_line i
JOIN po_line p ON p.po_number = i.po_number AND p.po_line = i.po_line
JOIN contract_price c ON c.vendor_id = i.vendor_id AND c.item_id = i.item_id
                     AND p.po_date BETWEEN c.effective_start AND c.effective_end
JOIN item_master im ON im.item_id = i.item_id
WHERE i.unit_price > c.contract_price + 0.005
GROUP BY i.vendor_id, im.description, substr(p.po_date, 1, 7), c.contract_price
ORDER BY po_month;
-- The pacemaker vendor kept billing the old price after the July 1 price drop.
-- The gloves don't show here: their invoices were right and their POs were wrong. S6 shows those.


-- S6. Three-way match: invoice against PO (price) and against receipts (quantity).
WITH rcv AS (
  SELECT po_number, po_line, SUM(qty_received) AS qty_received
  FROM receipt GROUP BY po_number, po_line
),
matched AS (
  SELECT i.*,
         CASE
           WHEN i.po_number IS NULL THEN 'No PO'
           WHEN ABS(i.unit_price - p.unit_price) > 0.005 THEN 'Price exception'
           WHEN i.qty_invoiced > COALESCE(r.qty_received, 0) THEN 'Quantity exception'
           ELSE 'Matched'
         END AS match_status
  FROM invoice_line i
  LEFT JOIN po_line p ON p.po_number = i.po_number AND p.po_line = i.po_line
  LEFT JOIN rcv r ON r.po_number = i.po_number AND r.po_line = i.po_line
)
SELECT match_status,
       COUNT(*) AS lines,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM matched
GROUP BY match_status
ORDER BY lines DESC;

-- (b) Match rate by invoice month.
WITH rcv AS (
  SELECT po_number, po_line, SUM(qty_received) AS qty_received
  FROM receipt GROUP BY po_number, po_line
),
matched AS (
  SELECT i.invoice_date,
         CASE
           WHEN i.po_number IS NULL THEN 'No PO'
           WHEN ABS(i.unit_price - p.unit_price) > 0.005 THEN 'Price exception'
           WHEN i.qty_invoiced > COALESCE(r.qty_received, 0) THEN 'Quantity exception'
           ELSE 'Matched'
         END AS match_status
  FROM invoice_line i
  LEFT JOIN po_line p ON p.po_number = i.po_number AND p.po_line = i.po_line
  LEFT JOIN rcv r ON r.po_number = i.po_number AND r.po_line = i.po_line
)
SELECT substr(invoice_date, 1, 7) AS invoice_month,
       COUNT(*) AS lines,
       SUM(match_status = 'Matched') AS matched,
       ROUND(100.0 * SUM(match_status = 'Matched') / COUNT(*), 1) AS match_rate_pct
FROM matched
GROUP BY substr(invoice_date, 1, 7)
ORDER BY invoice_month;
-- Watch July to October: the glove PO price wasn't updated, and the pacemaker invoices were.
-- Also note what this test misses: a duplicate invoice matches its PO perfectly. That's S7.
-- SQL Server: SUM(CASE WHEN match_status = 'Matched' THEN 1 ELSE 0 END).


-- S7. Duplicate invoices: the same bill sent twice under a slightly different number.
-- Normalize the number (trim, upper case, drop a trailing "-1"), then look for repeats per vendor.
WITH norm AS (
  SELECT vendor_id, invoice_number,
         CASE WHEN UPPER(TRIM(invoice_number)) LIKE '%-1'
              THEN substr(UPPER(TRIM(invoice_number)), 1, length(TRIM(invoice_number)) - 2)
              ELSE UPPER(TRIM(invoice_number)) END AS norm_number,
         SUM(line_amount) AS amount
  FROM invoice_line
  GROUP BY vendor_id, invoice_number
)
SELECT vendor_id, norm_number,
       COUNT(*) AS copies,
       GROUP_CONCAT('[' || invoice_number || ']', ' ') AS numbers_as_billed,
       ROUND(MAX(amount), 2) AS amount_each,
       ROUND(SUM(amount) - MAX(amount), 2) AS duplicate_amount
FROM norm
GROUP BY vendor_id, norm_number
HAVING COUNT(*) > 1
ORDER BY vendor_id, norm_number;
-- The brackets make the trailing space visible. Another check that catches these:
-- same vendor, same PO and same total, different invoice number.


-- ============================================================================
-- Part C. Clinical integration: cases, surgeons and implants
-- ============================================================================

-- Cost of one EACH on a given date: the contract price in effect, otherwise list price,
-- divided by the units in the purchase unit (a box of 100 gloves costs 9.50, a glove 0.095).

-- S8. Average supply cost per completed knee replacement (TKA), July to December, by surgeon.
WITH line_cost AS (
  SELECT sc.case_id, sc.surgeon_id,
         u.qty_used * COALESCE(c.contract_price, im.list_price) / im.units_per_uom AS cost
  FROM surgical_case sc
  JOIN case_supply_usage u ON u.case_id = sc.case_id
  JOIN item_master im ON im.item_id = u.item_id
  LEFT JOIN contract_price c ON c.item_id = u.item_id
                            AND sc.case_date BETWEEN c.effective_start AND c.effective_end
  WHERE sc.procedure_code = 'TKA' AND sc.case_status = 'Completed'
    AND sc.case_date >= '2025-07-01'
),
per_case AS (
  SELECT case_id, surgeon_id, SUM(cost) AS case_cost FROM line_cost GROUP BY case_id, surgeon_id
)
SELECT surgeon_id, COUNT(*) AS cases, ROUND(AVG(case_cost), 2) AS avg_cost_per_case
FROM per_case
GROUP BY surgeon_id
ORDER BY avg_cost_per_case DESC;
-- Leave out "/ im.units_per_uom" and every case looks about $2,000 more expensive:
-- 12 gloves priced as 12 boxes, 20 gauze as 20 boxes of 200, 4 gowns as 4 boxes of 20,
-- 3 sutures as 3 boxes of 36.
-- A subtler leak: cases that used a duplicate item ID (S1) fall back to list price, because
-- the duplicate has no contract. Map items to their master record to price them correctly.

-- S9. The July 1 implant conversion.
-- (a) Average implant cost per completed TKA by month.
WITH implant_cost AS (
  SELECT sc.case_id, substr(sc.case_date, 1, 7) AS case_month,
         SUM(u.qty_used * COALESCE(c.contract_price, im.list_price) / im.units_per_uom) AS implant_cost
  FROM surgical_case sc
  JOIN case_supply_usage u ON u.case_id = sc.case_id
  JOIN item_master im ON im.item_id = u.item_id AND im.is_implant = 1
  LEFT JOIN contract_price c ON c.item_id = u.item_id
                            AND sc.case_date BETWEEN c.effective_start AND c.effective_end
  WHERE sc.procedure_code = 'TKA' AND sc.case_status = 'Completed'
  GROUP BY sc.case_id, substr(sc.case_date, 1, 7)
)
SELECT case_month, COUNT(*) AS cases, ROUND(AVG(implant_cost), 2) AS avg_implant_cost
FROM implant_cost
GROUP BY case_month
ORDER BY case_month;

-- (b) Compliance after the conversion: share of each surgeon's knee and hip cases on Meridian.
WITH case_brand AS (
  SELECT sc.case_id, sc.surgeon_id,
         MAX(im.manufacturer = 'Apex Orthopedics') AS used_apex
  FROM surgical_case sc
  JOIN case_supply_usage u ON u.case_id = sc.case_id
  JOIN item_master im ON im.item_id = u.item_id AND im.is_implant = 1
  WHERE sc.procedure_code IN ('TKA', 'THA') AND sc.case_status = 'Completed'
    AND sc.case_date >= '2025-07-01'
  GROUP BY sc.case_id, sc.surgeon_id
)
SELECT surgeon_id, COUNT(*) AS cases,
       SUM(used_apex) AS apex_cases,
       ROUND(100.0 * (COUNT(*) - SUM(used_apex)) / COUNT(*), 1) AS meridian_pct
FROM case_brand
GROUP BY surgeon_id
ORDER BY meridian_pct;

-- (c) Why: compare each surgeon's preference card with the conversion date.
SELECT pc.surgeon_id, pc.last_updated,
       MAX(im.manufacturer) AS implant_brand_on_card
FROM preference_card pc
JOIN item_master im ON im.item_id = pc.item_id AND im.is_implant = 1
WHERE pc.procedure_code = 'TKA'
GROUP BY pc.surgeon_id, pc.last_updated
ORDER BY pc.last_updated;
-- One card was last touched in 2023 and still lists Apex. The conversion never reached it.


-- ============================================================================
-- Part D. Inventory and backorders
-- ============================================================================

-- S10. Runs of 3 or more consecutive calendar days at or below the reorder point.
-- Gaps and islands: within a run, (day number - row number) stays constant.
WITH low AS (
  SELECT location_id, item_id, snapshot_date,
         CAST(julianday(snapshot_date) AS INTEGER)
           - ROW_NUMBER() OVER (PARTITION BY location_id, item_id ORDER BY snapshot_date) AS grp
  FROM inventory_snapshot
  WHERE on_hand_qty <= reorder_point
)
SELECT l.location_id, im.description,
       MIN(snapshot_date) AS first_day, MAX(snapshot_date) AS last_day,
       COUNT(*) AS days_low
FROM low l
JOIN item_master im ON im.item_id = l.item_id
GROUP BY l.location_id, im.description, grp
HAVING COUNT(*) >= 3
ORDER BY first_day;
-- There's no snapshot for 2025-11-27. Comparing each row with the previous ROW (LAG) would join
-- Nov 26 and Nov 28 into one run. Using the calendar keeps the missing day as a break.
-- SQL Server: DATEDIFF(day, '2000-01-01', snapshot_date). Oracle: snapshot_date - DATE '2000-01-01'.

-- S11. Scheduled cases at risk from an open backorder, through 2025-12-29.
SELECT sc.case_id, sc.case_date, sc.surgeon_id, sc.procedure_code,
       im.description AS item_on_backorder, b.expected_release_date
FROM surgical_case sc
JOIN preference_card pc ON pc.surgeon_id = sc.surgeon_id AND pc.procedure_code = sc.procedure_code
JOIN backorder b ON b.item_id = pc.item_id AND b.resolved_date IS NULL
JOIN item_master im ON im.item_id = pc.item_id
WHERE sc.case_status = 'Scheduled'
  AND sc.case_date BETWEEN '2025-12-16' AND '2025-12-29'
  AND sc.case_date < b.expected_release_date
ORDER BY sc.case_date, sc.case_id;


-- ============================================================================
-- Part E. Build the Power BI fact table
-- ============================================================================

-- S12. One row per supply line on a completed case, with the cost already in EACH.
DROP VIEW IF EXISTS fact_case_supply;
CREATE VIEW fact_case_supply AS
SELECT u.usage_id,
       sc.case_id, sc.case_date, substr(sc.case_date, 1, 7) AS case_month,
       sc.surgeon_id, sc.procedure_code, sc.location_id,
       u.item_id, im.category, im.manufacturer, im.is_implant,
       u.qty_used AS qty_each,
       COALESCE(c.contract_price, im.list_price) / im.units_per_uom AS unit_cost_each,
       u.qty_used * COALESCE(c.contract_price, im.list_price) / im.units_per_uom AS extended_cost,
       u.wasted_flag
FROM case_supply_usage u
JOIN surgical_case sc ON sc.case_id = u.case_id AND sc.case_status = 'Completed'
JOIN item_master im ON im.item_id = u.item_id
LEFT JOIN contract_price c ON c.item_id = u.item_id
                          AND sc.case_date BETWEEN c.effective_start AND c.effective_end;

SELECT COUNT(*) AS fact_rows FROM fact_case_supply;

-- Check it ties out to S8 before anyone builds a visual on it.
SELECT surgeon_id, ROUND(SUM(extended_cost) / COUNT(DISTINCT case_id), 2) AS avg_cost_per_case
FROM fact_case_supply
WHERE procedure_code = 'TKA' AND case_date >= '2025-07-01'
GROUP BY surgeon_id
ORDER BY avg_cost_per_case DESC;

-- What it costs to open the wrong size: implants and catheters opened in the room, not used.
SELECT procedure_code, COUNT(*) AS wasted_lines, ROUND(SUM(extended_cost), 2) AS wasted_cost
FROM fact_case_supply
WHERE wasted_flag = 'Y'
GROUP BY procedure_code
ORDER BY wasted_cost DESC;
-- In Power BI: fact_case_supply in the middle, with surgeon, procedure, item and a date table
-- around it. Grain is one supply line per case, so case counts need DISTINCTCOUNT(case_id).
