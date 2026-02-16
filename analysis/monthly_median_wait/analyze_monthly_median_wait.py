import os
import sqlite3
from pathlib import Path

# Keep matplotlib cache writable in sandboxed runs.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path("/Users/milo/Desktop/BNP_BDD")
DB_PATH = BASE_DIR / "hobart.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "monthly_median_wait"
OUTPUT_MD = OUTPUT_DIR / "monthly_median_wait_table.md"
OUTPUT_CSV = OUTPUT_DIR / "monthly_median_wait_table.csv"
OUTPUT_PNG = OUTPUT_DIR / "monthly_median_wait_chart.png"

ANALYSIS_START_DATE = pd.Timestamp("2024-01-01")


def parse_hobart_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%y-%m-%d %H.%M.%S", errors="coerce")


def run_analysis() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    query = """
    WITH ordered_activity AS (
        SELECT
            sr_id,
            jur_assignedgroup_id,
            creationdate,
            LAG(jur_assignedgroup_id) OVER (
                PARTITION BY sr_id
                ORDER BY creationdate
            ) AS prev_group
        FROM activity
        WHERE jur_assignedgroup_id IS NOT NULL
    ),
    transfer_counts AS (
        SELECT
            sr_id,
            SUM(
                CASE
                    WHEN prev_group IS NOT NULL
                     AND jur_assignedgroup_id != prev_group
                    THEN 1
                    ELSE 0
                END
            ) AS transfer_count
        FROM ordered_activity
        GROUP BY sr_id
    ),
    comm_counts AS (
        SELECT
            sr_id,
            COUNT(*) AS comm_count
        FROM srcontact
        GROUP BY sr_id
    ),
    task_counts AS (
        SELECT
            sr_id,
            COUNT(*) AS task_count
        FROM activity
        GROUP BY sr_id
    )
    SELECT
        s.id AS sr_id,
        s.creationdate_parsed,
        s.closingdate_parsed
    FROM sr s
    LEFT JOIN transfer_counts tc ON s.id = tc.sr_id
    LEFT JOIN comm_counts cc ON s.id = cc.sr_id
    LEFT JOIN task_counts ac ON s.id = ac.sr_id
    WHERE s.closingdate_parsed IS NOT NULL
      AND s.creationdate_parsed IS NOT NULL
      AND s.reopen_date_parsed IS NULL
      AND COALESCE(tc.transfer_count, 0) <= 1
      AND COALESCE(cc.comm_count, 0) <= 1
      AND COALESCE(ac.task_count, 0) <= 1;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise RuntimeError("No automatable closed tickets returned.")

    df["creation_dt"] = parse_hobart_datetime(df["creationdate_parsed"])
    df["closing_dt"] = parse_hobart_datetime(df["closingdate_parsed"])
    df = df.dropna(subset=["creation_dt", "closing_dt"])
    df = df[df["creation_dt"] >= ANALYSIS_START_DATE].copy()

    df["wait_hours"] = (df["closing_dt"] - df["creation_dt"]).dt.total_seconds() / 3600.0
    df = df[df["wait_hours"] >= 0]
    df["month"] = df["creation_dt"].dt.to_period("M").astype(str)

    summary = (
        df.groupby("month")
        .agg(
            tickets=("sr_id", "count"),
            median_wait_hours=("wait_hours", "median"),
            p90_wait_hours=("wait_hours", lambda x: x.quantile(0.9)),
            mean_wait_hours=("wait_hours", "mean"),
        )
        .reset_index()
        .sort_values("month")
    )
    summary["median_wait_days"] = summary["median_wait_hours"] / 24.0

    # Chart on log scale to keep large outlier months readable while preserving values.
    summary["month_dt"] = pd.to_datetime(summary["month"] + "-01", format="%Y-%m-%d")
    plt.figure(figsize=(12, 6))
    plt.grid(axis="y", alpha=0.25)
    plt.plot(
        summary["month_dt"],
        summary["median_wait_hours"],
        marker="o",
        linewidth=2,
        color="#2f6ea3",
    )
    plt.yscale("log")
    plt.title("Monthly Median Wait Time (Automatable Tickets, Log Scale)", fontsize=14, fontweight="bold")
    plt.xlabel("Month")
    plt.ylabel("Median Wait (Hours, log scale)")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=300)
    plt.close()

    summary_out = summary.drop(columns=["month_dt"])
    summary_out.to_csv(OUTPUT_CSV, index=False)

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Monthly Median Wait Time (Automatable Tickets)\n\n")
        f.write("Population: closed automatable tickets (`transfer<=1`, `comm<=1`, `task<=1`, no reopen).\n\n")
        f.write("Chart: `monthly_median_wait_chart.png` (log-scale y-axis).\n\n")
        f.write(summary_out.to_markdown(index=False))
        f.write("\n")


if __name__ == "__main__":
    run_analysis()
