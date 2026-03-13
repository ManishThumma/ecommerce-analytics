"""
Product Performance Analytics
--------------------------------
- Best sellers by revenue, volume, and profit margin
- Category-level margin analysis
- Rating vs. sales correlation
- Price elasticity buckets
- Return rate by category
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR  = Path(__file__).parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.read_csv(DATA_DIR / "products.csv")
    items    = pd.read_csv(DATA_DIR / "order_items.csv", parse_dates=["order_date"])
    orders   = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
    return products, items, orders


def product_performance(products: pd.DataFrame, items: pd.DataFrame,
                        orders: pd.DataFrame) -> pd.DataFrame:
    delivered = orders[orders["status"] == "delivered"]["order_id"]
    returned  = orders[orders["status"] == "returned"]["order_id"]

    # Revenue per product (delivered orders only)
    rev = items[items["order_id"].isin(delivered)].groupby("product_id").agg(
        units_sold=("quantity", "sum"),
        gross_revenue=("revenue", "sum"),
        order_count=("order_id", "nunique"),
    ).reset_index()

    # Return volume
    ret = items[items["order_id"].isin(returned)].groupby("product_id").agg(
        units_returned=("quantity", "sum"),
    ).reset_index()

    perf = products.merge(rev, on="product_id", how="left") \
                   .merge(ret, on="product_id", how="left")
    perf.fillna({"units_sold": 0, "gross_revenue": 0,
                 "order_count": 0, "units_returned": 0}, inplace=True)

    perf["cogs"]           = perf["cost"] * perf["units_sold"]
    perf["gross_profit"]   = perf["gross_revenue"] - perf["cogs"]
    perf["margin_pct"]     = np.where(
        perf["gross_revenue"] > 0,
        perf["gross_profit"] / perf["gross_revenue"] * 100, 0
    )
    perf["return_rate"]    = np.where(
        perf["units_sold"] > 0,
        perf["units_returned"] / (perf["units_sold"] + perf["units_returned"]) * 100, 0
    )
    perf["revenue_rank"]   = perf["gross_revenue"].rank(ascending=False).astype(int)
    return perf


def category_summary(perf: pd.DataFrame) -> pd.DataFrame:
    cat = perf.groupby("category").agg(
        products=("product_id", "count"),
        total_revenue=("gross_revenue", "sum"),
        total_profit=("gross_profit", "sum"),
        avg_margin_pct=("margin_pct", "mean"),
        avg_rating=("rating", "mean"),
        avg_return_rate=("return_rate", "mean"),
        units_sold=("units_sold", "sum"),
    ).round(2)
    cat["revenue_share_pct"] = (cat["total_revenue"] / cat["total_revenue"].sum() * 100).round(1)
    return cat.sort_values("total_revenue", ascending=False)


def price_bucket_analysis(perf: pd.DataFrame) -> pd.DataFrame:
    bins   = [0, 20, 50, 100, 250, 500, float("inf")]
    labels = ["<$20", "$20-50", "$50-100", "$100-250", "$250-500", "$500+"]
    perf["price_bucket"] = pd.cut(perf["price"], bins=bins, labels=labels)
    return perf.groupby("price_bucket", observed=True).agg(
        products=("product_id", "count"),
        total_revenue=("gross_revenue", "sum"),
        avg_margin=("margin_pct", "mean"),
        avg_return_rate=("return_rate", "mean"),
    ).round(2)


# ── Visualisations ────────────────────────────────────────────────────────────
def plot_top_products(perf: pd.DataFrame, n: int = 15):
    top = perf.nlargest(n, "gross_revenue")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(f"Top {n} Products by Revenue", fontsize=15, fontweight="bold")

    # Revenue + margin
    bars = axes[0].barh(range(n), top["gross_revenue"], color=plt.cm.Blues(
        np.linspace(0.4, 0.9, n)))
    axes[0].set_yticks(range(n))
    axes[0].set_yticklabels([f"{pid}\n({cat})" for pid, cat in
                              zip(top["product_id"], top["category"])], fontsize=8)
    axes[0].set_xlabel("Gross Revenue ($)")
    axes[0].set_title("Revenue")
    axes[0].invert_yaxis()

    ax2 = axes[0].twiny()
    ax2.plot(top["margin_pct"], range(n), "r^", markersize=7, label="Margin %")
    ax2.set_xlabel("Margin (%)", color="red")
    ax2.tick_params(axis="x", colors="red")

    # Rating vs Revenue bubble
    axes[1].scatter(
        perf["rating"], perf["gross_revenue"],
        s=perf["units_sold"] / 5 + 10,
        c=perf["margin_pct"], cmap="RdYlGn",
        alpha=0.6, edgecolors="none"
    )
    axes[1].set_xlabel("Product Rating")
    axes[1].set_ylabel("Gross Revenue ($)")
    axes[1].set_title("Rating vs Revenue  |  size = Units Sold  |  color = Margin")
    cbar = plt.colorbar(axes[1].collections[0], ax=axes[1])
    cbar.set_label("Margin (%)")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "product_performance.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/product_performance.png")


def plot_category_margin(cat_summary: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Category Profitability", fontsize=14, fontweight="bold")

    cats = cat_summary.index
    x    = np.arange(len(cats))
    w    = 0.35

    axes[0].bar(x - w/2, cat_summary["total_revenue"] / 1e6,  w, label="Revenue ($M)", color="#3498db")
    axes[0].bar(x + w/2, cat_summary["total_profit"]  / 1e6,  w, label="Profit ($M)",  color="#2ecc71")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(cats, rotation=30, ha="right", fontsize=9)
    axes[0].set_ylabel("Amount ($M)")
    axes[0].set_title("Revenue vs Gross Profit by Category")
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    colors = ["#e74c3c" if m > cat_summary["avg_return_rate"].mean() else "#2ecc71"
              for m in cat_summary["avg_return_rate"]]
    axes[1].bar(cats, cat_summary["avg_return_rate"], color=colors)
    axes[1].set_xticklabels(cats, rotation=30, ha="right", fontsize=9)
    axes[1].set_ylabel("Return Rate (%)")
    axes[1].set_title("Average Return Rate by Category")
    axes[1].axhline(cat_summary["avg_return_rate"].mean(), color="black",
                    linestyle="--", label="Overall Avg")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "category_margins.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/category_margins.png")


# ── Entry point ───────────────────────────────────────────────────────────────
def run():
    print("\n=== Product Analytics ===")
    products, items, orders = load_data()

    perf    = product_performance(products, items, orders)
    cat_sum = category_summary(perf)
    price_b = price_bucket_analysis(perf)

    print("\nTop 5 Products by Revenue:")
    print(perf.nlargest(5, "gross_revenue")[
        ["product_id", "category", "gross_revenue", "margin_pct", "return_rate"]
    ].to_string(index=False))

    print("\nCategory Summary:")
    print(cat_sum[["total_revenue", "avg_margin_pct", "avg_return_rate", "revenue_share_pct"]].to_string())

    print("\nRevenue by Price Bucket:")
    print(price_b.to_string())

    perf.to_csv(OUT_DIR / "product_performance.csv", index=False)
    cat_sum.to_csv(OUT_DIR / "category_summary.csv")
    price_b.to_csv(OUT_DIR / "price_bucket_analysis.csv")
    print("\n  Saved → outputs/product_performance.csv")
    print("  Saved → outputs/category_summary.csv")

    plot_top_products(perf)
    plot_category_margin(cat_sum)

    return perf, cat_sum


if __name__ == "__main__":
    run()
