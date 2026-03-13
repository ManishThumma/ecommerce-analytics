"""
Sales Trend Analysis & Forecasting
------------------------------------
- Monthly / weekly revenue trends
- Year-over-year growth
- Category-level contribution
- Simple linear + seasonal naive forecast for next 3 months
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR  = Path(__file__).parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = pd.read_csv(DATA_DIR / "orders.csv",      parse_dates=["order_date"])
    items  = pd.read_csv(DATA_DIR / "order_items.csv", parse_dates=["order_date"])
    orders = orders[orders["status"] == "delivered"].copy()
    items  = items[items["order_id"].isin(orders["order_id"])].copy()
    return orders, items


def monthly_revenue(orders: pd.DataFrame) -> pd.DataFrame:
    orders["month"] = orders["order_date"].dt.to_period("M")
    monthly = orders.groupby("month").agg(
        revenue=("total_amount", "sum"),
        orders=("order_id", "count"),
        customers=("customer_id", "nunique"),
    ).reset_index()
    monthly["aov"]              = monthly["revenue"] / monthly["orders"]
    monthly["month_dt"]         = monthly["month"].dt.to_timestamp()
    monthly["revenue_mom_pct"]  = monthly["revenue"].pct_change() * 100
    monthly["revenue_yoy_pct"]  = monthly["revenue"].pct_change(periods=12) * 100
    return monthly


def category_monthly(items: pd.DataFrame) -> pd.DataFrame:
    items["month"] = items["order_date"].dt.to_period("M")
    cat = items.groupby(["month", "category"])["revenue"].sum().reset_index()
    cat["month_dt"] = cat["month"].dt.to_timestamp()
    return cat


def seasonal_naive_forecast(series: pd.Series, periods: int = 3) -> pd.Series:
    """Seasonal naive: forecast = value from same month one year ago * growth factor."""
    if len(series) < 13:
        return pd.Series([series.mean()] * periods)
    yoy_growth = (series.iloc[-12:].values / series.iloc[-24:-12].values).mean()
    last_year  = series.iloc[-12:].values
    forecast   = last_year[:periods] * yoy_growth
    return pd.Series(forecast)


def compute_kpis(orders: pd.DataFrame) -> dict:
    total_rev   = orders["total_amount"].sum()
    total_orders= orders["order_id"].nunique()
    total_cust  = orders["customer_id"].nunique()
    aov         = total_rev / total_orders
    orders_per  = total_orders / total_cust

    orders["year"] = orders["order_date"].dt.year
    yoy = orders.groupby("year")["total_amount"].sum()
    yoy_growth = ((yoy.iloc[-1] / yoy.iloc[-2]) - 1) * 100 if len(yoy) >= 2 else None

    return {
        "total_revenue":   total_rev,
        "total_orders":    total_orders,
        "unique_customers":total_cust,
        "avg_order_value": aov,
        "orders_per_cust": orders_per,
        "yoy_revenue_growth_pct": yoy_growth,
    }


# ── Visualisations ────────────────────────────────────────────────────────────
def plot_revenue_trend(monthly: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=False)
    fig.suptitle("Revenue Trend Analysis", fontsize=16, fontweight="bold")

    # 1) Monthly revenue + 3-month forecast
    ax = axes[0]
    ax.fill_between(monthly["month_dt"], monthly["revenue"], alpha=0.2, color="#1f77b4")
    ax.plot(monthly["month_dt"], monthly["revenue"], color="#1f77b4", linewidth=2, label="Actual Revenue")

    # Forecast
    forecast = seasonal_naive_forecast(monthly["revenue"], periods=3)
    last_date = monthly["month_dt"].iloc[-1]
    future_dates = pd.date_range(last_date + pd.offsets.MonthBegin(), periods=3, freq="MS")
    ax.plot(future_dates, forecast, "r--o", linewidth=2, label="3-Month Forecast")
    ax.fill_between(future_dates, forecast * 0.92, forecast * 1.08, alpha=0.15, color="red", label="±8% CI")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    ax.set_title("Monthly Revenue with Forecast")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # 2) MoM growth %
    ax2 = axes[1]
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in monthly["revenue_mom_pct"].fillna(0)]
    ax2.bar(monthly["month_dt"], monthly["revenue_mom_pct"].fillna(0), color=colors, width=20)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title("Month-over-Month Revenue Growth (%)")
    ax2.set_ylabel("%")
    ax2.grid(axis="y", alpha=0.3)

    # 3) AOV trend
    ax3 = axes[2]
    ax3.plot(monthly["month_dt"], monthly["aov"], color="#9b59b6", linewidth=2, marker="o", markersize=4)
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
    ax3.set_title("Average Order Value (AOV) Trend")
    ax3.set_ylabel("AOV ($)")
    ax3.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "revenue_trend.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/revenue_trend.png")


def plot_category_breakdown(cat_monthly: pd.DataFrame):
    pivot = cat_monthly.pivot_table(
        index="month_dt", columns="category", values="revenue", aggfunc="sum"
    ).fillna(0)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle("Category Performance", fontsize=16, fontweight="bold")

    # Stacked area
    pivot.plot(kind="area", stacked=True, ax=axes[0], alpha=0.75, colormap="tab10")
    axes[0].set_title("Monthly Revenue by Category (Stacked)")
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    axes[0].legend(loc="upper left", fontsize=8)
    axes[0].grid(axis="y", alpha=0.3)

    # Latest-year pie
    latest_year  = cat_monthly["month_dt"].dt.year.max()
    cat_year     = cat_monthly[cat_monthly["month_dt"].dt.year == latest_year]
    cat_totals   = cat_year.groupby("category")["revenue"].sum().sort_values(ascending=False)
    axes[1].pie(cat_totals, labels=cat_totals.index, autopct="%1.1f%%",
                startangle=140, colors=plt.cm.tab10.colors)
    axes[1].set_title(f"Revenue Share by Category ({latest_year})")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "category_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved → outputs/category_breakdown.png")


# ── Entry point ───────────────────────────────────────────────────────────────
def run():
    print("\n=== Sales Trend Analysis ===")
    orders, items = load_data()

    kpis = compute_kpis(orders)
    print("\nKPIs:")
    for k, v in kpis.items():
        if isinstance(v, float):
            print(f"  {k:<30} {v:>12,.2f}")
        else:
            print(f"  {k:<30} {v:>12,}")

    monthly     = monthly_revenue(orders)
    cat_monthly = category_monthly(items)

    monthly.to_csv(OUT_DIR / "monthly_revenue.csv", index=False)
    cat_monthly.to_csv(OUT_DIR / "category_monthly.csv", index=False)
    print("\n  Saved → outputs/monthly_revenue.csv")
    print("  Saved → outputs/category_monthly.csv")

    plot_revenue_trend(monthly)
    plot_category_breakdown(cat_monthly)

    return monthly, cat_monthly, kpis


if __name__ == "__main__":
    run()
