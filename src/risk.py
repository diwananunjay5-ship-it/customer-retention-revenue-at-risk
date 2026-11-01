"""
Module: src.risk
Implements Phase 5: Revenue-at-Risk calculation, win-back recovery scenario modeling,
and prioritized high-value action list generation.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import duckdb
import pandas as pd


def execute_revenue_at_risk(
    db_path: Optional[Path] = None,
    export_csv: bool = True,
) -> Dict[str, Any]:
    """
    Executes sql/05_revenue_at_risk.sql on the DuckDB database, creating
    revenue_at_risk_summary, win_back_scenarios, and action_list tables.
    Exports results to data/processed/.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"

    conn = duckdb.connect(str(db_path))

    sql_path = base_dir / "sql" / "05_revenue_at_risk.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        risk_sql = f.read()

    conn.execute(risk_sql)

    if export_csv:
        processed_dir = base_dir / "data" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        # Export customer_rfm with expected_annual_value and is_at_risk
        conn.execute(f"""
            COPY customer_rfm TO '{str(processed_dir / 'customer_rfm.csv').replace(chr(92), '/')}' (HEADER, DELIMITER ',');
        """)
        # Export revenue_at_risk_summary
        conn.execute(f"""
            COPY revenue_at_risk_summary TO '{str(processed_dir / 'revenue_at_risk_summary.csv').replace(chr(92), '/')}' (HEADER, DELIMITER ',');
        """)
        # Export win_back_scenarios
        conn.execute(f"""
            COPY win_back_scenarios TO '{str(processed_dir / 'win_back_scenarios.csv').replace(chr(92), '/')}' (HEADER, DELIMITER ',');
        """)
        # Export action_list
        conn.execute(f"""
            COPY action_list TO '{str(processed_dir / 'action_list.csv').replace(chr(92), '/')}' (HEADER, DELIMITER ',');
        """)

    summary_df = conn.execute("SELECT * FROM revenue_at_risk_summary").df()
    scenarios_df = conn.execute("SELECT * FROM win_back_scenarios").df()
    action_df = conn.execute("SELECT * FROM action_list").df()

    total_row = summary_df[summary_df["segment"] == "Total Revenue-at-Risk"].iloc[0]
    total_rar = float(total_row["revenue_at_risk"])
    total_rar_pct = float(total_row["revenue_at_risk_pct"])
    total_at_risk_cust = int(total_row["customer_count"])

    conn.close()

    return {
        "total_revenue_at_risk": total_rar,
        "total_revenue_at_risk_pct": total_rar_pct,
        "total_at_risk_customers": total_at_risk_cust,
        "summary_table": summary_df,
        "scenarios_table": scenarios_df,
        "action_list_table": action_df,
    }


if __name__ == "__main__":
    res = execute_revenue_at_risk()
    print("=== REVENUE AT RISK SUMMARY ===")
    print(res["summary_table"].to_string(index=False))
    print("\n=== WIN-BACK SCENARIOS ===")
    print(res["scenarios_table"].to_string(index=False))
    print("\n=== ACTION LIST (TOP 5) ===")
    print(res["action_list_table"].head(5).to_string(index=False))
