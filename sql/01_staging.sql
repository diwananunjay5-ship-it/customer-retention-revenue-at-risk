-- ==============================================================================
-- 01_staging.sql
-- Customer Retention & Revenue-at-Risk Pipeline: Staging & Hygiene
-- ==============================================================================

-- 1. Deduplication & Initial Type Casting
CREATE OR REPLACE TABLE stg_deduplicated AS
SELECT DISTINCT
    TRIM(Invoice) AS invoice,
    TRIM(StockCode) AS stock_code,
    TRIM(Description) AS description,
    Quantity AS quantity,
    CAST(InvoiceDate AS TIMESTAMP) AS invoice_date,
    CAST(InvoiceDate AS DATE) AS order_date,
    Price AS price,
    CAST("Customer ID" AS BIGINT) AS customer_id,
    TRIM(Country) AS country
FROM raw_retail;

-- 2. Isolate Guest Checkouts (Missing Customer ID)
-- Retained for traffic analysis and audit logging; excluded from customer cohort/RFM modeling.
CREATE OR REPLACE TABLE stg_guest_checkouts AS
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    order_date,
    price,
    ROUND(quantity * price, 4) AS line_total,
    country
FROM stg_deduplicated
WHERE customer_id IS NULL;

-- 3. Identified Customer Transactions
CREATE OR REPLACE TABLE stg_with_customer AS
SELECT *
FROM stg_deduplicated
WHERE customer_id IS NOT NULL;

-- 4. Isolate Cancellations & Returns (Invoices prefixed with 'C')
-- Separated to track return behaviors without contaminating gross sales metrics.
CREATE OR REPLACE TABLE fact_returns AS
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    order_date,
    price,
    ROUND(quantity * price, 4) AS line_total,
    customer_id,
    country
FROM stg_with_customer
WHERE invoice LIKE 'C%' OR invoice LIKE 'c%';

-- 5. Non-Cancellation Transactions
CREATE OR REPLACE TABLE stg_non_cancellations AS
SELECT *
FROM stg_with_customer
WHERE NOT (invoice LIKE 'C%' OR invoice LIKE 'c%');

-- 6. Isolate Invalid Non-Cancellation Records (Quantity <= 0 or Price <= 0)
CREATE OR REPLACE TABLE stg_invalid_records AS
SELECT *
FROM stg_non_cancellations
WHERE quantity <= 0 OR price <= 0;

-- Intermediate Valid Customer Transactions (Positive Quantity & Price)
CREATE OR REPLACE TABLE stg_valid_transactions AS
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    order_date,
    price,
    ROUND(quantity * price, 4) AS line_total,
    customer_id,
    country
FROM stg_non_cancellations
WHERE quantity > 0 AND price > 0;

-- 7. Isolate Non-Product Transactions (Postage, Manual Entries, Discounts, Fees, Bank Charges, Test Codes)
CREATE OR REPLACE TABLE fact_non_products AS
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    order_date,
    price,
    line_total,
    customer_id,
    country
FROM stg_valid_transactions
WHERE UPPER(TRIM(stock_code)) IN ('POST', 'DOT', 'M', 'D', 'CRUK', 'BANK CHARGES', 'AMAZONFEE', 'S', 'B')
   OR UPPER(TRIM(stock_code)) LIKE 'TEST%'
   OR UPPER(TRIM(stock_code)) LIKE 'ADJUST%';

-- 8. Clean Sales Fact Table (Genuine Product Purchases)
CREATE OR REPLACE TABLE clean_sales AS
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    order_date,
    price,
    line_total,
    customer_id,
    country
FROM stg_valid_transactions
WHERE NOT (
    UPPER(TRIM(stock_code)) IN ('POST', 'DOT', 'M', 'D', 'CRUK', 'BANK CHARGES', 'AMAZONFEE', 'S', 'B')
    OR UPPER(TRIM(stock_code)) LIKE 'TEST%'
    OR UPPER(TRIM(stock_code)) LIKE 'ADJUST%'
);
