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

    # Prepare matrix for heatmap
    # Mask partial month (Dec 2011) to avoid 9-day truncation visual bias
    df_heatmap = df.copy()
    df_heatmap.loc[df_heatmap["is_partial_month"], "retention_pct"] = np.nan

    pivot_table = df_heatmap.pivot(
        index="cohort_label", columns="month_index", values="retention_pct"
    )

    # Order cohorts chronologically
    cohort_order = conn.execute("""
        SELECT DISTINCT cohort_label, cohort_month 
        FROM cohort_retention 
        ORDER BY cohort_month
    """).df()["cohort_label"].tolist()

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


if __name__ == "__main__":
    out = generate_cohort_heatmap()
    print(f"Heatmap generated at: {out}")
