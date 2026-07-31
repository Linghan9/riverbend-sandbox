# Exercises

Twelve exercises, in order. Roughly one per week at 6–8 hours a week, so
about a quarter of work. Each names the skill, the task, and the finish line.

---

## Exercise 1 — Get the machine running

**Skill:** environment isolation, VS Code, git

1. Open the folder in VS Code. Create a virtual environment, activate it,
   select it as the interpreter (`Ctrl+Shift+P` → "Python: Select Interpreter").
2. `pip install -r requirements.txt`
3. Run `python src/generate_data.py` and `python src/build_db.py`.
4. `git init`, commit everything except what `.gitignore` excludes.
5. Set a breakpoint inside `make_labs` in `src/generate_data.py`. Run the
   debugger. Step through one loop iteration. Inspect `value_repr` in the
   variables pane.

**Done when:** `pytest -q` runs and reports failures (not errors), and
`git log` shows one commit.

**Why the debugger first:** print-statement debugging will carry you about
a year and then become the bottleneck. Learn the real tool now, while the
code you're stepping through is simple.

---

## Exercise 2 — Look before you touch

**Skill:** data profiling, resisting the urge to start cleaning

Write `src/profile.py`. For every raw CSV it should report, per column:
dtype, null/blank count, distinct count, the 10 most frequent values, and
for anything numeric-looking, min/max/mean.

Do **not** clean anything yet. Just describe what's there.

**Done when:** you can answer these without opening Excel:
- How many distinct spellings does `department` actually have?
- What fraction of `result_value` in labs is not parseable as a number?
- Which encounter IDs in `billing.csv` don't appear in `encounters.csv`?

**Write your answers down** in `notes/profile_findings.md`. You will be
wrong about at least one of them later, and you'll want the record.

---

## Exercise 3 — The cleaning layer

**Skill:** writing tested, reusable functions

Fill in the stubs in `src/clean.py`. The tests in `tests/test_clean.py`
define the contract — read them first, they're the spec.

- `parse_flexible_date` — handles all three formats, returns `NaT` on junk
- `normalize_department` — six spellings → one canonical name
- `normalize_sex` — eight codes → `{"M", "F", None}`
- `parse_currency` — `"$1,234.56"` → `1234.56`
- `parse_lab_value` — returns `(value, was_censored)`; `"<0.01"` → `(0.01, True)`
- `normalize_zip` — five digits or `None`

**Done when:** `pytest tests/test_clean.py` is fully green.

**The lesson:** you wrote these once, in one place, with tests. Every
downstream thing imports them. Compare that to the alternative, where the
same date-parsing logic gets pasted into nine notebook cells and three of
them drift.

---

## Exercise 4 — Integrity validation

**Skill:** referential integrity, defensive data work

Write `src/validate.py` producing a report that counts:

- exact duplicate rows per table
- orphan foreign keys (encounters → patients, labs → encounters, billing → encounters)
- suspected duplicate patients (same DOB + zip, different `patient_id`)
- rows where `length_of_stay` disagrees with `discharge_date - admit_date`
- encounters with a discharge date before the admit date
- encounters with no discharge date

Output a tidy DataFrame: `check_name | severity | count | pct | example_ids`.

**Done when:** the report runs on one command and you could hand it to a
colleague without explaining it.

**Note:** you have already built this exact artifact for LSPP. Build it
again from scratch anyway. The second time is when the pattern becomes
yours rather than something you happened to produce.

---

## Exercise 5 — SQL: joins and aggregation

**Skill:** SQL fundamentals

Write these in `sql/` as `.sql` files, run against `data/riverbend.db`:

1. Encounter count and average LOS by department (post-normalization)
2. The 10 providers with the most encounters, with their specialty
3. Total charged and total paid by payer, with collection rate
4. Patients with 3+ encounters, with their first and last admit dates
5. Encounters that have labs but no billing record

**Done when:** each query returns the same answer as the pandas equivalent.
Verify at least two of them both ways. When they disagree — and one will —
find out which is right before moving on.

---

## Exercise 6 — SQL: window functions

**Skill:** window functions, which are the actual dividing line between
casual and competent SQL

Using `LAG`/`LEAD` and `PARTITION BY`, write a query that flags each
encounter with whether the same patient was readmitted within 30 days of
discharge.

Rules that matter:
- Exclude encounters ending in death
- Exclude the patient's final encounter (no chance to be readmitted)
- Planned readmissions would normally be excluded too — note in a comment
  that you can't do this here, and why that matters

**Done when:** your query and a pandas `groupby().shift()` implementation
produce identical row-level flags.

---

## Exercise 7 — The snapshot reconciliation

**Skill:** schema drift, and the professional instinct of not trusting a
column just because it has a familiar name

`raw_snapshot_202406` and `raw_snapshot_202412` are the same table, six
months apart. The column names changed. One column changed something worse.

Write `src/reconcile.py` that:
1. Maps v1 columns to v2 columns
2. Produces a unified long-format table with a `snapshot_date` column
3. Reports, for encounters present in both: which fields changed, and
   how many
4. **Flags the field whose values shifted in a way that is not a real
   change in the underlying facts**

**Done when:** you find the trap. There is exactly one, it is not subtle
once you look at the distributions, and it is invisible if you only look
at column names. If your change-report says a field changed for ~100% of
rows, stop and ask why before you write it up as a finding.

---

## Exercise 8 — Statistics, refreshed

**Skill:** getting the stats degree back

For the readmission flag from Exercise 6:

1. Compute the overall 30-day rate with a 95% confidence interval. Do it
   three ways — normal approximation, Wilson, and bootstrap — and explain
   which you'd report and why.
2. Compute rates by department with CIs. Plot them as a forest plot.
3. Simulate: if the true rate is 12%, how many discharges do you need to
   detect a 2-point difference at 80% power?

**Done when:** you can explain, in writing, why the normal approximation
misbehaves for small departments.

---

## Exercise 9 — Inference

**Skill:** hypothesis testing, and its limits

1. Is the readmission rate for SNF discharges different from home
   discharges? Chi-square and a two-proportion z-test.
2. You just ran tests across six departments. Apply a multiple-comparison
   correction. Explain what changes.
3. Write a paragraph on why a significant p-value here does **not** mean
   SNF discharge causes readmission.

**Done when:** part 3 is honest. That paragraph is the most valuable thing
in this exercise, and it's the part that separates people who can be
trusted with a dashboard from people who can't.

---

## Exercise 10 — Regression

**Skill:** logistic regression, interpreted correctly

Model 30-day readmission on age, sex, insurance type, primary diagnosis,
discharge disposition, and LOS.

1. Fit it with `statsmodels` so you get a proper summary table
2. Interpret three coefficients as odds ratios, in plain English
3. Check for separation and multicollinearity
4. Compare your fitted effects to the generator's actual risk logic in
   `src/generate_data.py` — you know ground truth here, which is a luxury
   you will never have again

**Done when:** you can say which effects you recovered accurately, which
you didn't, and why.

---

## Exercise 11 — Capstone: the readmission analysis

**Skill:** all of it, assembled

Produce `notebooks/readmission_analysis.ipynb` that runs top to bottom on
a clean kernel and imports everything real from `src/`:

- The question, stated up front
- Data provenance and known limitations
- Cleaning and validation summary
- Descriptive results with visualizations
- The model, with honest evaluation
- What you'd recommend, and what you would not claim

Then write `REPORT.md` — 800 words, no code, written for a hospital
operations director.

**Done when:** the notebook has no cell that defines a function. If logic
lives in the notebook, move it to `src/` and import it.

---

## Exercise 12 — Make it a real repository

**Skill:** the engineering practices that make you hireable

1. Test coverage above 80% on `src/`
2. Ruff clean
3. Type hints on every public function
4. A README a stranger could follow
5. Git history that reads as a narrative
6. Push it to GitHub, public

**Done when:** it's public. This is your first portfolio piece, and the
readmission topic maps directly onto CMS's actual Hospital Readmissions
Reduction Program — which means a healthcare hiring manager will recognize
what you built without you having to explain the domain.

---

## After this

Repeat the whole arc with **real** data: CMS publishes hospital
readmission rates, provider utilization, and cost reports as open
downloads. Same skills, real numbers, and a second portfolio piece where
the findings are actually true.

Then Year 2 begins.
