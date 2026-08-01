# Riverbend — a data science sandbox

A synthetic hospital system with realistically broken data, built as a
training ground. Everything here is fake. Nothing here is clean.

---

## The honest version of the goal

Create the AI from the ground up myself within 3 years.
**Achievable in three years, comfortably:** implement a transformer from
scratch in PyTorch, write your own tokenizer, train a small language model
on a corpus you choose, fine-tune open-weight models, and understand every
line of it. People do this. You have a stats degree and you already write
working ETL code, which puts you further along than most people who start.

**Not achievable, and not because of you:** a frontier model. Training runs
at that scale cost eight to nine figures in compute. Nobody builds one
alone. If someone tells you otherwise they're selling a course.

The first thing is the real goal. It's also the thing that makes you
employable as a healthcare data scientist, which is the outcome you
actually described wanting.

---

## Roadmap

Budget **6–8 hours a week**. That is the number that survives contact with
two kids and a full-time job. Sixteen hours one week and zero for a month
is how this dies.

### Year 1 — Foundations

The unglamorous year. Skipping it is the single most common reason people
stall out in year two.

| Quarter | Focus |
|---|---|
| Q1 | VS Code, git, virtual environments, testing, type hints. pandas properly. **This sandbox, exercises 1–7.** |
| Q2 | SQL for real: joins, CTEs, window functions, query plans. Stats part 1 — probability, distributions, sampling, CLT. |
| Q3 | Stats part 2 — inference, linear and logistic regression, GLMs. Done in code, not just on paper. |
| Q4 | **Capstone 1:** the readmission analysis, end to end, on GitHub with a written writeup. |

### Year 2 — Machine learning

| Quarter | Focus |
|---|---|
| Q1 | scikit-learn: trees, ensembles, regularization, cross-validation, leakage, calibration. |
| Q2 | The linear algebra and calculus you actually need. Then a neural net from scratch in NumPy — backprop written by hand. |
| Q3 | PyTorch: tensors, autograd, training loops, GPU. Rebuild the NumPy net in PyTorch and confirm they agree. |
| Q4 | **Capstone 2:** a trained model with honest evaluation, served behind an API. |

### Year 3 — Building the thing

| Quarter | Focus |
|---|---|
| Q1 | Embeddings, sequence models, attention. Read *Attention Is All You Need* and implement it. |
| Q2 | Build a GPT from scratch, tokenizer included. Karpathy's "Zero to Hero" series is the canonical path. |
| Q3 | Train a small LM on your own corpus. Fine-tuning, LoRA, evaluation, and why evaluation is the hard part. |
| Q4 | **Capstone 3:** a domain model you trained yourself, plus a technical writeup. |

---

## Setup

```bash
# 1. Open the folder in VS Code:  File > Open Folder > riverbend
# 2. Create an isolated environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install
pip install -r requirements.txt

# 4. Generate the data and build the database
python src/generate_data.py
python src/build_db.py

# 5. Confirm the tests run (they will FAIL — that is the point)
pytest -q
```

### VS Code extensions worth having

- **Python** (Microsoft) — the only mandatory one
- **Jupyter** — for notebooks
- **SQLite Viewer** — click `data/riverbend.db` and browse it
- **Ruff** — linting and formatting, fast
- **GitLens** — makes git history legible while you're learning it

---

## What's in the data

Seven raw extracts in `data/raw/`, loaded as-is into `data/riverbend.db`:

| File | Rows | What it is |
|---|---|---|
| `patients.csv` | ~4,100 | Demographics, insurance |
| `encounters.csv` | ~6,800 | Admissions and discharges |
| `labs.csv` | ~19,600 | Lab results (semicolon-delimited, latin-1) |
| `billing.csv` | ~6,500 | Claims |
| `providers.csv` | 60 | Attending physicians |
| `encounter_snapshot_2024_06.csv` | ~3,800 | Archive extract, schema v1 |
| `encounter_snapshot_2024_12.csv` | ~4,400 | Archive extract, schema v2 |

### The known defects

These are all deliberate. Each one is a thing that has happened to a real
analyst on a real Tuesday.

1. **Three date formats**, mixed *within* the same column, row by row
2. **Six spellings per department** — case, whitespace, abbreviations
3. **Sex coded eight ways** across merged source systems
4. **Duplicate patients** entered under different IDs, same DOB and zip
5. **Exact duplicate rows** from a double-posted extract
6. **Orphan encounters** referencing patient IDs that don't exist
7. **Lab values as strings** — units glued on, censored `<0.01`, `SEE NOTE`
8. **Currency as text** with dollar signs and thousands separators
9. **`length_of_stay` that contradicts the dates**, and is sometimes blank
10. **Two files in latin-1 with semicolons**, because a vendor used Excel
11. **Snapshot schema drift** — and one column silently changed *units*
    between v1 and v2 with no rename. This is the trap. It is also
    exactly the LSPP problem, which is why it's here.

There is a real 30-day readmission signal buried in this data, driven by
diagnosis, discharge disposition, and length of stay. Your analysis should
be able to recover it. If your numbers come out flat, your cleaning is
wrong — not the data.

---

## How to work through this

`EXERCISES.md` has twelve exercises in order. Each one names a specific
skill and tells you what "done" looks like.

Rules that make this work:

- **Write code in `src/`, not in notebooks.** Notebooks are for looking at
  things. Functions that other code depends on go in modules, where they
  can be tested. This habit separates analysts from engineers.
- **Run `pytest` constantly.** The tests in `tests/` describe what your
  cleaning functions must do. Red to green is the loop.
- **Commit after every exercise.** Small commits, real messages. Three
  years from now your git history is a resume.
- **Don't open `solutions/` until you've genuinely tried.** Reading a
  solution feels like learning and isn't. Struggle first, then compare —
  the comparison is where the learning actually happens.
- **Don't let an AI write the code for you.** Use one to explain a concept,
  review something you wrote, or unstick you after twenty minutes. Not to
  produce the thing. The typing is where the knowledge forms.

Start with Exercise 1.
