# ============================================================
# OEE MANUFACTURING ANALYTICS — PYTHON ETL SCRIPT
# Author  : Akshay Kanavaje
# Purpose : Extract CSV → Profile → Transform → Load Snowflake
# Run     : python 02_etl_load_snowflake.py
# Requires: pip install snowflake-connector-python pandas python-dotenv
# ============================================================

import pandas as pd
import numpy as np
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv
import os
import sys
from datetime import datetime

# ============================================================
# SECTION 1 — CONFIGURATION
# Reads credentials from .env file (never hardcode passwords)
# ============================================================

load_dotenv()  # loads variables from .env file in same folder

SNOWFLAKE_CONFIG = {
    "account"   : os.getenv("SNOWFLAKE_ACCOUNT"),    # from .env
    "user"      : os.getenv("SNOWFLAKE_USER"),        # from .env
    "password"  : os.getenv("SNOWFLAKE_PASSWORD"),    # from .env
    "warehouse" : "OEE_WH",
    "database"  : "MANUFACTURING_DB",
    "schema"    : "OEE_ANALYTICS",
}

CSV_PATH = "OEE_Manufacturing_Data.csv"   # put CSV in same folder as this script


# ============================================================
# SECTION 2 — EXTRACT
# Simply reads the CSV into a pandas DataFrame
# ============================================================

def extract(csv_path):
    print("\n" + "="*60)
    print("STEP 1: EXTRACT")
    print("="*60)

    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df):,} rows and {len(df.columns)} columns from {csv_path}")
    return df


# ============================================================
# SECTION 3 — PROFILE
# Checks data quality before we touch anything.
# A real data engineer always profiles before transforming.
# ============================================================

def profile(df):
    print("\n" + "="*60)
    print("STEP 2: DATA PROFILING REPORT")
    print("="*60)

    # --- Row count ---
    print(f"\n  Total rows         : {len(df):,}")
    print(f"  Total columns      : {len(df.columns)}")

    # --- Null check ---
    nulls = df.isnull().sum()
    total_nulls = nulls.sum()
    print(f"\n  Null values        : {total_nulls}")
    if total_nulls > 0:
        print("  Columns with nulls:")
        print(nulls[nulls > 0].to_string())
    else:
        print("  ✓ No null values found")

    # --- Duplicate check (business key = Date + Machine + Shift) ---
    dupes = df.duplicated(subset=["Date", "Machine_ID", "Shift"]).sum()
    print(f"\n  Duplicate rows     : {dupes}")
    if dupes == 0:
        print("  ✓ No duplicates on Date + Machine_ID + Shift")
    else:
        print(f"  ✗ WARNING: {dupes} duplicate rows found — will be dropped")

    # --- Date range ---
    print(f"\n  Date range         : {df['Date'].min()}  to  {df['Date'].max()}")

    # --- Machine cardinality ---
    print(f"\n  Unique machines    : {df['Machine_ID'].nunique()}")
    print(f"  Unique shifts      : {df['Shift'].nunique()} — {df['Shift'].unique().tolist()}")
    print(f"  Unique DT reasons  : {df['Downtime_Reason'].nunique()} — {df['Downtime_Reason'].unique().tolist()}")

    # --- Numeric sanity checks ---
    print("\n  Numeric range checks:")
    checks = {
        "Planned_Time_Min"  : (400, 500),
        "Downtime_Min"      : (0, 480),
        "Run_Time_Min"      : (0, 480),
        "Good_Units"        : (0, 500),
        "Defective_Units"   : (0, 500),
    }
    for col, (low, high) in checks.items():
        out_of_range = df[(df[col] < low) | (df[col] > high)]
        status = "✓ OK" if len(out_of_range) == 0 else f"✗ {len(out_of_range)} out of range"
        print(f"    {col:<25}: {status}")

    # --- No Downtime rows ---
    no_dt = df[df["Downtime_Reason"] == "No Downtime"]
    print(f"\n  'No Downtime' rows : {len(no_dt)} (Downtime_Min = 0 on these rows)")
    print("  ✓ Will map to REASON_SK = 0 (a special 'No Downtime' record in DIM_DOWNTIME_REASON)")

    print("\n  ✓ Profiling complete — data is clean, proceeding to transform\n")
    return df   # return unchanged, just profiled


# ============================================================
# SECTION 4 — TRANSFORM
# Builds the 5 dataframes: 4 dims + 1 fact.
# No ratios or percentages in the fact table.
# ============================================================

def transform(df):
    print("="*60)
    print("STEP 3: TRANSFORM")
    print("="*60)

    # --- DIM_MACHINE ---
    # Deduplicate on Machine_ID, assign integer surrogate key
    dim_machine = (
        df[["Machine_ID", "Machine_Name", "Machine_Type", "Theoretical_Max_Output"]]
        .drop_duplicates(subset=["Machine_ID"])
        .sort_values("Machine_ID")
        .reset_index(drop=True)
    )
    dim_machine.insert(0, "MACHINE_SK", range(1, len(dim_machine) + 1))
    dim_machine.columns = ["MACHINE_SK", "MACHINE_ID", "MACHINE_NAME", "MACHINE_TYPE", "THEORETICAL_MAX_OUTPUT"]
    print(f"\n  DIM_MACHINE  : {len(dim_machine)} rows")

    # --- DIM_SHIFT ---
    # Hardcoded — only 3 shifts, times are known
    dim_shift = pd.DataFrame({
        "SHIFT_SK"        : [1, 2, 3],
        "SHIFT_NAME"      : ["Morning", "Afternoon", "Night"],
        "SHIFT_START_TIME": ["06:00:00", "14:00:00", "22:00:00"],
        "SHIFT_END_TIME"  : ["14:00:00", "22:00:00", "06:00:00"],
    })
    print(f"  DIM_SHIFT    : {len(dim_shift)} rows")

    # --- DIM_DOWNTIME_REASON ---
    # REASON_SK = 0 reserved for 'No Downtime' (special case)
    reason_map = {
        "No Downtime"       : (0, "None",       "No Downtime",  False),
        "Unplanned Breakdown": (1, "Mechanical", "Unplanned",    True),
        "Material Shortage" : (2, "Supply",      "Supply",       True),
        "Planned Maintenance": (3, "Planned",    "Planned",      False),
        "Power Failure"     : (4, "Electrical",  "External",     False),
        "Quality Check Hold": (5, "Quality",     "Quality",      True),
        "Operator Absence"  : (6, "Labour",      "Labour",       True),
        "Tool Change"       : (7, "Mechanical",  "Planned",      False),
    }
    dim_downtime = pd.DataFrame([
        {"REASON_SK": v[0], "REASON_NAME": k, "REASON_CATEGORY": v[2], "CONTROLLABLE": v[3]}
        for k, v in reason_map.items()
    ]).sort_values("REASON_SK").reset_index(drop=True)
    print(f"  DIM_DOWNTIME : {len(dim_downtime)} rows")

    # --- DIM_DATE ---
    # Generate one row per unique date. Derive all date attributes from the date itself.
    # We do NOT trust the Month/Weekday text columns in CSV —
    # we derive them cleanly from the actual date value.
    unique_dates = pd.to_datetime(df["Date"].unique())
    unique_dates = sorted(unique_dates)

    month_names  = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"]
    weekday_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    date_rows = []
    for d in unique_dates:
        date_rows.append({
            "DATE_KEY"   : int(d.strftime("%Y%m%d")),   # 20240101
            "FULL_DATE"  : d.date(),
            "DAY_NUM"    : d.day,
            "MONTH_NUM"  : d.month,
            "MONTH_NAME" : month_names[d.month - 1],
            "QUARTER"    : (d.month - 1) // 3 + 1,
            "YEAR_NUM"   : d.year,
            "WEEK_NUM"   : d.isocalendar()[1],
            "WEEKDAY_NUM": d.weekday() + 1,              # 1=Mon, 6=Sat
            "WEEKDAY"    : weekday_names[d.weekday()],
        })
    dim_date = pd.DataFrame(date_rows)
    print(f"  DIM_DATE     : {len(dim_date)} rows (dates in dataset)")

    # --- FACT_OEE_DAILY ---
    # Join the surrogate keys from each dim onto the flat CSV.
    # Drop all text columns and derived ratio columns — only raw measures stay.

    # Build lookup dictionaries for fast mapping
    machine_sk_map  = dict(zip(dim_machine["MACHINE_ID"],  dim_machine["MACHINE_SK"]))
    shift_sk_map    = dict(zip(dim_shift["SHIFT_NAME"],    dim_shift["SHIFT_SK"]))
    reason_sk_map   = {k: v[0] for k, v in reason_map.items()}
    date_key_map    = dict(zip(
        pd.to_datetime(dim_date["FULL_DATE"]).dt.strftime("%Y-%m-%d"),
        dim_date["DATE_KEY"]
    ))

    fact = df.copy()

    # Map foreign keys
    fact["DATE_KEY"]   = fact["Date"].map(date_key_map)
    fact["MACHINE_SK"] = fact["Machine_ID"].map(machine_sk_map)
    fact["SHIFT_SK"]   = fact["Shift"].map(shift_sk_map)
    fact["REASON_SK"]  = fact["Downtime_Reason"].map(reason_sk_map)

    # Add surrogate key for fact row
    fact.insert(0, "FACT_SK", range(1, len(fact) + 1))

    # Select only the columns that belong in the fact table
    fact_final = fact[[
        "FACT_SK",
        "DATE_KEY",
        "MACHINE_SK",
        "SHIFT_SK",
        "REASON_SK",
        "Planned_Time_Min",
        "Run_Time_Min",
        "Downtime_Min",
        "Actual_Output_Units",
        "Good_Units",
        "Defective_Units",
    ]].copy()

    # Rename to match Snowflake column names exactly
    fact_final.columns = [
        "FACT_SK",
        "DATE_KEY",
        "MACHINE_SK",
        "SHIFT_SK",
        "REASON_SK",
        "PLANNED_TIME_MIN",
        "RUN_TIME_MIN",
        "DOWNTIME_MIN",
        "ACTUAL_OUTPUT",
        "GOOD_UNITS",
        "DEFECTIVE_UNITS",
    ]

    print(f"  FACT_OEE     : {len(fact_final)} rows")

    # Verify no NaN in any FK column (would mean a mapping failed)
    fk_nulls = fact_final[["DATE_KEY","MACHINE_SK","SHIFT_SK","REASON_SK"]].isnull().sum()
    if fk_nulls.sum() > 0:
        print("\n  ✗ ERROR: FK mapping produced nulls — check source data")
        print(fk_nulls)
        sys.exit(1)
    else:
        print("  ✓ All foreign key mappings resolved — no nulls in fact FKs")

    print("\n  ✓ Transform complete\n")
    return dim_machine, dim_shift, dim_downtime, dim_date, fact_final


# ============================================================
# SECTION 5 — LOAD
# Connects to Snowflake and loads tables.
# Order matters: dims first, fact last (FK constraint).
# Uses TRUNCATE + reload pattern — safe to rerun any time.
# ============================================================

def load(dim_machine, dim_shift, dim_downtime, dim_date, fact_final):
    print("="*60)
    print("STEP 4: LOAD TO SNOWFLAKE")
    print("="*60)

    # Connect
    print("\n  Connecting to Snowflake...")
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cur  = conn.cursor()
    print("  ✓ Connected\n")

    # Helper function — truncate table then bulk load dataframe
    def load_table(df, table_name):
        print(f"  Loading {table_name}...")
        cur.execute(f"TRUNCATE TABLE IF EXISTS {table_name}")
        success, nchunks, nrows, _ = write_pandas(
            conn, df, table_name,
            database="MANUFACTURING_DB",
            schema="OEE_ANALYTICS"
        )
        if success:
            print(f"  ✓ {table_name:<30} {nrows:>6,} rows loaded")
        else:
            print(f"  ✗ FAILED to load {table_name}")
            sys.exit(1)

    # Load dimensions first — order matters for FK constraints
    load_table(dim_machine,  "DIM_MACHINE")
    load_table(dim_shift,    "DIM_SHIFT")
    load_table(dim_downtime, "DIM_DOWNTIME_REASON")
    load_table(dim_date,     "DIM_DATE")

    # Load fact last
    load_table(fact_final,   "FACT_OEE_DAILY")

    print()

    # --------------------------------------------------------
    # SECTION 6 — VALIDATE
    # Row count check — confirm what we loaded matches source
    # --------------------------------------------------------
    print("="*60)
    print("STEP 5: VALIDATION")
    print("="*60)
    print()

    validation_queries = {
        "DIM_MACHINE"        : "SELECT COUNT(*) FROM DIM_MACHINE",
        "DIM_SHIFT"          : "SELECT COUNT(*) FROM DIM_SHIFT",
        "DIM_DOWNTIME_REASON": "SELECT COUNT(*) FROM DIM_DOWNTIME_REASON",
        "DIM_DATE"           : "SELECT COUNT(*) FROM DIM_DATE",
        "FACT_OEE_DAILY"     : "SELECT COUNT(*) FROM FACT_OEE_DAILY",
    }

    expected = {
        "DIM_MACHINE"        : 8,
        "DIM_SHIFT"          : 3,
        "DIM_DOWNTIME_REASON": 8,
        "DIM_DATE"           : None,   # varies — just report it
        "FACT_OEE_DAILY"     : 7120,
    }

    all_ok = True
    for table, query in validation_queries.items():
        cur.execute(query)
        actual = cur.fetchone()[0]
        exp    = expected[table]
        if exp is None:
            print(f"  {table:<30}: {actual:>6,} rows  ✓")
        elif actual == exp:
            print(f"  {table:<30}: {actual:>6,} rows  ✓  (expected {exp})")
        else:
            print(f"  {table:<30}: {actual:>6,} rows  ✗  (expected {exp}) — MISMATCH")
            all_ok = False

    # Orphan FK check — any fact rows with no matching dimension?
    print()
    orphan_checks = [
        ("Date FK"   , "SELECT COUNT(*) FROM FACT_OEE_DAILY f LEFT JOIN DIM_DATE d ON f.DATE_KEY = d.DATE_KEY WHERE d.DATE_KEY IS NULL"),
        ("Machine FK", "SELECT COUNT(*) FROM FACT_OEE_DAILY f LEFT JOIN DIM_MACHINE m ON f.MACHINE_SK = m.MACHINE_SK WHERE m.MACHINE_SK IS NULL"),
        ("Shift FK"  , "SELECT COUNT(*) FROM FACT_OEE_DAILY f LEFT JOIN DIM_SHIFT s ON f.SHIFT_SK = s.SHIFT_SK WHERE s.SHIFT_SK IS NULL"),
        ("Reason FK" , "SELECT COUNT(*) FROM FACT_OEE_DAILY f LEFT JOIN DIM_DOWNTIME_REASON r ON f.REASON_SK = r.REASON_SK WHERE r.REASON_SK IS NULL"),
    ]
    for label, query in orphan_checks:
        cur.execute(query)
        orphans = cur.fetchone()[0]
        status = "✓ No orphans" if orphans == 0 else f"✗ {orphans} orphan rows!"
        print(f"  {label:<15}: {status}")

    cur.close()
    conn.close()

    print()
    if all_ok:
        print("  ✓ ALL VALIDATION CHECKS PASSED")
        print("  ✓ Snowflake is loaded and ready for Power BI")
    else:
        print("  ✗ Some checks failed — review above")

    print()
    print("="*60)
    print(f"  ETL completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


# ============================================================
# MAIN — runs all steps in order
# ============================================================

if __name__ == "__main__":
    raw_df                                              = extract(CSV_PATH)
    profiled_df                                         = profile(raw_df)
    dim_machine, dim_shift, dim_downtime, dim_date, fact = transform(profiled_df)
    load(dim_machine, dim_shift, dim_downtime, dim_date, fact)