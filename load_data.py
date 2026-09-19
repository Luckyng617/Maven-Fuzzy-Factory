"""Load Maven Fuzzy Factory CSVs into a local SQLite database.

Usage: python3 load_data.py
Creates fuzzy_factory.db in the same folder.
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
DB_PATH = os.path.join(BASE_DIR, "fuzzy_factory.db")

TABLES = {
    "website_sessions": {
        "file": "website_sessions.csv",
        "dtypes": {
            "website_session_id": "int64",
            "user_id": "int64",
            "is_repeat_session": "int64",
            "utm_source": "str",
            "utm_campaign": "str",
            "utm_content": "str",
            "device_type": "str",
            "http_referer": "str",
        },
        "dates": ["created_at"],
    },
    "website_pageviews": {
        "file": "website_pageviews.csv",
        "dtypes": {
            "website_pageview_id": "int64",
            "website_session_id": "int64",
            "pageview_url": "str",
        },
        "dates": ["created_at"],
    },
    "orders": {
        "file": "orders.csv",
        "dtypes": {
            "order_id": "int64",
            "website_session_id": "int64",
            "user_id": "int64",
            "primary_product_id": "int64",
            "items_purchased": "int64",
            "price_usd": "float64",
            "cogs_usd": "float64",
        },
        "dates": ["created_at"],
    },
    "order_items": {
        "file": "order_items.csv",
        "dtypes": {
            "order_item_id": "int64",
            "order_id": "int64",
            "product_id": "int64",
            "is_primary_item": "int64",
            "price_usd": "float64",
            "cogs_usd": "float64",
        },
        "dates": ["created_at"],
    },
    "order_item_refunds": {
        "file": "order_item_refunds.csv",
        "dtypes": {
            "order_item_refund_id": "int64",
            "order_item_id": "int64",
            "order_id": "int64",
            "refund_amount_usd": "float64",
        },
        "dates": ["created_at"],
    },
    "products": {
        "file": "products.csv",
        "dtypes": {"product_id": "int64", "product_name": "str"},
        "dates": ["created_at"],
    },
}

EXPECTED_ROWS = {
    "website_sessions": 472871,
    "website_pageviews": 1188124,
    "orders": 32313,
    "order_items": 40025,
    "order_item_refunds": 1731,
    "products": 4,
}


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    for table, spec in TABLES.items():
        df = pd.read_csv(
            os.path.join(RAW_DATA_DIR, spec["file"]),
            dtype=spec["dtypes"],
        )
        for col in spec["dates"]:
            df[col] = pd.to_datetime(df[col])

        df.to_sql(table, conn, index=False, if_exists="replace")
        conn.execute(
            f"CREATE INDEX idx_{table}_created ON {table} (created_at)"
        )

    # Extra indexes for the dashboard's filter queries
    conn.execute(
        "CREATE INDEX idx_ws_source_campaign "
        "ON website_sessions (utm_source, utm_campaign)"
    )
    conn.execute(
        "CREATE INDEX idx_pv_session ON website_pageviews (website_session_id)"
    )
    conn.execute(
        "CREATE INDEX idx_orders_session ON orders (website_session_id)"
    )
    conn.commit()

    print(f"Loaded tables into {DB_PATH}")
    print(f"{'table':<22}{'rows loaded':>12}{'expected':>10}  match")
    ok = True
    for table, expected in EXPECTED_ROWS.items():
        (loaded,) = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()
        match = loaded == expected
        ok = ok and match
        print(f"{table:<22}{loaded:>12,}{expected:>10,}  {'OK' if match else 'MISMATCH'}")

    conn.close()
    if not ok:
        raise SystemExit("Row counts do not match the source CSVs")
    print("Verification passed.")


if __name__ == "__main__":
    main()
