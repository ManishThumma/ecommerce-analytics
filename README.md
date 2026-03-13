# E-Commerce Analytics Platform

A full-stack data analytics project that mirrors the kind of instrumentation, analysis, and experimentation infrastructure used at large-scale e-commerce companies.

**Live Dashboard → [manish-ecommerce-analytics.streamlit.app](https://manish-ecommerce-analytics.streamlit.app)**

---

## What's Inside

| Module | Technique | Business Question Answered |
|---|---|---|
| `data/generate_data.py` | Synthetic data generation | Creates 5K customers, 500 products, 40K orders |
| `analysis/sales_trends.py` | Time-series, YoY growth, seasonal naive forecast | *Where is revenue heading?* |
| `analysis/rfm_analysis.py` | RFM scoring + behavioral segmentation | *Who are my best customers?* |
| `analysis/product_analytics.py` | Margin analysis, return rate, rating-revenue correlation | *Which products drive profit?* |
| `analysis/cohort_analysis.py` | Cohort retention matrix, cumulative LTV curves | *Are we retaining customers?* |
| `analysis/ab_testing.py` | Two-proportion z-test, Welch's t-test, Bonferroni-corrected A/B/n | *Did the experiment work?* |
| `sql/analytics_queries.sql` | Redshift/Athena-compatible analytical SQL | Production-ready query library |
| `dashboard/app.py` | Interactive Streamlit dashboard | End-to-end analytics UI |

---

## Project Structure

```
amazon-analytics/
├── data/
│   └── generate_data.py       # Generates customers, orders, products, events CSVs
├── analysis/
│   ├── rfm_analysis.py        # Customer segmentation
│   ├── sales_trends.py        # Revenue trend + forecasting
│   ├── product_analytics.py   # Product & category performance
│   ├── cohort_analysis.py     # Retention & LTV cohorts
│   └── ab_testing.py          # Statistical testing framework
├── dashboard/
│   └── app.py                 # Streamlit multi-page dashboard
├── sql/
│   └── analytics_queries.sql  # Production SQL (Redshift / Athena / Postgres)
├── outputs/                   # Auto-generated charts and CSVs
├── run_all.py                 # One-shot pipeline runner
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the full pipeline (generates data + all analyses)
```bash
python run_all.py
```

### 3. Launch the dashboard
```bash
streamlit run dashboard/app.py
```

---

## Analysis Highlights

### RFM Segmentation
Customers are scored on three dimensions (1–5 each):
- **Recency** — how recently they placed an order
- **Frequency** — how often they order
- **Monetary** — total spend

Segments produced: Champions, Loyal Customers, Potential Loyalist, At Risk, Hibernating.

### A/B Testing
The framework supports:
- **Two-proportion z-test** for conversion rate experiments
- **Welch's t-test** for revenue/AOV experiments
- **Multi-variant (A/B/n)** with Bonferroni correction
- **Sample size calculator** given baseline rate and MDE

### Cohort Retention
Customers are grouped by signup month. The retention heatmap shows what percentage of each cohort is still ordering in months 1–12, giving a direct view of long-term customer loyalty.

### Sales Forecasting
Uses a **seasonal naive** model — last year's value for the same month × YoY growth factor. Simple, interpretable, and surprisingly competitive on stable seasonal data.

---

## SQL Layer

All queries in `sql/analytics_queries.sql` are written for **Amazon Redshift** syntax but are compatible with PostgreSQL, Athena (Presto), and Snowflake with minor adjustments. Queries cover:

- Rolling 7-day average revenue
- MoM and YoY growth with window functions
- RFM scoring using `NTILE`
- Cohort retention in a single CTE chain
- Conversion funnel from clickstream events
- Prime vs Non-Prime customer comparison

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data processing | pandas, numpy |
| Statistical tests | scipy.stats |
| Visualisation | matplotlib, seaborn, plotly |
| Dashboard | Streamlit |
| Data warehouse SQL | Amazon Redshift / PostgreSQL |

---

## Output Files

After running the pipeline, the `outputs/` folder contains:

| File | Description |
|---|---|
| `monthly_revenue.csv` | Month-level revenue, orders, AOV, MoM/YoY growth |
| `category_monthly.csv` | Category-level monthly revenue |
| `rfm_scores.csv` | Per-customer RFM scores and segment labels |
| `rfm_summary.csv` | Segment-level aggregates |
| `product_performance.csv` | Per-product revenue, margin, return rate |
| `category_summary.csv` | Category-level margin and revenue share |
| `cohort_retention.csv` | Retention matrix (cohort × period) |
| `cohort_ltv.csv` | Cumulative LTV by cohort |
| `ab_test_multivariant.csv` | Multi-variant test results |
| `*.png` | Publication-quality charts |
