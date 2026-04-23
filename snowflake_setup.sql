-- ============================================================
-- OEE MANUFACTURING ANALYTICS — SNOWFLAKE SETUP SCRIPT
-- Author : Akshay Kanavaje
-- Purpose: Create warehouse, database, schema and all tables
-- Run    : Paste entire script in Snowflake worksheet, run all
-- ============================================================


-- ============================================================
-- BLOCK 1: WAREHOUSE
-- The compute engine. XS = extra small = cheapest.
-- Auto-suspend after 60 seconds of no activity (saves credits).
-- Auto-resume when a query hits it.
-- ============================================================

CREATE WAREHOUSE IF NOT EXISTS OEE_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND   = 60
    AUTO_RESUME    = TRUE
    COMMENT        = 'Warehouse for OEE Manufacturing Analytics project';


-- ============================================================
-- BLOCK 2: DATABASE
-- The top-level container for this project.
-- ============================================================

CREATE DATABASE IF NOT EXISTS MANUFACTURING_DB
    COMMENT = 'Manufacturing OEE Analytics — Akshay Kanavaje portfolio project';


-- ============================================================
-- BLOCK 3: SCHEMA
-- A namespace (folder) inside the database.
-- We switch context to the right DB + Schema so all CREATE TABLE
-- statements below land in the correct place.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS MANUFACTURING_DB.OEE_ANALYTICS
    COMMENT = 'Star schema for OEE daily production data';

-- Set context so we don't have to write full path every time
USE WAREHOUSE OEE_WH;
USE DATABASE  MANUFACTURING_DB;
USE SCHEMA    OEE_ANALYTICS;


-- ============================================================
-- BLOCK 4: DIMENSION TABLES
-- Small, descriptive tables. Load these FIRST before the fact.
-- ============================================================

-- DIM_MACHINE
-- One row per machine. Stores descriptive attributes.
-- MACHINE_SK = surrogate key (integer we assign, clean and stable)
-- MACHINE_ID = natural key (the original ID from your CSV like M001)

CREATE TABLE IF NOT EXISTS DIM_MACHINE (
    MACHINE_SK              INT           NOT NULL,   -- surrogate key (1,2,3...)
    MACHINE_ID              VARCHAR(10)   NOT NULL,   -- natural key  (M001, M002...)
    MACHINE_NAME            VARCHAR(50)   NOT NULL,   -- Assembly Line A, CNC Lathe 1...
    MACHINE_TYPE            VARCHAR(50)   NOT NULL,   -- Assembly, CNC Lathe, Milling...
    THEORETICAL_MAX_OUTPUT  INT           NOT NULL,   -- max units possible per shift

    CONSTRAINT PK_DIM_MACHINE PRIMARY KEY (MACHINE_SK)
);


-- DIM_DATE
-- One row per calendar date in 2024 (366 rows — 2024 is a leap year).
-- DATE_KEY = integer in YYYYMMDD format e.g. 20240115
-- This is standard warehouse practice — integer joins are faster than date joins.

CREATE TABLE IF NOT EXISTS DIM_DATE (
    DATE_KEY    INT           NOT NULL,   -- 20240101, 20240102 ...
    FULL_DATE   DATE          NOT NULL,   -- actual DATE value
    DAY_NUM     INT           NOT NULL,   -- 1 to 31
    MONTH_NUM   INT           NOT NULL,   -- 1 to 12
    MONTH_NAME  VARCHAR(15)   NOT NULL,   -- January, February ...
    QUARTER     INT           NOT NULL,   -- 1, 2, 3, 4
    YEAR_NUM    INT           NOT NULL,   -- 2024
    WEEK_NUM    INT           NOT NULL,   -- ISO week number 1-53
    WEEKDAY_NUM INT           NOT NULL,   -- 1=Monday ... 7=Sunday
    WEEKDAY     VARCHAR(15)   NOT NULL,   -- Monday, Tuesday ...

    CONSTRAINT PK_DIM_DATE PRIMARY KEY (DATE_KEY)
);


-- DIM_SHIFT
-- Only 3 rows: Morning, Afternoon, Night.
-- Small table but having it as a dimension means you can add
-- shift attributes later (supervisor name, target OEE etc.)

CREATE TABLE IF NOT EXISTS DIM_SHIFT (
    SHIFT_SK         INT          NOT NULL,   -- 1, 2, 3
    SHIFT_NAME       VARCHAR(20)  NOT NULL,   -- Morning, Afternoon, Night
    SHIFT_START_TIME TIME         NOT NULL,   -- 06:00, 14:00, 22:00
    SHIFT_END_TIME   TIME         NOT NULL,   -- 14:00, 22:00, 06:00

    CONSTRAINT PK_DIM_SHIFT PRIMARY KEY (SHIFT_SK)
);


-- DIM_DOWNTIME_REASON
-- One row per downtime reason type.
-- CONTROLLABLE flag is important for analysis —
-- Unplanned Breakdown is controllable (maintenance can fix it),
-- Power Failure is not (external).

CREATE TABLE IF NOT EXISTS DIM_DOWNTIME_REASON (
    REASON_SK       INT          NOT NULL,   -- surrogate key
    REASON_NAME     VARCHAR(50)  NOT NULL,   -- Unplanned Breakdown, Material Shortage...
    REASON_CATEGORY VARCHAR(30)  NOT NULL,   -- Mechanical, Supply, Planned, Electrical, Quality, Labour
    CONTROLLABLE    BOOLEAN      NOT NULL,   -- TRUE if operations team can fix it

    CONSTRAINT PK_DIM_DOWNTIME_REASON PRIMARY KEY (REASON_SK)
);


-- ============================================================
-- BLOCK 5: FACT TABLE
-- One row per machine per shift per day = 7,120 rows.
-- Stores ONLY raw additive measures — no ratios or percentages.
-- Foreign keys point to the 4 dimension tables above.
-- OEE % will be calculated in SQL and DAX — not stored here.
-- ============================================================

CREATE TABLE IF NOT EXISTS FACT_OEE_DAILY (
    -- Surrogate key for the fact row itself
    FACT_SK             INT     NOT NULL,

    -- Foreign keys to dimensions
    DATE_KEY            INT     NOT NULL,   -- joins to DIM_DATE.DATE_KEY
    MACHINE_SK          INT     NOT NULL,   -- joins to DIM_MACHINE.MACHINE_SK
    SHIFT_SK            INT     NOT NULL,   -- joins to DIM_SHIFT.SHIFT_SK
    REASON_SK           INT     NOT NULL,   -- joins to DIM_DOWNTIME_REASON.REASON_SK

    -- Raw additive measures (base facts — no ratios)
    PLANNED_TIME_MIN    INT     NOT NULL,   -- total planned production minutes
    RUN_TIME_MIN        INT     NOT NULL,   -- actual run time (planned minus downtime)
    DOWNTIME_MIN        INT     NOT NULL,   -- total downtime minutes
    ACTUAL_OUTPUT       INT     NOT NULL,   -- units actually produced
    GOOD_UNITS          INT     NOT NULL,   -- units passing quality check
    DEFECTIVE_UNITS     INT     NOT NULL,   -- units failing quality check

    CONSTRAINT PK_FACT_OEE         PRIMARY KEY (FACT_SK),
    CONSTRAINT FK_FACT_DATE        FOREIGN KEY (DATE_KEY)   REFERENCES DIM_DATE(DATE_KEY),
    CONSTRAINT FK_FACT_MACHINE     FOREIGN KEY (MACHINE_SK) REFERENCES DIM_MACHINE(MACHINE_SK),
    CONSTRAINT FK_FACT_SHIFT       FOREIGN KEY (SHIFT_SK)   REFERENCES DIM_SHIFT(SHIFT_SK),
    CONSTRAINT FK_FACT_REASON      FOREIGN KEY (REASON_SK)  REFERENCES DIM_DOWNTIME_REASON(REASON_SK)
);


-- ============================================================
-- BLOCK 6: VERIFY — run this after the above to confirm
-- all 5 tables were created successfully
-- ============================================================

SHOW TABLES IN SCHEMA MANUFACTURING_DB.OEE_ANALYTICS;