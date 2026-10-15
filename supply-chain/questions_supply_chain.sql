-- SUPPLY CHAIN: SQL practice on a hospital's supply chain, 2025.
-- Write your answers below each question (or in your own file) and run:
--     python run_sql.py my_answers.sql
-- Check solutions_supply_chain.sql only after you've tried. Say your approach out loud first.
--
-- "Today" in this dataset is 2025-12-15. Cases after that date are scheduled, not done.
--
-- Tables:
--   item_master         every product the hospital buys (item_id, description, manufacturer,
--                       mfr_catalog_no, category, purchase_uom, units_per_uom, list_price, is_implant)
--   vendor              who we buy from (vendor_id, vendor_name, vendor_type, tax_id)
--   contract_price      group-purchasing (GPO) contract prices, with effective_start / effective_end
--   po_line             purchase order lines (po_number, po_line, po_date, vendor_id, item_id,
--                       qty_ordered, purchase_uom, unit_price, ship_to_location, po_type)
--   receipt             what was received against each PO line (qty_received, received_date)
--   invoice_line        what vendors billed (invoice_number, vendor_id, invoice_date, po_number,
--                       po_line, item_id, qty_invoiced, unit_price, line_amount)
--   surgical_case       one row per case (case_date, surgeon_id, procedure_code, case_status)
--   case_supply_usage   supplies used on each case, always counted in EACH (qty_used, wasted_flag)
--   preference_card     what each surgeon wants opened for each procedure (last_updated)
--   surgeon, procedure, location
--   inventory_snapshot  daily on-hand count vs par level and reorder point, by location
--   backorder           vendor backorders (reported, expected release, resolved, substitute item)
--
-- Units matter here: purchase_uom is how an item is bought (BX = box), units_per_uom is how
-- many EACH are in it. A box of 100 gloves costs 9.50; one glove costs 0.095.


-- ============================================================================
-- Part A. Clean master data first
-- ============================================================================

-- S1. Find items that exist twice in the item master: the same manufacturer catalog number
--     under different item IDs. Show the IDs and descriptions side by side.
--                                                            (expect 4 rows)


-- S2. Find vendors that exist twice. Matching names won't catch them all; find a column that
--     identifies one legal company.                          (expect 2 rows)


-- S3. Invoice spend by vendor, counting duplicate vendor records as one company. Show each
--     vendor's share of total spend and the running (cumulative) share, largest first.
--                                                            (expect 7 rows)


-- S4. (a) A PO line is "on contract" when that vendor and item have a contract price in effect
--         on the PO date. Count the off-contract lines and their spend.
--                                                            (expect 1 row: 500 lines)
--     (b) Break the off-contract spend down by vendor and item, largest first.
--                                                            (expect 29 rows)
--     (c) Some of (a) is a false alarm caused by S1 and S2. Re-run (a) after mapping each
--         vendor and item to its master record.              (expect 1 row: 261 lines)
--         What is left, and why is it off contract?


-- ============================================================================
-- Part B. Procure-to-pay
-- ============================================================================

-- S5. Find invoices billed above the contract price that was in effect on the PO date.
--     Summarize by vendor, item and PO month, with the dollars overbilled.
--                                                            (expect 3 rows)


-- S6. Three-way match. Classify every invoice line as one of:
--       'No PO'               no PO number on the invoice
--       'Price exception'     invoice price differs from the PO price
--       'Quantity exception'  invoiced more than was received on that PO line
--       'Matched'             everything else
--     (a) Count lines by status, with each status's share.   (expect 4 rows)
--     (b) Match rate by invoice month. Which months dip, and why?
--                                                            (expect 12 rows)


-- S7. Some invoices were sent twice under a slightly different invoice number (case, spaces,
--     or a "-1" on the end). Find them, with the amount paid twice.
--                                                            (expect 12 rows)


-- ============================================================================
-- Part C. Clinical integration: cases, surgeons and implants
-- ============================================================================

-- For cost questions, price one EACH as: the contract price in effect on the case date if there
-- is one, otherwise list price, divided by units_per_uom.

-- S8. Average supply cost per completed knee replacement (procedure 'TKA'), July to December,
--     by surgeon, highest first.                            (expect 5 rows)
--     Run it once without dividing by units_per_uom. How far off is it?


-- S9. On July 1 the hospital converted knee and hip implants from Apex to Meridian.
--     (a) Average implant cost per completed TKA, by month. (expect 12 rows)
--     (b) After July 1: for each surgeon, the share of knee and hip cases done with Meridian
--         implants.                                          (expect 5 rows)
--     (c) One surgeon didn't convert. Use preference_card to find out why.
--                                                            (expect 5 rows)


-- ============================================================================
-- Part D. Inventory and backorders
-- ============================================================================

-- S10. Find every run of 3 or more consecutive calendar days where an item's on-hand count was
--      at or below its reorder point. Show location, item, first day, last day and days.
--      Check the calendar before you trust "consecutive."    (expect 3 rows)


-- S11. Using preference cards, list the scheduled cases from 2025-12-16 to 2025-12-29 that need
--      an item with an open backorder (resolved_date is null) and fall before its expected
--      release date.                                         (expect 20 rows)


-- ============================================================================
-- Part E. Build the Power BI fact table
-- ============================================================================

-- S12. Create a view fact_case_supply with one row per supply line on a completed case:
--      case and date, surgeon, procedure, item, category, qty in EACH, cost per EACH,
--      extended cost, wasted flag.                           (expect 13,022 rows)
--      Then prove it ties to S8, and use it to total the cost of implants and catheters
--      opened but not used (wasted_flag = 'Y'), by procedure.
