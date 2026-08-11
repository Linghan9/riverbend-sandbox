

import pandas as pd
import pathlib as path 

billing = pd.read_csv("../data/raw/billing.csv")
encounter = pd.read_csv("../data/raw/encounters.csv")
labs = pd.read_csv("../data/raw/labs.csv", sep=";")
patient = pd.read_csv("../data/raw/patients.csv")



def find_orphans (child_df, child_key, parent_df, parent_key):

    check =  child_df[child_key].isin(parent_df[parent_key]) 
    orphans = child_df[~check]
    return {
    "check_name": f"{child_key} -> {parent_key}",
    "count": len(orphans),
    "pct": len(orphans) / len(child_df) * 100,
    "example_ids": orphans[child_key].head(5).tolist()
}
print(labs.columns.tolist())
print(find_orphans(billing, "encounter_id", encounter, "encounter_id"))
print(find_orphans(labs, "encounter_id", encounter, "encounter_id"))
print(find_orphans(encounter, "patient_id", patient, "patient_id"))
print(patient[patient["patient_id"] == "PT999019"])
print("billing", billing.duplicated().sum())
print("encounter", encounter.duplicated().sum())
print("labs", labs.duplicated().sum())
print("patient", patient.duplicated().sum())
print(encounter[encounter.duplicated(keep=False)].sort_values("encounter_id").head(10))
print(patient.duplicated(subset=["birth_date", "zip_code"], keep=False).sum())

dupes = patient[patient.duplicated(subset=["birth_date", "zip_code"], keep=False)]
print(dupes.sort_values(["birth_date", "zip_code"]).head(10))

print(dupes["patient_id"].str.startswith("PT9").sum())
weak = dupes[~dupes["patient_id"].str.startswith("PT9")]
print(len(weak))
print(weak.sort_values(["birth_date", "zip_code"]).head(6))

