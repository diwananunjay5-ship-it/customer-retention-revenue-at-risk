"""
Module: src.ingest
Handles ingestion of raw transaction data into DuckDB.
Supports CSV and multi-sheet Excel files.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import duckdb
import pandas as pd

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def find_raw_file(base_dir: Optional[Path] = None) -> Path:
    """Locates the raw Online Retail II dataset file."""
    if base_dir is None:
        base_dir = BASE_DIR

    candidate_paths = [
        base_dir / "data" / "raw" / "online_retail_II.csv",
        base_dir / "data" / "raw" / "online_retail_II.xlsx",
        base_dir / "Data" / "Raw" / "online_retail_II.csv",
        base_dir / "Data" / "Raw" / "online_retail_II.xlsx",
    ]

    for path in candidate_paths:
        if path.exists():
            return path

    # Fallback search
    for pattern in ["*online_retail*.csv", "*online_retail*.xlsx"]:
        matches = list(base_dir.glob(f"**/{pattern}"))
        if matches:
            return matches[0]

    raise FileNotFoundError("Raw online_retail_II dataset could not be found.")


def get_raw_metadata(conn: duckdb.DuckDBPyConnection, raw_path: Path) -> Dict[str, Any]:
    """
    Extracts column names, data types, row count, and first 5 rows
    directly from the raw file before any transformation.
    """
    path_str = str(raw_path).replace("\\", "/")
    
    # First 5 rows
    sample_df = conn.execute(f"""
        SELECT * 
        FROM read_csv_auto('{path_str}', ignore_errors=true)
        LIMIT 5
    """).df()

    # Column schema and types
    schema_df = conn.execute(f"""
        DESCRIBE SELECT * FROM read_csv_auto('{path_str}', ignore_errors=true)
    """).df()

    # Total row count
    total_rows = conn.execute(f"""
        SELECT COUNT(*) 
        FROM read_csv_auto('{path_str}', ignore_errors=true)
    """).fetchone()[0]

    return {
        "file_path": str(raw_path),
        "total_rows": total_rows,
        "sample_df": sample_df,
        "schema_df": schema_df,
        "columns": list(sample_df.columns),
        "dtypes": dict(zip(schema_df["column_name"], schema_df["column_type"])),
    }


def ingest_raw_data(conn: duckdb.DuckDBPyConnection, raw_path: Optional[Path] = None) -> int:
    """
    Loads raw data into the 'raw_retail' table in DuckDB.
    Returns total rows loaded.
    """
    if raw_path is None:
        raw_path = find_raw_file()

    path_str = str(raw_path).replace("\\", "/")

    conn.execute(f"""
        CREATE OR REPLACE TABLE raw_retail AS 
        SELECT * FROM read_csv_auto('{path_str}', ignore_errors=true);
    """)

    total_rows = conn.execute("SELECT COUNT(*) FROM raw_retail").fetchone()[0]
    return total_rows


if __name__ == "__main__":
    db_conn = duckdb.connect()
    raw_file = find_raw_file()
    meta = get_raw_metadata(db_conn, raw_file)
    print("=== RAW DATA INSPECTION ===")
    print(f"File: {meta['file_path']}")
    print(f"Total Rows: {meta['total_rows']:,}")
    print("\nColumns and Types:")
    for col, dtype in meta["dtypes"].items():
        print(f"  - {col}: {dtype}")
    print("\nFirst 5 Rows:")
    print(meta["sample_df"].to_string())
