# Riverbend Supply Chain

A year (2025) of a made-up hospital's supply chain: what it buys, from whom, at what contract price, what the operating rooms and cath lab used on each case, and what the vendors billed. Everything is fake. As with the rest of Riverbend, the mess is on purpose.

It's built around the questions a health-system supply chain analytics team actually answers: is our invoice match rate healthy, how much are we spending off contract, what does a knee replacement cost by surgeon, did the implant conversion stick, and which scheduled cases are at risk from a backorder.

**It connects to Riverbend.** Surgeon IDs are Riverbend provider IDs (PRV0002, PRV0006, ...), so `surgeon` joins to `raw_providers` in `data/riverbend.db`.

## Start here

The data is generated, not stored in git. Build it first:

```
cd supply-chain
python build_supply_chain.py
```

That creates `supply_chain.db` and CSV copies of every table in `data/`. The fixed seed makes every rebuild identical. Standard library only: no `pip install` needed.

```
python run_sql.py "SELECT * FROM procedure"
python run_sql.py my_answers.sql
```

On Windows, use `py` if `python` isn't recognized.

## What's inside

| File | What it is |
| --- | --- |
| `build_supply_chain.py` | Generates `supply_chain.db` and `data/` |
| `questions_supply_chain.sql` | 12 SQL questions (S1–S12) with expected row counts |
| `solutions_supply_chain.sql` | Answer key, with SQL Server and Oracle notes |
| `run_sql.py` | Runs a query or a `.sql` file and prints a table |

| Table | Rows | What it is |
| --- | --- | --- |
| `item_master` | 44 | Every product: catalog number, category, purchase unit, units per unit, list price |
| `vendor` | 9 | Distributors and manufacturers, with tax ID |
| `contract_price` | 48 | Group-purchasing contract prices and their effective dates |
| `po_line` | ~4,900 | Purchase order lines: weekly replenishment, plus bill-only orders for implants |
| `receipt` | ~4,800 | What arrived against each PO line |
| `invoice_line` | ~4,900 | What vendors billed |
| `surgical_case` | ~1,350 | Knee and hip replacements, pacemakers, ICDs and AFib ablations |
| `case_supply_usage` | ~13,000 | Supplies used on each case, counted in each |
| `preference_card` | 216 | What each surgeon wants opened for each procedure |
| `surgeon`, `procedure`, `location` | small | Dimensions |
| `inventory_snapshot` | ~1,400 | Daily on-hand vs par and reorder point, Sept–Dec |
| `backorder` | 8 | Vendor backorders, with substitutes where there is one |

## The known defects

All deliberate. Each one happens in real hospital supply chains.

1. **Duplicate item records:** the same product under two item IDs, and only one is on contract
2. **Duplicate vendor records:** one company, two vendor IDs, two spellings
3. **Contract prices that change mid-year,** so the right price depends on the date
4. **A price file loaded late** in the purchasing system
5. **Invoices that don't match** their PO or their receipt
6. **Invoices billed twice** under a slightly different number
7. **Bought by the box, used by the each:** usage is counted in each, prices are per box
8. **A product conversion** that not every surgeon followed
9. **A day with no inventory count**
10. **Backorders** that push purchases to an off-contract distributor

## Question map

| | What it practices | The real-world question |
| --- | --- | --- |
| S1–S2 | GROUP BY / HAVING on identity columns | Is the item and vendor master clean? |
| S3 | Window functions, running totals | Where does the money go (Pareto)? |
| S4 | NOT EXISTS with a date-effective join | How much spend is off contract, really? |
| S5 | Date-effective joins | Are vendors billing the contract price? |
| S6 | CASE classification, LEFT JOINs | What's our invoice match rate? |
| S7 | String normalization | Did we pay anything twice? |
| S8 | Unit-of-measure conversion, COALESCE | What does a knee replacement cost, by surgeon? |
| S9 | Before/after analysis, conditional aggregation | Did the implant conversion stick? |
| S10 | Gaps and islands | Where are we running low, and for how long? |
| S11 | Multi-table join on a schedule | Which upcoming cases are at risk? |
| S12 | Designing a fact table | What would the Power BI model sit on? |

## Glossary

| Term | What it means |
| --- | --- |
| **GPO** | Group purchasing organization. Negotiates contract prices on behalf of many hospitals. |
| **Contract price / on contract** | The negotiated price for a vendor and item, valid between two dates. Buying at a different price or from a different vendor is off contract, also called leakage. |
| **Item master** | The hospital's catalog of every product it buys. Duplicates here break every downstream report. |
| **Unit of measure (UOM)** | How an item is bought (box, case, each). Usage is usually counted in each, so converting is mandatory. |
| **PO, receipt, invoice** | What we ordered, what arrived, what we were billed. |
| **Three-way match** | Checking the invoice against the PO (price) and the receipt (quantity) before paying it. |
| **Match rate** | Share of invoice lines that pass the three-way match. Exceptions go to a person to resolve. |
| **Bill-only implant** | An implant used from the vendor's stock in the OR; the PO is created after the case. |
| **Preference card** | The list of supplies a surgeon wants opened for a procedure. Stale cards drive waste and non-compliance. |
| **Value analysis** | A clinical and supply chain team deciding whether a cheaper product is clinically equivalent. |
| **Product conversion** | Moving all users from one product to another, usually to a contracted or standardized one. |
| **Compliance** | Share of usage on the chosen product after a conversion. |
| **Cost per case** | Total supply cost of a procedure, usually compared by surgeon. |
| **Waste (opened, not used)** | Items opened in the room but not used, typically the wrong size. Still paid for. |
| **Par level / reorder point** | Target stock on the shelf, and the level that triggers a reorder. |
| **Backorder / substitution** | A vendor can't ship; the hospital switches to an approved alternative. |

## Power BI notes

S12 builds `fact_case_supply`, one row per supply line on a completed case, with cost already converted to each. Around it: `surgeon`, `procedure`, `item_master`, `location` and a date table. Because the grain is a supply line, count cases with `DISTINCTCOUNT(case_id)`, not rows.

A second fact table worth building is `invoice_line` with its match status from S6, at invoice-line grain, sharing the vendor (by tax ID) and item dimensions.
