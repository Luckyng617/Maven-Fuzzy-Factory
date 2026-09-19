"""Generate portfolio-quality PNG charts for the Maven Fuzzy Factory analysis.

Usage: python3 make_charts.py   -> writes charts/*.png
"""

import os
import sqlite3

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "charts")
os.makedirs(OUT_DIR, exist_ok=True)

PURPLE = "#4E2A84"
ORANGE = "#E8983D"
GREY = "#9AA5B1"
DARK = "#2B2B2B"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#DDDDDD",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
})

conn = sqlite3.connect(os.path.join(BASE_DIR, "fuzzy_factory.db"))

sessions = pd.read_sql_query(
    "SELECT website_session_id, created_at, utm_source, utm_campaign, device_type FROM website_sessions",
    conn, parse_dates=["created_at"],
)
orders = pd.read_sql_query(
    "SELECT order_id, created_at, website_session_id, price_usd FROM orders",
    conn, parse_dates=["created_at"],
)
products = pd.read_sql_query(
    "SELECT created_at, product_name FROM products", conn, parse_dates=["created_at"]
)
conn.close()

sessions["month"] = sessions["created_at"].dt.to_period("M").astype(str)
orders["month"] = orders["created_at"].dt.to_period("M").astype(str)

sessions["channel"] = (
    sessions["utm_source"].fillna("direct/none") + " / " + sessions["utm_campaign"].fillna("none")
)

trend = (
    sessions.groupby("month").size().rename("sessions").to_frame()
    .join(orders.groupby("month").size().rename("orders"))
)
trend["conv"] = 100 * trend["orders"] / trend["sessions"]
x = pd.to_datetime(trend.index)

def annotate_launches(ax, top_y):
    for _, row in products.iterrows():
        d = row["created_at"]
        if trend.index.min() <= d.strftime("%Y-%m") <= trend.index.max():
            ax.axvline(d, color=GREY, linestyle=":", linewidth=1.2, alpha=0.8)
            ax.annotate(
                row["product_name"].replace("The ", "") + " launch",
                xy=(d, top_y), fontsize=8, color="#555555",
                rotation=90, va="top", ha="right",
            )

# ------------------------------------------------------------------
# Chart 1: Monthly sessions vs orders + conversion rate
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(x, trend["sessions"], color=PURPLE, linewidth=2.5, label="Sessions")
ax.fill_between(x, trend["sessions"], color=PURPLE, alpha=0.10)
ax.plot(x, trend["orders"], color=ORANGE, linewidth=2.5, label="Orders")
ax.set_title(
    "Maven Fuzzy Factory — 3 Years of Growth\n"
    "Monthly website sessions and order volume, Mar 2012 – Mar 2015"
)
ax.set_ylabel("Count")
ax.yaxis.set_major_formatter(lambda v, _: f"{v/1000:.0f}k")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
annotate_launches(ax, trend["sessions"].max() * 0.55)
ax.set_ylim(0, trend["sessions"].max() * 1.15)

ax2 = ax.twinx()
ax2.spines["top"].set_visible(False)
ax2.plot(x, trend["conv"], color=DARK, linewidth=1.8, linestyle="--", label="Conversion rate")
ax2.set_ylabel("Conversion rate (%)", color=DARK)
ax2.set_ylim(0, 12)
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "1_sessions_orders_trend.png"), dpi=150)
plt.close(fig)

# ------------------------------------------------------------------
# Chart 2: Revenue by marketing channel
# ------------------------------------------------------------------
chan_of_session = sessions.set_index("website_session_id")["channel"]
summary = pd.DataFrame({
    "revenue": orders.assign(channel=orders["website_session_id"].map(chan_of_session))
    .groupby("channel")["price_usd"].sum(),
    "sessions": sessions["channel"].value_counts(),
    "orders": orders["website_session_id"].map(chan_of_session).value_counts(),
}).sort_values("revenue")
summary["conv"] = 100 * summary["orders"] / summary["sessions"]

colors = [GREY] * len(summary)
colors[-1] = ORANGE  # biggest channel highlighted
colors[-2] = PURPLE
fig, ax = plt.subplots(figsize=(11, 5))
ax.barh(summary.index, summary["revenue"] / 1000, color=colors, height=0.62)
ax.set_title(
    "Where the Revenue Comes From\nRevenue by marketing channel, 2012–2015"
)
ax.set_xlabel("Revenue (USD)")
ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}k")
for i, row in enumerate(summary.itertuples()):
    ax.text(row.revenue / 1000 + summary["revenue"].max() / 1000 * 0.015, i,
            f"{row.conv:.1f}% conv", va="center", fontsize=9, color="#555555")
ax.margins(x=0.12)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "2_channel_revenue.png"), dpi=150)
plt.close(fig)

# ------------------------------------------------------------------
# Chart 3: AOV + revenue per session over time
# ------------------------------------------------------------------
aov_m = orders.groupby("month")["price_usd"].mean()
monthly_rev = orders.groupby("month")["price_usd"].sum()
rev_ps = monthly_rev / trend["sessions"]
x3 = pd.to_datetime(aov_m.index)

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(x3, aov_m, color=PURPLE, linewidth=2.5, marker="o", markersize=4, label="Revenue per order (AOV)")
ax.set_ylabel("Revenue per order (USD)", color=PURPLE)
ax.set_ylim(45, 70)
annotate_launches(ax, aov_m.max() * 0.97)

ax3 = ax.twinx()
ax3.spines["top"].set_visible(False)
ax3.plot(x3, rev_ps, color=ORANGE, linewidth=2.5, marker="o", markersize=4, label="Revenue per session")
ax3.set_ylabel("Revenue per session (USD)", color=ORANGE)
ax3.set_ylim(0, rev_ps.max() * 1.25)
ax.set_title(
    "Product Launches Lifted Revenue Metrics\nRevenue per order and per session, monthly"
)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax3.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "3_revenue_per_order_session.png"), dpi=150)
plt.close(fig)

# ------------------------------------------------------------------
# Chart 4: Device conversion gap
# ------------------------------------------------------------------
device_of_session = sessions.set_index("website_session_id")["device_type"]
sess_dev = sessions["device_type"].value_counts()
ord_dev = orders["website_session_id"].map(device_of_session).value_counts()
conv_dev = (100 * ord_dev / sess_dev).reindex(["desktop", "mobile"])

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(conv_dev.index, conv_dev.values, color=[PURPLE, GREY], width=0.45)
for b, v in zip(bars, conv_dev.values):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v:.1f}%",
            ha="center", fontsize=13, fontweight="bold", color=DARK)
ax.set_title(
    "Desktop Converts ~2.7x Better Than Mobile\n"
    "Session-to-order conversion rate by device, 2012–2015"
)
ax.set_ylabel("Conversion rate (%)")
ax.set_ylim(0, 10)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "4_device_gap.png"), dpi=150)
plt.close(fig)

print("Charts written to", OUT_DIR)
for f in sorted(os.listdir(OUT_DIR)):
    print(" -", f)
