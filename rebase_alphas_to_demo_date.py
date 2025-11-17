import pandas as pd
from datetime import datetime

import os
print("Working directory:", os.getcwd())

# ---------------------------------------------------------
# CONFIGURATION — Adjust these two lines for any demo
# ---------------------------------------------------------
REAL_END = pd.Timestamp("2025-10-27")     # last real date to keep
DEMO_END = pd.Timestamp("2025-11-17")     # demo timeline end date
INPUT_PATH = "/Users/billyeskel/var/inputs/pwbi_dyn/Global_LC_Combined_Long_20251109_2113_sub.csv.gz"

# Timestamp for all exports
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
# ---------------------------------------------------------


# ---------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------
df = pd.read_csv(INPUT_PATH, compression="gzip")


# ---------------------------------------------------------
# 2. Inspect date range (optional)
# ---------------------------------------------------------
date_series = pd.to_datetime(df["Date"])
print("Real start:", date_series.min())
print("Real end:  ", date_series.max())


# ---------------------------------------------------------
# 3. Filter to real dates through REAL_END
# ---------------------------------------------------------
mask = date_series <= REAL_END
df_filtered = df.loc[mask].copy()
df_filtered["Date"] = pd.to_datetime(df_filtered["Date"])  # convert once


# Export filtered real data
# df_filtered.to_csv(
#     f"Global_LC_Combined_Long_thru_realend_{TS}.csv.gz",
#     index=False,
#     compression="gzip"
# )
# print(f"Exported filtered real dataset → Global_LC_Combined_Long_thru_realend_{TS}.csv.gz")


# ---------------------------------------------------------
# 4. Build weekday-only demo dates using unique real dates
# ---------------------------------------------------------

# Get unique real dates in sorted order
unique_real_dates = (
    df_filtered["Date"]
    .drop_duplicates()
    .sort_values()
    .reset_index(drop=True)
)

num_unique_days = len(unique_real_dates)

# Build weekday-only demo dates for *unique* days
demo_unique = pd.bdate_range(end=DEMO_END, periods=num_unique_days)

# Create mapping table
date_map = pd.DataFrame({
    "Date": unique_real_dates,
    "date_demo": demo_unique
})

# Merge mapping back onto full dataset
df_filtered = df_filtered.merge(date_map, on="Date", how="left")


print("Demo dates span:", df_filtered["date_demo"].min(), "→", df_filtered["date_demo"].max())
print("Are demo dates weekdays only?", df_filtered["date_demo"].dt.weekday.max() <= 4)


# ---------------------------------------------------------
# 4b. General confirmation (ALL real + demo dates, full + unique)
# ---------------------------------------------------------

# Full mapping of all real → demo dates across entire filtered dataset
confirm_all = (
    df_filtered[["Date", "date_demo"]]
    .drop_duplicates()
    .sort_values("Date")
)

# Unique mapping (same thing, but kept for clarity)
confirm_unique = confirm_all.copy()

# Create Excel with 2 sheets
confirm_path = f"DEMO_DATE_SHIFT_CONFIRMATION_{TS}.xlsx"

with pd.ExcelWriter(confirm_path, engine="xlsxwriter") as writer:
    confirm_all.to_excel(writer, sheet_name="All_DatePairs", index=False)
    confirm_unique.to_excel(writer, sheet_name="Unique_DatePairs", index=False)

print(f"\nDEMO_DATE_SHIFT_CONFIRMATION exported → {confirm_path}")


# ---------------------------------------------------------
# 4c. Enhanced confirmation using Tesla and Nvidia (5 days, Overall only)
# ---------------------------------------------------------

target_names = ["TESLA", "NVIDIA", "MICROSOFT"]

df_overall = df_filtered[
    df_filtered["Metric_Level2"].str.upper() == "OVERALL"
].copy()

df_two = df_overall[
    df_overall["SECURITY_NAME"].str.upper().str.contains("TESLA|NVIDIA", na=False)
].copy()

recent_dates = df_two["Date"].sort_values().unique()[-5:]
df_two_last5 = df_two[df_two["Date"].isin(recent_dates)].copy()

cols = [
    "BarraId", "SECURITY_NAME",
    "Date", "date_demo",
    "Metric", "Metric_Level1", "Metric_Level2", "Value"
]

confirm_two = df_two_last5[cols].sort_values(["SECURITY_NAME", "Date"])

confirm_two_path = f"DEMO_DATE_SHIFT_CONFIRMATION_TESLA_NVIDIA_{TS}.csv"
confirm_two.to_csv(confirm_two_path, index=False)

print(f"Tesla/Nvidia 5-day confirmation exported → {confirm_two_path}")


# ---------------------------------------------------------
# 5. Build exportable demo dataset (Date = date_demo)
# ---------------------------------------------------------
df_export = df_filtered.copy()
df_export["Date"] = df_export["date_demo"]
df_export = df_export.drop(columns=["date_demo"])


# ---------------------------------------------------------
# 6. Export final demo dataset
# ---------------------------------------------------------
demo_export_path = f"Global_LC_Combined_Long_DEMO_ending_{DEMO_END.date()}_{TS}.csv.gz"

df_export.to_csv(
    demo_export_path,
    index=False,
    compression="gzip"
)

print(f"Demo export complete → {demo_export_path}")


# ---------------------------------------------------------
# 7. EX-POST VERIFICATION — Tesla & Nvidia across ALL dates
# ---------------------------------------------------------

# Load the demo file again
df_demo_loaded = pd.read_csv(demo_export_path, compression="gzip")
df_demo_loaded["Date"] = pd.to_datetime(df_demo_loaded["Date"])

# Build mapping real→demo from original filtered data
mapping = df_filtered[["Date", "date_demo"]].drop_duplicates()

# Merge demo file with mapping to recover real dates
df_merged = df_demo_loaded.merge(
    mapping,
    left_on="Date",      # demo date
    right_on="date_demo",
    how="left"
)

df_merged = df_merged.rename(
    columns={"Date_x": "Date_demo", "Date_y": "Date_real"}
)

# Extract Tesla + Nvidia again
mask_tn = df_merged["SECURITY_NAME"].str.upper().str.contains("TESLA|NVIDIA", na=False)
df_tn_check = df_merged.loc[mask_tn].copy()

# Unique date pairs
unique_pairs = (
    df_tn_check[["SECURITY_NAME", "Date_real", "Date_demo"]]
    .drop_duplicates()
    .sort_values(["SECURITY_NAME", "Date_real"])
)

# Export multi-sheet ex-post verification
expost_path = f"DEMO_DATE_SHIFT_EXPOST_TN_{TS}.xlsx"

with pd.ExcelWriter(expost_path, engine="xlsxwriter") as writer:
    
    # 1. Full rows (real + demo dates + metrics)
    df_tn_check.to_excel(writer, sheet_name="AllRows", index=False)

    # 2. Unique mapping pairs
    unique_pairs.to_excel(writer, sheet_name="UniqueDatePairs", index=False)

    # 3. Unique Real Dates
    (
        df_tn_check[["SECURITY_NAME", "Date_real"]]
        .drop_duplicates()
        .sort_values(["SECURITY_NAME", "Date_real"])
        .to_excel(writer, sheet_name="RealDates", index=False)
    )

    # 4. Unique Demo Dates
    (
        df_tn_check[["SECURITY_NAME", "Date_demo"]]
        .drop_duplicates()
        .sort_values(["SECURITY_NAME", "Date_demo"])
        .to_excel(writer, sheet_name="DemoDates", index=False)
    )

print(f"\nEX-POST Tesla/Nvidia verification exported → {expost_path}")
print("\nAll exports finished successfully.")
