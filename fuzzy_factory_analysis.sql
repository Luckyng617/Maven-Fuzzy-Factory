-- ============================================================
-- Maven Fuzzy Factory -- Portfolio Analysis
-- Data: Maven Analytics (free Maven Fuzzy Factory dataset)
-- Runs on the local SQLite database built by load_data.py
-- ============================================================


-- ------------------------------------------------------------
-- 1. TREND: Monthly website sessions vs. order volume
-- ------------------------------------------------------------
WITH monthly_sessions AS (
    SELECT strftime('%Y-%m', created_at) AS month,
           COUNT(*) AS sessions
    FROM website_sessions
    GROUP BY month
),
monthly_orders AS (
    SELECT strftime('%Y-%m', created_at) AS month,
           COUNT(*) AS orders
    FROM orders
    GROUP BY month
)
SELECT s.month,
       s.sessions,
       COALESCE(o.orders, 0) AS orders,
       ROUND(100.0 * COALESCE(o.orders, 0) / s.sessions, 2) AS conv_rate_pct
FROM monthly_sessions s
LEFT JOIN monthly_orders o USING (month)
ORDER BY s.month;


-- ------------------------------------------------------------
-- 2. SESSION-TO-ORDER CONVERSION RATE, month over month
-- ------------------------------------------------------------
WITH monthly AS (
    SELECT strftime('%Y-%m', s.created_at) AS month,
           COUNT(*) AS sessions,
           COUNT(o.order_id) AS orders
    FROM website_sessions s
    LEFT JOIN orders o
           ON o.website_session_id = s.website_session_id
    GROUP BY month
)
SELECT month,
       sessions,
       orders,
       ROUND(100.0 * orders / sessions, 2) AS conv_rate_pct,
       ROUND(100.0 * (orders * 1.0 / sessions
            - LAG(orders * 1.0 / sessions) OVER (ORDER BY month))
            / (LAG(orders * 1.0 / sessions) OVER (ORDER BY month)), 2)
            AS conv_rate_change_pct
FROM monthly
ORDER BY month;


-- ------------------------------------------------------------
-- 3a. MARKETING CHANNEL PERFORMANCE
--     Sessions, orders, conversion rate, revenue by utm_source + campaign
-- ------------------------------------------------------------
SELECT s.utm_source,
       s.utm_campaign,
       COUNT(DISTINCT s.website_session_id)                       AS sessions,
       COUNT(DISTINCT o.order_id)                                 AS orders,
       ROUND(100.0 * COUNT(DISTINCT o.order_id)
             / COUNT(DISTINCT s.website_session_id), 2)            AS conv_rate_pct,
       ROUND(COALESCE(SUM(o.price_usd), 0), 2)                    AS revenue_usd,
       ROUND(COALESCE(SUM(o.price_usd), 0)
             / COUNT(DISTINCT s.website_session_id), 2)            AS revenue_per_session
FROM website_sessions s
LEFT JOIN orders o ON o.website_session_id = s.website_session_id
GROUP BY s.utm_source, s.utm_campaign
ORDER BY revenue_usd DESC;


-- ------------------------------------------------------------
-- 3b. CHANNEL MIX BY DEVICE TYPE
--     Conversion rate: desktop vs. mobile per source
-- ------------------------------------------------------------
SELECT utm_source,
       device_type,
       COUNT(DISTINCT s.website_session_id)                       AS sessions,
       COUNT(DISTINCT o.order_id)                                 AS orders,
       ROUND(100.0 * COUNT(DISTINCT o.order_id)
             / COUNT(DISTINCT s.website_session_id), 2)            AS conv_rate_pct
FROM website_sessions s
LEFT JOIN orders o ON o.website_session_id = s.website_session_id
GROUP BY utm_source, device_type
ORDER BY utm_source, device_type;


-- ------------------------------------------------------------
-- 4a. REVENUE PER ORDER AND REVENUE PER SESSION, monthly
-- ------------------------------------------------------------
WITH monthly_sessions AS (
    SELECT strftime('%Y-%m', created_at) AS month,
           COUNT(*) AS sessions
    FROM website_sessions
    GROUP BY month
),
monthly_rev AS (
    SELECT strftime('%Y-%m', created_at) AS month,
           COUNT(*)                      AS orders,
           ROUND(AVG(price_usd), 2)      AS avg_order_value,
           ROUND(SUM(price_usd), 2)      AS revenue
    FROM orders
    GROUP BY month
)
SELECT m.month,
       m.orders,
       m.avg_order_value,
       s.sessions,
       ROUND(m.revenue / s.sessions, 4) AS revenue_per_session
FROM monthly_rev m
JOIN monthly_sessions s USING (month)
ORDER BY m.month;


-- ------------------------------------------------------------
-- 4b. ORDER-PERIOD MARGIN (revenue minus COGS and refunds)
--     Refunds are assigned to the month the related order was created,
--     so all components use the same order-period time basis.
-- ------------------------------------------------------------
WITH monthly_orders AS (
    SELECT strftime('%Y-%m', created_at) AS month,
           ROUND(SUM(price_usd), 2)      AS revenue,
           ROUND(SUM(cogs_usd), 2)       AS cogs
    FROM orders
    GROUP BY month
),
monthly_refunds AS (
    SELECT strftime('%Y-%m', o.created_at) AS month,
           ROUND(SUM(refund_amount_usd), 2) AS refunds
    FROM order_item_refunds r
    JOIN orders o ON o.order_id = r.order_id
    GROUP BY month
)
SELECT o.month,
       o.revenue,
       o.cogs,
       COALESCE(r.refunds, 0)                          AS refunds,
       ROUND(o.revenue - o.cogs - COALESCE(r.refunds, 0), 2) AS net_margin,
       ROUND(100.0 * (o.revenue - o.cogs - COALESCE(r.refunds, 0))
             / o.revenue, 2)                           AS margin_pct
FROM monthly_orders o
LEFT JOIN monthly_refunds r USING (month)
ORDER BY o.month;


-- ------------------------------------------------------------
-- BONUS A. Repeat vs. new sessions over time (loyalty trend)
-- ------------------------------------------------------------
SELECT strftime('%Y-%m', created_at) AS month,
       COUNT(*)                                                AS sessions,
       SUM(is_repeat_session)                                  AS repeat_sessions,
       ROUND(100.0 * SUM(is_repeat_session) / COUNT(*), 2)     AS repeat_pct
FROM website_sessions
GROUP BY month
ORDER BY month;


-- ------------------------------------------------------------
-- BONUS B. Product launch impact on order volume
-- ------------------------------------------------------------
SELECT p.product_name,
       p.created_at                                   AS launch_date,
       COUNT(o.order_id)                              AS lifetime_orders,
       ROUND(SUM(oi.price_usd), 2)                    AS lifetime_revenue,
       ROUND(AVG(oi.price_usd), 2)                    AS avg_price
FROM products p
LEFT JOIN order_items oi ON oi.product_id = p.product_id
LEFT JOIN orders o       ON o.order_id    = oi.order_id
WHERE oi.is_primary_item = 1
GROUP BY p.product_id
ORDER BY p.product_id;


-- ------------------------------------------------------------
-- BONUS C. Pageview depth per session (engagement proxy)
-- ------------------------------------------------------------
SELECT pageviews_in_session,
       COUNT(*)                                AS sessions,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM website_sessions), 2) AS pct_of_sessions
FROM (
    SELECT s.website_session_id,
           COUNT(p.website_pageview_id) AS pageviews_in_session
    FROM website_sessions s
    LEFT JOIN website_pageviews p
           ON p.website_session_id = s.website_session_id
    GROUP BY s.website_session_id
)
GROUP BY pageviews_in_session
ORDER BY pageviews_in_session;
