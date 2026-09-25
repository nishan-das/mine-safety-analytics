"""
=================================================================
 MINE SAFETY ANALYTICS  -  STREAMLIT DASHBOARD
=================================================================
 Run:   python create_database.py      (once)
        streamlit run app.py

 Uses the same functions as safety_metrics.py, so the numbers on
 screen always match the Excel report.

 *** ALL DATA IS SYNTHETIC. No real mine or person is represented. ***
=================================================================
"""

import os
import sqlite3

import pandas as pd
import streamlit as st

import safety_metrics as sm

st.set_page_config(page_title="Mine Safety Analytics", layout="wide")
st.title("Mine Safety Performance Dashboard")
st.caption("Synthetic data for a fictional opencast + underground coal mine, Jul 2025 - Jun 2026.")

if not os.path.exists(sm.DB_NAME):
    st.error("mine_safety.db not found. Run `python create_database.py` first.")
    st.stop()

connection = sqlite3.connect(sm.DB_NAME)
incidents, exposure = sm.load_tables(connection)
connection.close()
incidents = sm.add_flags(incidents)

# ---- Sidebar filter --------------------------------------------
zones = st.sidebar.multiselect("Zone", sorted(incidents["zone"].unique()),
                               default=sorted(incidents["zone"].unique()))
filtered = incidents[incidents["zone"].isin(zones)]
st.sidebar.caption("Rates use whole-mine man-hours, because exposure is not recorded per zone.")

# ---- Headline numbers ------------------------------------------
summary = sm.site_summary(filtered, exposure).iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("LTIFR (per 1M man-hours)", f"{summary['LTIFR']:.2f}")
c2.metric("Lost-time injuries", int(summary["lost_time_injuries"]))
c3.metric("Near misses", int(summary["near_misses"]))
c4.metric("Near misses per LTI", summary["near_miss_ratio"])

# ---- Key finding ------------------------------------------------
st.subheader("Contractor vs departmental workers")
by_type = sm.rates_by_employment_type(filtered, exposure)
left, right = st.columns([1, 1])
left.dataframe(by_type, hide_index=True)
right.bar_chart(by_type.set_index("employment_type")["LTIFR"])
st.caption("Raw injury counts look similar; normalising by man-hours shows the contractor rate is about twice as high.")

# ---- Trend and locations ---------------------------------------
st.subheader("Monthly LTIFR")
trend = sm.monthly_trend(filtered, exposure)
st.line_chart(trend.set_index("month")["LTIFR"])

st.subheader("Near-miss reporting vs injuries by location")
st.dataframe(sm.location_summary(filtered), hide_index=True)

st.subheader("Incident register")
types = st.multiselect("Incident type", sorted(filtered["incident_type"].unique()),
                       default=sorted(filtered["incident_type"].unique()))
st.dataframe(
    filtered[filtered["incident_type"].isin(types)][
        ["incident_date", "shift_id", "location_name", "employment_type",
         "incident_type", "cause_category", "days_lost", "description"]
    ].sort_values("incident_date"),
    hide_index=True,
)
