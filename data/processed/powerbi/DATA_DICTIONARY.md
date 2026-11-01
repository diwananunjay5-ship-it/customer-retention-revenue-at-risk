# Power BI Data Dictionary & Schema Specification

> **Customer Retention & Revenue-at-Risk Analytical Star Schema**  
> *Production-grade, snake_case data model exports formatted for direct import into Power BI.*

---

## 1. Table Inventory

| File Name | Grain / Entity | Row Count | Primary Key | Description |
| :--- | :--- | :---: | :--- | :--- |
| `dim_customer.csv` | 1 row per unique customer | 5,853 | `customer_id` | Master customer dimension containing RFM scores, segments, tenure, gross spend, returns, and Net Expected Annual Value. |
| `fact_orders.csv` | 1 row per distinct order invoice | 36,600 | `invoice_no` | Transactional fact table tracking order dates, revenue, and item units linked to customer accounts. |
| `dim_date.csv` | 1 row per calendar day | 761 | `date` | Standard calendar dimension spanning the full 2-year analysis window (2009-12-01 to 2011-12-31). |
| `cohort_retention.csv` | 1 row per cohort and month index | 325 | `cohort_month` + `month_index` | Acquisition cohort retention table tracking active accounts and repeat rates over elapsed months. |
| `segment_summary.csv` | 1 row per RFM segment | 7 | `segment` | Aggregate KPI summary table detailing customer counts, revenue share, and average RFM metrics by segment. |
| `revenue_at_risk_summary.csv` | 1 row per at-risk segment + total | 3 | `segment` | Executive annualized Revenue-at-Risk summary isolating gross vs. net exposure after customer returns. |
| `win_back_scenarios.csv` | 1 row per rate and scope combo | 9 | `recovery_rate` + `scope` | Sensitivity model estimating recoverable annual revenue at 5%, 10%, and 15% win-back rates. |
| `action_list.csv` | 1 row per prioritized account | 50 | `customer_id` | Prioritized outreach target list of top 50 dormant high-value accounts ranked by Net Expected Annual Value. |

---

## 2. Column-by-Column Data Dictionary

### `dim_customer.csv`
- `customer_id`: Unique integer customer account identifier (Primary Key, integer).
- `country`: Geographic market where the customer placed the majority of their orders (string).
- `first_order_date`: Calendar date of the customer's earliest recorded purchase in YYYY-MM-DD format (date).
- `last_order_date`: Calendar date of the customer's most recent purchase in YYYY-MM-DD format (date).
- `recency_days`: Number of days elapsed between last_order_date and the analysis snapshot date 2011-12-10 (integer).
- `order_count`: Total number of distinct completed purchase invoices placed across the customer's lifespan (integer).
- `total_revenue`: Total cumulative gross merchandise spend across all valid orders before deductions (decimal, GBP).
- `returns_amount`: Total cumulative value of refunded merchandise across cancellation invoices (decimal, GBP).
- `net_revenue`: Total net customer spend calculated as gross total_revenue minus returns_amount (decimal, GBP).
- `gross_expected_annual_value`: Annualized run-rate gross value computed as total_revenue / MAX(1, years since first order) (decimal, GBP).
- `net_expected_annual_value`: Annualized run-rate net recurring value computed as MAX(0, net_revenue) / MAX(1, years) (decimal, GBP).
- `r_score`: Recency quintile score from 1 (dormant) to 5 (most recent purchase) with customer_id tie-breaking (integer).
- `f_score`: Frequency score from 1 (1 order) to 5 (10+ orders) based on deterministic fixed integer bands (integer).
- `m_score`: Monetary quintile score from 1 (lowest gross spend) to 5 (highest gross spend) (integer).
- `segment`: Behavioral customer segment classification based on combined RFM score business rules (string).
- `segment_order`: Natural presentation sort order (1=Champions, 2=Loyal, 3=Can't Lose Them, 4=At Risk, 5=Need Attention, 6=New/Promising, 7=Hibernating/Lost) (integer).
- `is_at_risk`: Boolean flag set to TRUE strictly for accounts in 'At Risk' or 'Can't Lose Them' segments (boolean).

### `fact_orders.csv`
- `customer_id`: Integer customer identifier linking the order to dim_customer (Foreign Key, integer).
- `invoice_no`: Unique order invoice code identifying the distinct order transaction (Primary Key, string).
- `order_date`: Calendar date the order was completed in YYYY-MM-DD format (date).
- `order_revenue`: Total merchandise invoice revenue in British Pounds rounded to 2 decimal places (decimal, GBP).
- `units`: Total physical units of merchandise purchased across all line items in the invoice (integer).

### `dim_date.csv`
- `date`: Calendar date in YYYY-MM-DD format representing the day dimension grain (Primary Key, date).
- `year`: Four-digit calendar year (integer).
- `quarter`: Calendar quarter number from 1 to 4 (integer).
- `month_no`: Calendar month number from 1 to 12 (integer).
- `month_name`: Full text name of the month (e.g., December, January) (string).
- `month_year`: Formatted abbreviation of month and four-digit year (e.g., Dec 2009) (string).
- `cohort_month`: First day of the calendar month in YYYY-MM-DD format (date).
- `day_of_month`: Day of the month from 1 to 31 (integer).
- `day_name`: Full name of the day of the week (e.g., Monday, Tuesday) (string).
- `is_weekend`: Boolean flag indicating whether the date falls on Saturday or Sunday (boolean).

### `cohort_retention.csv`
- `cohort_month`: First day of the customer acquisition cohort month in YYYY-MM-DD format (date).
- `cohort_label`: Human-readable cohort label indicating acquisition month and legacy data caveats (string).
- `month_index`: Elapsed months since customer acquisition, starting at 0 for the acquisition month (integer).
- `order_cohort_month`: Calendar month in which the repeat orders took place in YYYY-MM-DD format (date).
- `is_partial_month`: Boolean flag identifying partial calendar months truncated by data collection boundaries (boolean).
- `cohort_size`: Total count of unique customer accounts acquired during cohort_month (integer).
- `active_customers`: Count of cohort customers who placed at least one purchase order during month_index (integer).
- `retention_pct`: Percentage of the original cohort active in month_index (active_customers / cohort_size * 100) (decimal).
- `cohort_revenue`: Total merchandise revenue generated by cohort members during month_index (decimal, GBP).

### `segment_summary.csv`
- `segment`: Name of the RFM behavioral customer segment (Primary Key, string).
- `segment_order`: Integer presentation sort key matching the standard hierarchy 1 to 7 (integer).
- `customers`: Number of unique customer accounts classified into the segment (integer).
- `pct_customers`: Percentage of the total customer base belonging to the segment (decimal).
- `revenue`: Cumulative gross merchandise revenue generated by the segment before returns (decimal, GBP).
- `pct_revenue`: Percentage of enterprise gross merchandise revenue contributed by the segment (decimal).
- `avg_recency`: Mean days elapsed since last purchase across accounts in the segment (decimal, days).
- `avg_frequency`: Mean lifetime completed orders per customer account within the segment (decimal, orders).
- `avg_order_value`: Mean revenue per completed order invoice within the segment (decimal, GBP).

### `revenue_at_risk_summary.csv`
- `segment`: Name of the evaluated at-risk segment or 'Total Revenue-at-Risk' aggregate line (Primary Key, string).
- `customer_count`: Total number of dormant high-value customer accounts within the scope (integer).
- `pct_of_customers`: Proportion of total customer base represented by accounts in the scope (decimal).
- `gross_revenue`: Historical cumulative gross sales generated by scoped accounts before returns (decimal, GBP).
- `returns_amount`: Cumulative refunds and cancellations attributed to scoped accounts (decimal, GBP).
- `net_revenue`: Historical net sales generated by scoped accounts after deducting returns (decimal, GBP).
- `gross_revenue_at_risk`: Baseline annualized run-rate exposure calculated using gross revenue (decimal, GBP).
- `revenue_at_risk`: Official annualized run-rate exposure calculated using net revenue post-cancellations (decimal, GBP).
- `revenue_at_risk_pct`: Proportion of enterprise-wide net expected annual customer value at risk (decimal).

### `win_back_scenarios.csv`
- `recovery_rate`: Target win-back customer reactivation benchmark (5%, 10%, or 15%) (string).
- `scope`: Customer segment target cohort evaluated (Can't Lose Them Only, At Risk Only, Both Combined) (string).
- `customers_targeted`: Total number of dormant accounts in the evaluated segment scope (integer).
- `revenue_at_risk_base`: Total annualized Net Revenue-at-Risk available for recovery within the scope (decimal, GBP).
- `recovered_revenue`: Estimated annual recurring revenue recaptured at the given recovery rate (decimal, GBP).
- `notes`: Audit classification disclaimer noting numbers are scenario assumptions, not forecasts (string).

### `action_list.csv`
- `customer_id`: Unique integer customer account identifier (Primary Key, integer).
- `country`: Primary geographic market of the customer (string).
- `segment`: RFM segment classification ('Can't Lose Them' or 'At Risk') (string).
- `last_order_date`: Date of the customer's last purchase in YYYY-MM-DD format (date).
- `recency_days`: Days elapsed since last order as of snapshot date 2011-12-10 (integer).
- `order_count`: Total lifetime completed orders placed by the customer (integer).
- `total_revenue`: Lifetime gross merchandise spend before returns (decimal, GBP).
- `returns_amount`: Total value of refund and cancellation invoices matched to the customer (decimal, GBP).
- `net_revenue`: Lifetime net spend (total_revenue minus returns_amount) (decimal, GBP).
- `return_pct`: Returns expressed as a percentage of gross spend (decimal).
- `returns_flag`: Boolean flag indicating if customer returns exceed 50% of gross spend (boolean).
- `gross_expected_annual_value`: Historical gross expected annual spend run-rate (decimal, GBP).
- `net_expected_annual_value`: Net expected annual value run-rate used to rank prioritization (decimal, GBP).
- `suggested_action`: Prescribed outreach play ('personal call + loyalty offer' or 'win-back email with a discount') (string).

---
*Generated automatically by `src/powerbi.py` as part of Phase 6 data modeling.*
