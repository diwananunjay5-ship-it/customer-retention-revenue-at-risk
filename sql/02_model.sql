-- ==============================================================================
-- 02_model.sql
-- Customer Retention & Revenue-at-Risk Pipeline: Dimensional Star Schema
-- Tables:
--   1. config_snapshot : Central parameter table holding the analysis snapshot date
--   2. dim_date        : Calendar dimension table spanning the full analysis timeline
--   3. dim_customer    : Customer dimension table with acquisition cohorts & lifetime metrics
--   4. fact_orders     : Order-grain transaction fact table for order-level analytics
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Snapshot Date Configuration
-- Centrally defined as max(order_date) + 1 day (2011-12-10).
-- Used across all recency, tenure, and churn scoring calculations.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE config_snapshot AS
SELECT 
    (MAX(order_date) + INTERVAL 1 DAY)::DATE AS snapshot_date
FROM clean_sales;


-- ------------------------------------------------------------------------------
-- 2. Date Dimension (dim_date)
-- Complete calendar dimension covering the entire transactional observation window.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_date AS
WITH date_bounds AS (
    SELECT 
        MIN(order_date) AS min_date,
        '2011-12-31'::DATE AS max_date
    FROM clean_sales
),
calendar AS (
    SELECT 
        UNNEST(generate_series(min_date, max_date, INTERVAL 1 DAY))::DATE AS date
    FROM date_bounds
)
SELECT
    date,
    EXTRACT('year' FROM date)::INTEGER AS year,
    EXTRACT('quarter' FROM date)::INTEGER AS quarter,
    EXTRACT('month' FROM date)::INTEGER AS month,
    STRFTIME(date, '%B') AS month_name,
    STRFTIME(date, '%b %Y') AS month_year,
    DATE_TRUNC('month', date)::DATE AS cohort_month,
    EXTRACT('day' FROM date)::INTEGER AS day_of_month,
    EXTRACT('dayofweek' FROM date)::INTEGER AS day_of_week,
    STRFTIME(date, '%A') AS day_name,
    (EXTRACT('dayofweek' FROM date) IN (0, 6)) AS is_weekend
FROM calendar
ORDER BY date;


-- ------------------------------------------------------------------------------
-- 3. Customer Dimension (dim_customer)
-- Unique customer account profiles with acquisition cohorts and historical metrics.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_customer AS
WITH cust_orders AS (
    SELECT
        customer_id,
        MODE(country) AS country,
        MIN(order_date) AS first_order_date,
        MIN(invoice_date) AS first_order_timestamp,
        DATE_TRUNC('month', MIN(order_date))::DATE AS first_cohort_month,
        MAX(order_date) AS last_order_date,
        MAX(invoice_date) AS last_order_timestamp,
        COUNT(DISTINCT invoice) AS total_orders,
        SUM(quantity) AS total_items,
        SUM(line_total) AS total_revenue
    FROM clean_sales
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.country,
    c.first_order_date,
    c.first_order_timestamp,
    c.first_cohort_month,
    c.last_order_date,
    c.last_order_timestamp,
    DATEDIFF('day', c.last_order_date, s.snapshot_date) AS recency_days,
    DATEDIFF('day', c.first_order_date, c.last_order_date) AS customer_lifespan_days,
    c.total_orders,
    c.total_items,
    ROUND(c.total_revenue, 4) AS total_revenue,
    ROUND(c.total_revenue / c.total_orders, 2) AS avg_order_value,
    (c.total_orders > 1) AS is_repeat_customer
FROM cust_orders c
CROSS JOIN config_snapshot s;


-- ------------------------------------------------------------------------------
-- 4. Order Fact Table (fact_orders)
-- Order-grain transaction table summarizing each individual customer invoice.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_orders AS
SELECT
    invoice AS order_id,
    customer_id,
    order_date,
    MIN(invoice_date) AS order_timestamp,
    DATE_TRUNC('month', order_date)::DATE AS order_cohort_month,
    country,
    COUNT(*) AS line_item_count,
    SUM(quantity) AS total_quantity,
    ROUND(SUM(line_total), 4) AS total_revenue
FROM clean_sales
GROUP BY invoice, customer_id, order_date, country;
