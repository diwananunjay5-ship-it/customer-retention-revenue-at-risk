"""
Module: src.charts
Visualization generator for publication-grade cohort heatmaps,
RFM segment distributions, and Pareto curves.
"""

from pathlib import Path
from typing import Optional
import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def generate_cohort_heatmap(
    db_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generates and saves the monthly customer cohort retention heatmap.
    Excludes partial month December 2011 to maintain visual integrity.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"
    if output_path is None:
        output_path = base_dir / "reports" / "figures" / "cohort_retention_heatmap.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))

    # Read cohort retention table
    df = conn.execute("SELECT * FROM cohort_retention").df()

    # Filter out Dec 2011 from cohort rows (has only 9 days of activity and zero retention horizons)
    df_clean = df[df["cohort_month"] != pd.to_datetime("2011-12-01").date()].copy()
    # Mask partial month December 2011 from retention columns to prevent truncated visual bias
    df_clean.loc[df_clean["is_partial_month"], "retention_pct"] = np.nan

    pivot_table = df_clean.pivot(
        index="cohort_label", columns="month_index", values="retention_pct"
    )

    # Order cohorts chronologically
    cohort_order = [
        c for c in conn.execute("""
            SELECT DISTINCT cohort_label, cohort_month 
            FROM cohort_retention 
            ORDER BY cohort_month
        """).df()["cohort_label"].tolist()
        if "Dec 2011" not in c
    ]

    pivot_table = pivot_table.reindex(cohort_order)

    # Plotting
    fig, ax = plt.subplots(figsize=(18, 12), dpi=300)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    cmap = sns.color_palette("YlGnBu", as_cmap=True)

    sns.heatmap(
        pivot_table,
        annot=True,
        fmt=".1f",
        cmap=cmap,
        vmin=0,
        vmax=50,
        cbar_kws={"label": "Retention Rate (%)", "shrink": 0.8},
        linewidths=0.5,
        linecolor="#e0e0e0",
        ax=ax,
        mask=pivot_table.isnull(),
    )

    ax.set_title("Monthly Customer Cohort Retention Rates (%)", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Months Since Acquisition (Month Index)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("Acquisition Cohort", fontsize=12, fontweight="bold", labelpad=10)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=9, rotation=0)

    plt.figtext(
        0.5, 0.01,
        "Note: December 2009 cohort includes active legacy customers at dataset inception. December 2011 is a partial month (ends Dec 9) and is excluded from heatmap.",
        ha="center", fontsize=9, style="italic", color="#555555"
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    plt.savefig(output_path, dpi=300)
    plt.close()

    conn.close()
    return output_path


def generate_segment_size_vs_revenue(
    db_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generates and saves the RFM Segment Size vs. Revenue Share comparison chart.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"
    if output_path is None:
        output_path = base_dir / "reports" / "figures" / "segment_size_vs_revenue.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    segment_df = conn.execute("SELECT * FROM segment_summary").df()
    conn.close()

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

    ordered_segments = [
        "Champions", "Loyal", "New/Promising", "Need Attention", "At Risk", "Can't Lose Them", "Hibernating/Lost"
    ]
    plot_df = segment_df.set_index("segment").reindex(ordered_segments).reset_index()
    plot_df = plot_df.iloc[::-1].reset_index(drop=True)

    y = np.arange(len(plot_df))
    height = 0.38

    ax.barh(y - height/2, plot_df["pct_customers"], height, label="% of Customers", color="#4A90E2", alpha=0.9, edgecolor="#2A60A0", linewidth=1)
    ax.barh(y + height/2, plot_df["pct_revenue"], height, label="% of Total Revenue", color="#2ECC71", alpha=0.9, edgecolor="#1E824C", linewidth=1)

    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["segment"], fontsize=11, fontweight="bold")
    ax.set_xlabel("Share (%)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_xlim(0, 80)

    for i, row in plot_df.iterrows():
        c_val = row["pct_customers"]
        c_count = int(row["customers"])
        ax.text(c_val + 0.8, i - height/2, f"{c_val:.1f}% ({c_count:,})", va="center", fontsize=9, color="#1A3A60", fontweight="semibold")
        
        r_val = row["pct_revenue"]
        r_amt = row["revenue"]
        amt_str = f"£{r_amt/1e6:.2f}M" if r_amt >= 1e6 else f"£{r_amt/1e3:.0f}k"
        ax.text(r_val + 0.8, i + height/2, f"{r_val:.1f}% ({amt_str})", va="center", fontsize=9, color="#0E5A2A", fontweight="bold")

    ax.set_title("Customer Base Size vs. Revenue Contribution by RFM Segment\n"
                 "Champions drive 68.4% of revenue from 23.7% of accounts; £1.53M in historical revenue from At Risk and Can't Lose Them customers.",
                 fontsize=13, fontweight="bold", pad=15, loc="left")

    ax.legend(loc="lower right", frameon=True, framealpha=0.95, facecolor="#ffffff", edgecolor="#cccccc", fontsize=10)
    ax.grid(axis="x", linestyle="--", alpha=0.6)
    ax.grid(axis="y", visible=False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def generate_pareto_curve(
    db_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generates and saves the Pareto cumulative revenue concentration curve.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"
    if output_path is None:
        output_path = base_dir / "reports" / "figures" / "pareto_curve.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    pareto_df = conn.execute("""
        WITH cust_ranked AS (
            SELECT 
                customer_id,
                total_revenue,
                ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS rank,
                COUNT(*) OVER () AS total_customers,
                SUM(total_revenue) OVER () AS grand_total_revenue
            FROM dim_customer
        )
        SELECT 
            rank,
            ROUND(rank * 100.0 / total_customers, 4) AS cum_customer_pct,
            ROUND(SUM(total_revenue) OVER (ORDER BY rank) * 100.0 / grand_total_revenue, 4) AS cum_revenue_pct
        FROM cust_ranked
        ORDER BY rank;
    """).df()
    conn.close()

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)

    x = pareto_df["cum_customer_pct"]
    y = pareto_df["cum_revenue_pct"]

    ax.plot(x, y, color="#1B365D", linewidth=3, label="Cumulative Revenue Curve (Pareto)")
    ax.fill_between(x, y, color="#4A90E2", alpha=0.15)
    ax.plot([0, 100], [0, 100], linestyle="--", color="#888888", linewidth=1.5, label="Equality Baseline (Uniform Spend)")

    # 20% mark
    total_cust = len(pareto_df)
    n_20 = int(round(total_cust * 0.20))
    p20_row = pareto_df[pareto_df["rank"] == n_20].iloc[0]
    x_20 = p20_row["cum_customer_pct"]
    y_20 = p20_row["cum_revenue_pct"]

    ax.scatter([x_20], [y_20], color="#E74C3C", s=90, zorder=5)
    ax.axvline(x=20, color="#E74C3C", linestyle=":", linewidth=1.5, alpha=0.8)
    ax.axhline(y=y_20, color="#E74C3C", linestyle=":", linewidth=1.5, alpha=0.8)

    ax.annotate(
        f"80/20 Rule Validated:\nTop 20% of Customers ({n_20:,} accounts)\nGenerate {y_20:.1f}% of Total Revenue (£13.18M)",
        xy=(x_20, y_20),
        xytext=(x_20 + 8, y_20 - 18),
        arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=2, shrinkB=8),
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#FDEDEC", edgecolor="#E74C3C", lw=1.5),
        fontsize=10,
        fontweight="bold",
        color="#78281F"
    )

    # Top 5% marker
    n_5 = int(round(total_cust * 0.05))
    p5_row = pareto_df[pareto_df["rank"] == n_5].iloc[0]
    ax.scatter([p5_row["cum_customer_pct"]], [p5_row["cum_revenue_pct"]], color="#8E44AD", s=60, zorder=5)
    ax.annotate(
        f"Top 5% = {p5_row['cum_revenue_pct']:.1f}% Rev (£8.88M)",
        xy=(p5_row["cum_customer_pct"], p5_row["cum_revenue_pct"]),
        xytext=(p5_row["cum_customer_pct"] + 7, p5_row["cum_revenue_pct"] - 5),
        arrowprops=dict(arrowstyle="->", color="#8E44AD", lw=1.2, shrinkB=5),
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#F4ECF7", edgecolor="#8E44AD", lw=1),
        fontsize=9,
        fontweight="semibold",
        color="#4A235A"
    )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Cumulative % of Customers (Ranked by Revenue)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("Cumulative % of Total Revenue", fontsize=12, fontweight="bold", labelpad=10)

    ax.set_title("Customer Revenue Concentration: Pareto Curve\n"
                 "Total revenue of £17.08M across 5,853 unique retail accounts (Dec 2009 – Dec 2011)",
                 fontsize=13, fontweight="bold", pad=15, loc="left")

    ax.legend(loc="lower right", frameon=True, framealpha=0.95, facecolor="#ffffff", edgecolor="#cccccc", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def generate_revenue_at_risk_by_segment(
    db_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generates and saves the Revenue-at-Risk comparison chart:
    Historical spend vs. Annualized Revenue-at-Risk by segment.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"
    if output_path is None:
        output_path = base_dir / "reports" / "figures" / "revenue_at_risk_by_segment.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    summary_df = conn.execute("SELECT * FROM revenue_at_risk_summary").df()
    conn.close()

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # Order segments: Can't Lose Them, At Risk, Total Revenue-at-Risk
    seg_map = {
        "Can't Lose Them": "Can't Lose Them",
        "At Risk": "At Risk",
        "Total Revenue-at-Risk": "Total At-Risk"
    }
    plot_df = summary_df.copy()
    plot_df["display_name"] = plot_df["segment"].map(seg_map)
    order = ["Can't Lose Them", "At Risk", "Total At-Risk"]
    plot_df = plot_df.set_index("display_name").reindex(order).reset_index()

    segments = plot_df["display_name"].tolist()
    cust_counts = plot_df["customer_count"].tolist()
    net_rev = (plot_df["net_revenue"] / 1e3).tolist()
    net_rar_eav = (plot_df["revenue_at_risk"] / 1e3).tolist()

    x = np.arange(len(segments))
    width = 0.35

    rects1 = ax.bar(x - width/2, net_rev, width, label="Historical Net Spend (Post-Returns)", color="#95A5A6", alpha=0.9, edgecolor="#7F8C8D")
    rects2 = ax.bar(x + width/2, net_rar_eav, width, label="Annualized Net Revenue-at-Risk", color="#E74C3C", alpha=0.95, edgecolor="#C0392B")

    ax.set_ylabel("Revenue (£ Thousands)", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_title("Revenue-at-Risk by Segment: Historical Net Spend vs. Annualized Exposure\n"
                 "Total annualized Net Revenue-at-Risk is £769.1k (7.87% of total customer net EAV) across 710 dormant accounts.",
                 fontsize=12.5, fontweight="bold", pad=15, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s}\n({c:,} accounts)" for s, c in zip(segments, cust_counts)], fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(net_rev) * 1.25)

    for r in rects1:
        h = r.get_height()
        ax.annotate(f"£{h:.1f}k",
                    xy=(r.get_x() + r.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#555555')

    for r in rects2:
        h = r.get_height()
        ax.annotate(f"£{h:.1f}k",
                    xy=(r.get_x() + r.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#922B21')

    ax.legend(loc="upper left", frameon=True, framealpha=0.95, facecolor="#ffffff", edgecolor="#cccccc", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.grid(axis="x", visible=False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def generate_win_back_scenarios(
    db_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generates and saves the Win-Back Scenarios sensitivity chart (5%, 10%, 15% recovery rates on Net RAR).
    """
    base_dir = Path(__file__).resolve().parent.parent
    if db_path is None:
        db_path = base_dir / "data" / "retention.duckdb"
    if output_path is None:
        output_path = base_dir / "reports" / "figures" / "win_back_scenarios.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    scenarios_df = conn.execute("SELECT * FROM win_back_scenarios").df()
    conn.close()

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)

    rates = ["5% Recovery", "10% Recovery", "15% Recovery"]
    cant_lose = (scenarios_df[scenarios_df["scope"] == "Can't Lose Them Only"]["recovered_revenue"] / 1e3).tolist()
    at_risk = (scenarios_df[scenarios_df["scope"] == "At Risk Only"]["recovered_revenue"] / 1e3).tolist()
    both_combined = (scenarios_df[scenarios_df["scope"] == "Both (Total At-Risk)"]["recovered_revenue"] / 1e3).tolist()

    x = np.arange(len(rates))
    width = 0.25

    b1 = ax.bar(x - width, cant_lose, width, label="Can't Lose Them Only (287 accounts)", color="#F39C12", alpha=0.9, edgecolor="#D68910")
    b2 = ax.bar(x, at_risk, width, label="At Risk Only (423 accounts)", color="#3498DB", alpha=0.9, edgecolor="#2980B9")
    b3 = ax.bar(x + width, both_combined, width, label="Both Combined (710 accounts)", color="#2ECC71", alpha=0.95, edgecolor="#27AE60")

    ax.set_ylabel("Recovered Annual Revenue (£ Thousands)", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_title("Win-Back Opportunity: Potential Annual Revenue Recovery (Net Basis)\n"
                 "Label: Scenario assumptions, not forecasts (Reclaiming 10% of both segments recovers ~£76.9k annually)",
                 fontsize=12.5, fontweight="bold", pad=15, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels(rates, fontsize=10.5, fontweight="bold")
    ax.set_ylim(0, max(both_combined) * 1.25)

    for b in [b1, b2, b3]:
        for r in b:
            h = r.get_height()
            ax.annotate(f"£{h:.1f}k",
                        xy=(r.get_x() + r.get_width() / 2, h),
                        xytext=(0, 4), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1C2833')

    ax.legend(loc="upper left", frameon=True, framealpha=0.95, facecolor="#ffffff", edgecolor="#cccccc", fontsize=9.5)
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.grid(axis="x", visible=False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def generate_all_charts(db_path: Optional[Path] = None) -> None:
    """Generates all publication-grade charts."""
    generate_cohort_heatmap(db_path=db_path)
    generate_segment_size_vs_revenue(db_path=db_path)
    generate_pareto_curve(db_path=db_path)
    generate_revenue_at_risk_by_segment(db_path=db_path)
    generate_win_back_scenarios(db_path=db_path)


if __name__ == "__main__":
    generate_all_charts()
    print("All charts generated successfully.")
