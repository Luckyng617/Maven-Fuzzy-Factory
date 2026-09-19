import os
import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Maven Fuzzy Factory | E-Commerce Analytics", page_icon="🧸", layout="wide")

BRAND = "#4E2A84"
ACCENT = "#E8983D"

@st.cache_data
def load_data():
    db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_data.db")
    if not os.path.exists(db):
        raise FileNotFoundError(
            "dashboard_data.db is missing. Run build_dashboard_data.py first."
        )
    conn = sqlite3.connect(db)

    sessions = pd.read_sql_query(
        "SELECT website_session_id, created_at, utm_source, utm_campaign, "
        "device_type, is_repeat_session, pageviews, orders, revenue, month, channel "
        "FROM dashboard_sessions",
        conn, parse_dates=["created_at"],
    )
    products = pd.read_sql_query(
        "SELECT product_id, created_at, product_name FROM products",
        conn, parse_dates=["created_at"],
    )
    conn.close()
    return sessions, products

try:
    sessions, products = load_data()
except (FileNotFoundError, sqlite3.Error) as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.title("Maven Fuzzy Factory")
st.sidebar.caption("Toy Store E-Commerce Analytics | 2012-2015")
st.sidebar.markdown("---")

min_d, max_d = sessions["created_at"].min().date(), sessions["created_at"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
channels = st.sidebar.multiselect("Channel (source / campaign)", sorted(sessions["channel"].unique()))
devices = st.sidebar.multiselect("Device type", sorted(sessions["device_type"].unique()))

if isinstance(date_range, (tuple, list)):
    start_date = date_range[0]
    end_date = date_range[-1]
else:
    start_date = end_date = date_range
start, end = pd.Timestamp(start_date), pd.Timestamp(end_date) + pd.Timedelta(days=1)
mask = (sessions["created_at"] >= start) & (sessions["created_at"] < end)
if channels:
    mask &= sessions["channel"].isin(channels)
if devices:
    mask &= sessions["device_type"].isin(devices)

sel_sessions = sessions.loc[mask]

if sel_sessions.empty:
    st.warning("No sessions match the selected filters. Adjust the date, channel, or device filters.")
    st.stop()

n_sessions = len(sel_sessions)
n_orders = int(sel_sessions["orders"].sum())
conv = 100 * n_orders / n_sessions if n_sessions else 0
revenue = sel_sessions["revenue"].sum()
aov = revenue / n_orders if n_orders else 0
rev_per_session = revenue / n_sessions if n_sessions else 0

st.title("🧸 Maven Fuzzy Factory — Marketing & Conversion Analytics")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Sessions", f"{n_sessions:,}")
c2.metric("Orders", f"{n_orders:,}")
c3.metric("Conversion Rate", f"{conv:.2f}%")
c4.metric("Revenue", f"${revenue:,.0f}")
c5.metric("Avg Order Value", f"${aov:,.2f}")

st.caption(f"Revenue per session: ${rev_per_session:,.2f}")

# ---- Monthly sessions vs orders + conversion rate ----
trend = (
    sel_sessions.groupby("month")
    .agg(Sessions=("website_session_id", "size"), Orders=("orders", "sum"))
    .reset_index()
)
trend["Orders"] = trend["Orders"].fillna(0)
trend["Conversion %"] = 100 * trend["Orders"] / trend["Sessions"]

fig_trend = go.Figure()
fig_trend.add_bar(x=trend["month"], y=trend["Sessions"], name="Sessions", marker_color="#B8C4D9")
fig_trend.add_bar(x=trend["month"], y=trend["Orders"], name="Orders", marker_color=ACCENT)
fig_trend.add_scatter(x=trend["month"], y=trend["Conversion %"], name="Conversion %", mode="lines+markers", yaxis="y2", line=dict(color=BRAND, width=3))
fig_trend.update_layout(
    title="Monthly Sessions, Orders & Conversion Rate",
    barmode="group", height=420,
    yaxis=dict(title="Count"),
    yaxis2=dict(title="Conversion %", overlaying="y", side="right", range=[0, max(float(trend["Conversion %"].max()) * 1.8, 1)]),
    legend=dict(orientation="h", y=1.08, x=0),
    margin=dict(t=60, l=20, r=20),
)
st.plotly_chart(fig_trend, width="stretch")

col1, col2 = st.columns([3, 2])

# ---- Channel performance ----
chan = (
    sel_sessions.groupby("channel")
    .agg(Sessions=("website_session_id", "count"), Orders=("orders", "sum"), Revenue=("revenue", "sum"))
    .reset_index()
)
chan["Conv %"] = 100 * chan["Orders"] / chan["Sessions"]
chan = chan.sort_values("Revenue", ascending=True).reset_index(drop=True)

fig_chan = go.Figure()
fig_chan.add_bar(x=chan["Revenue"], y=chan["channel"], orientation="h", name="Revenue", marker_color=BRAND, customdata=chan[["Sessions", "Conv %"]])
fig_chan.update_traces(hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<br>Sessions: %{customdata[0]:,}<br>Conversion: %{customdata[1]:.2f}%<extra></extra>")
fig_chan.update_layout(title="Revenue by Marketing Channel", height=420, margin=dict(t=50, l=20, r=20), xaxis_title="Revenue (USD)")
col1.plotly_chart(fig_chan, width="stretch")

# ---- Device split ----
dev = (
    sel_sessions.groupby("device_type")
    .agg(Sessions=("website_session_id", "count"), Orders=("orders", "sum"))
    .reset_index()
)
dev["Conv %"] = 100 * dev["Orders"] / dev["Sessions"]

fig_dev = go.Figure()
fig_dev.add_bar(x=dev["device_type"], y=dev["Sessions"], name="Sessions", marker_color="#B8C4D9")
fig_dev.add_scatter(x=dev["device_type"], y=dev["Conv %"], name="Conversion %", mode="lines+markers", yaxis="y2", line=dict(color=ACCENT, width=3))
fig_dev.update_layout(
    title="Desktop vs. Mobile", height=420, margin=dict(t=50, l=20, r=20),
    yaxis=dict(title="Sessions"),
    yaxis2=dict(title="Conversion %", overlaying="y", side="right", range=[0, max(float(dev["Conv %"].max()) * 1.6, 1)]),
    legend=dict(orientation="h", y=1.08, x=0),
)
col2.plotly_chart(fig_dev, width="stretch")

# ---- AOV & revenue per session over time ----
if n_orders:
    aov_month = (
        sel_sessions.groupby("month")
        .agg(Revenue=("revenue", "sum"), Orders=("orders", "sum"), Sessions=("website_session_id", "size"))
        .reset_index()
    )
    aov_month["AOV"] = aov_month["Revenue"] / aov_month["Orders"]
    aov_month["Rev / Session"] = aov_month["Revenue"] / aov_month["Sessions"]

    fig_rev = go.Figure()
    fig_rev.add_scatter(x=aov_month["month"], y=aov_month["AOV"], name="Avg Order Value", mode="lines+markers", line=dict(color=BRAND, width=3))
    fig_rev.add_scatter(x=aov_month["month"], y=aov_month["Rev / Session"], name="Revenue per Session", mode="lines+markers", line=dict(color=ACCENT, width=3))
    for launch in products["created_at"]:
        d = launch.strftime("%Y-%m")
        if aov_month["month"].min() <= d <= aov_month["month"].max():
            fig_rev.add_vline(x=d, line=dict(color="#888", dash="dot"), opacity=0.6)
    fig_rev.update_layout(
        title="Revenue per Order & Revenue per Session (dotted lines = product launches)",
        height=420, margin=dict(t=60, l=20, r=20), yaxis_title="USD",
        legend=dict(orientation="h", y=1.08, x=0),
    )
    st.plotly_chart(fig_rev, width="stretch")
else:
    st.info("No orders match the selected filters, so revenue trend charts are unavailable.")

# ---- Engagement & repeat sessions ----
col3, col4 = st.columns(2)

pv = sel_sessions["pageviews"]
fig_pv = px.histogram(x=pv, nbins=15, title="Pageviews per Session", labels={"x": "Pageviews", "count": "Sessions"})
fig_pv.update_traces(marker_color="#B8C4D9")
fig_pv.update_layout(height=380, margin=dict(t=50, l=20, r=20), showlegend=False)
col3.plotly_chart(fig_pv, width="stretch")

repeat = sel_sessions.groupby("month").agg(
    Sessions=("website_session_id", "count"),
    Repeat=("is_repeat_session", "sum"),
).reset_index()
repeat["Repeat %"] = 100 * repeat["Repeat"] / repeat["Sessions"]
fig_rep = px.area(repeat, x="month", y="Repeat %", title="Repeat Sessions Over Time")
fig_rep.update_traces(line_color=BRAND)
fig_rep.update_layout(height=380, margin=dict(t=50, l=20, r=20))
col4.plotly_chart(fig_rep, width="stretch")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: Maven Fuzzy Factory dataset (Maven Analytics). "
    "Built with SQL + Python (Streamlit, Plotly)."
)
