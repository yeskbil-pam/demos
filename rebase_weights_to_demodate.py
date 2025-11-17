import pandas as pd
from datetime import datetime

import os
print("Working directory:", os.getcwd())

# ---------------------------------------------------------
# CONFIGURATION — Adjust these two lines for any demo
# ---------------------------------------------------------
REAL_END = pd.Timestamp("2025-10-27")     # last real date to keep
DEMO_END = pd.Timestamp("2025-11-17")     # demo timeline end date

INPUT_PATH = "/Users/billyeskel/var/inputs/pwbi_dyn/Global_LC_Weights_Long_20251110_2139_weights_long.csv.gz"

# Timestamp for filenames
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
# ---------------------------------------------------------


# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------
df = pd.read_csv(INPUT_PATH, compression="gzip")

df["Date"] = pd.to_datetime(df["Date"])

print("Real start:", df["Date"].min())
print("Real end:  ", df["Date"].max())


# ---------------------------------------------------------
# 2. FILTER TO REAL DATES THROUGH REAL_END
# ---------------------------------------------------------
df_filtered = df.loc[df["Date"] <= REAL_END].copy()


# ---------------------------------------------------------
# 3. BUILD WEEKDAY-ONLY DEMO DATES USING UNIQUE REAL DATES
# ---------------------------------------------------------

# Unique sorted real dates
unique_real_dates = (
    df_filtered["Date"]
    .drop_duplicates()
    .sort_values()
    .reset_index(drop=True)
)

num_unique_days = len(unique_real_dates)

# Create weekday-only demo dates ending on DEMO_END
demo_unique = pd.bdate_range(end=DEMO_END, periods=num_unique_days)

# Build mapping table
date_map = pd.DataFrame({
    "Date": unique_real_dates,
    "date_demo": demo_unique
})

# Merge mapping back to the full dataset
df_filtered = df_filtered.merge(date_map, on="Date", how="left")

print("\nDemo dates span:", df_filtered["date_demo"].min(), "→", df_filtered["date_demo"].max())
print("Are demo dates weekdays only?", df_filtered["date_demo"].dt.weekday.max() <= 4)


# ---------------------------------------------------------
# 4. EXPORT DATE MAPPING CONFIRMATION
# ---------------------------------------------------------
confirm_df = (
    df_filtered[["Date", "date_demo"]]
    .drop_duplicates()
    .sort_values("Date")
)

confirm_path = f"Weights_DEMO_DATE_SHIFT_CONFIRMATION_{TS}.csv"
confirm_df.to_csv(confirm_path, index=False)

print(f"\nDate mapping exported → {confirm_path}")


# ---------------------------------------------------------
# 5. BUILD EXPORTABLE DEMO DATASET (Date = date_demo)
# ---------------------------------------------------------
df_export = df_filtered.copy()
df_export["Date"] = df_export["date_demo"]
df_export = df_export.drop(columns=["date_demo"])

# ---------------------------------------------------------
# 6. EXPORT FINAL DEMO DATASET
# ---------------------------------------------------------
output_path = f"Global_LC_Weights_Long_DEMO_ending_{DEMO_END.date()}_{TS}.csv.gz"

df_export.to_csv(
    output_path,
    index=False,
    compression="gzip"
)

print(f"\nDemo weights export complete → {output_path}")
print("\nAll done.")



# ---------------------------------------------------------
# 7. EX-POST VERIFICATION — Full timeline date checking
# ---------------------------------------------------------

# Load demo file
df_demo_loaded = pd.read_csv(output_path, compression="gzip")
df_demo_loaded["Date"] = pd.to_datetime(df_demo_loaded["Date"])

# Build real→demo mapping from filtered data
mapping = df_filtered[["Date", "date_demo"]].drop_duplicates()

# Merge to recover real dates in the demo export
df_merged = df_demo_loaded.merge(
    mapping,
    left_on="Date",      # Date in demo file
    right_on="date_demo",  # fake date in mapping
    how="left"
)

df_merged = df_merged.rename(columns={
    "Date_x": "Date_demo",
    "Date_y": "Date_real"
})

# Build unique pairs
unique_pairs = (
    df_merged[["Date_real", "Date_demo"]]
    .drop_duplicates()
    .sort_values("Date_real")
)

# Export multi-sheet Excel verification
expost_path = f"Weights_DEMO_DATE_SHIFT_EXPOST_{TS}.xlsx"

with pd.ExcelWriter(expost_path, engine="xlsxwriter") as writer:
    
    # 1. All rows with real and fake dates
    df_merged.to_excel(writer, sheet_name="AllRows", index=False)
    
    # 2. Unique date pairs
    unique_pairs.to_excel(writer, sheet_name="UniquePairs", index=False)
    
    # 3. Unique real dates only
    (
        df_merged[["Date_real"]]
        .drop_duplicates()
        .sort_values("Date_real")
        .to_excel(writer, sheet_name="RealDates", index=False)
    )
    
    # 4. Unique demo dates only
    (
        df_merged[["Date_demo"]]
        .drop_duplicates()
        .sort_values("Date_demo")
        .to_excel(writer, sheet_name="DemoDates", index=False)
    )

print(f"\nEX-POST verification exported → {expost_path}")
print("\nAll done.")
