"""Build the compact, interactive dashboard data model.

The full source database is useful for analysis but is too large for a
standard GitHub/Streamlit deployment. This extract keeps one row per session
and rolls orders/pageviews up to that session, preserving dynamic dashboard
filters without shipping the raw event tables.

Usage: python3 build_dashboard_data.py
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB = os.path.join(BASE_DIR, "fuzzy_factory.db")
OUTPUT_DB = os.path.join(BASE_DIR, "dashboard_data.db")


def main() -> None:
    if not os.path.exists(SOURCE_DB):
        raise SystemExit("fuzzy_factory.db not found; run load_data.py first")

    source_uri = f"file:{SOURCE_DB}?mode=ro"
    source = sqlite3.connect(source_uri, uri=True)
    sessions = pd.read_sql_query(
        """
        WITH order_rollup AS (
            SELECT website_session_id,
                   COUNT(*) AS orders,
                   SUM(price_usd) AS revenue
            FROM orders
            GROUP BY website_session_id
        ),
        pageview_rollup AS (
            SELECT website_session_id,
                   COUNT(*) AS pageviews
            FROM website_pageviews
            GROUP BY website_session_id
        )
        SELECT s.website_session_id,
               s.created_at,
               s.utm_source,
               s.utm_campaign,
               s.device_type,
               s.is_repeat_session,
               COALESCE(p.pageviews, 0) AS pageviews,
               COALESCE(o.orders, 0) AS orders,
               COALESCE(o.revenue, 0.0) AS revenue
        FROM website_sessions s
        LEFT JOIN order_rollup o USING (website_session_id)
        LEFT JOIN pageview_rollup p USING (website_session_id)
        ORDER BY s.website_session_id
        """,
        source,
        parse_dates=["created_at"],
    )
    products = pd.read_sql_query(
        "SELECT product_id, created_at, product_name FROM products ORDER BY product_id",
        source,
        parse_dates=["created_at"],
    )
    source_session_count = source.execute(
        "SELECT COUNT(*) FROM website_sessions"
    ).fetchone()[0]
    source.close()

    if len(sessions) != source_session_count:
        raise SystemExit("Dashboard extract changed the session grain")
    if sessions["website_session_id"].duplicated().any():
        raise SystemExit("Dashboard extract contains duplicate sessions")

    sessions["month"] = sessions["created_at"].dt.to_period("M").astype(str)
    sessions["channel"] = (
        sessions["utm_source"].fillna("direct/none")
        + " / "
        + sessions["utm_campaign"].fillna("none")
    )

    if os.path.exists(OUTPUT_DB):
        os.remove(OUTPUT_DB)
    output = sqlite3.connect(OUTPUT_DB)
    sessions.to_sql("dashboard_sessions", output, index=False, if_exists="replace")
    products.to_sql("products", output, index=False, if_exists="replace")
    output.execute(
        "CREATE INDEX idx_dashboard_sessions_created "
        "ON dashboard_sessions (created_at)"
    )
    output.execute(
        "CREATE INDEX idx_dashboard_sessions_channel "
        "ON dashboard_sessions (channel)"
    )
    output.execute(
        "CREATE INDEX idx_dashboard_sessions_device "
        "ON dashboard_sessions (device_type)"
    )
    output.commit()
    output.execute("VACUUM")
    output.close()

    size_mb = os.path.getsize(OUTPUT_DB) / (1024 * 1024)
    print(f"Built {OUTPUT_DB}")
    print(f"Sessions: {len(sessions):,}; products: {len(products):,}")
    print(f"Dashboard database size: {size_mb:.1f} MB")
    if size_mb >= 100:
        raise SystemExit("Dashboard database is too large for GitHub's file limit")


if __name__ == "__main__":
    main()
