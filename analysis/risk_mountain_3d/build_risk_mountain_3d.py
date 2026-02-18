import os
import sqlite3
from pathlib import Path

# Keep matplotlib cache writable in sandboxed runs.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


BASE_DIR = Path("/Users/milo/Desktop/BNP_BDD")
DB_PATH = BASE_DIR / "hobart.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "risk_mountain_3d"

OUTPUT_CELLS_CSV = OUTPUT_DIR / "risk_mountain_cells.csv"
OUTPUT_CELLS_STABLE_CSV = OUTPUT_DIR / "risk_mountain_cells_stable.csv"
OUTPUT_HTML = OUTPUT_DIR / "risk_mountain_3d.html"
OUTPUT_PNG = OUTPUT_DIR / "risk_mountain_3d.png"
OUTPUT_REPORT = OUTPUT_DIR / "risk_mountain_3d_report.md"

ANALYSIS_LOAD_PERIOD = "2025-01_to_2025-09"
SLA_THRESHOLD_HOURS = 72.0
MAX_BUCKET = 6
STABLE_CELL_MIN_TICKETS = 100


def sql_median(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    where_clause: str = "1=1",
    params: tuple = (),
) -> float:
    n = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {where_clause};",
        params,
    ).fetchone()[0]
    if n == 0:
        return float("nan")

    if n % 2 == 1:
        return float(
            conn.execute(
                f"""
                SELECT {column}
                FROM {table}
                WHERE {where_clause}
                ORDER BY {column}
                LIMIT 1 OFFSET ?;
                """,
                params + (n // 2,),
            ).fetchone()[0]
        )

    lo = float(
        conn.execute(
            f"""
            SELECT {column}
            FROM {table}
            WHERE {where_clause}
            ORDER BY {column}
            LIMIT 1 OFFSET ?;
            """,
            params + (n // 2 - 1,),
        ).fetchone()[0]
    )
    hi = float(
        conn.execute(
            f"""
            SELECT {column}
            FROM {table}
            WHERE {where_clause}
            ORDER BY {column}
            LIMIT 1 OFFSET ?;
            """,
            params + (n // 2,),
        ).fetchone()[0]
    )
    return (lo + hi) / 2.0


def bucket_label(x: int) -> str:
    return f"{MAX_BUCKET}+" if x >= MAX_BUCKET else str(x)


def build_dataset() -> tuple[pd.DataFrame, dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -200000;")
    print("[1/8] Building activity-backed SR scope...", flush=True)

    # Scope to tickets with observable desk activity so transfer metrics are meaningful.
    conn.execute(
        """
        CREATE TEMP TABLE activity_sr_scope AS
        SELECT DISTINCT sr_id
        FROM activity
        WHERE load_period = ?
          AND sr_id IS NOT NULL
          AND jur_assignedgroup_id IS NOT NULL;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_activity_sr_scope_sr_id ON activity_sr_scope(sr_id);")

    print("[2/8] Building closed scope...", flush=True)

    # 1) Closed-ticket scope with robust parsed datetime conversion.
    conn.execute(
        """
        CREATE TEMP TABLE closed_scope_raw AS
        WITH parsed AS (
            SELECT
                id AS sr_id,
                datetime(
                    '20' || substr(creationdate_parsed, 1, 2)
                    || '-' || substr(creationdate_parsed, 4, 2)
                    || '-' || substr(creationdate_parsed, 7, 2)
                    || ' ' || replace(substr(creationdate_parsed, 10), '.', ':')
                ) AS creation_dt,
                datetime(
                    '20' || substr(closingdate_parsed, 1, 2)
                    || '-' || substr(closingdate_parsed, 4, 2)
                    || '-' || substr(closingdate_parsed, 7, 2)
                    || ' ' || replace(substr(closingdate_parsed, 10), '.', ':')
                ) AS closing_dt
            FROM sr
            JOIN activity_sr_scope a
              ON sr.id = a.sr_id
            WHERE load_period = ?
              AND creationdate_parsed IS NOT NULL
              AND closingdate_parsed IS NOT NULL
        )
        SELECT
            sr_id,
            (julianday(closing_dt) - julianday(creation_dt)) * 24.0 AS duration_hours
        FROM parsed
        WHERE creation_dt IS NOT NULL
          AND closing_dt IS NOT NULL;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_closed_scope_raw_sr_id ON closed_scope_raw(sr_id);")

    conn.execute(
        """
        CREATE TEMP TABLE closed_scope AS
        SELECT *
        FROM closed_scope_raw
        WHERE duration_hours >= 0;
        """
    )
    conn.execute("CREATE INDEX idx_closed_scope_sr_id ON closed_scope(sr_id);")
    print("[3/8] Building owner-change counts...", flush=True)

    # 2) Ownership changes from SR history events.
    conn.execute(
        """
        CREATE TEMP TABLE owner_change_counts AS
        SELECT
            h.sr_id,
            COUNT(*) AS owner_change_count
        FROM historysr h
        WHERE h.load_period = ?
          AND h.action = 'Re-assign'
          AND h.sr_id IN (SELECT sr_id FROM activity_sr_scope)
        GROUP BY h.sr_id;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_owner_change_counts_sr_id ON owner_change_counts(sr_id);")
    print("[4/8] Building desk-transfer counts...", flush=True)

    # 3) Desk-transfer counts from activity stream (desk changes in time order).
    conn.execute(
        """
        CREATE TEMP TABLE desk_transfer_counts AS
        WITH ordered_activity AS (
            SELECT
                sr_id,
                jur_assignedgroup_id,
                LAG(jur_assignedgroup_id) OVER (
                    PARTITION BY sr_id
                    ORDER BY COALESCE(
                        creationdate,
                        update_date,
                        closingdate,
                        notificationdate,
                        accepted_date,
                        rejected_date,
                        completiondate
                    ), id
                ) AS prev_group
            FROM activity
            WHERE load_period = ?
              AND sr_id IS NOT NULL
              AND jur_assignedgroup_id IS NOT NULL
        )
        SELECT
            sr_id,
            SUM(
                CASE
                    WHEN prev_group IS NOT NULL
                     AND jur_assignedgroup_id != prev_group
                    THEN 1 ELSE 0
                END
            ) AS desk_transfer_count
        FROM ordered_activity
        GROUP BY sr_id;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_desk_transfer_counts_sr_id ON desk_transfer_counts(sr_id);")
    print("[5/8] Building ticket facts...", flush=True)

    # 4) Ticket-level fact table for risk mountain.
    conn.execute(
        """
        CREATE TEMP TABLE ticket_facts AS
        SELECT
            c.sr_id,
            c.duration_hours,
            CASE
                WHEN COALESCE(o.owner_change_count, 0) >= ? THEN ?
                ELSE COALESCE(o.owner_change_count, 0)
            END AS owner_bucket,
            CASE
                WHEN COALESCE(d.desk_transfer_count, 0) >= ? THEN ?
                ELSE COALESCE(d.desk_transfer_count, 0)
            END AS transfer_bucket,
            CASE WHEN c.duration_hours > ? THEN 1 ELSE 0 END AS sla_miss
        FROM closed_scope c
        LEFT JOIN owner_change_counts o ON c.sr_id = o.sr_id
        LEFT JOIN desk_transfer_counts d ON c.sr_id = d.sr_id;
        """,
        (MAX_BUCKET, MAX_BUCKET, MAX_BUCKET, MAX_BUCKET, SLA_THRESHOLD_HOURS),
    )
    conn.execute("CREATE INDEX idx_ticket_facts_bucket ON ticket_facts(owner_bucket, transfer_bucket);")
    conn.execute("CREATE INDEX idx_ticket_facts_duration ON ticket_facts(duration_hours);")
    print("[6/8] Loading ticket facts to pandas and aggregating cells...", flush=True)

    facts = pd.read_sql_query(
        """
        SELECT owner_bucket, transfer_bucket, duration_hours, sla_miss
        FROM ticket_facts;
        """,
        conn,
    )
    cells = (
        facts.groupby(["owner_bucket", "transfer_bucket"], as_index=False)
        .agg(
            tickets=("duration_hours", "size"),
            sla_miss_rate=("sla_miss", "mean"),
            avg_duration_hours=("duration_hours", "mean"),
            median_duration_hours=("duration_hours", "median"),
        )
        .sort_values(["owner_bucket", "transfer_bucket"])
        .reset_index(drop=True)
    )
    print("[7/8] Computing QA summary metrics...", flush=True)

    qa = pd.read_sql_query(
        """
        SELECT
            (SELECT COUNT(*) FROM sr WHERE load_period = ?) AS sr_rows_in_period,
            (SELECT COUNT(*) FROM activity_sr_scope) AS sr_rows_with_activity_desk,
            (SELECT COUNT(*) FROM sr WHERE load_period = ? AND creationdate_parsed IS NOT NULL AND closingdate_parsed IS NOT NULL) AS sr_with_parsed_dates,
            (SELECT COUNT(*) FROM closed_scope_raw WHERE duration_hours < 0) AS negative_duration_rows,
            (SELECT COUNT(*) FROM closed_scope) AS final_ticket_rows,
            (SELECT COUNT(*) FROM historysr WHERE load_period = ? AND action = 'Re-assign') AS owner_change_events,
            (SELECT COUNT(*) FROM activity WHERE load_period = ? AND sr_id IS NOT NULL AND jur_assignedgroup_id IS NOT NULL) AS activity_rows_with_desk,
            (SELECT COUNT(*) FROM ticket_facts) AS ticket_fact_rows;
        """,
        conn,
        params=(ANALYSIS_LOAD_PERIOD, ANALYSIS_LOAD_PERIOD, ANALYSIS_LOAD_PERIOD, ANALYSIS_LOAD_PERIOD),
    )

    overall_median_hours = sql_median(conn, "ticket_facts", "duration_hours")
    overall_avg_hours = float(
        conn.execute("SELECT AVG(duration_hours) FROM ticket_facts;").fetchone()[0]
    )
    overall_sla_miss_rate = float(
        conn.execute("SELECT AVG(sla_miss) FROM ticket_facts;").fetchone()[0]
    )

    summary = {
        "sr_rows_in_period": int(qa.loc[0, "sr_rows_in_period"]),
        "sr_rows_with_activity_desk": int(qa.loc[0, "sr_rows_with_activity_desk"]),
        "sr_with_parsed_dates": int(qa.loc[0, "sr_with_parsed_dates"]),
        "negative_duration_rows": int(qa.loc[0, "negative_duration_rows"]),
        "final_ticket_rows": int(qa.loc[0, "final_ticket_rows"]),
        "owner_change_events": int(qa.loc[0, "owner_change_events"]),
        "activity_rows_with_desk": int(qa.loc[0, "activity_rows_with_desk"]),
        "ticket_fact_rows": int(qa.loc[0, "ticket_fact_rows"]),
        "overall_median_hours": overall_median_hours,
        "overall_avg_hours": overall_avg_hours,
        "overall_sla_miss_rate": overall_sla_miss_rate,
    }

    conn.close()
    print("[8/8] Dataset ready.", flush=True)
    return cells, summary


def build_visuals(cells: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cells = cells.copy()
    cells["owner_bucket"] = cells["owner_bucket"].astype(int)
    cells["transfer_bucket"] = cells["transfer_bucket"].astype(int)
    cells["owner_bucket_label"] = cells["owner_bucket"].map(bucket_label)
    cells["transfer_bucket_label"] = cells["transfer_bucket"].map(bucket_label)
    cells["avg_duration_days"] = cells["avg_duration_hours"] / 24.0
    cells["median_duration_days"] = cells["median_duration_hours"] / 24.0
    cells["sla_miss_pct"] = cells["sla_miss_rate"] * 100.0
    cells["expected_sla_miss_tickets"] = cells["tickets"] * cells["sla_miss_rate"]
    cells["is_stable_cell"] = cells["tickets"] >= STABLE_CELL_MIN_TICKETS

    stable_cells = cells[cells["is_stable_cell"]].copy()

    # Interactive 3D mountain (bubble size = volume, color = SLA miss risk).
    plot_df = cells.sort_values("tickets", ascending=True).copy()

    fig = px.scatter_3d(
        plot_df,
        x="owner_bucket",
        y="transfer_bucket",
        z="median_duration_days",
        size="tickets",
        color="sla_miss_pct",
        color_continuous_scale="YlOrRd",
        size_max=64,
        custom_data=[
            "owner_bucket_label",
            "transfer_bucket_label",
            "tickets",
            "median_duration_days",
            "avg_duration_days",
            "sla_miss_pct",
            "expected_sla_miss_tickets",
            "is_stable_cell",
        ],
    )
    fig.update_traces(
        marker={
            "opacity": 0.88,
            "line": {"width": 0.8, "color": "rgba(0,0,0,0.35)"},
        },
        hovertemplate=(
            "<b>Owner changes:</b> %{customdata[0]}<br>"
            "<b>Desk transfers:</b> %{customdata[1]}<br>"
            "<b>Tickets:</b> %{customdata[2]:,}<br>"
            "<b>Median resolution:</b> %{customdata[3]:.2f} days<br>"
            "<b>Average resolution:</b> %{customdata[4]:.2f} days<br>"
            "<b>SLA miss rate:</b> %{customdata[5]:.1f}%<br>"
            "<b>Expected SLA-miss tickets:</b> %{customdata[6]:,.1f}<br>"
            "<b>Stable cell (n>=100):</b> %{customdata[7]}<extra></extra>"
        ),
    )

    x_axis_vals = list(range(0, MAX_BUCKET + 1))
    x_axis_text = [bucket_label(x) for x in x_axis_vals]

    # Optional reference plane at SLA threshold for visual grounding.
    fig.add_trace(
        go.Surface(
            x=[[0, MAX_BUCKET], [0, MAX_BUCKET]],
            y=[[0, 0], [MAX_BUCKET, MAX_BUCKET]],
            z=[
                [SLA_THRESHOLD_HOURS / 24.0, SLA_THRESHOLD_HOURS / 24.0],
                [SLA_THRESHOLD_HOURS / 24.0, SLA_THRESHOLD_HOURS / 24.0],
            ],
            showscale=False,
            opacity=0.12,
            colorscale=[[0, "#2ca25f"], [1, "#2ca25f"]],
            hoverinfo="skip",
            name=f"SLA threshold ({SLA_THRESHOLD_HOURS/24.0:.1f}d)",
        )
    )

    fig.update_layout(
        title=(
            "Risk Mountain (Interactive 3D): Ownership Changes vs Desk Transfers vs Resolution Time"
            f"<br><sup>Load period: {ANALYSIS_LOAD_PERIOD} | Color = SLA miss rate (>{SLA_THRESHOLD_HOURS:.0f}h)"
            f" | Bubble size = ticket volume | Buckets capped at {MAX_BUCKET}+</sup>"
        ),
        template="plotly_white",
        width=1300,
        height=850,
        margin={"l": 0, "r": 0, "t": 90, "b": 0},
        scene={
            "xaxis": {
                "title": f"Owner changes (count; {MAX_BUCKET}+ capped)",
                "tickvals": x_axis_vals,
                "ticktext": x_axis_text,
                "gridcolor": "rgba(0,0,0,0.15)",
                "zerolinecolor": "rgba(0,0,0,0.25)",
            },
            "yaxis": {
                "title": f"Desk transfers (count; {MAX_BUCKET}+ capped)",
                "tickvals": x_axis_vals,
                "ticktext": x_axis_text,
                "gridcolor": "rgba(0,0,0,0.15)",
                "zerolinecolor": "rgba(0,0,0,0.25)",
            },
            "zaxis": {
                "title": "Median resolution time (days)",
                "gridcolor": "rgba(0,0,0,0.15)",
                "zerolinecolor": "rgba(0,0,0,0.25)",
            },
            "camera": {"eye": {"x": 1.55, "y": 1.55, "z": 0.95}},
        },
        coloraxis_colorbar={"title": "SLA miss %"},
    )
    fig.write_html(OUTPUT_HTML, include_plotlyjs="cdn", full_html=True)

    # Static backup image for quick embedding if interactive view is unavailable.
    fig_static = plt.figure(figsize=(11, 8))
    ax = fig_static.add_subplot(111, projection="3d")
    scatter = ax.scatter(
        cells["owner_bucket"],
        cells["transfer_bucket"],
        cells["median_duration_days"],
        s=np.sqrt(cells["tickets"]) * 8.0,
        c=cells["sla_miss_pct"],
        cmap="YlOrRd",
        alpha=0.85,
        edgecolors="black",
        linewidths=0.4,
    )
    ax.set_xlabel(f"Owner changes ({MAX_BUCKET}+ capped)")
    ax.set_ylabel(f"Desk transfers ({MAX_BUCKET}+ capped)")
    ax.set_zlabel("Median resolution (days)")
    ax.set_title(
        "Risk Mountain (3D static backup)\n"
        f"Color=SLA miss % (> {SLA_THRESHOLD_HOURS:.0f}h), Size=volume"
    )
    cbar = plt.colorbar(scatter, pad=0.12)
    cbar.set_label("SLA miss %")
    ax.view_init(elev=25, azim=35)
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=300)
    plt.close()

    return cells, stable_cells


def build_report(cells: pd.DataFrame, stable_cells: pd.DataFrame, summary: dict) -> None:
    top_sla_miss_burden = cells.sort_values("expected_sla_miss_tickets", ascending=False).head(10).copy()
    top_sla_miss_burden["owner_bucket"] = top_sla_miss_burden["owner_bucket"].map(bucket_label)
    top_sla_miss_burden["transfer_bucket"] = top_sla_miss_burden["transfer_bucket"].map(bucket_label)
    top_sla_miss_burden["sla_miss_pct"] = top_sla_miss_burden["sla_miss_pct"].round(2)
    top_sla_miss_burden["median_duration_days"] = top_sla_miss_burden["median_duration_days"].round(3)
    top_sla_miss_burden["expected_sla_miss_tickets"] = top_sla_miss_burden["expected_sla_miss_tickets"].round(1)

    stable_coverage = (
        float(stable_cells["tickets"].sum()) / float(cells["tickets"].sum())
        if len(cells) > 0
        else 0.0
    )

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("# Risk Mountain (Interactive 3D) - Report\n\n")
        f.write("## Business Objective\n")
        f.write(
            "Create a high-impact visual showing where operational complexity clusters: "
            "owner changes (X), desk transfers (Y), and median resolution time (Z), "
            "with bubble size for volume and color for SLA-miss risk.\n\n"
        )

        f.write("## Methodology\n")
        f.write(f"- Load period: **{ANALYSIS_LOAD_PERIOD}**\n")
        f.write("- Ticket scope: tickets with desk activity records, then filtered to closed tickets with valid parsed creation/closing timestamps and non-negative duration.\n")
        f.write("- Owner changes: count of `historysr.action = \"Re-assign\"` events per ticket.\n")
        f.write("- Desk transfers: count of desk changes in `activity.jur_assignedgroup_id` in event-time order.\n")
        f.write(f"- SLA miss proxy: `duration_hours > {SLA_THRESHOLD_HOURS:.0f}`.\n")
        f.write(f"- Bucketing: counts capped at **{MAX_BUCKET}+** for visual stability.\n")
        f.write(
            f"- Stable-cell rule for interpretation focus: `tickets >= {STABLE_CELL_MIN_TICKETS}` "
            "(full chart still includes all cells).\n\n"
        )

        f.write("## QA and Coverage\n")
        f.write(f"- SR rows in load period: **{summary['sr_rows_in_period']:,}**\n")
        f.write(f"- SR rows with desk activity records: **{summary['sr_rows_with_activity_desk']:,}**\n")
        f.write(f"- SR rows with parsed start/end: **{summary['sr_with_parsed_dates']:,}**\n")
        f.write(f"- Negative-duration rows excluded: **{summary['negative_duration_rows']:,}**\n")
        f.write(f"- Final ticket rows analyzed: **{summary['final_ticket_rows']:,}**\n")
        f.write(f"- Owner-change events (`Re-assign`): **{summary['owner_change_events']:,}**\n")
        f.write(f"- Activity rows with desk assignment: **{summary['activity_rows_with_desk']:,}**\n")
        f.write(f"- Overall median resolution: **{summary['overall_median_hours']/24.0:.3f} days**\n")
        f.write(f"- Overall average resolution: **{summary['overall_avg_hours']/24.0:.3f} days**\n")
        f.write(f"- Overall SLA miss rate (> {SLA_THRESHOLD_HOURS:.0f}h): **{summary['overall_sla_miss_rate']*100.0:.2f}%**\n")
        f.write(f"- 3D cells (all): **{len(cells):,}**\n")
        f.write(
            f"- Stable cells (`n >= {STABLE_CELL_MIN_TICKETS}`): **{len(stable_cells):,}** "
            f"(coverage: **{stable_coverage*100.0:.2f}%** of tickets)\n\n"
        )

        f.write("## Top Cells by Expected SLA-Miss Burden\n")
        f.write("(Expected burden = `tickets * sla_miss_rate`)\n\n")
        f.write(
            top_sla_miss_burden[
                [
                    "owner_bucket",
                    "transfer_bucket",
                    "tickets",
                    "median_duration_days",
                    "sla_miss_pct",
                    "expected_sla_miss_tickets",
                ]
            ].to_markdown(index=False)
        )
        f.write("\n\n")

        f.write("## How to Read the Mountain\n")
        f.write("- Taller bubbles (higher Z) indicate slower median resolution.\n")
        f.write("- Warmer colors indicate higher SLA-miss risk.\n")
        f.write("- Larger bubbles indicate higher-volume pain points.\n")
        f.write(
            "- High volume + high elevation + warm color clusters are the strongest candidates "
            "for AI coordination and stricter ownership governance.\n"
        )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Starting Risk Mountain build...", flush=True)
    cells, summary = build_dataset()
    if cells.empty:
        raise RuntimeError("No cells returned for risk-mountain analysis.")

    print("Building visuals...", flush=True)
    cells, stable_cells = build_visuals(cells)
    print("Writing outputs...", flush=True)
    cells.to_csv(OUTPUT_CELLS_CSV, index=False)
    stable_cells.to_csv(OUTPUT_CELLS_STABLE_CSV, index=False)
    build_report(cells, stable_cells, summary)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
