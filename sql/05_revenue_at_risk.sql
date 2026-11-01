-- Customer Retention & Revenue-at-Risk Pipeline: Phase 5 Revenue-at-Risk & Win-back Scenarios
-- Quantifies annualized enterprise revenue exposure from dormant high-value accounts,
-- models 5%, 10%, 15% win-back recovery scenarios, and generates a prioritized Top 50 Action List.

-- ------------------------------------------------------------------------------
-- 1. Revenue-at-Risk Summary Table (revenue_at_risk_summary)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE revenue_at_risk_summary AS
WITH segment_rar AS (
    SELECT
        segment,
        COUNT(*) AS customer_count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customer_rfm), 2) AS pct_of_customers,
        ROUND(SUM(monetary), 2) AS historical_revenue,
        ROUND(SUM(expected_annual_value), 2) AS revenue_at_risk,
        ROUND(SUM(expected_annual_value) * 100.0 / (SELECT SUM(expected_annual_value) FROM customer_rfm), 2) AS revenue_at_risk_pct
    FROM customer_rfm
    WHERE is_at_risk = TRUE
    GROUP BY segment
),
total_rar AS (
    SELECT
        'Total Revenue-at-Risk' AS segment,
        COUNT(*) AS customer_count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customer_rfm), 2) AS pct_of_customers,
        ROUND(SUM(monetary), 2) AS historical_revenue,
        ROUND(SUM(expected_annual_value), 2) AS revenue_at_risk,
        ROUND(SUM(expected_annual_value) * 100.0 / (SELECT SUM(expected_annual_value) FROM customer_rfm), 2) AS revenue_at_risk_pct
    FROM customer_rfm
    WHERE is_at_risk = TRUE
)
SELECT * FROM segment_rar
UNION ALL
SELECT * FROM total_rar;


-- ------------------------------------------------------------------------------
-- 2. Win-Back Scenarios Sensitivity Table (win_back_scenarios)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE win_back_scenarios AS
WITH rates AS (
    SELECT 0.05 AS rate_val, '5%' AS recovery_rate
    UNION ALL SELECT 0.10, '10%'
    UNION ALL SELECT 0.15, '15%'
),
scopes AS (
    SELECT 
        'Can''t Lose Them Only' AS scope,
        COUNT(*) AS customers_targeted,
        ROUND(SUM(expected_annual_value), 2) AS revenue_at_risk_base
    FROM customer_rfm WHERE segment = 'Can''t Lose Them'
    UNION ALL
    SELECT 
        'At Risk Only' AS scope,
        COUNT(*) AS customers_targeted,
        ROUND(SUM(expected_annual_value), 2) AS revenue_at_risk_base
    FROM customer_rfm WHERE segment = 'At Risk'
    UNION ALL
    SELECT 
        'Both (Total At-Risk)' AS scope,
        COUNT(*) AS customers_targeted,
        ROUND(SUM(expected_annual_value), 2) AS revenue_at_risk_base
    FROM customer_rfm WHERE is_at_risk = TRUE
)
SELECT
    r.recovery_rate,
    s.scope,
    s.customers_targeted,
    s.revenue_at_risk_base,
    ROUND(s.revenue_at_risk_base * r.rate_val, 2) AS recovered_revenue,
    'scenario assumptions, not forecasts' AS notes
FROM rates r
CROSS JOIN scopes s
ORDER BY r.rate_val, s.scope;


-- ------------------------------------------------------------------------------
-- 3. Top 50 At-Risk Accounts Action List (action_list)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE action_list AS
SELECT
    customer_id,
    country,
    segment,
    last_order_date,
    recency_days,
    frequency AS order_count,
    ROUND(monetary, 2) AS total_revenue,
    expected_annual_value,
    CASE 
        WHEN segment = 'Can''t Lose Them' THEN 'personal call + loyalty offer'
        WHEN segment = 'At Risk' THEN 'win-back email with a discount'
        ELSE 'general outreach'
    END AS suggested_action
FROM customer_rfm
WHERE is_at_risk = TRUE
ORDER BY expected_annual_value DESC
LIMIT 50;
