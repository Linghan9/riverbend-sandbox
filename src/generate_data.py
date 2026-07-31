"""
Riverbend Health System — synthetic data generator.

Produces deliberately messy CSV extracts that mirror the kinds of problems
found in real operational systems: inconsistent formats, orphaned foreign
keys, duplicate rows, censored lab values, drifting snapshot schemas.

The messiness is INTENTIONAL. Do not "fix" this file. Fix the data
downstream, in your own cleaning code. That is the exercise.

Deterministic: same seed -> same data, every time.

Usage:
    python src/generate_data.py
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260731
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

N_PATIENTS = 4000
N_PROVIDERS = 60
START = date(2024, 1, 1)
END = date(2025, 12, 31)

DEPARTMENTS = [
    "Cardiology",
    "General Medicine",
    "Orthopedics",
    "Pulmonology",
    "Nephrology",
    "Emergency",
]

# Same department, six ways of writing it. You will need to normalize these.
DEPT_VARIANTS = {
    "Cardiology": ["Cardiology", "cardiology", "CARDIOLOGY", " Cardiology", "Cardiology ", "Cardio"],
    "General Medicine": ["General Medicine", "general medicine", "Gen Med", "GENERAL MEDICINE", "Gen. Medicine", "General  Medicine"],
    "Orthopedics": ["Orthopedics", "orthopedics", "Ortho", "ORTHOPEDICS", "Orthopaedics", "Orthopedics "],
    "Pulmonology": ["Pulmonology", "pulmonology", "Pulm", "PULMONOLOGY", "Pulmonary", " Pulmonology"],
    "Nephrology": ["Nephrology", "nephrology", "Nephro", "NEPHROLOGY", "Renal", "Nephrology "],
    "Emergency": ["Emergency", "emergency", "ED", "EMERGENCY", "Emergency Dept", "ER"],
}

SPECIALTIES = ["Cardiology", "Internal Medicine", "Orthopedic Surgery",
               "Pulmonology", "Nephrology", "Emergency Medicine"]

INSURANCE = ["Medicare", "Medicaid", "Commercial", "Self-Pay", "Dual Eligible"]

DISPOSITIONS = ["Home", "Home Health", "SNF", "AMA", "Expired", "Transfer"]

DX_CODES = {
    "I50.9": "Heart failure, unspecified",
    "J44.1": "COPD with acute exacerbation",
    "N18.6": "End stage renal disease",
    "E11.65": "Type 2 diabetes with hyperglycemia",
    "I21.4": "Non-ST elevation myocardial infarction",
    "J18.9": "Pneumonia, unspecified organism",
    "M17.11": "Unilateral primary osteoarthritis, right knee",
    "A41.9": "Sepsis, unspecified organism",
    "I10": "Essential hypertension",
    "K92.2": "Gastrointestinal hemorrhage, unspecified",
}

# Diagnoses that genuinely carry higher readmission risk. Your analysis
# should be able to recover this signal.
HIGH_RISK_DX = {"I50.9", "J44.1", "N18.6", "A41.9"}

LAB_PANEL = [
    ("HGB", "Hemoglobin", "g/dL", 13.5, 1.8),
    ("CREA", "Creatinine", "mg/dL", 1.1, 0.6),
    ("NA", "Sodium", "mmol/L", 139.0, 3.5),
    ("K", "Potassium", "mmol/L", 4.1, 0.5),
    ("BNP", "B-type Natriuretic Peptide", "pg/mL", 180.0, 220.0),
    ("WBC", "White Blood Cell Count", "10*9/L", 7.5, 2.6),
    ("TROP", "Troponin I", "ng/mL", 0.02, 0.05),
]


def _rand_date(rng, start=START, end=END):
    span = (end - start).days
    return start + timedelta(days=int(rng.integers(0, span + 1)))


def _fmt_date(d, style):
    """Three date formats live in this warehouse. Welcome to healthcare."""
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return ""
    if style == "iso":
        return d.strftime("%Y-%m-%d")
    if style == "us":
        return d.strftime("%m/%d/%Y")
    if style == "oracle":
        return d.strftime("%d-%b-%Y").upper()
    if style == "iso_ts":
        return d.strftime("%Y-%m-%d %H:%M:%S")
    raise ValueError(style)


def make_providers(rng):
    rows = []
    for i in range(1, N_PROVIDERS + 1):
        rows.append(
            {
                "provider_id": f"PRV{i:04d}",
                "provider_name": f"Provider {i:03d}",
                "specialty": SPECIALTIES[i % len(SPECIALTIES)],
                "npi": 1000000000 + int(rng.integers(0, 899999999)),
                "active_flag": rng.choice(["Y", "N", "y", "1"], p=[0.72, 0.08, 0.15, 0.05]),
            }
        )
    return pd.DataFrame(rows)


def make_patients(rng):
    rows = []
    # Sex is coded five different ways because three systems merged in 2019.
    sex_codes = ["M", "F", "Male", "Female", "1", "2", "U", ""]
    sex_p = [0.34, 0.34, 0.08, 0.08, 0.05, 0.05, 0.04, 0.02]

    for i in range(1, N_PATIENTS + 1):
        age = int(np.clip(rng.normal(62, 18), 18, 98))
        birth = date(2025 - age, int(rng.integers(1, 13)), int(rng.integers(1, 29)))
        rows.append(
            {
                "patient_id": f"PT{i:06d}",
                "birth_date": _fmt_date(birth, rng.choice(["iso", "us", "oracle"], p=[0.6, 0.3, 0.1])),
                "sex": rng.choice(sex_codes, p=sex_p),
                "zip_code": rng.choice(
                    ["23060", "23059", "23233", "23294", "23228", "23111",
                     "23005", " 23060", "23060-1234", "2306"],
                    p=[0.20, 0.16, 0.14, 0.13, 0.12, 0.10, 0.07, 0.04, 0.03, 0.01],
                ),
                "insurance_type": rng.choice(INSURANCE, p=[0.42, 0.14, 0.32, 0.06, 0.06]),
                "registered_date": _fmt_date(_rand_date(rng, date(2018, 1, 1), date(2024, 6, 30)), "iso"),
            }
        )
    df = pd.DataFrame(rows)

    # ~1.5% of patients got entered twice under different IDs with the same
    # birth date and zip. Real duplicate-patient problem, real MPI headache.
    dupes = df.sample(frac=0.015, random_state=SEED).copy()
    dupes["patient_id"] = ["PT9" + pid[3:] for pid in dupes["patient_id"]]
    df = pd.concat([df, dupes], ignore_index=True)

    return df


def make_encounters(rng, patients, providers):
    """Encounters carry the readmission signal we want to be recoverable."""
    rows = []
    pids = patients["patient_id"].tolist()
    prov_ids = providers["provider_id"].tolist()
    enc_seq = 1

    # Build an age lookup so risk can depend on it.
    def _age_of(pid_idx):
        return int(np.clip(rng.normal(62, 18), 18, 98))

    for pid in pids:
        n_enc = int(rng.choice([1, 1, 2, 2, 3, 4, 5], p=[0.22, 0.14, 0.22, 0.16, 0.14, 0.08, 0.04]))
        cursor = _rand_date(rng, START, END - timedelta(days=60))

        for _ in range(n_enc):
            dx = str(rng.choice(list(DX_CODES.keys())))
            dept = DEPARTMENTS[hash(dx) % len(DEPARTMENTS)]
            los = int(np.clip(rng.poisson(4) + 1, 1, 30))
            admit = cursor
            discharge = admit + timedelta(days=los)

            disposition = str(
                rng.choice(DISPOSITIONS, p=[0.55, 0.14, 0.16, 0.03, 0.04, 0.08])
            )

            rows.append(
                {
                    "encounter_id": f"ENC{enc_seq:07d}",
                    "patient_id": pid,
                    "admit_date": admit,
                    "discharge_date": None if rng.random() < 0.02 else discharge,
                    "department": rng.choice(DEPT_VARIANTS[dept]),
                    "attending_provider_id": str(rng.choice(prov_ids)),
                    "discharge_disposition": disposition,
                    "primary_dx_code": dx,
                    "length_of_stay": los,
                }
            )
            enc_seq += 1

            # Readmission risk: driven by diagnosis, disposition and LOS.
            risk = 0.13
            if dx in HIGH_RISK_DX:
                risk += 0.16
            if disposition in ("SNF", "AMA"):
                risk += 0.11
            if los >= 8:
                risk += 0.06

            if disposition == "Expired":
                break  # no further encounters, obviously

            if rng.random() < risk:
                gap = int(rng.integers(2, 29))  # readmit inside 30 days
            else:
                gap = int(rng.integers(45, 400))
            cursor = discharge + timedelta(days=gap)
            if cursor > END:
                break

    df = pd.DataFrame(rows)

    # --- Now degrade it. ---

    # Mixed date formats, assigned per-row not per-column. Cruel but real.
    styles = rng.choice(["iso", "us", "oracle"], size=len(df), p=[0.72, 0.22, 0.06])
    df["admit_date"] = [_fmt_date(d, s) for d, s in zip(df["admit_date"], styles)]
    df["discharge_date"] = [_fmt_date(d, s) for d, s in zip(df["discharge_date"], styles)]

    # 0.8% exact duplicate rows (double-posted extract).
    dupes = df.sample(frac=0.008, random_state=SEED + 1)
    df = pd.concat([df, dupes], ignore_index=True)

    # 0.5% orphan encounters pointing at patients who do not exist.
    orphans = df.sample(frac=0.005, random_state=SEED + 2).copy()
    orphans["encounter_id"] = ["ORF" + e[3:] for e in orphans["encounter_id"]]
    orphans["patient_id"] = ["PT999" + str(i).zfill(3) for i in range(len(orphans))]
    df = pd.concat([df, orphans], ignore_index=True)

    # length_of_stay is sometimes blank and sometimes disagrees with the dates.
    df["length_of_stay"] = df["length_of_stay"].astype(object)
    blank_idx = df.sample(frac=0.06, random_state=SEED + 3).index
    df.loc[blank_idx, "length_of_stay"] = ""
    wrong_idx = df.sample(frac=0.02, random_state=SEED + 4).index
    df.loc[wrong_idx, "length_of_stay"] = -1

    return df.sample(frac=1.0, random_state=SEED + 5).reset_index(drop=True)


def make_labs(rng, encounters):
    rows = []
    lab_seq = 1
    enc_sample = encounters[~encounters["encounter_id"].str.startswith("ORF")]
    enc_sample = enc_sample.sample(frac=0.75, random_state=SEED + 6)

    for enc_id in enc_sample["encounter_id"]:
        for code, name, unit, mean, sd in LAB_PANEL:
            if rng.random() > 0.55:
                continue
            val = float(rng.normal(mean, sd))
            val = max(val, 0.001)

            # Some results arrive as strings with the unit glued on,
            # some are censored ("<0.01"), some are frankly garbage.
            r = rng.random()
            if r < 0.06:
                value_repr = f"{val:.2f} {unit}"
            elif r < 0.10 and code in ("TROP", "BNP"):
                value_repr = "<0.01"
            elif r < 0.115:
                value_repr = ""
            elif r < 0.125:
                value_repr = "SEE NOTE"
            else:
                value_repr = f"{val:.2f}"

            rows.append(
                {
                    "lab_id": f"LAB{lab_seq:08d}",
                    "encounter_id": enc_id,
                    "test_code": code,
                    "test_name": name,
                    "result_value": value_repr,
                    "result_unit": rng.choice([unit, unit.lower(), ""], p=[0.85, 0.10, 0.05]),
                    "collected_at": _fmt_date(
                        datetime(2024, 1, 1) + timedelta(minutes=int(rng.integers(0, 1050000))),
                        "iso_ts",
                    ),
                    "abnormal_flag": rng.choice(["", "H", "L", "A", "h"], p=[0.70, 0.12, 0.11, 0.05, 0.02]),
                }
            )
            lab_seq += 1

    return pd.DataFrame(rows)


def make_billing(rng, encounters):
    rows = []
    claim_seq = 1
    for _, enc in encounters.iterrows():
        if str(enc["encounter_id"]).startswith("ORF"):
            continue
        if rng.random() < 0.04:
            continue  # some encounters never got billed

        base = float(rng.lognormal(8.6, 0.75))
        charge = round(base, 2)
        status = str(rng.choice(["PAID", "DENIED", "PENDING", "paid", "ADJUSTED"],
                                p=[0.62, 0.09, 0.14, 0.10, 0.05]))
        if status.upper() == "PAID":
            paid = round(charge * float(rng.uniform(0.28, 0.82)), 2)
        elif status.upper() == "ADJUSTED":
            paid = round(-abs(charge) * float(rng.uniform(0.05, 0.3)), 2)
        else:
            paid = 0.0

        rows.append(
            {
                "claim_id": f"CLM{claim_seq:07d}",
                "encounter_id": enc["encounter_id"],
                # Currency stored as text with symbols and commas. Of course.
                "charge_amount": rng.choice(
                    [f"{charge:,.2f}", f"${charge:,.2f}", f"{charge:.2f}"],
                    p=[0.30, 0.25, 0.45],
                ),
                "paid_amount": f"{paid:.2f}",
                "payer": rng.choice(INSURANCE + ["MEDICARE", "medicaid", ""],
                                    p=[0.30, 0.10, 0.24, 0.05, 0.05, 0.12, 0.10, 0.04]),
                "claim_status": status,
                "posted_date": _fmt_date(_rand_date(rng, START, END), "iso"),
            }
        )
        claim_seq += 1

    return pd.DataFrame(rows)


def make_snapshots(rng, encounters):
    """
    Two monthly 'archive' extracts of the same table, taken six months apart,
    with drifted column names and one column that silently changed meaning.

    This is the LSPP problem in miniature: reconciling snapshots whose schema
    moved under you.
    """
    cols_v1 = {
        "encounter_id": "ENCOUNTER_ID",
        "patient_id": "PATIENT_ID",
        "department": "DEPT",
        "primary_dx_code": "DX",
        "length_of_stay": "LOS_DAYS",
    }
    cols_v2 = {
        "encounter_id": "Encounter ID",
        "patient_id": "Patient ID",
        "department": "Department Name",
        "primary_dx_code": "Primary Diagnosis Code",
        "length_of_stay": "LOS",  # v2 measures this in HOURS. Nobody told you.
    }

    base = encounters[list(cols_v1.keys())].copy()

    v1 = base.sample(frac=0.55, random_state=SEED + 7).rename(columns=cols_v1)

    v2 = base.sample(frac=0.65, random_state=SEED + 8).copy()
    v2["length_of_stay"] = pd.to_numeric(v2["length_of_stay"], errors="coerce") * 24
    v2 = v2.rename(columns=cols_v2)
    v2["Status Code"] = rng.choice(["A", "C", "P"], size=len(v2))  # new column in v2

    return v1, v2


def main():
    rng = np.random.default_rng(SEED)
    random.seed(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    providers = make_providers(rng)
    patients = make_patients(rng)
    encounters = make_encounters(rng, patients, providers)
    labs = make_labs(rng, encounters)
    billing = make_billing(rng, encounters)
    snap_v1, snap_v2 = make_snapshots(rng, encounters)

    outputs = {
        "providers.csv": providers,
        "patients.csv": patients,
        "encounters.csv": encounters,
        "labs.csv": labs,
        "billing.csv": billing,
        "encounter_snapshot_2024_06.csv": snap_v1,
        "encounter_snapshot_2024_12.csv": snap_v2,
    }

    for name, df in outputs.items():
        path = RAW / name
        # Two files ship as latin-1 with semicolons, because a vendor
        # exported them from Excel on a Windows box in 2019.
        if name in ("labs.csv", "encounter_snapshot_2024_12.csv"):
            df.to_csv(path, index=False, sep=";", encoding="latin-1")
        else:
            df.to_csv(path, index=False)
        print(f"  {name:34s} {len(df):>8,} rows")

    print(f"\nWrote {len(outputs)} files to {RAW}")


if __name__ == "__main__":
    main()
