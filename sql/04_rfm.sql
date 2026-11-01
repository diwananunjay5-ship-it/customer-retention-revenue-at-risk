-- Customer Retention & Revenue-at-Risk Pipeline: RFM Segmentation
-- Computes customer-level Recency, Frequency, Monetary metrics, assigns quintile/band scores,
-- and classifies each customer account into mutually exclusive behavioral segments.
-- Also incorporates customer-matched returns to compute net revenue, gross EAV, and net EAV.

-- ------------------------------------------------------------------------------
-- 1. Customer RFM Table (customer_rfm)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE customer_rfm AS
WITH cust_returns AS (
    SELECT 
        customer_id, 
        ROUND(SUM(ABS(line_total)), 4) AS returns_amount
    FROM fact_returns
    GROUP BY customer_id
),
base_rfm AS (
    SELECT
        c.customer_id,
        c.country,
        c.first_order_date,
        c.last_order_date,
        c.recency_days,
        c.total_orders AS frequency,
        ROUND(c.total_revenue, 4) AS monetary,
        c.avg_order_value,
        -- R Score (1 to 5): 5 is most recent (lowest recency_days), 1 is least recent (customer_id ASC tie-breaker)
        NTILE(5) OVER (ORDER BY c.recency_days DESC, c.customer_id ASC) AS r_score,
        -- F Score (1 to 5): deterministic fixed bands to prevent arbitrary tie breaks
        CASE 
            WHEN c.total_orders = 1 THEN 1
            WHEN c.total_orders = 2 THEN 2
            WHEN c.total_orders BETWEEN 3 AND 4 THEN 3
            WHEN c.total_orders BETWEEN 5 AND 9 THEN 4
            ELSE 5
        END AS f_score,
        -- M Score (1 to 5): 5 is highest monetary spend, 1 is lowest monetary spend (customer_id ASC tie-breaker)
        NTILE(5) OVER (ORDER BY c.total_revenue ASC, c.customer_id ASC) AS m_score,
        COALESCE(r.returns_amount, 0.0) AS returns_amount
    FROM dim_customer c
    LEFT JOIN cust_returns r ON c.customer_id = r.customer_id
),
scored_rfm AS (
    SELECT
        customer_id,
        country,
        first_order_date,
        last_order_date,
        recency_days,
        frequency,
        monetary,
        ROUND(returns_amount, 2) AS returns_amount,
        ROUND(monetary - returns_amount, 2) AS net_revenue,
        avg_order_value,
        r_score,
        f_score,
        m_score,
        r_score || f_score || m_score AS rfm_cell,
        -- Ordered rules: first match wins (segments remain based on gross monetary)
        CASE 
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'New/Promising'
            WHEN r_score <= 2 AND f_score >= 4 THEN 'Can''t Lose Them'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating/Lost'
            ELSE 'Need Attention'
        END AS segment,
        -- Gross Expected Annual Value
        ROUND(monetary / GREATEST(1.0, DATEDIFF('day', first_order_date, (SELECT snapshot_date FROM config_snapshot)) / 365.0), 2) AS gross_expected_annual_value,
        -- Net Expected Annual Value: MAX(0, net_revenue) / MAX(1, years since first order)
        ROUND(GREATEST(0.0, monetary - returns_amount) / GREATEST(1.0, DATEDIFF('day', first_order_date, (SELECT snapshot_date FROM config_snapshot)) / 365.0), 2) AS net_expected_annual_value,
        -- Backward compatibility alias
        ROUND(GREATEST(0.0, monetary - returns_amount) / GREATEST(1.0, DATEDIFF('day', first_order_date, (SELECT snapshot_date FROM config_snapshot)) / 365.0), 2) AS expected_annual_value
    FROM base_rfm
)
SELECT 
    *,
    (segment IN ('At Risk', 'Can''t Lose Them')) AS is_at_risk
FROM scored_rfm;


-- ------------------------------------------------------------------------------
-- 2. Segment Summary Table (segment_summary)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE segment_summary AS
SELECT
    segment,
    COUNT(*) AS customers,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customer_rfm), 2) AS pct_customers,
    ROUND(SUM(monetary), 2) AS revenue,
    ROUND(SUM(monetary) * 100.0 / (SELECT SUM(monetary) FROM customer_rfm), 2) AS pct_revenue,
    ROUND(AVG(recency_days), 1) AS avg_recency,
    ROUND(AVG(frequency), 1) AS avg_frequency,
    ROUND(AVG(avg_order_value), 2) AS avg_order_value
FROM customer_rfm
GROUP BY segment
ORDER BY revenue DESC;
