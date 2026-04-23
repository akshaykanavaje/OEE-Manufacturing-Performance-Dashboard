# OEE Manufacturing Analytics Pipeline

An end-to-end manufacturing analytics pipeline built to monitor and analyse Overall Equipment Effectiveness (OEE) across an 8-machine production plant. The project progresses from a Power BI dashboard backed by a flat CSV file into a fully structured data engineering pipeline — with a Python ETL script, a Snowflake cloud data warehouse, a dimensional star schema, and advanced analytical SQL queries.

The dashboard covers equipment performance tracking, downtime classification, shift analysis, and machine-level diagnostics to support data-driven maintenance and operational decision-making.

---

## Architecture

```
CSV File
   │
   ▼
Python ETL Script
(Extract → Profile → Transform → Load)
   │
   ▼
Snowflake Data Warehouse (AWS ap-southeast-1)
MANUFACTURING_DB / OEE_ANALYTICS
   │
   ├── DIM_MACHINE
   ├── DIM_DATE
   ├── DIM_SHIFT
   ├── DIM_DOWNTIME_REASON
   └── FACT_OEE_DAILY
   │
   ▼
Power BI Dashboard (DirectQuery)
4 Pages — Plant Overview, Machine Deep Dive,
Shift and Time Analysis, Downtime Analysis
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Generation | Python (Pandas, NumPy) |
| ETL Pipeline | Python (snowflake-connector-python, python-dotenv) |
| Cloud Data Warehouse | Snowflake on AWS (ap-southeast-1) |
| Data Modelling | Star Schema — 1 Fact + 4 Dimensions |
| Analytical SQL | Snowflake SQL (CTEs, Window Functions) |
| Visualisation | Power BI Desktop (DirectQuery to Snowflake) |
| Measure Design | DAX (18 measures) |
| Data Transformation | Power Query (M Language) |

---

## Project Structure

```
oee-pipeline/
├── data/
│   └── OEE_Manufacturing_Data.csv
├── etl/
│   ├── 02_etl_load_snowflake.py
│   └── requirements.txt
├── sql/
│   ├── 01_snowflake_setup.sql
│   └── 03_analytical_queries_v2.sql
├── powerbi/
│   └── OEE_Dashboard.pbix
├── docs/
│   └── screenshots/
└── README.md
```

---

## Data Overview

- Synthetic dataset of 7,120 production records generated in Python to reflect realistic manufacturing patterns
- 8 machines across 5 machine types — CNC Lathe, Milling Machine, Drill Press, Assembly, Welding
- 3 shifts per day — Morning, Afternoon, Night — across a full calendar year (January to December 2024)
- Sundays and Saturday Night shifts excluded to reflect realistic plant scheduling
- Each record contains planned time, downtime, downtime reason, actual output, good units and defective units
- Machine-specific performance profiles built in to reflect realistic variation including seasonal degradation in June and July

---

## Phase 1 — Snowflake Setup

Created a Snowflake free trial account on AWS (ap-southeast-1 region) and set up the following infrastructure using SQL DDL:

- Virtual warehouse: `OEE_WH` (X-Small, auto-suspend 60 seconds)
- Database: `MANUFACTURING_DB`
- Schema: `OEE_ANALYTICS`
- 5 tables with primary keys, foreign keys and appropriate data types

All DDL is in `sql/01_snowflake_setup.sql`.

---

## Phase 2 — Dimensional Data Model (Star Schema)

The flat 21-column CSV was decomposed into a proper star schema:

**FACT_OEE_DAILY** — one row per machine per shift per day (7,120 rows)
Stores only raw additive measures — no pre-calculated ratios or percentages

| Column | Type | Description |
|---|---|---|
| FACT_SK | INT | Surrogate key |
| DATE_KEY | INT | FK to DIM_DATE |
| MACHINE_SK | INT | FK to DIM_MACHINE |
| SHIFT_SK | INT | FK to DIM_SHIFT |
| REASON_SK | INT | FK to DIM_DOWNTIME_REASON |
| PLANNED_TIME_MIN | INT | Total planned production minutes |
| RUN_TIME_MIN | INT | Actual run time minutes |
| DOWNTIME_MIN | INT | Total downtime minutes |
| ACTUAL_OUTPUT | INT | Units produced |
| GOOD_UNITS | INT | Units passing quality check |
| DEFECTIVE_UNITS | INT | Units failing quality check |

**DIM_MACHINE** — 8 rows, one per machine
**DIM_DATE** — 314 rows, one per production date in 2024
**DIM_SHIFT** — 3 rows — Morning, Afternoon, Night with shift times
**DIM_DOWNTIME_REASON** — 8 rows with reason category and controllable flag

OEE percentages (Availability, Performance, Quality, OEE) are not stored in the fact table — they are computed at query time in SQL and DAX. This follows standard data warehousing practice since ratios are not additively aggregable.

---

## Phase 3 — Python ETL Pipeline

`etl/02_etl_load_snowflake.py` runs a full extract, profile, transform and load pipeline in 5 stages:

**Stage 1 — Extract**: Reads the CSV using pandas

**Stage 2 — Profile**: Runs data quality checks before any transformation
- Null check across all 21 columns
- Duplicate check on business key (Date + Machine_ID + Shift)
- Date range validation
- Cardinality check on categorical columns
- Numeric range sanity checks
- Special case detection (No Downtime rows)

**Stage 3 — Transform**: Builds 5 clean dataframes
- Assigns surrogate keys to dimension tables
- Derives all date attributes from actual date values (not CSV text columns)
- Maps all foreign keys onto the fact table
- Validates FK mappings — fails fast if any mapping produces nulls
- Drops all pre-calculated ratio columns from fact

**Stage 4 — Load**: Connects to Snowflake and bulk loads using `write_pandas`
- Dimensions load first (parent tables before child)
- Fact loads last (enforces FK integrity)
- Truncate-and-reload pattern — safe to rerun

**Stage 5 — Validate**: Post-load quality checks
- Row count verification for all 5 tables
- Orphan FK check — confirms every fact row has a matching dimension row

**ETL output on successful run:**
```
✓ DIM_MACHINE                    8 rows loaded
✓ DIM_SHIFT                      3 rows loaded
✓ DIM_DOWNTIME_REASON             8 rows loaded
✓ DIM_DATE                      314 rows loaded
✓ FACT_OEE_DAILY               7,120 rows loaded
✓ ALL VALIDATION CHECKS PASSED
✓ Snowflake is loaded and ready for Power BI
```

Credentials are managed via a `.env` file — never hardcoded. `.env` is excluded from version control via `.gitignore`.

---

## Phase 4 — Analytical SQL Queries

5 advanced queries written in Snowflake SQL using CTEs and window functions. All queries in `sql/03_analytical_queries_v2.sql`.

**Query 1 — Rolling 3-Month OEE Average per Machine**
Uses `AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` to smooth monthly OEE fluctuations and surface real performance trends per machine.

**Query 2 — Shift Performance Ranking per Machine**
Uses `RANK() OVER (PARTITION BY MACHINE_NAME ORDER BY oee_pct DESC)` to rank Morning, Afternoon and Night shifts within each machine — identifying which shift consistently underperforms.

**Query 3 — Month over Month OEE Change**
Uses `LAG()` window function to compare each month's plant OEE against the prior month — with directional trend indicators (▲ Improving / ▼ Declining).

**Query 4 — Unplanned Downtime Percentage per Machine**
Uses CTEs and conditional aggregation (`CASE WHEN`) to break down downtime by type per machine — flagging machines as CRITICAL, HIGH or MODERATE based on unplanned breakdown rate.

**Query 5 — Machine OEE vs Plant Average**
Uses a single-row CTE for the plant benchmark joined via `CROSS JOIN` — classifying each machine as World Class, Above Plant Average, Below Plant Average or Critical Underperformer.

---

## Phase 5 — Power BI Dashboard Connected to Snowflake

Power BI Desktop connected to Snowflake via the native Snowflake connector using DirectQuery mode. Star schema relationships built in Model view:

- FACT_OEE_DAILY → DIM_DATE (DATE_KEY)
- FACT_OEE_DAILY → DIM_MACHINE (MACHINE_SK)
- FACT_OEE_DAILY → DIM_SHIFT (SHIFT_SK)
- FACT_OEE_DAILY → DIM_DOWNTIME_REASON (REASON_SK)

### Page 1 — Plant Overview
Answers: How is the plant performing overall and where are the biggest problems?

- 4 KPI cards — Average OEE %, Availability %, Performance %, Quality %
- Horizontal bar chart ranking all 8 machines by OEE with traffic light colouring
- Donut chart showing downtime reason distribution
- Monthly OEE trend line with 85% world-class reference line

<img width="1304" height="733" alt="image" src="https://github.com/user-attachments/assets/3b5bba13-6c15-4886-9e71-48adbb00c62c" />


### Page 2 — Machine Deep Dive
Answers: Why is a specific machine underperforming and when does it happen?

- Machine slicer filters all visuals dynamically
- OEE components clustered bar chart
- Shift column chart showing OEE by Morning, Afternoon and Night
- Downtime reasons bar chart filtered to selected machine
- Monthly OEE trend line with 85% reference line

<img width="1291" height="720" alt="image" src="https://github.com/user-attachments/assets/14cc99b5-57f9-410d-95b1-2ed2847fcf8f" />


### Page 3 — Shift and Time Analysis
Answers: When do performance problems happen — which shift, which day, which month?

- KPI cards — Best Shift OEE %, Worst Shift OEE %, Shift Performance Gap %
- OEE % by machine type and by weekday
- Defect Rate % by machine type
- Monthly OEE trend by shift — three separate lines

<img width="1292" height="728" alt="image" src="https://github.com/user-attachments/assets/252975d5-42e3-4706-9162-f716b65a6d93" />


### Page 4 — Downtime Analysis
Answers: How much time is the plant losing, why, and which machines are responsible?

- KPI cards — Total Downtime Hours, Unplanned Downtime %
- Downtime by reason bar chart
- Monthly downtime trend with July peak annotation
- Stacked bar chart — downtime reason breakdown per machine
- Reference table with conditional formatting on Unplanned Downtime %

<img width="1288" height="722" alt="image" src="https://github.com/user-attachments/assets/fd4a2b15-c57c-4074-b68a-1b89933966e4" />


---

## Key Findings

- Plant-wide OEE of **69.62%** sits 15.4 percentage points below the 85% world-class benchmark
- **Unplanned breakdowns** account for **34.21%** of 8,690 total downtime hours — the single largest loss category
- **Assembly Line B** is the critical underperformer at **50.87% OEE** with 2,083 hours lost annually — nearly 4x higher than Assembly Line A at 541 hours despite being the same machine type
- Assembly Line B carries a **49.13% unplanned downtime rate** vs Assembly Line A's 19.31% — indicating reactive versus proactive maintenance on identical equipment
- A **15.8 percentage point OEE gap** exists between Morning (75.76%) and Night (59.96%) shifts consistently across all machines
- The shift gap widens to approximately 20 points during June and July — suggesting seasonal operational sensitivity specific to night operations
- Assembly Line B and CNC Lathe 2 together account for **43% of total plant downtime**
- Day of week shows negligible OEE variation — shift pattern is a stronger performance variable than weekday

---

## Dashboard Design

A consistent 4-colour palette applied across all pages:

| Colour | Meaning |
|---|---|
| Red | Problem — OEE below 60%, unplanned downtime, defective units |
| Yellow | Warning — OEE 60–75%, manageable downtime |
| Green | Healthy — OEE above 75%, good units |
| Blue | Neutral — trend lines, planned activities, component metrics |

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Snowflake account
- Power BI Desktop
- Snowflake ODBC driver

### Run the ETL Pipeline

```bash
# Install dependencies
pip install -r etl/requirements.txt

# Create .env file in etl/ folder
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password

# Run ETL
python etl/02_etl_load_snowflake.py
```

### Run SQL Queries
Open `sql/03_analytical_queries_v2.sql` in a Snowflake worksheet and execute each query individually.

### Open Dashboard
Open `powerbi/OEE_Dashboard.pbix` in Power BI Desktop. Update the Snowflake connection credentials when prompted.

---

## Limitations and Future Improvements

- Dataset is synthetic — generated to reflect realistic patterns rather than sourced from live sensor data
- OEE calculations assume fixed planned time per shift with no allowance for scheduled short stoppages
- Future enhancements could include:
  - Integration with live IoT sensor data for real-time OEE monitoring
  - Predictive maintenance modelling using machine learning on historical failure patterns
  - Automated anomaly detection flagging unusual OEE drops
  - dbt transformation layer between raw ingestion and analytical schema
  - Airflow or Prefect for ETL orchestration and scheduling

---

## Author

**Akshay Kanavaje**
MSc Data Science — Cardiff University
