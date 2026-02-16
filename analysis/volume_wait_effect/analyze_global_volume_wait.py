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
OUTPUT_DIR = BASE_DIR / "analysis" / "volume_wait_effect"
REPORT_PATH = OUTPUT_DIR / "global_volume_wait_report.md"
DAILY_CHART_PATH = OUTPUT_DIR / "daily_total_volume_vs_median_wait.png"
WEEKLY_CHART_PATH = OUTPUT_DIR / "weekly_total_volume_vs_median_wait.png"

ANALYSIS_START_DATE = pd.Timestamp("2024-01-01")


def parse_hobart_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%y-%m-%d %H.%M.%S", errors="coerce")


def assign_quintiles(series: pd.Series) -> pd.Series:
    pct = series.rank(method="max", pct=True)
    labels = pd.Series(index=series.index, dtype="object")
    labels[pct <= 0.2] = "Q1 (Low)"
    labels[(pct > 0.2) & (pct <= 0.4)] = "Q2"
    labels[(pct > 0.4) & (pct <= 0.6)] = "Q3"
    labels[(pct > 0.6) & (pct <= 0.8)] = "Q4"
    labels[pct > 0.8] = "Q5 (High)"
    return labels


def fetch_automatable_closed_tickets(conn: sqlite3.Connection) -> pd.DataFrame:
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
        s.closingdate_parsed,
        COALESCE(tc.transfer_count, 0) AS transfer_count,
        COALESCE(cc.comm_count, 0) AS comm_count,
        COALESCE(ac.task_count, 0) AS task_count
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
    return pd.read_sql_query(query, conn)


def fetch_total_volume_population(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    SELECT
        id AS sr_id,
        creationdate_parsed
    FROM sr
    WHERE creationdate_parsed IS NOT NULL;
    """
    return pd.read_sql_query(query, conn)


def build_daily_dataset(automatable_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    automatable_df["creation_dt"] = parse_hobart_datetime(automatable_df["creationdate_parsed"])
    automatable_df["closing_dt"] = parse_hobart_datetime(automatable_df["closingdate_parsed"])
    automatable_df = automatable_df.dropna(subset=["creation_dt", "closing_dt"])
    automatable_df = automatable_df[automatable_df["creation_dt"] >= ANALYSIS_START_DATE].copy()
    automatable_df["wait_hours"] = (
        automatable_df["closing_dt"] - automatable_df["creation_dt"]
    ).dt.total_seconds() / 3600.0
    automatable_df = automatable_df[automatable_df["wait_hours"] >= 0]
    automatable_df["day"] = automatable_df["creation_dt"].dt.floor("D")

    volume_df["creation_dt"] = parse_hobart_datetime(volume_df["creationdate_parsed"])
    volume_df = volume_df.dropna(subset=["creation_dt"])
    volume_df = volume_df[volume_df["creation_dt"] >= ANALYSIS_START_DATE].copy()
    volume_df["day"] = volume_df["creation_dt"].dt.floor("D")

    daily_wait = (
        automatable_df.groupby("day")
        .agg(
            automatable_tickets=("sr_id", "count"),
            median_wait_hours=("wait_hours", "median"),
        )
        .reset_index()
    )

    daily_volume = (
        volume_df.groupby("day")
        .agg(total_volume=("sr_id", "count"))
        .reset_index()
    )

    daily = daily_wait.merge(daily_volume, on="day", how="inner")
    daily["volume_quintile"] = assign_quintiles(daily["total_volume"])
    daily["volume_quintile"] = pd.Categorical(
        daily["volume_quintile"],
        categories=["Q1 (Low)", "Q2", "Q3", "Q4", "Q5 (High)"],
        ordered=True,
    )
    return daily


def build_weekly_dataset(automatable_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    auto = automatable_df.copy()
    vol = volume_df.copy()

    auto["creation_dt"] = parse_hobart_datetime(auto["creationdate_parsed"])
    auto["closing_dt"] = parse_hobart_datetime(auto["closingdate_parsed"])
    auto = auto.dropna(subset=["creation_dt", "closing_dt"])
    auto = auto[auto["creation_dt"] >= ANALYSIS_START_DATE].copy()
    auto["wait_hours"] = (auto["closing_dt"] - auto["creation_dt"]).dt.total_seconds() / 3600.0
    auto = auto[auto["wait_hours"] >= 0]
    auto["week"] = auto["creation_dt"].dt.to_period("W").dt.start_time

    vol["creation_dt"] = parse_hobart_datetime(vol["creationdate_parsed"])
    vol = vol.dropna(subset=["creation_dt"])
    vol = vol[vol["creation_dt"] >= ANALYSIS_START_DATE].copy()
    vol["week"] = vol["creation_dt"].dt.to_period("W").dt.start_time

    weekly_wait = (
        auto.groupby("week")
        .agg(
            automatable_tickets=("sr_id", "count"),
            median_wait_hours=("wait_hours", "median"),
        )
        .reset_index()
    )

    weekly_volume = (
        vol.groupby("week")
        .agg(total_volume=("sr_id", "count"))
        .reset_index()
    )

    weekly = weekly_wait.merge(weekly_volume, on="week", how="inner")
    weekly["volume_quintile"] = assign_quintiles(weekly["total_volume"])
    weekly["volume_quintile"] = pd.Categorical(
        weekly["volume_quintile"],
        categories=["Q1 (Low)", "Q2", "Q3", "Q4", "Q5 (High)"],
        ordered=True,
    )
    return weekly


def make_scatter_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str, out_path: Path) -> None:
    plt.figure(figsize=(10, 6))
    plt.grid(alpha=0.25)
    plt.scatter(df[x_col], df[y_col], alpha=0.5, s=22, color="#2f6ea3")
    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel("Total Volume")
    plt.ylabel("Median Wait (Hours)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def summarize_by_quintile(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("volume_quintile", observed=True)
        .agg(
            periods=("median_wait_hours", "count"),
            avg_total_volume=("total_volume", "mean"),
            median_wait_hours=("median_wait_hours", "median"),
            p90_wait_hours=("median_wait_hours", lambda x: x.quantile(0.9)),
        )
        .reset_index()
        .sort_values("volume_quintile")
    )


def run_analysis() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    automatable_df = fetch_automatable_closed_tickets(conn)
    volume_df = fetch_total_volume_population(conn)
    conn.close()

    if automatable_df.empty:
        raise RuntimeError("No automatable tickets found.")
    if volume_df.empty:
        raise RuntimeError("No volume population found.")

    daily = build_daily_dataset(automatable_df, volume_df)
    weekly = build_weekly_dataset(automatable_df, volume_df)

    make_scatter_chart(
        daily,
        x_col="total_volume",
        y_col="median_wait_hours",
        title="Daily: Total Volume vs Median Wait (Automatable Tickets)",
        out_path=DAILY_CHART_PATH,
    )
    make_scatter_chart(
        weekly,
        x_col="total_volume",
        y_col="median_wait_hours",
        title="Weekly: Total Volume vs Median Wait (Automatable Tickets)",
        out_path=WEEKLY_CHART_PATH,
    )

    daily_pearson = daily["total_volume"].corr(daily["median_wait_hours"], method="pearson")
    daily_spearman = daily["total_volume"].corr(daily["median_wait_hours"], method="spearman")
    weekly_pearson = weekly["total_volume"].corr(weekly["median_wait_hours"], method="pearson")
    weekly_spearman = weekly["total_volume"].corr(weekly["median_wait_hours"], method="spearman")

    daily_q = summarize_by_quintile(daily)
    weekly_q = summarize_by_quintile(weekly)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Global Volume vs Median Wait Report\n\n")
        f.write("## Objective\n")
        f.write(
            "Assess whether higher total ticket volume (all desks combined) is associated with longer median wait time "
            "for automatable tickets.\n\n"
        )

        f.write("## Population Definition\n")
        f.write("- Closed tickets only (`closingdate_parsed` populated)\n")
        f.write("- Automatable criteria:\n")
        f.write("1. `transfer_count <= 1`\n")
        f.write("2. `comm_count <= 1`\n")
        f.write("3. `task_count <= 1`\n")
        f.write("4. `reopen_date_parsed IS NULL`\n")
        f.write(f"- Analysis window starts on: `{ANALYSIS_START_DATE.date()}`\n\n")

        f.write("## Daily Analysis\n")
        f.write(f"- Number of daily periods analyzed: **{len(daily):,}**\n")
        f.write(f"- Pearson correlation (volume vs median wait): **{daily_pearson:.4f}**\n")
        f.write(f"- Spearman correlation (volume vs median wait): **{daily_spearman:.4f}**\n\n")
        f.write("### Daily Volume Quintile Summary\n\n")
        f.write(daily_q.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Weekly Analysis\n")
        f.write(f"- Number of weekly periods analyzed: **{len(weekly):,}**\n")
        f.write(f"- Pearson correlation (volume vs median wait): **{weekly_pearson:.4f}**\n")
        f.write(f"- Spearman correlation (volume vs median wait): **{weekly_spearman:.4f}**\n\n")
        f.write("### Weekly Volume Quintile Summary\n\n")
        f.write(weekly_q.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Interpretation Guidance\n")
        f.write("- Positive correlation: higher volume tends to increase median wait.\n")
        f.write("- Near-zero correlation: weak or no linear/monotonic association.\n")
        f.write("- Negative correlation: higher volume coincides with lower median wait (possible process/capacity effects).\n")


if __name__ == "__main__":
    run_analysis()
