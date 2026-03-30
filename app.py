import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.metrics import load_data, compute_kpis

# ─────────────────────────────────────────────
# STREAMLIT CONCEPT 1: st.set_page_config()
# This must be the FIRST Streamlit call in your
# script. It sets the browser tab title, icon,
# and layout (wide = full browser width).
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="UAC Care System Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# STREAMLIT CONCEPT 2: st.cache_data
# Streamlit reruns your ENTIRE script on every
# user interaction. Without caching, it would
# reload the CSV every single time.
# @st.cache_data tells Streamlit: run this once,
# store the result, reuse it on reruns.
# ─────────────────────────────────────────────
@st.cache_data
def get_data():
    return load_data("data/HHS_Unaccompanied_Alien_Children_Program.csv")

df_full = get_data()

# ─────────────────────────────────────────────
# STREAMLIT CONCEPT 3: st.sidebar
# Everything inside `with st.sidebar:` renders
# in the left panel. It's the standard place
# for filters and controls.
# ─────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://www.hhs.gov/sites/default/files/hhs-logo.png",
        width=160
    )
    st.markdown("## Filters")

    # Date range filter
    min_date = df_full["date"].min().date()
    max_date = df_full["date"].max().date()

    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Year quick-select
    st.markdown("**Quick select year**")
    col1, col2, col3, col4 = st.columns(4)
    year_filter = None
    if col1.button("All"):  year_filter = None
    if col2.button("2023"): year_filter = 2023
    if col3.button("2024"): year_filter = 2024
    if col4.button("2025"): year_filter = 2025

    st.markdown("---")

    # Rolling window selector
    rolling_window = st.selectbox(
        "Rolling average window",
        options=[7, 14, 30],
        index=0,
        format_func=lambda x: f"{x}-day avg"
    )

    st.markdown("---")
    st.caption(f"Dataset: {df_full['date'].min().strftime('%b %Y')} – {df_full['date'].max().strftime('%b %Y')}")
    st.caption(f"{len(df_full):,} reporting days")

# Apply date filter
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    df = df_full[
        (df_full["date"].dt.date >= start) &
        (df_full["date"].dt.date <= end)
    ].copy()
else:
    df = df_full.copy()

if year_filter:
    df = df_full[df_full["year"] == year_filter].copy()

# Recompute rolling avg on filtered data with chosen window
df["rolling_hhs"] = df["hhs_care"].rolling(rolling_window, min_periods=1).mean().round(1)
df["rolling_net"]  = df["net_intake"].rolling(rolling_window, min_periods=1).mean().round(1)

kpis = compute_kpis(df)

# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────
st.title("🏥 UAC Care System — Capacity & Load Analytics")
st.caption(
    f"U.S. Department of Health & Human Services · "
    f"Reporting period: {kpis['date_range']} · "
    f"{len(df):,} days selected"
)
st.divider()

# ─────────────────────────────────────────────
# STREAMLIT CONCEPT 4: st.metric()
# Displays a KPI card with a label, value, and
# optional delta (arrow + color for change).
# st.columns(n) splits the row into n equal cols.
# ─────────────────────────────────────────────
st.subheader("Key Performance Indicators")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    label="Total System Load",
    value=f"{kpis['total_load']:,}",
    help="CBP custody + HHS care (latest day)"
)
k2.metric(
    label="Children in HHS Care",
    value=f"{kpis['hhs_care']:,}",
    help="Latest reported HHS care load"
)
k3.metric(
    label="Net Intake Pressure (7d avg)",
    value=f"{kpis['net_pressure']:+,}",
    delta=f"{'↑ Backlog building' if kpis['net_pressure'] > 0 else '↓ Relief trend'}",
    delta_color="inverse"
)
k4.metric(
    label="Discharge Offset Ratio (7d avg)",
    value=f"{kpis['discharge_ratio']}%",
    help="Discharges ÷ Transfers × 100. Above 100% = system relieving."
)
k5.metric(
    label="Peak HHS Load",
    value=f"{kpis['peak_hhs']:,}",
    help=f"Reached on {kpis['peak_date']}"
)

st.divider()

# ─────────────────────────────────────────────
# MODULE 2: SYSTEM LOAD OVERVIEW
# ─────────────────────────────────────────────
st.subheader("System Load Overview")

tab1, tab2, tab3 = st.tabs([
    "📈 HHS Care Trend",
    "⚖️ CBP vs HHS Comparison",
    "🔄 Net Intake & Backlog"
])

with tab1:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df["date"], y=df["hhs_care"],
        name="Daily HHS Care",
        line=dict(color="#B5D4F4", width=1),
        opacity=0.5
    ))
    fig1.add_trace(go.Scatter(
        x=df["date"], y=df["rolling_hhs"],
        name=f"{rolling_window}-Day Rolling Avg",
        line=dict(color="#185FA5", width=2.5)
    ))
    fig1.add_trace(go.Scatter(
        x=df["date"], y=df["total_load"],
        name="Total System Load",
        line=dict(color="#D85A30", width=1.5, dash="dot")
    ))
    # peak annotation
    peak_idx = df["hhs_care"].idxmax()
    fig1.add_annotation(
        x=df.loc[peak_idx, "date"],
        y=df.loc[peak_idx, "hhs_care"],
        text=f"Peak: {df.loc[peak_idx, 'hhs_care']:,}",
        showarrow=True, arrowhead=2,
        bgcolor="#D85A30", font=dict(color="white", size=11),
        arrowcolor="#D85A30"
    )
    fig1.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15),
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Children"
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.caption(
        f"Peak HHS care: **{kpis['peak_hhs']:,}** on {kpis['peak_date']} · "
        f"Volatility index (std dev): ±{kpis['volatility_index']:,}"
    )

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df["date"], y=df["hhs_care"],
        name="HHS Care Load",
        fill="tozeroy", fillcolor="rgba(55,138,221,0.1)",
        line=dict(color="#185FA5", width=2)
    ))
    fig2.add_trace(go.Scatter(
        x=df["date"], y=df["cbp_custody"],
        name="CBP Custody",
        fill="tozeroy", fillcolor="rgba(186,117,23,0.15)",
        line=dict(color="#BA7517", width=2)
    ))
    fig2.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15),
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Children"
    )
    st.plotly_chart(fig2, use_container_width=True)
    col_a, col_b = st.columns(2)
    col_a.metric("Avg CBP Custody (period)", f"{int(df['cbp_custody'].mean()):,}")
    col_b.metric("Avg HHS Care (period)",    f"{int(df['hhs_care'].mean()):,}")

with tab3:
    fig3 = go.Figure()
    # shade positive (backlog building) vs negative (relief)
    fig3.add_trace(go.Bar(
        x=df["date"], y=df["net_intake"],
        name="Daily Net Intake",
        marker_color=np.where(df["net_intake"] > 0, "#E24B4A", "#1D9E75"),
        opacity=0.4
    ))
    fig3.add_trace(go.Scatter(
        x=df["date"], y=df["rolling_net"],
        name=f"{rolling_window}-Day Avg Net Intake",
        line=dict(color="#D85A30", width=2.5)
    ))
    fig3.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
    fig3.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15),
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Net Children/Day"
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Red bars = backlog building (transfers > discharges). Green = system relieving.")

st.divider()

# ─────────────────────────────────────────────
# MODULE 3: MONTHLY BREAKDOWN
# ─────────────────────────────────────────────
st.subheader("Monthly Care Load Breakdown")

monthly = (
    df.groupby("year_month")
    .agg(
        avg_hhs    = ("hhs_care",       "mean"),
        avg_cbp    = ("cbp_custody",    "mean"),
        total_in   = ("cbp_transferred","sum"),
        total_out  = ("hhs_discharged", "sum"),
        net_total  = ("net_intake",     "sum")
    )
    .reset_index()
)
monthly["avg_hhs"] = monthly["avg_hhs"].round(0).astype(int)
monthly["avg_cbp"] = monthly["avg_cbp"].round(0).astype(int)

fig4 = px.bar(
    monthly, x="year_month", y="avg_hhs",
    color="avg_hhs",
    color_continuous_scale=["#1D9E75","#378ADD","#BA7517","#E24B4A"],
    labels={"year_month": "Month", "avg_hhs": "Avg HHS Care"},
    title=""
)
fig4.update_layout(
    height=350,
    margin=dict(l=0, r=0, t=10, b=0),
    coloraxis_showscale=False,
    xaxis=dict(tickangle=45)
)
st.plotly_chart(fig4, use_container_width=True)

# Monthly table
with st.expander("View monthly data table"):
    st.dataframe(
        monthly.rename(columns={
            "year_month": "Month",
            "avg_hhs":    "Avg HHS Care",
            "avg_cbp":    "Avg CBP Custody",
            "total_in":   "Total Transfers In",
            "total_out":  "Total Discharges",
            "net_total":  "Net Intake"
        }),
        use_container_width=True
    )

st.divider()

# ─────────────────────────────────────────────
# MODULE 4: STRESS ANALYSIS
# ─────────────────────────────────────────────
st.subheader("Capacity Stress Analysis")

stress_col1, stress_col2 = st.columns([2, 1])

with stress_col1:
    # Identify high-stress days (HHS care > 75th percentile)
    threshold_75 = df["hhs_care"].quantile(0.75)
    threshold_90 = df["hhs_care"].quantile(0.90)

    df["stress_level"] = "Normal"
    df.loc[df["hhs_care"] >= threshold_75, "stress_level"] = "Elevated"
    df.loc[df["hhs_care"] >= threshold_90, "stress_level"] = "Critical"

    color_map = {"Normal": "#1D9E75", "Elevated": "#BA7517", "Critical": "#E24B4A"}

    fig5 = px.scatter(
        df, x="date", y="hhs_care",
        color="stress_level",
        color_discrete_map=color_map,
        labels={"hhs_care": "HHS Care", "date": "Date", "stress_level": "Stress Level"},
        opacity=0.7
    )
    fig5.update_traces(marker=dict(size=4))
    fig5.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig5, use_container_width=True)

with stress_col2:
    normal_days   = int((df["stress_level"] == "Normal").sum())
    elevated_days = int((df["stress_level"] == "Elevated").sum())
    critical_days = int((df["stress_level"] == "Critical").sum())

    st.metric("Normal days",   normal_days)
    st.metric("Elevated days", elevated_days,
              help=f"HHS care > {threshold_75:,.0f}")
    st.metric("Critical days", critical_days,
              help=f"HHS care > {threshold_90:,.0f}",
              delta=f"{critical_days/len(df)*100:.1f}% of period",
              delta_color="inverse")

st.divider()

# ─────────────────────────────────────────────
# MODULE 5: RAW DATA EXPLORER
# ─────────────────────────────────────────────
with st.expander("📋 Raw data explorer"):
    st.dataframe(
        df[[
            "date","cbp_apprehended","cbp_custody",
            "cbp_transferred","hhs_care","hhs_discharged",
            "total_load","net_intake","discharge_ratio","stress_level"
        ]].sort_values("date", ascending=False),
        use_container_width=True
    )
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name="uac_filtered_data.csv",
        mime="text/csv"
    )

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.caption(
    "UAC Care System Analytics · "
    "Data source: HHS Office of Refugee Resettlement · "
    "Built with Streamlit"
)