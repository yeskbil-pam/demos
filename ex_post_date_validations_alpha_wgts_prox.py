import pandas as pd
from datetime import datetime
import os


# =========================================================
# CONFIG — EDIT THESE PATHS ONLY
# =========================================================
DEMO_COMBINED = "/Users/billyeskel/var/outputs/pwbi_dyn/demo_shift/official/Global_LC_Combined_Long_DEMO_ending_2025-11-17_20251116_143315.csv.gz"
DEMO_WEIGHTS  = "/Users/billyeskel/var/outputs/pwbi_dyn/demo_shift/official/Global_LC_Weights_Long_DEMO_ending_2025-11-17_20251116_153325.csv.gz"
PROXIMITY_FILE = "/Users/billyeskel/var/outputs/pwbi_dyn/demo_shift/official/Proximity Data.xlsx"

OUTPUT_ROOT = "/Users/billyeskel/var/outputs/pwbi_dyn/demo_shift/expost_validation/"
# =========================================================


os.makedirs(OUTPUT_ROOT, exist_ok=True)



# =========================================================
# CANONICAL BUSINESS-DAY CHECK
# =========================================================
def check_business_days_canonical(canon_dates, prefix):
    """
    Canonical business-day validation, printed to terminal and
    returned for Excel export.
    """
    print(f"\n----- BUSINESS DAY CHECK (CANONICAL): {prefix} -----")

    canon_dates = pd.to_datetime(canon_dates).sort_values().reset_index(drop=True)

    # 1 — Weekday check
    weekday_flags = canon_dates.dt.weekday
    all_weekdays = (weekday_flags <= 4).all()
    print(f"All weekdays (Mon–Fri only)?             {all_weekdays}")

    # 2 — Expected continuous BD calendar
    b_range = pd.bdate_range(start=canon_dates.min(), end=canon_dates.max())

    missing = sorted(list(set(b_range) - set(canon_dates)))

    sequence_ok = set(b_range) == set(canon_dates)

    print(f"Expected business days:                  {len(b_range)}")
    print(f"Actual business days:                    {len(canon_dates)}")
    print(f"Sequence matches continuous BD calendar? {sequence_ok}")

    if missing:
        print("Missing business days:")
        for d in missing:
            print(f"   - {d.date()}")
    else:
        print("No missing business days.")

    # Return DataFrame for Excel
    return pd.DataFrame([
        {"Check": "All weekdays (Mon-Fri)", "Result": all_weekdays},
        {"Check": "Sequence matches continuous BD range", "Result": sequence_ok},
        {"Check": "Expected business days", "Result": len(b_range)},
        {"Check": "Actual business days", "Result": len(canon_dates)},
        {"Check": "Missing business days", "Result": missing},
    ])



# =========================================================
# UNIFIED EX-POST PROCESSOR FOR ANY FILE
# =========================================================
def build_expost_from_demo(df, prefix):
    """
    PURE EX-POST LOGIC (SYNCHRONIZED for all datasets):
      - Extract unique demo dates
      - Construct canonical Real_Index mapping
      - Merge Real_Index into full DF
      - Business-day validation (canonical)
    """

    print(f"\n========== EXPOST VALIDATION: {prefix} ==========")

    # Unique demo dates
    demo_dates_unique = df["Date"].drop_duplicates().sort_values().reset_index(drop=True)

    # Real-Day Index
    real_index = pd.Series(range(len(demo_dates_unique)), name="Real_Index")

    # CANONICAL MAPPING
    mapping = pd.DataFrame({
        "Real_Index": real_index,
        "Date_demo": demo_dates_unique
    })

    # Attach Real_Index to full DF
    df_expost = df.merge(mapping, left_on="Date", right_on="Date_demo", how="left")

    # RUN CANONICAL BUSINESS-DAY CHECK
    bizday_check = check_business_days_canonical(mapping["Date_demo"], prefix)

    print(f"Rows in dataset: {len(df):,}")
    print(f"Unique canonical demo dates: {len(mapping):,}")

    return {
        "df": df,
        "df_expost": df_expost,
        "mapping": mapping,
        "demo_dates": mapping["Date_demo"],
        "bizday_check": bizday_check,
        "prefix": prefix
    }



# =========================================================
# DASHBOARD BUILDER
# =========================================================
def build_dashboard(datasets, output_root):
    """
    datasets = [data_combined, data_weights, data_proximity]
    """

    dashboard_path = os.path.join(output_root, "DEMO_SHIFT_EXPOST_DASHBOARD.xlsx")

    # -------------------------------------
    # 1. Merge ALL mappings (3-way)
    # -------------------------------------
    merged = datasets[0]["mapping"].assign(Source=datasets[0]["prefix"])

    for ds in datasets[1:]:
        merged = merged.merge(
            ds["mapping"].assign(Source=ds["prefix"]),
            on=["Real_Index", "Date_demo"],
            how="outer",
            suffixes=("", f"_{ds['prefix']}"),
            indicator=False
        )

    merged = merged.sort_values("Real_Index")

    # -------------------------------------
    # 2. Calendar alignment across datasets
    # -------------------------------------
    calendars_match = (
        datasets[0]["demo_dates"].equals(datasets[1]["demo_dates"]) and
        datasets[0]["demo_dates"].equals(datasets[2]["demo_dates"])
    )

    # -------------------------------------
    # 3. Build summary metadata
    # -------------------------------------
    metadata = pd.DataFrame({
        "Item": [
            "Dataset 1",
            "Dataset 2",
            "Dataset 3",
            "Total unique demo dates (union)",
            "All calendars match?",
            "Timestamp"
        ],
        "Value": [
            datasets[0]["prefix"],
            datasets[1]["prefix"],
            datasets[2]["prefix"],
            len(merged),
            calendars_match,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
    })

    # -------------------------------------
    # 4. Write to Excel (all canonical)
    # -------------------------------------
    with pd.ExcelWriter(dashboard_path, engine="xlsxwriter") as writer:

        metadata.to_excel(writer, sheet_name="Summary", index=False)
        merged.to_excel(writer, sheet_name="All_Mappings", index=False)

        for ds in datasets:
            ds["bizday_check"].to_excel(writer, sheet_name=f"{ds['prefix']}_BizDay", index=False)
            ds["mapping"].to_excel(writer, sheet_name=f"{ds['prefix']}_Mapping", index=False)

    print(f"\n📊 Dashboard created → {dashboard_path}\n")



# =========================================================
# LOAD ALL THREE DATASETS
# =========================================================
# Combined
df_combined = pd.read_csv(DEMO_COMBINED, compression="gzip")
df_combined["Date"] = pd.to_datetime(df_combined["Date"])

# Weights
df_weights = pd.read_csv(DEMO_WEIGHTS, compression="gzip")
df_weights["Date"] = pd.to_datetime(df_weights["Date"])

# Proximity (Excel)
df_prox = pd.read_excel(PROXIMITY_FILE)
df_prox["Date"] = pd.to_datetime(df_prox["Date"])



# =========================================================
# RUN EX-POST VALIDATION (3 datasets)
# =========================================================
data_combined = build_expost_from_demo(df_combined, "Combined_Long")
data_weights  = build_expost_from_demo(df_weights,  "Weights_Long")
data_prox     = build_expost_from_demo(df_prox,     "Proximity")

datasets = [data_combined, data_weights, data_prox]

build_dashboard(datasets, OUTPUT_ROOT)

# =========================================================
# FINAL SUCCESS MESSAGE (only when all conditions pass)
# =========================================================

all_weekdays_ok = (
    data_combined["bizday_check"].iloc[0]["Result"] and
    data_weights["bizday_check"].iloc[0]["Result"] and
    data_prox["bizday_check"].iloc[0]["Result"]
)

all_sequences_ok = (
    data_combined["bizday_check"].iloc[1]["Result"] and
    data_weights["bizday_check"].iloc[1]["Result"] and
    data_prox["bizday_check"].iloc[1]["Result"]
)

calendars_match = (
    data_combined["demo_dates"].equals(data_weights["demo_dates"]) and
    data_combined["demo_dates"].equals(data_prox["demo_dates"])
)

if all_weekdays_ok and all_sequences_ok and calendars_match:
    print("\n🎉 ALL DATASETS VALIDATED SUCCESSFULLY 🎉\n")
    print("All three files share the exact same business-day timeline,")
    print("with no gaps, no weekends, no mismatches, no missing dates,")
    print("and proper begin/end alignment.\n")
else:
    print("\n⚠️  ONE OR MORE DATASETS FAILED VALIDATION — SEE ABOVE ⚠️\n")


print("\nALL EX-POST CHECKS COMPLETE.\n")
