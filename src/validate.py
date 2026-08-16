

import pandas as pd
import pathlib as path 
from clean import parse_flexible_date 

billing = pd.read_csv("../data/raw/billing.csv")
encounter = pd.read_csv("../data/raw/encounters.csv")
labs = pd.read_csv("../data/raw/labs.csv", sep=";")
patient = pd.read_csv("../data/raw/patients.csv")

encounter["admit_date"] = encounter["admit_date"].apply(parse_flexible_date)
encounter["discharge_date"] = encounter["discharge_date"].apply(parse_flexible_date)



def find_orphans (child_df, child_key, parent_df, parent_key):

    check =  child_df[child_key].isin(parent_df[parent_key]) 
    orphans = child_df[~check]
    return {
    "check_name": f"{child_key} -> {parent_key}",
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
    
print(find_exact_duplicates(encounter, "encounters"))

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
print(encounter["admit_date"].dtype)

backwards = encounter[encounter["discharge_date"] < encounter["admit_date"]]
print(len(backwards))
print(encounter["admit_date"].isna().sum())
print(encounter["discharge_date"].isna().sum())
raw_encounter = pd.read_csv("../data/raw/encounters.csv")
print(raw_encounter["discharge_date"].isna().sum())

computed = (encounter["discharge_date"] - encounter["admit_date"]).dt.days
print(computed.head())
print(encounter["length_of_stay"].head(10))

computed = (encounter["discharge_date"] - encounter["admit_date"]).dt.days
mismatch = encounter[computed != encounter["length_of_stay"]]
print(len(mismatch))

real_mismatch = encounter[computed.notna() & (computed != encounter["length_of_stay"])]
diff = real_mismatch["length_of_stay"] - computed[real_mismatch.index]
# encounter["length_of_stay"] = encounter["length_of_stay"].replace(-1, pd.NA)


print(diff.describe())
print(diff.value_counts().head(15))
print(real_mismatch[["encounter_id", "admit_date", "discharge_date", "length_of_stay"]].head(10))
print(encounter["length_of_stay"].value_counts().head(10))
print((encounter["length_of_stay"] == -1).sum())