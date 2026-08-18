

import pandas as pd
import pathlib as path 
from clean import parse_flexible_date 

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

billing = pd.read_csv("../data/raw/billing.csv")
encounter = pd.read_csv("../data/raw/encounters.csv")
labs = pd.read_csv("../data/raw/labs.csv", sep=";")
patient = pd.read_csv("../data/raw/patients.csv")

encounter["admit_date"] = encounter["admit_date"].apply(parse_flexible_date)
encounter["discharge_date"] = encounter["discharge_date"].apply(parse_flexible_date)



def find_orphans (child_df, child_key, parent_df, parent_key, label):

    check =  child_df[child_key].isin(parent_df[parent_key]) 
    orphans = child_df[~check]
    return {
    "check_name": f"orphan FK:{label}",
    "count": len(orphans),
    "pct": len(orphans) / len(child_df) * 100,
    "example_ids": orphans[child_key].head(5).tolist()
}

def find_exact_duplicates (df, label):
    dupes = df[df.duplicated(keep = False)]
    return {
        "check_name": f"exact duplicate rows: {label}",
        "count": len(dupes),
        "pct": len(dupes) / len(df) * 100,
        "example_ids": [],
    }

def find_duplicate_patients(df, subset):
    dupes = df[df.duplicated(subset=subset, keep=False)]
    return {
        "check_name" :f"suspected duplicate patients: {' + '.join(subset)}",
        "count": len(dupes),
        "pct": len(dupes)/ len(df) *100,
        "example_ids": dupes["patient_id"].head(5).tolist(),
    }

def find_missing_values(df, column, label):
    missing = df[df[column].isna()]
    return {
        "check_name": f"missing values: {label}",
        "count": len(missing),
        "pct": len(missing)/len(df)* 100,
        "example_ids":[],
    }

def find_sentinel_values(df, column, sentinel, label):
    hits = df[df[column] == sentinel]
    return {
        "check_name": f"sentinel value: {sentinel}: {label}",
        "count": len(hits),
        "pct": len(hits)/len(df) * 100,
        "example_ids":[],
    }





results = [
    find_orphans(billing,"encounter_id", encounter, "encounter_id", "billing -> encounters"),
    find_orphans(labs, "encounter_id", encounter, "encounter_id", "labs -> encounters"),
    find_orphans(encounter, "patient_id", patient, "patient_id", "encounters -> patients"),
    find_exact_duplicates(encounter, "encounters"),
    find_duplicate_patients(patient, ["birth_date", "zip_code"]),
    find_missing_values(encounter, "discharge_date", "encounters.discharge_date"),
    find_sentinel_values(encounter, "length_of_stay", -1, "encounters.length_of_stay"),
                 
]
report = pd.DataFrame(results)
print(report)
