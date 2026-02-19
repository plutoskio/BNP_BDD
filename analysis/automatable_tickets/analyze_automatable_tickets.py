import os
import sqlite3
from pathlib import Path

# Keep matplotlib cache writable in sandboxed runs.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import FuncFormatter
import pandas as pd


BASE_DIR = Path("/Users/milo/Desktop/BNP_BDD")
DB_PATH = BASE_DIR / "hobart.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "automatable_tickets"
OUTPUT_REPORT = OUTPUT_DIR / "automatable_tickets_report.md"
OUTPUT_PIE = OUTPUT_DIR / "automatable_ticket_share_pie.png"
OUTPUT_IMPACT = OUTPUT_DIR / "automatable_time_lost_impact.png"

CHART_COLOR = "#01925c"


def parse_hobart_date(series: pd.Series) -> pd.Series:
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
        s.closingdate_parsed,
        s.reopen_date_parsed,
        COALESCE(tc.transfer_count, 0) AS transfer_count,
        COALESCE(cc.comm_count, 0) AS comm_count,
        COALESCE(ac.task_count, 0) AS task_count
    FROM sr s
    LEFT JOIN transfer_counts tc ON s.id = tc.sr_id
    LEFT JOIN comm_counts cc ON s.id = cc.sr_id
    LEFT JOIN task_counts ac ON s.id = ac.sr_id;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise RuntimeError("No rows returned from database.")

    # Closed-ticket population only (exclude open/in-progress tickets).
    df = df[df["closingdate_parsed"].notna()].copy()
    total_tickets = len(df)

    # Automatable criteria:
    # 1) Low routing complexity (transfer_count <= 1)
    # 2) Low communication load (comm_count <= 1)
    # 3) Low task complexity (task_count <= 1)
    # 4) No reopen signal (reopen_date_parsed is NULL)
    automatable_mask = (
        (df["transfer_count"] <= 1)
        & (df["comm_count"] <= 1)
        & (df["task_count"] <= 1)
        & (df["reopen_date_parsed"].isna())
    )
    automatable_df = df[automatable_mask].copy()
    non_automatable_df = df[~automatable_mask].copy()

    # Time-saved assumption:
    # If automatable tickets get immediate AI response, historical resolution
    # duration approximates potential cycle-time saved.
    # Use only tickets with valid parsed create/close dates for this metric.
    time_df = automatable_df[
        automatable_df["creationdate_parsed"].notna()
        & automatable_df["closingdate_parsed"].notna()
    ].copy()
    time_df["start"] = parse_hobart_date(time_df["creationdate_parsed"])
    time_df["end"] = parse_hobart_date(time_df["closingdate_parsed"])
    time_df = time_df.dropna(subset=["start", "end"])
    time_df["resolution_days"] = (time_df["end"] - time_df["start"]).dt.total_seconds() / 86400.0
    time_df = time_df[time_df["resolution_days"] >= 0]

    automatable_count = len(automatable_df)
    automatable_pct_total = (automatable_count / total_tickets) * 100 if total_tickets else 0.0
    median_time_saved_days = time_df["resolution_days"].median() if not time_df.empty else 0.0
    median_time_saved_hours = median_time_saved_days * 24.0

    # Robust total time estimate to reduce outlier impact:
    # total_time = number_of_tickets * median_duration
    robust_total_time_saved_days = median_time_saved_days * len(time_df)
    robust_total_time_saved_hours = robust_total_time_saved_days * 24.0
    robust_total_time_saved_years = robust_total_time_saved_days / 365.0

    # Pie chart for % of total ticket population (brand color palette).
    secondary_slice = (*mcolors.to_rgb(CHART_COLOR), 0.22)
    plt.figure(figsize=(8, 8))
    plt.pie(
        [automatable_count, len(non_automatable_df)],
        labels=["Automatable Tickets", "Non-Automatable Tickets"],
        autopct="%1.1f%%",
        startangle=90,
        colors=[CHART_COLOR, secondary_slice],
        wedgeprops={"edgecolor": "white", "linewidth": 1.2},
    )
    plt.title("Automatable Ticket Share of Total SR Population")
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(OUTPUT_PIE, dpi=300)
    plt.close()

    # Attention chart: visual impact of cycle-time lost.
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0b1f18")
    ax.set_facecolor("#0b1f18")

    ax.barh(["Automatable ticket time loss"], [robust_total_time_saved_days], color=CHART_COLOR, height=0.55)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1_000_000:.1f}M"))
    ax.grid(axis="x", alpha=0.15, color="white")
    ax.set_xlabel("Days (millions)", color="white", fontsize=11)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#2e5f4f")

    ax.set_title(
        "Cycle-Time Lost in Automatable Tickets",
        fontsize=20,
        fontweight="bold",
        color="white",
        pad=14,
    )

    ax.text(
        robust_total_time_saved_days * 0.50 if robust_total_time_saved_days > 0 else 0,
        0,
        f"{robust_total_time_saved_days/1_000_000:.2f}M days",
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color="white",
    )

    ax.text(
        robust_total_time_saved_days * 0.99 if robust_total_time_saved_days > 0 else 0,
        -0.23,
        f"{len(time_df):,} tickets × {median_time_saved_days:.2f} days (median)",
        ha="right",
        va="center",
        fontsize=12,
        color="white",
    )
    ax.text(
        robust_total_time_saved_days * 0.99 if robust_total_time_saved_days > 0 else 0,
        0.23,
        f"Equivalent: {robust_total_time_saved_years:,.0f} years",
        ha="right",
        va="center",
        fontsize=12,
        color="white",
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_IMPACT, dpi=300)
    plt.close()

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("# Automatable Tickets Report\n\n")
        f.write("## Objective\n")
        f.write("Estimate the size and time-impact of tickets suitable for first-line AI auto-response.\n\n")

        f.write("## Criteria Used\n")
        f.write("A ticket is labeled `automatable` when all of the following are true:\n")
        f.write("1. `transfer_count <= 1`\n")
        f.write("2. `comm_count <= 1`\n")
        f.write("3. `task_count <= 1`\n")
        f.write("4. `reopen_date_parsed IS NULL`\n\n")

        f.write("## Why These Criteria Are Justified\n")
        f.write("- `transfer_count <= 1`: simple tickets should not bounce across desks; allowing 1 transfer covers initial misrouting.\n")
        f.write("- `comm_count <= 1`: low back-and-forth indicates objective, low-ambiguity requests.\n")
        f.write("- `task_count <= 1`: multiple tasks indicate decomposition/escalation, which is usually non-simple work.\n")
        f.write("- `no reopen`: reduces risk by excluding tickets with known resolution fragility.\n\n")

        f.write("## Results\n")
        f.write(f"- Total tickets in population: **{total_tickets:,}**\n")
        f.write(f"- Automatable tickets: **{automatable_count:,}**\n")
        f.write(f"- Automatable share of total: **{automatable_pct_total:.2f}%**\n")
        f.write(f"- Automatable tickets with valid date pair for time estimate: **{len(time_df):,}**\n")
        f.write(f"- Median time saved per automatable ticket (cycle-time proxy): **{median_time_saved_days:.2f} days** (**{median_time_saved_hours:.2f} hours**)\n")
        f.write(f"- Robust total time saved (`tickets × median`): **{robust_total_time_saved_days:,.2f} days** (**{robust_total_time_saved_hours:,.2f} hours**)\n")
        f.write(f"- Robust total time saved in years: **{robust_total_time_saved_years:,.2f} years**\n\n")

        f.write("## Visuals\n")
        f.write("- Share chart: `automatable_ticket_share_pie.png`\n")
        f.write("- Impact chart: `automatable_time_lost_impact.png`\n\n")

        f.write("## Important Assumption\n")
        f.write("Time saved is estimated from historical ticket resolution duration (`closingdate_parsed - creationdate_parsed`) for eligible tickets.\n")
        f.write("To reduce outlier skew, the total impact uses **number of tickets × median duration** (not the raw sum of all durations).\n")


if __name__ == "__main__":
    run_analysis()
