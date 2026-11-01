"""
End-to-end Reproducible Pipeline Runner
Executes Phase 1 (Ingestion & Cleaning), Phase 2 (Dimensional Modeling),
Phase 3 (Cohort Retention), Phase 4 (RFM Segmentation),
Phase 5 (Revenue-at-Risk & Win-back Scenarios), and generates publication-grade figures.
"""

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.clean import run_clean_pipeline
from src.charts import generate_all_charts
from src.powerbi import export_powerbi_tables


def main():
    print("=" * 60)
    print("Customer Retention & Revenue-at-Risk Pipeline")
    print("=" * 60)
    
    print("\n[1/3] Executing Ingestion, Hygiene, Modeling, RFM & Risk Scenarios...")
    res = run_clean_pipeline()
    
    print(f"  • Deduplicated & Clean Sales Rows: {res['clean_rows']:,}")
    print(f"  • Orders Modeled (fact_orders): {res['fact_orders_rows']:,}")
    print(f"  • Customers Segmented (customer_rfm): {res['customer_rfm_rows']:,}")
    print(f"  • Snapshot Date: {res['snapshot_date']}")
    print(f"  • Tracked Clean Revenue: £{res['clean_sales_revenue']:,.2f}")
    print(f"  • Revenue Reconciled to Penny: {res['revenue_matches']}")
    print(f"  • At-Risk Customers Flagged: {res['at_risk_customers']:,}")
    print(f"  • Annualized Net Revenue-at-Risk: £{res['revenue_at_risk']:,.2f} ({res['revenue_at_risk_pct']:.2f}% of customer base net EAV)")
    print(f"  • Baseline Gross Revenue-at-Risk: £{res['gross_revenue_at_risk']:,.2f}")

    print("\n[2/3] Generating Publication-Grade Visualizations...")
    generate_all_charts()
    print("  • reports/figures/cohort_retention_heatmap.png")
    print("  • reports/figures/segment_size_vs_revenue.png")
    print("  • reports/figures/pareto_curve.png")
    print("  • reports/figures/revenue_at_risk_by_segment.png")
    print("  • reports/figures/win_back_scenarios.png")

    print("\n[3/3] Exporting Production Power BI Star-Schema Tables...")
    pbi_res = export_powerbi_tables()
    print(f"  • dim_customer.csv ({pbi_res['dim_customer_rows']:,} accounts)")
    print(f"  • fact_orders.csv ({pbi_res['fact_orders_rows']:,} orders)")
    print(f"  • dim_date.csv ({pbi_res['dim_date_rows']:,} days)")
    print(f"  • cohort_retention.csv ({pbi_res['cohort_retention_rows']:,} cells)")
    print(f"  • segment_summary.csv ({pbi_res['segment_summary_rows']:,} segments)")
    print(f"  • revenue_at_risk_summary.csv ({pbi_res['revenue_at_risk_summary_rows']:,} scopes)")
    print(f"  • win_back_scenarios.csv ({pbi_res['win_back_scenarios_rows']:,} scenarios)")
    print(f"  • action_list.csv ({pbi_res['action_list_rows']:,} prioritized accounts)")
    print("  • DATA_DICTIONARY.md (data specification)")

    print("\nPipeline completed successfully!")


if __name__ == "__main__":
    main()

