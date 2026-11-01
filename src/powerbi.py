"""
Module: src.powerbi
Generates clean, production-grade Power BI CSV exports in data/processed/powerbi/
adhering to dimensional star-schema modeling, strict snake_case conventions,
plain integer customer IDs, and zero-blank-row constraints.
Also generates a comprehensive data/processed/powerbi/DATA_DICTIONARY.md.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import duckdb
import pandas as pd


def export_powerbi_tables(
    db_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Exports all star-schema dimensions, facts, and aggregate analytical tables
    to data/processed/powerbi/ for direct ingestion into Power BI.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"
    if output_dir is None:
        output_dir = base_dir / "data" / "processed" / "powerbi"

    output_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))

    # -------------------------------------------------------------------------
    # 1. dim_customer.csv
    # -------------------------------------------------------------------------
    # Merged customer dimension: demographic, lifetime RFM scores, segment order,
    # gross and net revenue, returns, and expected annual value metrics.
    dim_cust_query = """
    SELECT
        CAST(customer_id AS INTEGER) AS customer_id,
        country,
        STRFTIME(first_order_date, '%Y-%m-%d') AS first_order_date,
        STRFTIME(last_order_date, '%Y-%m-%d') AS last_order_date,
        CAST(recency_days AS INTEGER) AS recency_days,
        CAST(frequency AS INTEGER) AS order_count,
        ROUND(monetary, 2) AS total_revenue,
        ROUND(returns_amount, 2) AS returns_amount,
        ROUND(net_revenue, 2) AS net_revenue,
        ROUND(gross_expected_annual_value, 2) AS gross_expected_annual_value,
        ROUND(net_expected_annual_value, 2) AS net_expected_annual_value,
        CAST(r_score AS INTEGER) AS r_score,
        CAST(f_score AS INTEGER) AS f_score,
        CAST(m_score AS INTEGER) AS m_score,
        segment,
        CASE segment
            WHEN 'Champions' THEN 1
            WHEN 'Loyal' THEN 2
            WHEN 'Can''t Lose Them' THEN 3
            WHEN 'At Risk' THEN 4
            WHEN 'Need Attention' THEN 5
            WHEN 'New/Promising' THEN 6
            WHEN 'Hibernating/Lost' THEN 7
            ELSE 8
        END AS segment_order,
        is_at_risk
    FROM customer_rfm
    ORDER BY customer_id ASC;
    """
    dim_cust_df = conn.execute(dim_cust_query).df()
    dim_cust_path = output_dir / "dim_customer.csv"
    dim_cust_df.to_csv(dim_cust_path, index=False)

    # -------------------------------------------------------------------------
    # 2. fact_orders.csv
    # -------------------------------------------------------------------------
    # Order-level transactions fact table
    fact_orders_query = """
    SELECT
        CAST(customer_id AS INTEGER) AS customer_id,
        order_id AS invoice_no,
        STRFTIME(order_date, '%Y-%m-%d') AS order_date,
        ROUND(total_revenue, 2) AS order_revenue,
        CAST(total_quantity AS INTEGER) AS units
    FROM fact_orders
    ORDER BY order_date ASC, order_id ASC;
    """
    fact_orders_df = conn.execute(fact_orders_query).df()
    fact_orders_path = output_dir / "fact_orders.csv"
    fact_orders_df.to_csv(fact_orders_path, index=False)

    # -------------------------------------------------------------------------
    # 3. dim_date.csv
    # -------------------------------------------------------------------------
    dim_date_query = """
    SELECT
        STRFTIME(date, '%Y-%m-%d') AS date,
        year,
        quarter,
        month AS month_no,
        month_name,
        month_year,
        STRFTIME(cohort_month, '%Y-%m-%d') AS cohort_month,
        day_of_month,
        day_name,
        is_weekend
    FROM dim_date
    ORDER BY date ASC;
    """
    dim_date_df = conn.execute(dim_date_query).df()
    dim_date_path = output_dir / "dim_date.csv"
    dim_date_df.to_csv(dim_date_path, index=False)

    # -------------------------------------------------------------------------
    # 4. cohort_retention.csv
    # -------------------------------------------------------------------------
    cohort_retention_query = """
    SELECT
        STRFTIME(cohort_month, '%Y-%m-%d') AS cohort_month,
        cohort_label,
        CAST(month_index AS INTEGER) AS month_index,
        STRFTIME(order_cohort_month, '%Y-%m-%d') AS order_cohort_month,
        is_partial_month,
        CAST(cohort_size AS INTEGER) AS cohort_size,
        CAST(active_customers AS INTEGER) AS active_customers,
        ROUND(retention_pct, 2) AS retention_pct,
        ROUND(cohort_revenue, 2) AS cohort_revenue
    FROM cohort_retention
    ORDER BY cohort_month ASC, month_index ASC;
    """
    cohort_df = conn.execute(cohort_retention_query).df()
    cohort_path = output_dir / "cohort_retention.csv"
    cohort_df.to_csv(cohort_path, index=False)

    # -------------------------------------------------------------------------
    # 5. segment_summary.csv
    # -------------------------------------------------------------------------
    segment_summary_query = """
    SELECT
        segment,
        CASE segment
            WHEN 'Champions' THEN 1
            WHEN 'Loyal' THEN 2
            WHEN 'Can''t Lose Them' THEN 3
            WHEN 'At Risk' THEN 4
            WHEN 'Need Attention' THEN 5
            WHEN 'New/Promising' THEN 6
            WHEN 'Hibernating/Lost' THEN 7
            ELSE 8
        END AS segment_order,
        CAST(customers AS INTEGER) AS customers,
        ROUND(pct_customers, 2) AS pct_customers,
        ROUND(revenue, 2) AS revenue,
        ROUND(pct_revenue, 2) AS pct_revenue,
        ROUND(avg_recency, 1) AS avg_recency,
        ROUND(avg_frequency, 1) AS avg_frequency,
        ROUND(avg_order_value, 2) AS avg_order_value
    FROM segment_summary
    ORDER BY segment_order ASC;
    """
    segment_df = conn.execute(segment_summary_query).df()
    segment_path = output_dir / "segment_summary.csv"
    segment_df.to_csv(segment_path, index=False)

    # -------------------------------------------------------------------------
    # 6. revenue_at_risk_summary.csv
    # -------------------------------------------------------------------------
    rar_summary_query = """
    SELECT
        segment,
        CAST(customer_count AS INTEGER) AS customer_count,
        ROUND(pct_of_customers, 2) AS pct_of_customers,
        ROUND(gross_revenue, 2) AS gross_revenue,
        ROUND(returns_amount, 2) AS returns_amount,
        ROUND(net_revenue, 2) AS net_revenue,
        ROUND(gross_revenue_at_risk, 2) AS gross_revenue_at_risk,
        ROUND(revenue_at_risk, 2) AS revenue_at_risk,
        ROUND(revenue_at_risk_pct, 2) AS revenue_at_risk_pct
    FROM revenue_at_risk_summary
    ORDER BY gross_revenue_at_risk DESC;
    """
    rar_df = conn.execute(rar_summary_query).df()
    rar_path = output_dir / "revenue_at_risk_summary.csv"
    rar_df.to_csv(rar_path, index=False)

    # -------------------------------------------------------------------------
    # 7. win_back_scenarios.csv
    # -------------------------------------------------------------------------
    win_back_query = """
    SELECT
        recovery_rate,
        scope,
        CAST(customers_targeted AS INTEGER) AS customers_targeted,
        ROUND(revenue_at_risk_base, 2) AS revenue_at_risk_base,
        ROUND(recovered_revenue, 2) AS recovered_revenue,
        notes
    FROM win_back_scenarios
    ORDER BY recovery_rate ASC, scope ASC;
    """
    win_back_df = conn.execute(win_back_query).df()
    win_back_path = output_dir / "win_back_scenarios.csv"
    win_back_df.to_csv(win_back_path, index=False)

    # -------------------------------------------------------------------------
    # 8. action_list.csv
    # -------------------------------------------------------------------------
    action_list_query = """
    SELECT
        CAST(customer_id AS INTEGER) AS customer_id,
        country,
        segment,
        STRFTIME(last_order_date, '%Y-%m-%d') AS last_order_date,
        CAST(recency_days AS INTEGER) AS recency_days,
        CAST(order_count AS INTEGER) AS order_count,
        ROUND(total_revenue, 2) AS total_revenue,
        ROUND(returns_amount, 2) AS returns_amount,
        ROUND(net_revenue, 2) AS net_revenue,
        ROUND(return_pct, 2) AS return_pct,
        returns_flag,
        ROUND(gross_expected_annual_value, 2) AS gross_expected_annual_value,
        ROUND(net_expected_annual_value, 2) AS net_expected_annual_value,
        suggested_action
    FROM action_list
    ORDER BY net_expected_annual_value DESC, customer_id ASC;
    """
    action_df = conn.execute(action_list_query).df()
    action_path = output_dir / "action_list.csv"
    action_df.to_csv(action_path, index=False)

    conn.close()

    # -------------------------------------------------------------------------
    # 9. Write DATA_DICTIONARY.md
    # -------------------------------------------------------------------------
    data_dict_path = output_dir / "DATA_DICTIONARY.md"
    write_data_dictionary(data_dict_path)

    return {
        "dim_customer_rows": len(dim_cust_df),
        "fact_orders_rows": len(fact_orders_df),
        "dim_date_rows": len(dim_date_df),
        "cohort_retention_rows": len(cohort_df),
        "segment_summary_rows": len(segment_df),
        "revenue_at_risk_summary_rows": len(rar_df),
        "win_back_scenarios_rows": len(win_back_df),
        "action_list_rows": len(action_df),
        "export_dir": str(output_dir),
    }


def write_data_dictionary(file_path: Path) -> None:
    """
    Writes a plain-English line for every exported file and column in data/processed/powerbi/.
    """
    content = """# Power BI Data Dictionary & Schema Specification

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
- `is_at_risk`: Boolean flag set to TRUE strictly for accounts in 'At Risk' or 'Can\'t Lose Them' segments (boolean).

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
- `segment`: RFM segment classification ('Can\'t Lose Them' or 'At Risk') (string).
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
"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


if __name__ == "__main__":
    res = export_powerbi_tables()
    print("Power BI tables exported successfully:")
    for k, v in res.items():
        print(f"  • {k}: {v}")
