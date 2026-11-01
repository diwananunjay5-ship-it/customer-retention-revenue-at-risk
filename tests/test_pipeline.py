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
