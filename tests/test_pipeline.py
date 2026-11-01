"""
Tests for Phase 1: Ingestion & Staging Data Integrity
"""

import sys
from pathlib import Path
import pytest
import duckdb

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ingest import find_raw_file, ingest_raw_data
from src.clean import run_clean_pipeline, get_audit_trail


@pytest.fixture(scope="session")
def db_conn(tmp_path_factory):
    """Session fixture creating an in-memory or temp DuckDB instance for tests."""
    temp_dir = tmp_path_factory.mktemp("db_test")
    db_file = temp_dir / "test_retention.duckdb"
    
    # Run the cleaning pipeline into this test database
    res = run_clean_pipeline(db_path=db_file, export_csv=False)
    conn = duckdb.connect(str(db_file))
    yield conn
    conn.close()


def test_raw_file_exists():
    """Verify raw file can be discovered in lowercase path."""
    raw_path = find_raw_file()
    assert raw_path.exists(), f"Raw file {raw_path} must exist"
    assert raw_path.stat().st_size > 0, "Raw file must not be empty"


def test_clean_sales_no_null_customers(db_conn):
    """Verify clean_sales has zero NULL customer IDs."""
    null_cust = db_conn.execute("SELECT COUNT(*) FROM clean_sales WHERE customer_id IS NULL").fetchone()[0]
    assert null_cust == 0, f"clean_sales should have 0 NULL customer IDs, found {null_cust}"


def test_clean_sales_strictly_positive_quantities(db_conn):
    """Verify clean_sales has strictly positive quantities."""
    non_pos = db_conn.execute("SELECT COUNT(*) FROM clean_sales WHERE quantity <= 0").fetchone()[0]
    assert non_pos == 0, f"clean_sales should have no non-positive quantities, found {non_pos}"


def test_clean_sales_strictly_positive_prices(db_conn):
    """Verify clean_sales has strictly positive prices."""
    non_pos = db_conn.execute("SELECT COUNT(*) FROM clean_sales WHERE price <= 0").fetchone()[0]
    assert non_pos == 0, f"clean_sales should have no non-positive prices, found {non_pos}"


def test_clean_sales_no_cancellations(db_conn):
    """Verify clean_sales has no invoices starting with 'C'."""
    c_invoices = db_conn.execute(
        "SELECT COUNT(*) FROM clean_sales WHERE invoice LIKE 'C%' OR invoice LIKE 'c%'"
    ).fetchone()[0]
    assert c_invoices == 0, f"clean_sales should contain zero cancellations, found {c_invoices}"


def test_fact_returns_isolated(db_conn):
    """Verify fact_returns only contains cancellation records."""
    non_c = db_conn.execute(
        "SELECT COUNT(*) FROM fact_returns WHERE NOT (invoice LIKE 'C%' OR invoice LIKE 'c%')"
    ).fetchone()[0]
    assert non_c == 0, f"fact_returns should only contain 'C' invoices, found {non_c}"


def test_clean_sales_no_non_product_codes(db_conn):
    """Verify clean_sales excludes all non-product service and adjustment stock codes."""
    non_prod_count = db_conn.execute("""
        SELECT COUNT(*) 
        FROM clean_sales 
        WHERE UPPER(TRIM(stock_code)) IN ('POST', 'DOT', 'M', 'D', 'CRUK', 'BANK CHARGES', 'AMAZONFEE', 'S', 'B')
           OR UPPER(TRIM(stock_code)) LIKE 'TEST%'
           OR UPPER(TRIM(stock_code)) LIKE 'ADJUST%'
    """).fetchone()[0]
    assert non_prod_count == 0, f"clean_sales should contain zero non-product codes, found {non_prod_count}"


def test_fact_non_products_isolated(db_conn):
    """Verify fact_non_products accurately captured isolated service/adjustment items."""
    non_prod_rows = db_conn.execute("SELECT COUNT(*) FROM fact_non_products").fetchone()[0]
    assert non_prod_rows == 2581, f"fact_non_products should have 2,581 records, found {non_prod_rows}"


def test_line_total_calculation(db_conn):
    """Verify line_total accurately matches quantity * price."""
    mismatches = db_conn.execute(
        "SELECT COUNT(*) FROM clean_sales WHERE ABS(line_total - ROUND(quantity * price, 4)) > 0.0001"
    ).fetchone()[0]
    assert mismatches == 0, f"Found {mismatches} line_total computation mismatches in clean_sales"


def test_audit_reconciliation_identities(db_conn):
    """Verify step-by-step arithmetic reconciliation across all 5 cleaning steps."""
    steps = get_audit_trail(db_conn)
    # Step 1: Raw - Dedup = dup_removed
    assert steps[1]["rows_before"] - steps[1]["rows_delta"] == steps[1]["rows_after"]
    # Step 2: Dedup - Guest = With Customer
    assert steps[2]["rows_before"] - steps[2]["rows_delta"] == steps[2]["rows_after"]
    # Step 3: With Customer - Returns = Non-cancellations
    assert steps[3]["rows_before"] - steps[3]["rows_delta"] == steps[3]["rows_after"]
    # Step 4: Non-cancellations - Invalid = Valid Transactions
    assert steps[4]["rows_before"] - steps[4]["rows_delta"] == steps[4]["rows_after"]
    # Step 5: Valid Transactions - Non-Products = Clean Sales
    assert steps[5]["rows_before"] - steps[5]["rows_delta"] == steps[5]["rows_after"]


# ==============================================================================
# Phase 2: Dimensional Star Schema Tests
# ==============================================================================

def test_snapshot_date_definition(db_conn):
    """Verify snapshot date is centrally defined as MAX(order_date) + 1 day (2011-12-10)."""
    snap_date = db_conn.execute("SELECT snapshot_date FROM config_snapshot").fetchone()[0]
    expected_date = db_conn.execute("SELECT (MAX(order_date) + INTERVAL 1 DAY)::DATE FROM clean_sales").fetchone()[0]
    assert snap_date == expected_date, f"Snapshot date {snap_date} does not match max + 1 day {expected_date}"
    assert str(snap_date) == "2011-12-10", f"Expected snapshot date 2011-12-10, got {snap_date}"


def test_fact_orders_row_count(db_conn):
    """Verify fact_orders contains exactly 36,600 unique orders."""
    order_count = db_conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    assert order_count == 36600, f"fact_orders should have 36,600 rows, found {order_count}"


def test_dim_customer_row_count(db_conn):
    """Verify dim_customer contains exactly 5,853 unique customers."""
    cust_count = db_conn.execute("SELECT COUNT(*) FROM dim_customer").fetchone()[0]
    assert cust_count == 5853, f"dim_customer should have 5,853 rows, found {cust_count}"


def test_dim_date_coverage(db_conn):
    """Verify dim_date spans 2009-12-01 through 2011-12-31 (761 contiguous calendar days)."""
    date_count = db_conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
    min_date = db_conn.execute("SELECT MIN(date) FROM dim_date").fetchone()[0]
    max_date = db_conn.execute("SELECT MAX(date) FROM dim_date").fetchone()[0]
    assert date_count == 761, f"dim_date should have 761 days, found {date_count}"
    assert str(min_date) == "2009-12-01", f"Expected min date 2009-12-01, got {min_date}"
    assert str(max_date) == "2011-12-31", f"Expected max date 2011-12-31, got {max_date}"


def test_revenue_reconciliation_exact(db_conn):
    """Verify total revenue in fact_orders matches total revenue in clean_sales exactly (£17,081,128.74)."""
    rev_clean = db_conn.execute("SELECT ROUND(SUM(line_total), 2) FROM clean_sales").fetchone()[0]
    rev_fact = db_conn.execute("SELECT ROUND(SUM(total_revenue), 2) FROM fact_orders").fetchone()[0]
    assert rev_clean == 17081128.74, f"clean_sales revenue £{rev_clean} does not match expected £17,081,128.74"
    assert rev_fact == rev_clean, f"fact_orders revenue £{rev_fact} must exactly match clean_sales £{rev_clean}"


def test_fact_orders_referential_integrity(db_conn):
    """Verify all customer IDs in fact_orders exist in dim_customer."""
    orphans = db_conn.execute("""
        SELECT COUNT(*)
        FROM fact_orders fo
        LEFT JOIN dim_customer dc ON fo.customer_id = dc.customer_id
        WHERE dc.customer_id IS NULL
    """).fetchone()[0]
    assert orphans == 0, f"Found {orphans} orphaned orders in fact_orders"


# ==============================================================================
# Phase 3: Cohort Retention Tests
# ==============================================================================

def test_cohort_month_zero_is_100_percent(db_conn):
    """Verify month_index 0 is exactly 100.0% for every cohort."""
    non_100 = db_conn.execute("""
        SELECT COUNT(*) 
        FROM cohort_retention 
        WHERE month_index = 0 AND ABS(retention_pct - 100.0) > 0.001
    """).fetchone()[0]
    assert non_100 == 0, f"Found {non_100} cohorts where month_index 0 is not 100%"


def test_cohort_retention_never_exceeds_100_percent(db_conn):
    """Verify retention rate is never above 100.0% or negative."""
    invalid = db_conn.execute("""
        SELECT COUNT(*) 
        FROM cohort_retention 
        WHERE retention_pct > 100.0 OR retention_pct < 0.0
    """).fetchone()[0]
    assert invalid == 0, f"Found {invalid} records with retention > 100% or < 0%"


def test_cohort_total_customers_reconciles(db_conn):
    """Verify sum of cohort sizes across all cohorts matches dim_customer (5,853)."""
    tot_cohort_size = db_conn.execute("""
        SELECT SUM(cohort_size) 
        FROM cohort_retention 
        WHERE month_index = 0
    """).fetchone()[0]
    assert tot_cohort_size == 5853, f"Total cohort size {tot_cohort_size} must equal 5,853"


def test_cohort_dec_2009_label(db_conn):
    """Verify December 2009 cohort is labeled with existing customer caveat."""
    label = db_conn.execute("""
        SELECT DISTINCT cohort_label 
        FROM cohort_retention 
        WHERE cohort_month = '2009-12-01'::DATE
    """).fetchone()[0]
    assert label == "Dec 2009 (includes existing customers)", f"Unexpected label: {label}"


def test_cohort_partial_month_flag(db_conn):
    """Verify December 2011 is accurately flagged as partial month."""
    partial_months = db_conn.execute("""
        SELECT DISTINCT order_cohort_month 
        FROM cohort_retention 
        WHERE is_partial_month = TRUE
    """).fetchall()
    assert len(partial_months) == 1
    assert str(partial_months[0][0]) == "2011-12-01"


# ==============================================================================
# Phase 4: RFM Segmentation Tests
# ==============================================================================

def test_rfm_customer_count(db_conn):
    """Verify customer_rfm contains exactly 5,853 unique customers."""
    cust_count = db_conn.execute("SELECT COUNT(*) FROM customer_rfm").fetchone()[0]
    assert cust_count == 5853, f"customer_rfm should have 5,853 rows, found {cust_count}"


def test_rfm_scores_range_1_to_5(db_conn):
    """Verify r_score, f_score, and m_score are strictly integers between 1 and 5."""
    invalid = db_conn.execute("""
        SELECT COUNT(*)
        FROM customer_rfm
        WHERE r_score NOT BETWEEN 1 AND 5
           OR f_score NOT BETWEEN 1 AND 5
           OR m_score NOT BETWEEN 1 AND 5
    """).fetchone()[0]
    assert invalid == 0, f"Found {invalid} customers with RFM scores outside 1-5"


def test_rfm_every_customer_has_exactly_one_valid_segment(db_conn):
    """Verify every customer has exactly one non-null segment belonging to defined taxonomy."""
    valid_segments = {
        "Champions", "Loyal", "New/Promising", "Can't Lose Them",
        "At Risk", "Hibernating/Lost", "Need Attention"
    }
    segments = db_conn.execute("""
        SELECT DISTINCT segment, COUNT(*) 
        FROM customer_rfm 
        GROUP BY segment
    """).fetchall()

    total_segmented = sum(s[1] for s in segments)
    assert total_segmented == 5853, f"Total segmented customers {total_segmented} must equal 5,853"

    for seg_name, _ in segments:
        assert seg_name in valid_segments, f"Unexpected segment name: {seg_name}"


def test_rfm_segment_summary_reconciles_counts_and_revenue(db_conn):
    """Verify segment_summary sums to 5,853 customers and matches total revenue (£17,081,128.74)."""
    summary_stats = db_conn.execute("""
        SELECT 
            SUM(customers) AS total_customers,
            ROUND(SUM(revenue), 2) AS total_revenue
        FROM segment_summary
    """).fetchone()

    total_rfm_rev = db_conn.execute("SELECT ROUND(SUM(monetary), 2) FROM customer_rfm").fetchone()[0]

    assert summary_stats[0] == 5853, f"Segment summary customer sum {summary_stats[0]} != 5,853"
    assert total_rfm_rev == 17081128.74, f"customer_rfm total revenue £{total_rfm_rev} != £17,081,128.74"
    assert abs(summary_stats[1] - 17081128.74) <= 0.02, f"Segment summary revenue £{summary_stats[1]} differs by more than 1p from £17,081,128.74"


# ==============================================================================
# Phase 5: Revenue-at-Risk & Win-Back Scenario Tests
# ==============================================================================

def test_is_at_risk_only_includes_two_segments(db_conn):
    """Verify is_at_risk flag is TRUE strictly and only for 'At Risk' and 'Can''t Lose Them'."""
    invalid_flagged = db_conn.execute("""
        SELECT COUNT(*)
        FROM customer_rfm
        WHERE is_at_risk = TRUE
          AND segment NOT IN ('At Risk', 'Can''t Lose Them')
    """).fetchone()[0]
    assert invalid_flagged == 0, f"Found {invalid_flagged} customers flagged as at-risk outside target segments"

    unflagged_target = db_conn.execute("""
        SELECT COUNT(*)
        FROM customer_rfm
        WHERE segment IN ('At Risk', 'Can''t Lose Them')
          AND is_at_risk = FALSE
    """).fetchone()[0]
    assert unflagged_target == 0, f"Found {unflagged_target} target segment customers not flagged as is_at_risk"

    total_at_risk = db_conn.execute("SELECT COUNT(*) FROM customer_rfm WHERE is_at_risk = TRUE").fetchone()[0]
    expected_at_risk_sum = db_conn.execute("""
        SELECT COUNT(*) FROM customer_rfm WHERE segment IN ('At Risk', 'Can''t Lose Them')
    """).fetchone()[0]
    assert total_at_risk == expected_at_risk_sum, f"is_at_risk count {total_at_risk} != target segment sum {expected_at_risk_sum}"
    assert total_at_risk > 0, "At least one at-risk customer must be identified"


def test_revenue_at_risk_sum_matches_action_logic(db_conn):
    """Verify Revenue-at-Risk in summary equals the sum of net_expected_annual_value for is_at_risk customers."""
    summary_rar = db_conn.execute("""
        SELECT revenue_at_risk, gross_revenue_at_risk
        FROM revenue_at_risk_summary 
        WHERE segment = 'Total Revenue-at-Risk'
    """).fetchone()

    calc_net_rar = db_conn.execute("""
        SELECT ROUND(SUM(net_expected_annual_value), 2)
        FROM customer_rfm
        WHERE is_at_risk = TRUE
    """).fetchone()[0]

    calc_gross_rar = db_conn.execute("""
        SELECT ROUND(SUM(gross_expected_annual_value), 2)
        FROM customer_rfm
        WHERE is_at_risk = TRUE
    """).fetchone()[0]

    assert summary_rar[0] == calc_net_rar, f"Summary Net RAR (£{summary_rar[0]}) != Customer RFM Net RAR sum (£{calc_net_rar})"
    assert summary_rar[1] == calc_gross_rar, f"Summary Gross RAR (£{summary_rar[1]}) != Customer RFM Gross RAR sum (£{calc_gross_rar})"
    assert summary_rar[0] > 0, "Net Revenue-at-Risk must be greater than zero"


def test_net_revenue_at_risk_not_above_gross(db_conn):
    """Verify net Revenue-at-Risk is not above gross Revenue-at-Risk enterprise-wide and per segment."""
    rows = db_conn.execute("""
        SELECT segment, gross_revenue_at_risk, revenue_at_risk 
        FROM revenue_at_risk_summary
    """).fetchall()
    for seg, gross_rar, net_rar in rows:
        assert net_rar <= gross_rar, f"Net RAR (£{net_rar}) exceeds gross RAR (£{gross_rar}) for segment {seg}"


def test_no_negative_net_expected_annual_value(db_conn):
    """Verify no customer has a negative net_expected_annual_value (floored at 0)."""
    neg_count = db_conn.execute("""
        SELECT COUNT(*) 
        FROM customer_rfm 
        WHERE net_expected_annual_value < 0
    """).fetchone()[0]
    assert neg_count == 0, f"Found {neg_count} customers with negative net_expected_annual_value"


def test_win_back_recovered_revenue_arithmetic(db_conn):
    """Verify win-back recovered revenue equals Revenue-at-Risk base times the recovery rate (5%, 10%, 15%)."""
    scenarios = db_conn.execute("""
        SELECT recovery_rate, scope, revenue_at_risk_base, recovered_revenue
        FROM win_back_scenarios
    """).fetchall()

    assert len(scenarios) == 9, f"Expected 9 scenario combinations (3 rates x 3 scopes), found {len(scenarios)}"

    rate_map = {"5%": 0.05, "10%": 0.10, "15%": 0.15}
    for rate_str, scope, base_val, recovered in scenarios:
        expected_recovered = round(base_val * rate_map[rate_str], 2)
        assert abs(recovered - expected_recovered) <= 0.01, (
            f"Arithmetic error in scenario {rate_str} for {scope}: {recovered} != {expected_recovered}"
        )


def test_action_list_has_50_rows_sorted_high_to_low(db_conn):
    """Verify action_list contains exactly 50 rows sorted high to low by net_expected_annual_value."""
    rows = db_conn.execute("""
        SELECT 
            customer_id, country, segment, last_order_date, recency_days,
            order_count, total_revenue, returns_amount, net_revenue, return_pct,
            returns_flag, gross_expected_annual_value, net_expected_annual_value, suggested_action
        FROM action_list
    """).fetchall()

    assert len(rows) == 50, f"action_list must contain exactly 50 rows, found {len(rows)}"

    net_eav_values = [r[12] for r in rows]
    # Verify strictly descending (monotonically non-increasing)
    for i in range(len(net_eav_values) - 1):
        assert net_eav_values[i] >= net_eav_values[i+1], (
            f"action_list not sorted descending at index {i}: {net_eav_values[i]} < {net_eav_values[i+1]}"
        )

    # Verify customer 12346 dropped out naturally
    cust_ids = [r[0] for r in rows]
    assert 12346 not in cust_ids, "Customer 12346 with net <= 0 spend should not be in the Top 50 Action List"

    # Verify all 50 accounts are at-risk segments with proper suggested actions and flag logic
    for r in rows:
        cid = r[0]
        seg = r[2]
        tot_rev = r[6]
        ret_amt = r[7]
        net_rev = r[8]
        ret_pct = r[9]
        ret_flag = r[10]
        act = r[13]

        assert seg in ("Can't Lose Them", "At Risk"), f"Invalid segment {seg} in action_list"
        assert abs(net_rev - round(tot_rev - ret_amt, 2)) <= 0.01, f"Net revenue calculation mismatch for {cid}"
        if tot_rev > 0:
            expected_flag = (ret_amt > 0.5 * tot_rev)
            assert ret_flag == expected_flag, f"returns_flag incorrect for {cid}"

        if seg == "Can't Lose Them":
            assert act == "personal call + loyalty offer"
        elif seg == "At Risk":
            assert act == "win-back email with a discount"


# ==============================================================================
# Phase 6: Power BI Exports Data Integrity Tests
# ==============================================================================

def test_powerbi_export_files_exist():
    """Verify all 8 CSV tables and DATA_DICTIONARY.md exist in data/processed/powerbi/."""
    pbi_dir = BASE_DIR / "data" / "processed" / "powerbi"
    expected_files = [
        "dim_customer.csv",
        "fact_orders.csv",
        "dim_date.csv",
        "cohort_retention.csv",
        "segment_summary.csv",
        "revenue_at_risk_summary.csv",
        "win_back_scenarios.csv",
        "action_list.csv",
        "DATA_DICTIONARY.md",
    ]
    for fname in expected_files:
        fpath = pbi_dir / fname
        assert fpath.exists(), f"Expected Power BI export file missing: {fpath}"
        assert fpath.stat().st_size > 0, f"Power BI export file is empty: {fpath}"


def test_powerbi_no_nulls_in_key_columns():
    """Verify key identifier columns contain zero NULLs in Power BI exports."""
    import pandas as pd
    pbi_dir = BASE_DIR / "data" / "processed" / "powerbi"
    
    # dim_customer: customer_id, segment, first_order_date, last_order_date
    dim_cust = pd.read_csv(pbi_dir / "dim_customer.csv")
    assert dim_cust["customer_id"].isnull().sum() == 0, "dim_customer has null customer_id"
    assert dim_cust["segment"].isnull().sum() == 0, "dim_customer has null segment"
    assert dim_cust["first_order_date"].isnull().sum() == 0, "dim_customer has null first_order_date"
    assert dim_cust["last_order_date"].isnull().sum() == 0, "dim_customer has null last_order_date"

    # fact_orders: customer_id, invoice_no, order_date
    fact_orders = pd.read_csv(pbi_dir / "fact_orders.csv")
    assert fact_orders["customer_id"].isnull().sum() == 0, "fact_orders has null customer_id"
    assert fact_orders["invoice_no"].isnull().sum() == 0, "fact_orders has null invoice_no"
    assert fact_orders["order_date"].isnull().sum() == 0, "fact_orders has null order_date"


def test_powerbi_dim_customer_unique_and_count():
    """Verify dim_customer.csv contains exactly 5,853 unique integer customer IDs."""
    import pandas as pd
    pbi_dir = BASE_DIR / "data" / "processed" / "powerbi"
    dim_cust = pd.read_csv(pbi_dir / "dim_customer.csv")
    assert len(dim_cust) == 5853, f"Expected 5,853 rows in dim_customer.csv, got {len(dim_cust)}"
    assert dim_cust["customer_id"].nunique() == 5853, "Customer IDs in dim_customer.csv are not unique"
    assert pd.api.types.is_integer_dtype(dim_cust["customer_id"]), "customer_id must be integer type"


def test_powerbi_referential_integrity():
    """Verify every customer_id in fact_orders.csv exists in dim_customer.csv."""
    import pandas as pd
    pbi_dir = BASE_DIR / "data" / "processed" / "powerbi"
    dim_cust = pd.read_csv(pbi_dir / "dim_customer.csv")
    fact_orders = pd.read_csv(pbi_dir / "fact_orders.csv")
    cust_set = set(dim_cust["customer_id"])
    order_cust_set = set(fact_orders["customer_id"])
    orphans = order_cust_set - cust_set
    assert len(orphans) == 0, f"Found {len(orphans)} orphaned customer IDs in fact_orders.csv"


def test_powerbi_revenue_reconciliation():
    """Verify gross revenue reconciles to £17,081,128.74 within rounding tolerance across fact_orders and dim_customer."""
    import pandas as pd
    pbi_dir = BASE_DIR / "data" / "processed" / "powerbi"
    dim_cust = pd.read_csv(pbi_dir / "dim_customer.csv")
    fact_orders = pd.read_csv(pbi_dir / "fact_orders.csv")
    tot_cust_rev = round(dim_cust["total_revenue"].sum(), 2)
    tot_fact_rev = round(fact_orders["order_revenue"].sum(), 2)
    assert abs(tot_cust_rev - 17081128.74) <= 0.05, f"dim_customer total_revenue £{tot_cust_rev} differs by >5p from £17,081,128.74"
    assert abs(tot_fact_rev - 17081128.74) <= 0.05, f"fact_orders order_revenue £{tot_fact_rev} differs by >5p from £17,081,128.74"



