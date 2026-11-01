"""
Module: src.rfm
Implements customer-level RFM scoring, frequency band binning, and behavioral segmentation.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import duckdb
import pandas as pd


def execute_rfm_segmentation(
    db_path: Optional[Path] = None,
    export_csv: bool = True,
) -> Dict[str, Any]:
    """
    Executes sql/04_rfm.sql on the DuckDB database, creating customer_rfm
    and segment_summary tables, and optionally exporting them to data/processed/.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"

    conn = duckdb.connect(str(db_path))

    sql_path = base_dir / "sql" / "04_rfm.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        rfm_sql = f.read()

    conn.execute(rfm_sql)

    if export_csv:
        processed_dir = base_dir / "data" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        conn.execute(f"""
            COPY customer_rfm TO '{str(processed_dir / 'customer_rfm.csv').replace(chr(92), '/')}' (HEADER, DELIMITER ',');
        """)
        conn.execute(f"""
            COPY segment_summary TO '{str(processed_dir / 'segment_summary.csv').replace(chr(92), '/')}' (HEADER, DELIMITER ',');
        """)

    summary_df = conn.execute("SELECT * FROM segment_summary ORDER BY revenue DESC").df()
    cust_count = conn.execute("SELECT COUNT(*) FROM customer_rfm").fetchone()[0]
    rev_total = conn.execute("SELECT ROUND(SUM(monetary), 2) FROM customer_rfm").fetchone()[0]

    conn.close()

    return {
        "customer_count": cust_count,
        "total_revenue": rev_total,
        "summary_table": summary_df,
    }


if __name__ == "__main__":
    res = execute_rfm_segmentation()
    print(f"Scored {res['customer_count']:,} customers, Total Revenue: £{res['total_revenue']:,.2f}")
    print("\nSegment Summary:")
    print(res["summary_table"].to_string(index=False))
