"""
RFM Customer Segmentation
--------------------------
Recency   — how recently did the customer buy?
Frequency — how often do they buy?
Monetary  — how much do they spend?

Scoring: 1-5 per dimension → composite RFM score → segment labels.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR  = Path(__file__).parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)

# Segment definitions (RFM score thresholds)
SEGMENTS = {
    "Champions":         lambda r, f, m: (r >= 4) & (f >= 4) & (m >= 4),
    "Loyal Customers":   lambda r, f, m: (f >= 3) & (m >= 3),
    "Potential Loyalist":lambda r, f, m: (r >= 3) & (f <= 2),
    "At Risk":           lambda r, f, m: (r <= 2) & (f >= 3) & (m >= 3),
    "Hibernating":       lambda r, f, m: (r <= 2) & (f <= 2) & (m <= 2),
    "Others":            lambda r, f, m: pd.Series(True, index=r.index),
}


def load_orders() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
    return df[df["status"] == "delivered"].copy()


def build_rfm(orders: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    rfm = orders.groupby("customer_id").agg(
        last_order_date=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("total_amount", "sum"),
    ).reset_index()

    rfm["recency"] = (snapshot_date - rfm["last_order_date"]).dt.days
    rfm.drop(columns="last_order_date", inplace=True)
    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    # Higher recency score = more recent purchase (lower days = better)
    rfm["r_score"] = pd.qcut(rfm["recency"],  q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"],  q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]
    return rfm


def label_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    rfm["segment"] = "Others"
    for label, condition in SEGMENTS.items():
        if label == "Others":
            continue
        mask = condition(rfm["r_score"], rfm["f_score"], rfm["m_score"])
        rfm.loc[mask & (rfm["segment"] == "Others"), "segment"] = label
    return rfm


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    summary = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency_days=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
    ).round(2)
    summary["revenue_pct"] = (summary["total_revenue"] / summary["total_revenue"].sum() * 100).round(1)
    return summary.sort_values("total_revenue", ascending=False)


# ── Visualisations ────────────────────────────────────────────────────────────
def plot_segment_treemap(summary: pd.DataFrame):
    """Treemap-style bar chart of revenue by segment."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("RFM Customer Segmentation", fontsize=16, fontweight="bold")

    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(summary)))

    # Revenue share
    axes[0].barh(summary.index, summary["revenue_pct"], color=colors)
    axes[0].set_xlabel("Revenue Share (%)")
    axes[0].set_title("Revenue Contribution by Segment")
    for i, (val, cnt) in enumerate(zip(summary["revenue_pct"], summary["customers"])):
        axes[0].text(val + 0.3, i, f"{val}%  ({cnt:,} customers)", va="center", fontsize=9)

    # RFM scatter: Recency vs Monetary (sized by Frequency)
    for seg, color in zip(summary.index, colors):
        mask = rfm_global["segment"] == seg
        sub  = rfm_global[mask]
        axes[1].scatter(
            sub["recency"], sub["monetary"],
            s=sub["frequency"] * 15,
            alpha=0.4, label=seg, color=color
        )
    axes[1].set_xlabel("Recency (days since last order)")
    axes[1].set_ylabel("Monetary Value ($)")
    axes[1].set_title("Recency vs Monetary  |  size = Frequency")
    axes[1].legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "rfm_segments.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/rfm_segments.png")


def plot_rfm_heatmap(rfm: pd.DataFrame):
    pivot = rfm.groupby(["r_score", "f_score"])["monetary"].mean().unstack()
    plt.figure(figsize=(8, 6))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlOrRd",
                linewidths=0.5, cbar_kws={"label": "Avg Monetary ($)"})
    plt.title("Average Spend by Recency × Frequency Score", fontsize=13, fontweight="bold")
    plt.xlabel("Frequency Score")
    plt.ylabel("Recency Score")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "rfm_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/rfm_heatmap.png")


# ── Entry point ───────────────────────────────────────────────────────────────
rfm_global: pd.DataFrame = pd.DataFrame()   # used by plot function

def run():
    global rfm_global
    print("\n=== RFM Analysis ===")

    orders        = load_orders()
    snapshot      = orders["order_date"].max() + pd.Timedelta(days=1)
    rfm           = build_rfm(orders, snapshot)
    rfm           = score_rfm(rfm)
    rfm           = label_segments(rfm)
    rfm_global    = rfm.copy()

    summary = segment_summary(rfm)
    print("\nSegment Summary:")
    print(summary.to_string())

    rfm.to_csv(OUT_DIR / "rfm_scores.csv", index=False)
    summary.to_csv(OUT_DIR / "rfm_summary.csv")
    print("\n  Saved → outputs/rfm_scores.csv")
    print("  Saved → outputs/rfm_summary.csv")

    plot_segment_treemap(summary)
    plot_rfm_heatmap(rfm)

    # Key insight printout
    champions = summary.loc["Champions"] if "Champions" in summary.index else None
    if champions is not None:
        print(f"\nKey Insight: Champions ({int(champions['customers']):,} customers) "
              f"drive {champions['revenue_pct']}% of revenue with avg order value "
              f"${champions['avg_monetary']:.2f}")

    return rfm, summary


if __name__ == "__main__":
    run()
