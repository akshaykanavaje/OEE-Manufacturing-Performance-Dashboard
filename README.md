# OEE Manufacturing Performance Dashboard

This project implements a interactive Power BI dashboard to monitor and analyse Overall Equipment Effectiveness (OEE) across an 8-machine manufacturing plant. The solution covers equipment performance tracking, downtime classification, shift analysis, and machine-level diagnostics to support data-driven maintenance and operational decision-making.

The dashboard is designed to be viewed interactively via Power BI Desktop (.pbix) or published online.

---

# Business Context

Manufacturing plants generate large volumes of operational data across machines, shifts, and production runs that must be monitored continuously for efficiency losses. Manual reporting through shift logs and weekly Excel reviews is delayed, inconsistent, and unable to surface patterns across hundreds of production records.

This project demonstrates how structured data analysis and dashboard design can be applied to:

- monitor plant-wide equipment effectiveness against industry benchmarks
- identify underperforming machines and shifts before losses accumulate
- classify downtime by root cause to distinguish controllable from uncontrollable losses
- support maintenance prioritisation decisions with quantified evidence

The emphasis is on operational clarity and actionable insight, not just metric reporting.

---

# Data Overview

- Synthetic dataset of 7,120 production records generated to reflect realistic manufacturing patterns
- Records cover 8 machines across 5 machine types — CNC Lathe, Milling Machine, Drill Press, Assembly, Welding
- 3 shifts per day — Morning, Afternoon, Night — across a full calendar year (January to December 2024)
- Sundays and Saturday Night shifts excluded to reflect realistic plant scheduling
- Each record contains planned time, downtime, downtime reason, actual output, good units, defective units and pre-calculated OEE components
- Machine-specific performance profiles built in to reflect realistic variation — including seasonal degradation in June and July

This represents a structured operational analytics problem with time-series, categorical and numerical dimensions.

---

# Analytical Approach

## 1. Data Preparation and Measure Design

- Imported raw CSV into Power BI and standardised data types in Power Query
- Created a Weekday sort column to enforce correct Monday–Saturday ordering
- Developed 18 DAX measures covering OEE components, production totals, downtime classification and comparative metrics
- Key measures include Avg OEE %, Total Downtime Hours, Unplanned Downtime %, Defect Rate %, Capacity Utilisation %, Shift Performance Gap, Best Shift OEE % and Worst Shift OEE %

Measure design preceded visual construction to ensure all calculations were reusable and filter-responsive across all four pages.

## 2. Page 1 — Plant Overview

Designed to answer: *How is the plant performing overall and where are the biggest problems?*

- 7 KPI cards covering OEE components, total good units, total defective units and total downtime hours
- Horizontal bar chart ranking all 8 machines by average OEE % with red/yellow/green traffic light colouring
- Donut chart showing downtime reason distribution — No Downtime category excluded
- Line chart showing monthly OEE trend with 85% world-class reference line

<img width="1304" height="733" alt="image" src="https://github.com/user-attachments/assets/3b5bba13-6c15-4886-9e71-48adbb00c62c" />



## 3. Page 2 — Machine Deep Dive

Designed to answer: *Why is a specific machine underperforming and when does it happen?*

- Machine slicer filters all visuals dynamically to selected machine
- OEE components clustered bar chart with fixed identity colours — blue for Availability, yellow for Performance, green for Quality
- Shift column chart showing OEE by Morning, Afternoon and Night for selected machine
- Downtime reasons bar chart filtered to selected machine
- Monthly OEE trend line for selected machine with 85% reference line


<img width="1291" height="720" alt="image" src="https://github.com/user-attachments/assets/14cc99b5-57f9-410d-95b1-2ed2847fcf8f" />


## 4. Page 3 — Shift and Time Analysis

Designed to answer: *When do performance problems happen — which shift, which day, which month?*

- 3 KPI cards — Best Shift OEE %, Shift Performance Gap and Worst Shift OEE %
- OEE % by machine type bar chart with traffic light colouring
- Defect Rate % by machine type bar chart
- OEE % by weekday column chart in uniform blue — flat pattern across weekdays is itself an analytical finding
- Monthly OEE trend by shift with three separate lines — Morning, Afternoon and Night — revealing seasonal shift gap widening

<img width="1292" height="728" alt="image" src="https://github.com/user-attachments/assets/252975d5-42e3-4706-9162-f716b65a6d93" />


## 5. Page 4 — Downtime Analysis

Designed to answer: *How much time is the plant losing, why, and which machines are responsible?*

- 2 KPI cards — Total Downtime Hours and Unplanned Downtime %
- Reference table with conditional formatting on Unplanned Downtime % column — red above 40%, yellow 25–40%, green below 25%
- Downtime by reason bar chart with colour logic — red for uncontrollable reasons, yellow for manageable, blue for planned
- Monthly downtime trend line with July peak annotation
- Stacked bar chart showing downtime reason breakdown per machine simultaneously

<img width="1288" height="722" alt="image" src="https://github.com/user-attachments/assets/fd4a2b15-c57c-4074-b68a-1b89933966e4" />


---

# Dashboard Design

A consistent 4-colour palette was applied across all pages to ensure visual coherence:

- **Red** — problem indicators, machines below 60% OEE, unplanned downtime, defective units
- **Yellow** — warning indicators, machines 60–75% OEE, manageable downtime reasons
- **Green** — healthy indicators, machines above 75% OEE, good units produced
- **Blue** — neutral indicators, component metrics, trend lines, planned activities

KPI card colours reflect the fixed meaning of each metric rather than dynamic thresholds, consistent with the dashboard's annual fixed dataset nature.

---

# Key Findings

- Plant-wide OEE of 69.62% sits 15.4 percentage points below the 85% world-class benchmark
- Unplanned breakdowns account for 34.21% of 8,690 total downtime hours — the single largest loss category
- Assembly Line B is the critical underperformer at 50.87% OEE with 2,083 hours lost annually — nearly 4x higher than Assembly Line A at 541 hours despite being the same machine type
- Assembly Line B carries a 49.13% unplanned downtime rate compared to Assembly Line A's 19.31% — indicating reactive versus proactive maintenance profiles on identical equipment
- A 15.8 percentage point OEE gap exists between Morning (75.76%) and Night (59.96%) shifts consistently across all machines and all months
- The shift gap widens to approximately 20 points during June and July — suggesting seasonal operational sensitivity specific to night operations
- Assembly Line B and CNC Lathe 2 together account for 43% of total plant downtime
- Day of week shows negligible OEE variation — shift pattern is a stronger performance variable than weekday

---

# Business Impact

This dashboard illustrates how structured operational analytics can:

- replace delayed weekly reporting with a visual plant health overview readable in under 30 seconds
- surface machine-level diagnostic insights that are invisible in aggregate shift logs
- quantify the cost difference between proactive and reactive maintenance approaches
- identify shift-based performance inequality and its seasonal variation for targeted intervention

The framework is adaptable to any manufacturing environment with shift-level production and downtime records.

---

# Tech Stack

- Power BI Desktop
- DAX (Data Analysis Expressions)
- Power Query (M Language)
- CSV data source

---

# Limitations and Future Improvements

- Dataset is synthetic — generated to reflect realistic patterns rather than sourced from live sensor data
- OEE calculations assume fixed planned time per shift with no allowance for scheduled short stoppages
- Machine profiles are static across the year — real equipment degrades non-linearly over time
- Future enhancements could include:
  - integration with live IoT sensor data for real-time OEE monitoring
  - predictive maintenance modelling using machine learning on historical failure patterns
  - drill-through pages connecting downtime events to specific operator or material batch records
  - automated anomaly detection flagging unusual OEE drops without manual review
