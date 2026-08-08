from modulefinder import test

import pandas as pd
import pathlib as path 



df1 = "billing"["encounter_id"].unique()
df2 = "encounters"["encounter_id"].unique() 

def find_orphans (df: pd.DataFrame, col: str) -> pd.DataFrame:
    billing = pd.read_csv("../data/raw/billing.csv")
    encounters = pd.read_csv("../data/raw/encounters.csv")

    check =  billing["encounter_id"].isin(encounters["encounter_id"]) 
    orphans = billing[~check]

    fake = billing.head(3).copy()
    fake["encounter_id"] = "DEFINITELY_NOT_REAL"
    test = pd.concat([billing, fake])
    print(len(test[~test["encounter_id"].isin(encounters["encounter_id"])]))