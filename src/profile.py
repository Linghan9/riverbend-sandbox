from pathlib import Path
import pandas as pd 
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

def profile_column(series, name):
    print(f"\n--- {name} ---")
    print(f" dtype: {series.dtype}")
    print(f" rows: {len(series)}")
    print(f" blank: {(series == '').sum()}")
    print(f" distinct: {series.nunique()}")
    print(series.value_counts().head(40))

FILES = {
    "providers.csv": (",", "utf-8"),
    "patients.csv": (",", "utf-8"),
    "encounters.csv": (",", "utf-8"),
    "labs.csv": (";", "latin-1"),
    "billing.csv": (",", "utf-8"),
    "encounter_snapshot_2024_06.csv": (",", "utf-8"),
    "encounter_snapshot_2024_12.csv": (";", "latin-1"),
}
for fname, (sep, enc) in FILES.items():
    df=pd.read_csv(RAW / fname, sep=sep, encoding=enc, dtype=str, keep_default_na=False)
    print(f"\n{'='*60}\n{fname} - {len(df)} rows x {len(df.columns)} cols\n{'='*60}")
    for col in df.columns:
        profile_column(df[col], col)
        
   


