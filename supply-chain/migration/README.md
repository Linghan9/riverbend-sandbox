# Round 2: the migration drill

The first round taught you to find bad data with SQL. This one is about what breaks *between* systems: a refresh that loads without a single error and still gives the wrong numbers.

## The situation

It's January 2026. Riverbend is retiring its Tableau supply chain dashboard and moving to Power BI. The ERP was upgraded at the same time, so the new dashboard reads from a new nightly extract, through a new pipeline.

The first refresh just ran. Every table loaded and the row counts look right. Then the supply chain director emails you:

> - The vendor page says one vendor has 100% of our spend.
> - Our invoice match rate looks better than it has ever been. I don't believe it.
> - The surgeon cost page is blank.
> - The backorder risk list is empty, and I know the ablation catheters are on backorder.
>
> Tableau was right. Make the new dashboard match it before we turn Tableau off.

Before Tableau was retired, its 2025 numbers were exported and signed off: `legacy_tableau_kpis.csv`. Those are your target.

## The rules

1. **Don't edit the extract.** It's what the source system sends. Fix things in the pipeline (`load_extract.py`), the report layer (`kpi_views.sql`) or the lookup table (`category_map.csv`).
2. **Don't read `source_system/erp_export.py`.** In real life you only ever see the files it writes. Reading it is reading the answer key.
3. **Don't edit `legacy_tableau_kpis.csv` or `tieout.py`.** They're the target and the referee.
4. **The director's list isn't the full list.** You aren't told how many defects there are. You're done when everything ties, not when the four complaints go away.
5. **Some KPIs have more than one cause.** Fixing one may change the numbers without making them tie. That's progress, not failure.

## Run it

From the `supply-chain` folder, once:

```
python build_supply_chain.py
python migration/source_system/erp_export.py
```

Then every time you change something:

```
python migration/load_extract.py
python migration/tieout.py
```

To look at the data:

```
python migration/run_sql.py "SELECT * FROM vendor"
python migration/tieout.py K2          every difference for one KPI
```

On Windows, use `py` if `python` isn't recognized.

## How to work it

Use the same habits each time a KPI fails, in this order:

1. **What exactly is wrong?** Read the tie-out at its grain. Missing rows, extra rows and wrong values point to different causes.
2. **Where is this number born?** Trace the view back through every table and join it depends on, to the source columns.
3. **What values actually exist?** Profile those columns in the loaded tables *and* in the extract CSVs. Don't trust a row count. Check nulls, distinct values and data types.
4. **What should the answer be?** Before you rerun the tie-out, write down which KPIs your fix should change, and to what.
5. **Afterward:** write the casebook entry (`CASEBOOK.md`).

A good first move on any failure: count the nulls in every column the view uses.

## When you're stuck

Ask Claude for a hint by KPI. `ANSWER_KEY.b64` holds a hint ladder for every defect: hint 1 says where to look, hint 2 says what's wrong, then the fix. Take one rung at a time.

Decode it only when you're finished, or when you've decided to give up on one:

```
python -c "import base64,pathlib; print(base64.b64decode(pathlib.Path('migration/ANSWER_KEY.b64').read_text()).decode())"
```

## Done when

- `tieout.py` reports 8 of 8.
- `CASEBOOK.md` has one entry per defect you fixed.
- You can explain each fix out loud in two sentences: what broke, and how you'd catch it next time before a user does.

That last one is the interview answer to "tell me about a time the numbers didn't tie."
