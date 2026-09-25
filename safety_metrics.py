"""
=================================================================
 MINE SAFETY ANALYTICS  -  VERSION 2  -  PYTHON METRICS LAYER
=================================================================
 Reads mine_safety.db and turns incident COUNTS into exposure-
 normalised RATES, then writes an Excel report and two charts.

 Why rates? 7 injuries among 170 contractors and 5 among 280
 departmental workers look "similar" as counts. They are not.
 A rate divides by the hours people were actually exposed.

 Metrics (per 1,000,000 man-hours, a common convention):
   LTIFR          = lost-time injuries  x 1e6 / man-hours worked
   Severity rate  = days lost           x 1e6 / man-hours worked
   Near-miss ratio= near misses reported per lost-time injury

 Run:   python create_database.py      (once)
        python safety_metrics.py

 *** ALL DATA IS SYNTHETIC. No real mine or person is represented. ***
=================================================================
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")                      # save charts without opening a window
import matplotlib.pyplot as plt
import pandas as pd

DB_NAME = "mine_safety.db"
OUTPUT_DIR = "outputs"
PER_MILLION = 1_000_000

# Incident types that count as a lost-time injury (LTI).
LTI_TYPES = ("Reportable Injury", "Serious Bodily Injury", "Fatal")

# A fatality has no "days lost" in the register. Many severity-rate
# conventions charge a fixed number of days per fatality (6,000 is
# used in ANSI Z16.1). It is a CONVENTION, not a law - change it or
# set it to 0 to exclude fatalities from the severity rate.
FATALITY_DAYS_CHARGED = 6000


def safe_rate(numerator, man_hours):
    """Rate per million man-hours, protected against divide-by-zero."""
    return numerator * PER_MILLION / man_hours if man_hours else 0.0


def load_tables(connection):
    """Pull the tables we need into pandas DataFrames."""
    incidents = pd.read_sql_query("""
        SELECT i.*, e.employment_type, l.location_name, l.zone,
               substr(i.incident_date, 1, 7) AS month
        FROM incidents AS i
        LEFT JOIN employees AS e ON i.emp_id = e.emp_id
        JOIN locations AS l      ON i.location_id = l.location_id
    """, connection)
    exposure = pd.read_sql_query("SELECT * FROM monthly_exposure", connection)
    return incidents, exposure


def add_flags(incidents):
    """Mark each incident as LTI / near miss and compute charged days."""
    incidents["is_lti"] = incidents["incident_type"].isin(LTI_TYPES)
    incidents["is_near_miss"] = incidents["incident_type"] == "Near Miss"
    incidents["charged_days"] = incidents["days_lost"]
    incidents.loc[incidents["incident_type"] == "Fatal", "charged_days"] = FATALITY_DAYS_CHARGED
    return incidents


def rates_by_employment_type(incidents, exposure):
    """The key finding: LTIFR for contractors vs departmental workers."""
    hours = exposure.groupby("employment_type")["man_hours_worked"].sum()
    rows = []
    for emp_type, man_hours in hours.items():
        group = incidents[incidents["employment_type"] == emp_type]
        ltis = int(group["is_lti"].sum())
        rows.append({
            "employment_type": emp_type,
            "man_hours": int(man_hours),
            "lost_time_injuries": ltis,
            "days_charged": int(group.loc[group["is_lti"], "charged_days"].sum()),
            "LTIFR": round(safe_rate(ltis, man_hours), 2),
            "severity_rate": round(safe_rate(group.loc[group["is_lti"], "charged_days"].sum(), man_hours), 1),
        })
    return pd.DataFrame(rows).sort_values("LTIFR", ascending=False)


def site_summary(incidents, exposure):
    """Whole-mine numbers for the year."""
    total_hours = exposure["man_hours_worked"].sum()
    ltis = int(incidents["is_lti"].sum())
    near_misses = int(incidents["is_near_miss"].sum())
    return pd.DataFrame([{
        "man_hours": int(total_hours),
        "lost_time_injuries": ltis,
        "fatalities": int((incidents["incident_type"] == "Fatal").sum()),
        "near_misses": near_misses,
        "LTIFR": round(safe_rate(ltis, total_hours), 2),
        "severity_rate": round(safe_rate(incidents.loc[incidents["is_lti"], "charged_days"].sum(), total_hours), 1),
        "near_miss_ratio": round(near_misses / ltis, 1) if ltis else None,
    }])


def monthly_trend(incidents, exposure):
    """LTIFR month by month (whole mine)."""
    hours = exposure.groupby("month")["man_hours_worked"].sum()
    ltis = incidents[incidents["is_lti"]].groupby("month").size()
    trend = pd.DataFrame({"man_hours": hours, "lost_time_injuries": ltis}).fillna(0)
    trend["LTIFR"] = [round(safe_rate(n, h), 2) for n, h in zip(trend["lost_time_injuries"], trend["man_hours"])]
    return trend.reset_index().rename(columns={"index": "month"})


def location_summary(incidents):
    """Near-miss reporting vs lost-time injuries, per location."""
    table = incidents.groupby("location_name").agg(
        near_misses=("is_near_miss", "sum"),
        lost_time_injuries=("is_lti", "sum"),
        days_lost=("days_lost", "sum"),
    ).sort_values("days_lost", ascending=False)
    table["near_miss_per_lti"] = [
        round(nm / lti, 1) if lti else None
        for nm, lti in zip(table["near_misses"], table["lost_time_injuries"])
    ]
    return table.reset_index()


def save_charts(by_type, trend):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(by_type["employment_type"], by_type["LTIFR"], color=["#c0504d", "#4f81bd"])
    ax.set_ylabel("LTIFR (per million man-hours)")
    ax.set_title("Lost-time injury frequency rate by employment type\n(synthetic data)")
    for x, y in zip(by_type["employment_type"], by_type["LTIFR"]):
        ax.text(x, y, f"{y:.1f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "ltifr_by_employment_type.png"), dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(trend["month"], trend["LTIFR"], marker="o")
    ax.set_ylabel("LTIFR (per million man-hours)")
    ax.set_title("Monthly LTIFR, whole mine (synthetic data)")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "monthly_ltifr.png"), dpi=120)
    plt.close(fig)


def main():
    if not os.path.exists(DB_NAME):
        print(f"{DB_NAME} not found. Run:  python create_database.py")
        return

    connection = sqlite3.connect(DB_NAME)
    incidents, exposure = load_tables(connection)
    connection.close()
    incidents = add_flags(incidents)

    summary = site_summary(incidents, exposure)
    by_type = rates_by_employment_type(incidents, exposure)
    trend = monthly_trend(incidents, exposure)
    locations = location_summary(incidents)

    pd.set_option("display.width", 120)
    print("=" * 70)
    print("  MINE SAFETY PERFORMANCE  (July 2025 - June 2026, SYNTHETIC DATA)")
    print("=" * 70)
    print(summary.to_string(index=False))
    print("\nBy employment type:")
    print(by_type.to_string(index=False))

    contractor = by_type.set_index("employment_type")["LTIFR"]
    if "Departmental" in contractor and contractor["Departmental"] > 0:
        ratio = contractor["Contractor"] / contractor["Departmental"]
        print(f"\n  -> Contractor LTIFR is {ratio:.1f}x the departmental LTIFR,")
        print("     even though the raw injury counts look similar (7 vs 5).")

    print("\nNear misses vs injuries by location (top 5 by days lost):")
    print(locations.head(5).to_string(index=False))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "safety_report.xlsx")
    with pd.ExcelWriter(report_path) as writer:
        summary.to_excel(writer, sheet_name="Site summary", index=False)
        by_type.to_excel(writer, sheet_name="By employment type", index=False)
        trend.to_excel(writer, sheet_name="Monthly LTIFR", index=False)
        locations.to_excel(writer, sheet_name="By location", index=False)
    save_charts(by_type, trend)
    print(f"\nSaved: {report_path} and charts in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
