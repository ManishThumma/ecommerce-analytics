"""
Cohort Retention Analysis
--------------------------
Groups customers by their signup month (acquisition cohort) and tracks:
- Month-over-month retention rate
- Revenue retention
- Cumulative LTV by cohort

This directly maps to Amazon's obsession with customer lifetime value.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR  = Path(__file__).parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    customers = pd.read_csv(DATA_DIR / "customers.csv", parse_dates=["signup_date"])
    orders    = pd.read_csv(DATA_DIR / "orders.csv",    parse_dates=["order_date"])
    orders    = orders[orders["status"] == "delivered"].copy()
    return customers, orders


def build_cohorts(customers: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    customers["cohort_month"] = customers["signup_date"].dt.to_period("M")

    merged = orders.merge(customers[["customer_id", "cohort_month"]], on="customer_id")
    merged["order_month"] = merged["order_date"].dt.to_period("M")
    merged["period_number"] = (
        merged["order_month"].astype(int) - merged["cohort_month"].astype(int)
    )
    # Keep only months 0-23
    merged = merged[merged["period_number"].between(0, 23)]
    return merged


def retention_matrix(cohort_data: pd.DataFrame) -> pd.DataFrame:
    pivot = cohort_data.groupby(["cohort_month", "period_number"])["customer_id"].nunique().unstack()
    # Normalise by cohort size at month 0
    cohort_sizes = pivot[0]
    retention    = pivot.divide(cohort_sizes, axis=0) * 100
    return retention.round(1)


def revenue_cohort(cohort_data: pd.DataFrame) -> pd.DataFrame:
    rev = cohort_data.groupby(["cohort_month", "period_number"])["total_amount"].sum().unstack()
    return rev.fillna(0)


def cumulative_ltv(cohort_data: pd.DataFrame) -> pd.DataFrame:
    rev = cohort_data.groupby(["cohort_month", "period_number"])["total_amount"].sum().unstack().fillna(0)
    return rev.cumsum(axis=1)


# ── Visualisations ────────────────────────────────────────────────────────────
def plot_retention_heatmap(retention: pd.DataFrame):
    # Show last 12 cohorts, first 13 periods
    ret = retention.iloc[-12:, :13]
    ret.index = ret.index.strftime("%Y-%m")

    plt.figure(figsize=(16, 8))
    mask = ret.isnull()
    annot = ret.map(lambda v: f"{v:.0f}%" if not pd.isna(v) else "")
    sns.heatmap(ret, annot=annot, fmt="", cmap="YlGnBu", linewidths=0.3,
                mask=mask, vmin=0, vmax=100,
                cbar_kws={"label": "Retention Rate (%)"})
    plt.title("Monthly Cohort Retention Heatmap\n(% of original cohort still ordering)",
              fontsize=14, fontweight="bold")
    plt.xlabel("Months Since First Order")
    plt.ylabel("Acquisition Cohort")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "cohort_retention.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/cohort_retention.png")


def plot_ltv_curves(ltv: pd.DataFrame):
    ltv_plot = ltv.iloc[-8:, :13]   # Last 8 cohorts, 12-month window
    ltv_plot.index = ltv_plot.index.strftime("%Y-%m")

    plt.figure(figsize=(12, 6))
    for cohort in ltv_plot.index:
        plt.plot(ltv_plot.columns, ltv_plot.loc[cohort] / 1000,
                 marker="o", markersize=4, linewidth=1.5, label=cohort)

    plt.xlabel("Months Since First Order")
    plt.ylabel("Cumulative Revenue ($K)")
    plt.title("Cumulative LTV by Cohort (per cohort total)", fontsize=13, fontweight="bold")
    plt.legend(title="Cohort", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "ltv_curves.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/ltv_curves.png")


# ── Entry point ───────────────────────────────────────────────────────────────
def run():
    print("\n=== Cohort Retention Analysis ===")
    customers, orders = load_data()

    cohort_data = build_cohorts(customers, orders)
    retention   = retention_matrix(cohort_data)
    ltv         = cumulative_ltv(cohort_data)

    # Summary stats
    avg_m1_ret = retention[1].dropna().mean()
    avg_m3_ret = retention[3].dropna().mean()
    avg_m6_ret = retention[6].dropna().mean() if 6 in retention.columns else None
    print(f"\n  Avg Month-1  retention: {avg_m1_ret:.1f}%")
    print(f"  Avg Month-3  retention: {avg_m3_ret:.1f}%")
    if avg_m6_ret:
        print(f"  Avg Month-6  retention: {avg_m6_ret:.1f}%")

    retention.to_csv(OUT_DIR / "cohort_retention.csv")
    ltv.to_csv(OUT_DIR / "cohort_ltv.csv")
    print("  Saved → outputs/cohort_retention.csv")
    print("  Saved → outputs/cohort_ltv.csv")

    plot_retention_heatmap(retention)
    plot_ltv_curves(ltv)

    return retention, ltv


if __name__ == "__main__":
    run()
