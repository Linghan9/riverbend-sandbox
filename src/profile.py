from pathlib import Path
import pandas as pd 
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

def profile_column(series, name):
    print(f"\n--- {name} ---")
    print(f" dtype: {series.dtype}")
    print(f" rows: {len(series)}")
    print(f" blank: {(series == '').sum()}")
    print(f" distinct: {series.nunique()}")

df = pd.read_csv(RAW / "encounters.csv", dtype=str, keep_default_na=False)
profile_column(df["department"], "department")

