-- ============================================================
--  E-Commerce Analytics SQL Queries
--  Compatible with: Amazon Redshift, PostgreSQL, Athena, Snowflake
-- ============================================================


-- ── 1. REVENUE OVERVIEW ──────────────────────────────────────────────────────

-- Daily revenue with rolling 7-day average
SELECT
    order_date,
    SUM(total_amount)                                      AS daily_revenue,
    COUNT(DISTINCT order_id)                               AS orders,
    COUNT(DISTINCT customer_id)                            AS unique_customers,
    SUM(total_amount) / COUNT(DISTINCT order_id)           AS aov,
    AVG(SUM(total_amount)) OVER (
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                                      AS revenue_7d_avg
FROM orders
WHERE status = 'delivered'
GROUP BY order_date
ORDER BY order_date;


-- Monthly Revenue + MoM Growth
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_date) AS month,
        SUM(total_amount)               AS revenue
    FROM orders
    WHERE status = 'delivered'
    GROUP BY 1
)
SELECT
    month,
    revenue,
    LAG(revenue)  OVER (ORDER BY month)                        AS prev_month_revenue,
    LAG(revenue, 12) OVER (ORDER BY month)                     AS prev_year_revenue,
    ROUND(
        (revenue - LAG(revenue)  OVER (ORDER BY month)) /
        NULLIF(LAG(revenue)  OVER (ORDER BY month), 0) * 100, 2
    )                                                          AS mom_growth_pct,
    ROUND(
        (revenue - LAG(revenue, 12) OVER (ORDER BY month)) /
        NULLIF(LAG(revenue, 12) OVER (ORDER BY month), 0) * 100, 2
    )                                                          AS yoy_growth_pct
FROM monthly
ORDER BY month;


-- ── 2. CUSTOMER METRICS ───────────────────────────────────────────────────────

-- RFM Scoring (Redshift-compatible)
WITH rfm_base AS (
    SELECT
        customer_id,
        DATEDIFF('day', MAX(order_date), CURRENT_DATE)    AS recency,
        COUNT(DISTINCT order_id)                           AS frequency,
        SUM(total_amount)                                  AS monetary
    FROM orders
    WHERE status = 'delivered'
    GROUP BY customer_id
),
rfm_scores AS (
    SELECT
        customer_id, recency, frequency, monetary,
        NTILE(5) OVER (ORDER BY recency DESC)              AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)             AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)              AS m_score
    FROM rfm_base
)
SELECT
    *,
    r_score + f_score + m_score                            AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4  THEN 'Champions'
        WHEN f_score >= 3 AND m_score >= 3                    THEN 'Loyal Customers'
        WHEN r_score >= 3 AND f_score <= 2                    THEN 'Potential Loyalist'
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3   THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2   THEN 'Hibernating'
        ELSE 'Others'
    END                                                    AS segment
FROM rfm_scores;


-- Customer Acquisition by Channel & Cohort
SELECT
    DATE_TRUNC('month', c.signup_date)                     AS cohort_month,
    c.channel,
    COUNT(DISTINCT c.customer_id)                          AS new_customers,
    COUNT(DISTINCT o.order_id)                             AS first_orders,
    SUM(o.total_amount)                                    AS first_month_revenue,
    SUM(o.total_amount) / NULLIF(COUNT(DISTINCT c.customer_id), 0) AS rev_per_new_customer
FROM customers c
LEFT JOIN orders o
    ON c.customer_id = o.customer_id
    AND DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', c.signup_date)
    AND o.status = 'delivered'
GROUP BY 1, 2
ORDER BY 1, 3 DESC;


-- ── 3. COHORT RETENTION ───────────────────────────────────────────────────────

-- Month-N retention rates (pivot-friendly output)
WITH cohort_base AS (
    SELECT
        c.customer_id,
        DATE_TRUNC('month', c.signup_date)                 AS cohort_month,
        DATE_TRUNC('month', o.order_date)                  AS order_month
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'delivered'
),
cohort_orders AS (
    SELECT
        cohort_month,
        customer_id,
        DATEDIFF('month', cohort_month, order_month)       AS period_number
    FROM cohort_base
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_n
    FROM cohort_orders
    WHERE period_number = 0
    GROUP BY cohort_month
)
SELECT
    co.cohort_month,
    cs.cohort_n,
    co.period_number,
    COUNT(DISTINCT co.customer_id)                         AS active_customers,
    ROUND(
        COUNT(DISTINCT co.customer_id)::FLOAT / cs.cohort_n * 100, 2
    )                                                      AS retention_rate
FROM cohort_orders co
JOIN cohort_size   cs USING (cohort_month)
WHERE co.period_number BETWEEN 0 AND 12
GROUP BY 1, 2, 3
ORDER BY 1, 3;


-- ── 4. PRODUCT ANALYTICS ─────────────────────────────────────────────────────

-- Top products by revenue with margin
SELECT
    oi.product_id,
    p.category,
    p.price,
    p.rating,
    SUM(oi.quantity)                                       AS units_sold,
    SUM(oi.revenue)                                        AS gross_revenue,
    SUM(oi.quantity * p.cost)                              AS cogs,
    SUM(oi.revenue) - SUM(oi.quantity * p.cost)            AS gross_profit,
    ROUND(
        (SUM(oi.revenue) - SUM(oi.quantity * p.cost)) /
        NULLIF(SUM(oi.revenue), 0) * 100, 2
    )                                                      AS margin_pct,
    RANK() OVER (ORDER BY SUM(oi.revenue) DESC)            AS revenue_rank
FROM order_items oi
JOIN products     p  USING (product_id)
JOIN orders       o  ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY 1, 2, 3, 4
ORDER BY gross_revenue DESC
LIMIT 50;


-- Category performance summary
SELECT
    p.category,
    COUNT(DISTINCT p.product_id)                           AS products,
    SUM(oi.quantity)                                       AS units_sold,
    SUM(oi.revenue)                                        AS total_revenue,
    ROUND(AVG(p.rating), 2)                                AS avg_rating,
    ROUND(
        SUM(oi.revenue) / SUM(SUM(oi.revenue)) OVER () * 100, 2
    )                                                      AS revenue_share_pct
FROM order_items oi
JOIN products     p  USING (product_id)
JOIN orders       o  ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY p.category
ORDER BY total_revenue DESC;


-- ── 5. CONVERSION FUNNEL ─────────────────────────────────────────────────────

-- Clickstream funnel: view → add_to_cart → purchase
WITH funnel AS (
    SELECT
        customer_id,
        MAX(CASE WHEN event_type = 'view'        THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS added_to_cart,
        MAX(CASE WHEN event_type = 'purchase'    THEN 1 ELSE 0 END) AS purchased
    FROM events
    GROUP BY customer_id
)
SELECT
    COUNT(*)                                               AS total_visitors,
    SUM(viewed)                                            AS product_viewers,
    SUM(added_to_cart)                                     AS added_to_cart,
    SUM(purchased)                                         AS purchasers,
    ROUND(SUM(added_to_cart)::FLOAT / NULLIF(SUM(viewed), 0) * 100, 2)
                                                           AS view_to_cart_pct,
    ROUND(SUM(purchased)::FLOAT    / NULLIF(SUM(added_to_cart), 0) * 100, 2)
                                                           AS cart_to_purchase_pct,
    ROUND(SUM(purchased)::FLOAT    / NULLIF(COUNT(*), 0) * 100, 2)
                                                           AS overall_cvr_pct
FROM funnel;


-- ── 6. PRIME vs NON-PRIME ANALYSIS ───────────────────────────────────────────

SELECT
    is_prime_order,
    COUNT(DISTINCT customer_id)                            AS customers,
    COUNT(DISTINCT order_id)                               AS orders,
    ROUND(AVG(total_amount), 2)                            AS avg_order_value,
    ROUND(SUM(total_amount), 2)                            AS total_revenue,
    ROUND(COUNT(DISTINCT order_id)::FLOAT /
          COUNT(DISTINCT customer_id), 2)                  AS orders_per_customer
FROM orders
WHERE status = 'delivered'
GROUP BY is_prime_order;


-- ── 7. DEMAND FORECASTING INPUT ───────────────────────────────────────────────

-- Weekly sales by category (input for time-series models)
SELECT
    DATE_TRUNC('week', order_date)                         AS week,
    p.category,
    SUM(oi.quantity)                                       AS units,
    SUM(oi.revenue)                                        AS revenue
FROM order_items oi
JOIN products     p USING (product_id)
JOIN orders       o ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY 1, 2
ORDER BY 1, 2;
