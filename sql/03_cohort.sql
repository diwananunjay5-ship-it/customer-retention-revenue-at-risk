-- ==============================================================================
-- 03_cohort.sql
-- Customer Retention & Revenue-at-Risk Pipeline: Monthly Cohort Retention Matrix
-- Computes customer retention and revenue decay by acquisition cohort over time.
-- ==============================================================================

CREATE OR REPLACE TABLE cohort_retention AS
WITH customer_cohort AS (
    SELECT 
        customer_id,
        first_cohort_month AS cohort_month
    FROM dim_customer
),
cohort_sizes AS (
    SELECT 
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_size
    FROM customer_cohort
    GROUP BY cohort_month
),
customer_activities AS (
    SELECT 
        o.customer_id,
        c.cohort_month,
        o.order_cohort_month,
        (EXTRACT('year' FROM o.order_cohort_month) - EXTRACT('year' FROM c.cohort_month)) * 12 + 
        (EXTRACT('month' FROM o.order_cohort_month) - EXTRACT('month' FROM c.cohort_month)) AS month_index,
        SUM(o.total_revenue) AS monthly_revenue
    FROM fact_orders o
    JOIN customer_cohort c ON o.customer_id = c.customer_id
    GROUP BY o.customer_id, c.cohort_month, o.order_cohort_month
)
SELECT 
    ca.cohort_month,
    CASE 
        WHEN ca.cohort_month = '2009-12-01'::DATE THEN 'Dec 2009 (includes existing customers)'
        ELSE STRFTIME(ca.cohort_month, '%b %Y')
    END AS cohort_label,
    ca.month_index,
    ca.order_cohort_month,
    (ca.order_cohort_month = '2011-12-01'::DATE) AS is_partial_month,
    cs.cohort_size,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(COUNT(DISTINCT ca.customer_id) * 100.0 / cs.cohort_size, 2) AS retention_pct,
    ROUND(SUM(ca.monthly_revenue), 2) AS cohort_revenue
FROM customer_activities ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
GROUP BY ca.cohort_month, ca.month_index, ca.order_cohort_month, cs.cohort_size
ORDER BY ca.cohort_month, ca.month_index;
