"""
E-Commerce Analytics Dashboard
---------------------------------
Interactive Streamlit app — run with:  streamlit run dashboard/app.py

Sections:
  1. Executive KPI Summary
  2. Revenue Trends & Forecast
  3. Customer Segmentation (RFM)
  4. Cohort Retention
  5. Product Performance
  6. A/B Test Results
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# Make sure parent package is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="E-Commerce Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-generate data + outputs if running on Streamlit Cloud ───────────────
def ensure_data():
    import runpy
    data_files = ["orders.csv", "customers.csv", "products.csv",
                  "order_items.csv", "events.csv"]
    out_files  = ["rfm_scores.csv", "monthly_revenue.csv",
                  "product_performance.csv", "cohort_retention.csv"]

    if any(not (ROOT / "data" / f).exists() for f in data_files):
        with st.spinner("Generating data — first load only, ~15 seconds..."):
            runpy.run_path(str(ROOT / "data" / "generate_data.py"), run_name="__main__")

    (ROOT / "outputs").mkdir(exist_ok=True)
    if any(not (ROOT / "outputs" / f).exists() for f in out_files):
        with st.spinner("Running analysis pipeline — first load only, ~30 seconds..."):
            from analysis.sales_trends   import run as run_sales
            from analysis.rfm_analysis   import run as run_rfm
            from analysis.product_analytics import run as run_products
            from analysis.cohort_analysis   import run as run_cohort
            run_sales()
            run_rfm()
            run_products()
            run_cohort()

ensure_data()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #0f3460;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #e94560; }
    .metric-label { font-size: 0.85rem; color: #aaa; text-transform: uppercase; }
    .metric-delta { font-size: 0.9rem; }
    section[data-testid="stSidebar"] { background: #0d0d1a; }
</style>
""", unsafe_allow_html=True)


# ── Data loaders (cached) ─────────────────────────────────────────────────────
DATA  = ROOT / "data"
OUT   = ROOT / "outputs"

@st.cache_data(ttl=3600)
def load_orders():
    df = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])
    return df[df["status"] == "delivered"].copy()

@st.cache_data(ttl=3600)
def load_items():
    return pd.read_csv(DATA / "order_items.csv", parse_dates=["order_date"])

@st.cache_data(ttl=3600)
def load_customers():
    return pd.read_csv(DATA / "customers.csv", parse_dates=["signup_date"])

@st.cache_data(ttl=3600)
def load_products():
    return pd.read_csv(DATA / "products.csv")

@st.cache_data(ttl=3600)
def load_output(name):
    p = OUT / name
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_events():
    return pd.read_csv(DATA / "events.csv", parse_dates=["event_date"])


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
st.sidebar.title("Analytics")
page = st.sidebar.radio(
    "Navigate",
    ["Executive Summary", "Revenue Trends", "Customer Segments",
     "Cohort Retention", "Product Performance", "A/B Testing"],
)

orders    = load_orders()
items     = load_items()
customers = load_customers()
products  = load_products()

# Date filter
min_d = orders["order_date"].min().date()
max_d = orders["order_date"].max().date()
st.sidebar.markdown("---")
st.sidebar.subheader("Date Range")
date_range = st.sidebar.date_input("Select range", value=(min_d, max_d),
                                    min_value=min_d, max_value=max_d)
if len(date_range) == 2:
    orders = orders[
        (orders["order_date"].dt.date >= date_range[0]) &
        (orders["order_date"].dt.date <= date_range[1])
    ]
    items = items[
        (items["order_date"].dt.date >= date_range[0]) &
        (items["order_date"].dt.date <= date_range[1])
    ]


# ── Page: Executive Summary ───────────────────────────────────────────────────
if page == "Executive Summary":
    st.title("Executive Summary")
    st.caption(f"Data range: {orders['order_date'].min().date()} → {orders['order_date'].max().date()}")

    total_rev    = orders["total_amount"].sum()
    total_orders = orders["order_id"].nunique()
    unique_cust  = orders["customer_id"].nunique()
    aov          = total_rev / total_orders if total_orders else 0
    prime_rev    = orders[orders["is_prime_order"]==True]["total_amount"].sum()
    prime_share  = prime_rev / total_rev * 100 if total_rev else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue",     f"${total_rev/1e6:.2f}M")
    c2.metric("Total Orders",      f"{total_orders:,}")
    c3.metric("Unique Customers",  f"{unique_cust:,}")
    c4.metric("Avg Order Value",   f"${aov:.2f}")
    c5.metric("Prime Revenue %",   f"{prime_share:.1f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Revenue by region
    reg = orders.groupby("region")["total_amount"].sum().reset_index()
    fig_reg = px.pie(reg, names="region", values="total_amount",
                     title="Revenue by Region", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Bold)
    col1.plotly_chart(fig_reg, use_container_width=True)

    # Revenue by channel
    chan = orders.groupby("channel")["total_amount"].sum().sort_values(ascending=True).reset_index()
    fig_chan = px.bar(chan, x="total_amount", y="channel", orientation="h",
                      title="Revenue by Acquisition Channel",
                      color="total_amount", color_continuous_scale="Blues")
    col2.plotly_chart(fig_chan, use_container_width=True)

    # Monthly revenue sparkline
    orders["month"] = orders["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly = orders.groupby("month")["total_amount"].sum().reset_index()
    fig_spark = px.area(monthly, x="month", y="total_amount",
                        title="Monthly Revenue Trend",
                        labels={"total_amount": "Revenue ($)", "month": ""},
                        color_discrete_sequence=["#e94560"])
    fig_spark.update_layout(showlegend=False)
    st.plotly_chart(fig_spark, use_container_width=True)


# ── Page: Revenue Trends ──────────────────────────────────────────────────────
elif page == "Revenue Trends":
    st.title("Revenue Trends & Forecasting")

    orders["month"] = orders["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly = orders.groupby("month").agg(
        revenue=("total_amount", "sum"),
        orders=("order_id", "count"),
    ).reset_index()
    monthly["aov"]     = monthly["revenue"] / monthly["orders"]
    monthly["mom_pct"] = monthly["revenue"].pct_change() * 100

    # Forecast (last 3 months)
    if len(monthly) >= 13:
        yoy_g = (monthly["revenue"].iloc[-12:].values /
                 monthly["revenue"].iloc[-24:-12].values).mean()
        last3  = monthly["revenue"].iloc[-3:].values * yoy_g
        fdates = pd.date_range(monthly["month"].iloc[-1] + pd.offsets.MonthBegin(),
                               periods=3, freq="MS")
        forecast_df = pd.DataFrame({"month": fdates, "forecast": last3})
    else:
        forecast_df = pd.DataFrame()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["revenue"],
                              name="Actual", mode="lines+markers",
                              line=dict(color="#1f77b4", width=2)))
    if not forecast_df.empty:
        fig.add_trace(go.Scatter(x=forecast_df["month"], y=forecast_df["forecast"],
                                  name="Forecast", mode="lines+markers",
                                  line=dict(color="#e94560", width=2, dash="dash")))
    fig.update_layout(title="Monthly Revenue with 3-Month Forecast",
                      yaxis_tickprefix="$", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    # MoM %
    fig_mom = px.bar(monthly.dropna(subset=["mom_pct"]),
                     x="month", y="mom_pct",
                     color=monthly.dropna(subset=["mom_pct"])["mom_pct"].apply(
                         lambda v: "positive" if v >= 0 else "negative"),
                     color_discrete_map={"positive": "#2ecc71", "negative": "#e74c3c"},
                     title="Month-over-Month Growth (%)",
                     labels={"mom_pct": "MoM %", "month": ""})
    col1.plotly_chart(fig_mom, use_container_width=True)

    # AOV trend
    fig_aov = px.line(monthly, x="month", y="aov",
                      title="Average Order Value Trend",
                      markers=True, color_discrete_sequence=["#9b59b6"],
                      labels={"aov": "AOV ($)", "month": ""})
    col2.plotly_chart(fig_aov, use_container_width=True)

    # Category breakdown — items already carries 'category' from the generator
    items_cat = items.copy()
    items_cat["month"] = items_cat["order_date"].dt.to_period("M").dt.to_timestamp()
    cat_monthly = items_cat.groupby(["month", "category"])["revenue"].sum().reset_index()

    fig_cat = px.area(cat_monthly, x="month", y="revenue", color="category",
                      title="Revenue by Category (Stacked)",
                      labels={"revenue": "Revenue ($)", "month": ""},
                      color_discrete_sequence=px.colors.qualitative.Plotly)
    st.plotly_chart(fig_cat, use_container_width=True)


# ── Page: Customer Segments ───────────────────────────────────────────────────
elif page == "Customer Segments":
    st.title("Customer Segmentation — RFM")

    @st.cache_data(ttl=3600)
    def compute_rfm(orders_df):
        snapshot = orders_df["order_date"].max() + pd.Timedelta(days=1)
        rfm = orders_df.groupby("customer_id").agg(
            recency=("order_date", lambda x: (snapshot - x.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("total_amount", "sum"),
        ).reset_index()
        rfm["r_score"] = pd.qcut(rfm["recency"],  q=5, labels=[5,4,3,2,1]).astype(int)
        rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1,2,3,4,5]).astype(int)
        rfm["m_score"] = pd.qcut(rfm["monetary"],  q=5, labels=[1,2,3,4,5]).astype(int)
        def label(r, f, m):
            if r >= 4 and f >= 4 and m >= 4: return "Champions"
            if f >= 3 and m >= 3:             return "Loyal Customers"
            if r >= 3 and f <= 2:             return "Potential Loyalist"
            if r <= 2 and f >= 3 and m >= 3:  return "At Risk"
            if r <= 2 and f <= 2 and m <= 2:  return "Hibernating"
            return "Others"
        rfm["segment"] = rfm.apply(lambda x: label(x.r_score, x.f_score, x.m_score), axis=1)
        return rfm

    rfm_df = compute_rfm(orders)

    seg_summary = rfm_df.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
    ).round(2)
    seg_summary["revenue_pct"] = (
        seg_summary["total_revenue"] / seg_summary["total_revenue"].sum() * 100
    ).round(1)

    c1, c2, c3 = st.columns(3)
    if "Champions" in seg_summary.index:
        ch = seg_summary.loc["Champions"]
        c1.metric("Champions", f"{int(ch['customers']):,}", f"{ch['revenue_pct']}% revenue")
    if "At Risk" in seg_summary.index:
        ar = seg_summary.loc["At Risk"]
        c2.metric("At Risk", f"{int(ar['customers']):,}", f"${ar['avg_monetary']:.0f} avg spend")
    c3.metric("Total Segments", len(seg_summary))

    col1, col2 = st.columns(2)

    fig_pie = px.pie(seg_summary.reset_index(), names="segment", values="revenue_pct",
                     title="Revenue Share by Segment", hole=0.35,
                     color_discrete_sequence=px.colors.qualitative.Safe)
    col1.plotly_chart(fig_pie, use_container_width=True)

    fig_scatter = px.scatter(
        rfm_df.sample(min(2000, len(rfm_df))),
        x="recency", y="monetary", size="frequency",
        color="segment", title="RFM Scatter (sample)",
        labels={"recency": "Recency (days)", "monetary": "Spend ($)"},
        size_max=20, opacity=0.6,
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    col2.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Segment Detail")
    st.dataframe(seg_summary.style.background_gradient(subset=["revenue_pct"], cmap="Greens"),
                 use_container_width=True)


# ── Page: Cohort Retention ────────────────────────────────────────────────────
elif page == "Cohort Retention":
    st.title("Cohort Retention Analysis")

    @st.cache_data(ttl=3600)
    def compute_cohorts(orders_df, customers_df):
        cust = customers_df[["customer_id", "signup_date"]].copy()
        cust["cohort_month"] = cust["signup_date"].dt.to_period("M")
        merged = orders_df.merge(cust, on="customer_id")
        merged["order_month"]   = merged["order_date"].dt.to_period("M")
        merged["period_number"] = (
            merged["order_month"].astype(int) - merged["cohort_month"].astype(int)
        )
        merged = merged[merged["period_number"].between(0, 23)]
        pivot  = merged.groupby(["cohort_month","period_number"])["customer_id"].nunique().unstack()
        return (pivot.divide(pivot[0], axis=0) * 100).round(1)

    retention = compute_cohorts(orders, customers)
    display   = retention.iloc[-12:, :13].astype(float)
    display.index = display.index.strftime("%Y-%m")

    fig_heat = go.Figure(data=go.Heatmap(
        z=display.values,
        x=[f"Month {c}" for c in display.columns],
        y=display.index,
        colorscale="YlGnBu",
        text=[[f"{v:.0f}%" if not np.isnan(v) else "" for v in row] for row in display.values],
        texttemplate="%{text}",
        hovertemplate="Cohort: %{y}<br>%{x}<br>Retention: %{z:.1f}%<extra></extra>",
        zmin=0, zmax=100,
    ))
    fig_heat.update_layout(
        title="Cohort Retention Heatmap (% of original cohort still ordering)",
        xaxis_title="Months Since First Order",
        yaxis_title="Acquisition Cohort",
        height=500,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    avg_ret = display.mean()
    fig_avg = px.line(x=avg_ret.index.astype(str), y=avg_ret.values,
                      markers=True, title="Average Retention by Month",
                      labels={"x": "Month", "y": "Retention (%)"},
                      color_discrete_sequence=["#e94560"])
    fig_avg.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_avg, use_container_width=True)


# ── Page: Product Performance ─────────────────────────────────────────────────
elif page == "Product Performance":
    st.title("Product Performance")

    @st.cache_data(ttl=3600)
    def compute_product_perf(orders_df, items_df, products_df):
        delivered = orders_df[orders_df["status"]=="delivered"]["order_id"]
        rev = items_df[items_df["order_id"].isin(delivered)].groupby("product_id").agg(
            units_sold=("quantity","sum"),
            gross_revenue=("revenue","sum"),
        ).reset_index()
        perf = products_df.merge(rev, on="product_id", how="left").fillna(
            {"units_sold":0,"gross_revenue":0})
        perf["gross_profit"] = perf["gross_revenue"] - perf["cost"] * perf["units_sold"]
        perf["margin_pct"]   = np.where(
            perf["gross_revenue"]>0,
            perf["gross_profit"]/perf["gross_revenue"]*100, 0)
        perf["return_rate"]  = 0.0
        return perf

    @st.cache_data(ttl=3600)
    def compute_cat_summary(perf_df):
        return perf_df.groupby("category").agg(
            total_revenue=("gross_revenue","sum"),
            total_profit=("gross_profit","sum"),
            avg_margin_pct=("margin_pct","mean"),
        ).round(2).reset_index()

    perf = compute_product_perf(orders, items, products)
    cat  = compute_cat_summary(perf)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products Analysed", f"{len(perf):,}")
    c2.metric("Total Gross Revenue", f"${perf['gross_revenue'].sum()/1e6:.2f}M")
    c3.metric("Avg Margin", f"{perf['margin_pct'].mean():.1f}%")
    c4.metric("Avg Return Rate", f"{perf['return_rate'].mean():.1f}%")

    st.markdown("---")
    col1, col2 = st.columns(2)

    top15 = perf.nlargest(15, "gross_revenue")
    fig_top = px.bar(top15, x="gross_revenue", y="product_id",
                     orientation="h", color="margin_pct",
                     color_continuous_scale="RdYlGn",
                     title="Top 15 Products by Revenue  |  color = Margin",
                     labels={"gross_revenue": "Revenue ($)", "product_id": "Product"})
    fig_top.update_yaxes(autorange="reversed")
    col1.plotly_chart(fig_top, use_container_width=True)

    fig_bubble = px.scatter(
        perf[perf["gross_revenue"] > 0],
        x="rating", y="gross_revenue",
        size="units_sold", color="margin_pct",
        color_continuous_scale="RdYlGn",
        title="Rating vs Revenue  |  size = Units Sold",
        labels={"rating": "Avg Rating", "gross_revenue": "Revenue ($)"},
        hover_data=["product_id", "category"],
        size_max=40, opacity=0.65,
    )
    col2.plotly_chart(fig_bubble, use_container_width=True)

    # Category
    if not cat.empty:
        fig_cat = px.bar(cat, x="category", y=["total_revenue", "total_profit"],
                         barmode="group", title="Revenue vs Profit by Category",
                         labels={"value": "$", "variable": "Metric"},
                         color_discrete_sequence=["#3498db", "#2ecc71"])
        st.plotly_chart(fig_cat, use_container_width=True)

    st.subheader("Top 20 Products")
    st.dataframe(
        perf.nlargest(20, "gross_revenue")[
            ["product_id", "category", "price", "rating",
             "units_sold", "gross_revenue", "margin_pct", "return_rate"]
        ].round(2),
        use_container_width=True,
    )


# ── Page: A/B Testing ─────────────────────────────────────────────────────────
elif page == "A/B Testing":
    st.title("A/B Testing Framework")
    st.caption("Simulated experiment: New Checkout UI vs Control")

    # Run inline for demo
    from analysis.ab_testing import simulate_experiment

    results = simulate_experiment()
    conv = results["conversion_test"]
    rev  = results["revenue_test"]
    mv   = results["multivariant"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Control CVR",   f"{conv.control_mean*100:.2f}%")
    c2.metric("Treatment CVR", f"{conv.treatment_mean*100:.2f}%",
              delta=f"{conv.relative_lift_pct:+.1f}%")
    c3.metric("p-value",       f"{conv.p_value:.4f}",
              delta="SIGNIFICANT" if conv.is_significant else "NOT SIGNIFICANT")
    c4.metric("Stat Power",    f"{conv.stat_power:.0%}")

    st.info(f"**Recommendation:** {conv.recommendation}")
    st.markdown("---")

    col1, col2 = st.columns(2)

    # Conversion comparison
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=["Control", "Treatment"],
        y=[conv.control_mean * 100, conv.treatment_mean * 100],
        marker_color=["#95a5a6", "#2ecc71" if conv.is_significant else "#e67e22"],
        text=[f"{conv.control_mean*100:.2f}%", f"{conv.treatment_mean*100:.2f}%"],
        textposition="outside",
    ))
    fig_bar.update_layout(title="Conversion Rate Comparison", yaxis_title="%", showlegend=False)
    col1.plotly_chart(fig_bar, use_container_width=True)

    # Multi-variant
    mv_colors = ["#2ecc71" if s else "#e74c3c" for s in mv["significant"]]
    fig_mv = go.Figure(go.Bar(
        x=mv["variant"],
        y=mv["vs_control_lift_pct"],
        marker_color=mv_colors,
        text=[f"{v:+.2f}%" for v in mv["vs_control_lift_pct"]],
        textposition="outside",
    ))
    fig_mv.add_hline(y=0, line_dash="dash", line_color="black")
    fig_mv.update_layout(title="Multi-Variant: Lift vs Control (%)", yaxis_title="Lift (%)")
    col2.plotly_chart(fig_mv, use_container_width=True)

    # Revenue test summary
    st.subheader("Revenue per Session Test")
    rev_data = {
        "Metric":           ["Control Mean", "Treatment Mean", "Absolute Lift",
                             "Relative Lift", "p-value", "Power"],
        "Value":            [f"${rev.control_mean:.2f}", f"${rev.treatment_mean:.2f}",
                             f"${rev.absolute_lift:+.2f}", f"{rev.relative_lift_pct:+.2f}%",
                             f"{rev.p_value:.4f}", f"{rev.stat_power:.0%}"],
        "Significant":      ["", "", "", "",
                             "Yes" if rev.is_significant else "No", ""],
    }
    st.table(pd.DataFrame(rev_data))

    st.subheader("Multi-Variant Results")
    st.dataframe(mv, use_container_width=True)

    st.markdown("---")
    st.subheader("Sample Size Calculator")
    col1, col2, col3 = st.columns(3)
    baseline = col1.number_input("Baseline CVR (%)", value=3.2, step=0.1) / 100
    mde      = col2.number_input("Min. Detectable Effect (pp)", value=0.3, step=0.1) / 100
    power    = col3.selectbox("Statistical Power", [0.80, 0.90], index=0)

    from analysis.ab_testing import required_sample_size
    n = required_sample_size(baseline, mde, power=power)
    st.success(f"Required sample size: **{n:,} per variant** ({n*2:,} total)")
