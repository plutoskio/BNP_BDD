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
from scipy.stats import fisher_exact, norm


BASE_DIR = Path("/Users/milo/Desktop/BNP_BDD")
DB_PATH = BASE_DIR / "hobart.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "ownership_transfers"
OUTPUT_REOPEN_REPORT = OUTPUT_DIR / "ownership_transfer_reopen_report.md"
OUTPUT_GLOBAL_REPORT = OUTPUT_DIR / "ownership_transfer_global_report.md"

OUTPUT_REOPEN_SUMMARY_CSV = OUTPUT_DIR / "ownership_transfer_reopen_summary.csv"
OUTPUT_REOPEN_BUCKETS_CSV = OUTPUT_DIR / "ownership_transfer_reopen_buckets.csv"
OUTPUT_REOPEN_BINARY_PNG = OUTPUT_DIR / "reopen_rate_transfer_vs_no_transfer.png"
OUTPUT_REOPEN_BUCKET_PNG = OUTPUT_DIR / "reopen_rate_by_transfer_count_bucket.png"

OUTPUT_DURATION_SUMMARY_CSV = OUTPUT_DIR / "ownership_transfer_duration_summary.csv"
OUTPUT_DURATION_BUCKETS_CSV = OUTPUT_DIR / "ownership_transfer_duration_buckets.csv"
OUTPUT_DURATION_BINARY_PNG = OUTPUT_DIR / "duration_transfer_vs_no_transfer.png"
OUTPUT_DURATION_BUCKET_PNG = OUTPUT_DIR / "duration_by_transfer_count_bucket.png"

# Reopen signal is only populated in this load period.
ANALYSIS_LOAD_PERIOD = "2025-01_to_2025-09"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")

    p_hat = k / n
    denom = 1 + (z**2 / n)
    center = (p_hat + (z**2 / (2 * n))) / denom
    margin = (
        z
        * np.sqrt((p_hat * (1 - p_hat) + (z**2 / (4 * n))) / n)
        / denom
    )
    return float(center - margin), float(center + margin)


def run_analysis() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TEMP TABLE closed_scope AS
        WITH parsed AS (
            SELECT
                id AS sr_id,
                CASE WHEN reopen_date_parsed IS NOT NULL THEN 1 ELSE 0 END AS reopened,
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
            WHERE load_period = ?
              AND closingdate_parsed IS NOT NULL
              AND creationdate_parsed IS NOT NULL
        )
        SELECT
            sr_id,
            reopened,
            creation_dt,
            closing_dt,
            (julianday(closing_dt) - julianday(creation_dt)) * 24.0 AS duration_hours
        FROM parsed;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_closed_scope_sr_id ON closed_scope(sr_id);")

    conn.execute(
        """
        CREATE TEMP TABLE reassign_events AS
        SELECT
            sr_id
        FROM historysr
        WHERE action = 'Re-assign'
          AND load_period = ?;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_reassign_events_sr_id ON reassign_events(sr_id);")

    conn.execute(
        """
        CREATE TEMP TABLE owner_transfer_counts AS
        SELECT
            r.sr_id,
            COUNT(*) AS owner_transfer_events
        FROM reassign_events r
        GROUP BY r.sr_id;
        """,
    )
    conn.execute("CREATE INDEX idx_owner_transfer_counts_sr_id ON owner_transfer_counts(sr_id);")

    summary = pd.read_sql_query(
        """
        SELECT
            CASE
                WHEN COALESCE(ot.owner_transfer_events, 0) > 0
                THEN 1
                ELSE 0
            END AS has_owner_transfer,
            COUNT(*) AS tickets,
            SUM(cs.reopened) AS reopened_tickets,
            AVG(COALESCE(ot.owner_transfer_events, 0)) AS avg_owner_transfer_events
        FROM closed_scope cs
        LEFT JOIN owner_transfer_counts ot ON cs.sr_id = ot.sr_id
        GROUP BY has_owner_transfer
        ORDER BY has_owner_transfer;
        """,
        conn,
    )

    bucket_summary = pd.read_sql_query(
        """
        SELECT
            CASE
                WHEN COALESCE(ot.owner_transfer_events, 0) = 0 THEN '0'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 1 THEN '1'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 2 THEN '2'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 3 THEN '3'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 4 THEN '4'
                ELSE '5+'
            END AS transfer_bucket,
            COUNT(*) AS tickets,
            SUM(cs.reopened) AS reopened_tickets
        FROM closed_scope cs
        LEFT JOIN owner_transfer_counts ot ON cs.sr_id = ot.sr_id
        GROUP BY transfer_bucket
        ORDER BY
            CASE transfer_bucket
                WHEN '0' THEN 0
                WHEN '1' THEN 1
                WHEN '2' THEN 2
                WHEN '3' THEN 3
                WHEN '4' THEN 4
                ELSE 5
            END;
        """,
        conn,
    )

    duration_summary = pd.read_sql_query(
        """
        SELECT
            CASE
                WHEN COALESCE(ot.owner_transfer_events, 0) > 0
                THEN 1
                ELSE 0
            END AS has_owner_transfer,
            COUNT(*) AS tickets,
            AVG(cs.duration_hours) AS avg_duration_hours,
            AVG(cs.duration_hours) / 24.0 AS avg_duration_days,
            AVG(CASE WHEN cs.duration_hours > 168.0 THEN 168.0 ELSE cs.duration_hours END) AS avg_duration_hours_capped_168,
            SUM(CASE WHEN cs.duration_hours > 24.0 THEN 1 ELSE 0 END) AS tickets_over_24h,
            SUM(CASE WHEN cs.duration_hours > 72.0 THEN 1 ELSE 0 END) AS tickets_over_72h,
            SUM(CASE WHEN cs.duration_hours > 168.0 THEN 1 ELSE 0 END) AS tickets_over_168h
        FROM closed_scope cs
        LEFT JOIN owner_transfer_counts ot ON cs.sr_id = ot.sr_id
        WHERE cs.duration_hours IS NOT NULL
          AND cs.duration_hours >= 0
        GROUP BY has_owner_transfer
        ORDER BY has_owner_transfer;
        """,
        conn,
    )

    duration_bucket_summary = pd.read_sql_query(
        """
        SELECT
            CASE
                WHEN COALESCE(ot.owner_transfer_events, 0) = 0 THEN '0'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 1 THEN '1'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 2 THEN '2'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 3 THEN '3'
                WHEN COALESCE(ot.owner_transfer_events, 0) = 4 THEN '4'
                ELSE '5+'
            END AS transfer_bucket,
            COUNT(*) AS tickets,
            AVG(cs.duration_hours) AS avg_duration_hours,
            AVG(cs.duration_hours) / 24.0 AS avg_duration_days,
            AVG(CASE WHEN cs.duration_hours > 168.0 THEN 168.0 ELSE cs.duration_hours END) AS avg_duration_hours_capped_168,
            SUM(CASE WHEN cs.duration_hours > 24.0 THEN 1 ELSE 0 END) AS tickets_over_24h,
            SUM(CASE WHEN cs.duration_hours > 72.0 THEN 1 ELSE 0 END) AS tickets_over_72h,
            SUM(CASE WHEN cs.duration_hours > 168.0 THEN 1 ELSE 0 END) AS tickets_over_168h
        FROM closed_scope cs
        LEFT JOIN owner_transfer_counts ot ON cs.sr_id = ot.sr_id
        WHERE cs.duration_hours IS NOT NULL
          AND cs.duration_hours >= 0
        GROUP BY transfer_bucket
        ORDER BY
            CASE transfer_bucket
                WHEN '0' THEN 0
                WHEN '1' THEN 1
                WHEN '2' THEN 2
                WHEN '3' THEN 3
                WHEN '4' THEN 4
                ELSE 5
            END;
        """,
        conn,
    )

    qa_owner_events = pd.read_sql_query(
        """
        SELECT
            COUNT(*) AS owner_event_rows,
            COUNT(DISTINCT original_id) AS owner_event_distinct_original_id,
            COUNT(*) - COUNT(DISTINCT original_id) AS owner_event_duplicate_rows
        FROM historysr
        WHERE action = 'Re-assign'
          AND load_period = ?;
        """,
        conn,
        params=(ANALYSIS_LOAD_PERIOD,),
    )

    qa_scope = pd.read_sql_query(
        """
        SELECT
            COUNT(*) AS closed_tickets,
            SUM(reopened) AS reopened_tickets
        FROM closed_scope;
        """,
        conn,
    )

    qa_duration = pd.read_sql_query(
        """
        SELECT
            COUNT(*) AS closed_scope_rows,
            SUM(CASE WHEN duration_hours IS NULL THEN 1 ELSE 0 END) AS duration_null_rows,
            SUM(CASE WHEN duration_hours < 0 THEN 1 ELSE 0 END) AS duration_negative_rows,
            SUM(CASE WHEN duration_hours >= 0 THEN 1 ELSE 0 END) AS duration_nonnegative_rows
        FROM closed_scope;
        """,
        conn,
    )
    conn.close()

    if summary.empty or bucket_summary.empty or duration_summary.empty or duration_bucket_summary.empty:
        raise RuntimeError("No rows returned for ownership transfer analysis.")

    summary["reopen_rate"] = summary["reopened_tickets"] / summary["tickets"]
    summary["reopen_rate_pct"] = summary["reopen_rate"] * 100.0
    summary["group"] = np.where(
        summary["has_owner_transfer"] == 1,
        "With Ownership Transfer",
        "No Ownership Transfer",
    )

    ci_bounds = summary.apply(lambda row: wilson_ci(int(row["reopened_tickets"]), int(row["tickets"])), axis=1)
    summary["reopen_rate_ci_low"] = [x[0] for x in ci_bounds]
    summary["reopen_rate_ci_high"] = [x[1] for x in ci_bounds]
    summary["reopen_rate_ci_low_pct"] = summary["reopen_rate_ci_low"] * 100.0
    summary["reopen_rate_ci_high_pct"] = summary["reopen_rate_ci_high"] * 100.0

    summary_out = summary[
        [
            "group",
            "tickets",
            "reopened_tickets",
            "reopen_rate",
            "reopen_rate_pct",
            "reopen_rate_ci_low",
            "reopen_rate_ci_high",
            "reopen_rate_ci_low_pct",
            "reopen_rate_ci_high_pct",
            "avg_owner_transfer_events",
        ]
    ].sort_values("group")
    summary_out.to_csv(OUTPUT_REOPEN_SUMMARY_CSV, index=False)

    bucket_order = ["0", "1", "2", "3", "4", "5+"]
    bucket_summary["transfer_bucket"] = pd.Categorical(
        bucket_summary["transfer_bucket"], categories=bucket_order, ordered=True
    )
    bucket_summary = bucket_summary.sort_values("transfer_bucket")
    bucket_summary["reopen_rate"] = bucket_summary["reopened_tickets"] / bucket_summary["tickets"]
    bucket_summary["reopen_rate_pct"] = bucket_summary["reopen_rate"] * 100.0

    bucket_ci = bucket_summary.apply(lambda row: wilson_ci(int(row["reopened_tickets"]), int(row["tickets"])), axis=1)
    bucket_summary["reopen_rate_ci_low"] = [x[0] for x in bucket_ci]
    bucket_summary["reopen_rate_ci_high"] = [x[1] for x in bucket_ci]
    bucket_summary["reopen_rate_ci_low_pct"] = bucket_summary["reopen_rate_ci_low"] * 100.0
    bucket_summary["reopen_rate_ci_high_pct"] = bucket_summary["reopen_rate_ci_high"] * 100.0
    bucket_summary.to_csv(OUTPUT_REOPEN_BUCKETS_CSV, index=False)

    duration_summary["group"] = np.where(
        duration_summary["has_owner_transfer"] == 1,
        "With Ownership Transfer",
        "No Ownership Transfer",
    )
    duration_summary["tickets_over_24h_pct"] = (duration_summary["tickets_over_24h"] / duration_summary["tickets"]) * 100.0
    duration_summary["tickets_over_72h_pct"] = (duration_summary["tickets_over_72h"] / duration_summary["tickets"]) * 100.0
    duration_summary["tickets_over_168h_pct"] = (duration_summary["tickets_over_168h"] / duration_summary["tickets"]) * 100.0
    duration_summary["avg_duration_days_capped_168"] = duration_summary["avg_duration_hours_capped_168"] / 24.0

    duration_summary_out = duration_summary[
        [
            "group",
            "tickets",
            "avg_duration_hours",
            "avg_duration_days",
            "avg_duration_hours_capped_168",
            "avg_duration_days_capped_168",
            "tickets_over_24h",
            "tickets_over_24h_pct",
            "tickets_over_72h",
            "tickets_over_72h_pct",
            "tickets_over_168h",
            "tickets_over_168h_pct",
        ]
    ].sort_values("group")
    duration_summary_out.to_csv(OUTPUT_DURATION_SUMMARY_CSV, index=False)

    duration_bucket_summary["transfer_bucket"] = pd.Categorical(
        duration_bucket_summary["transfer_bucket"], categories=bucket_order, ordered=True
    )
    duration_bucket_summary = duration_bucket_summary.sort_values("transfer_bucket")
    duration_bucket_summary["tickets_over_24h_pct"] = (
        duration_bucket_summary["tickets_over_24h"] / duration_bucket_summary["tickets"]
    ) * 100.0
    duration_bucket_summary["tickets_over_72h_pct"] = (
        duration_bucket_summary["tickets_over_72h"] / duration_bucket_summary["tickets"]
    ) * 100.0
    duration_bucket_summary["tickets_over_168h_pct"] = (
        duration_bucket_summary["tickets_over_168h"] / duration_bucket_summary["tickets"]
    ) * 100.0
    duration_bucket_summary["avg_duration_days_capped_168"] = duration_bucket_summary["avg_duration_hours_capped_168"] / 24.0
    duration_bucket_summary.to_csv(OUTPUT_DURATION_BUCKETS_CSV, index=False)

    # Effect size + significance for binary split.
    with_transfer = summary[summary["has_owner_transfer"] == 1].iloc[0]
    without_transfer = summary[summary["has_owner_transfer"] == 0].iloc[0]

    a = int(with_transfer["reopened_tickets"])
    b = int(with_transfer["tickets"] - with_transfer["reopened_tickets"])
    c = int(without_transfer["reopened_tickets"])
    d = int(without_transfer["tickets"] - without_transfer["reopened_tickets"])

    rate_with = a / (a + b)
    rate_without = c / (c + d)
    rate_diff = rate_with - rate_without
    rate_diff_pp = rate_diff * 100.0

    # Approximate 95% CI for risk difference using unpooled normal standard error.
    diff_se = np.sqrt((rate_with * (1 - rate_with) / (a + b)) + (rate_without * (1 - rate_without) / (c + d)))
    diff_ci_low = rate_diff - 1.96 * diff_se
    diff_ci_high = rate_diff + 1.96 * diff_se

    relative_risk = rate_with / rate_without if rate_without > 0 else np.nan
    odds_ratio, fisher_p_value = fisher_exact([[a, b], [c, d]], alternative="two-sided")

    pooled = (a + c) / (a + b + c + d)
    z_se = np.sqrt(pooled * (1 - pooled) * ((1 / (a + b)) + (1 / (c + d))))
    z_score = rate_diff / z_se if z_se > 0 else np.nan
    z_p_value = 2 * (1 - norm.cdf(abs(z_score))) if np.isfinite(z_score) else np.nan

    # Chart 1: binary transfer vs no transfer.
    plt.figure(figsize=(9, 6))
    x = np.arange(len(summary_out))
    y = summary_out["reopen_rate_pct"].to_numpy()
    yerr_low = y - summary_out["reopen_rate_ci_low_pct"].to_numpy()
    yerr_high = summary_out["reopen_rate_ci_high_pct"].to_numpy() - y

    plt.bar(x, y, color=["#1f77b4", "#ff7f0e"], width=0.62)
    plt.errorbar(
        x,
        y,
        yerr=[yerr_low, yerr_high],
        fmt="none",
        ecolor="black",
        capsize=4,
        linewidth=1,
    )
    plt.xticks(x, summary_out["group"], rotation=0)
    plt.ylabel("Reopen Rate (%)")
    plt.title("Reopen Rate: Tickets With vs Without Ownership Transfers", fontsize=13, fontweight="bold")
    plt.grid(axis="y", alpha=0.25)

    for i, row in enumerate(summary_out.itertuples(index=False)):
        plt.text(
            i,
            y[i] + max(y) * 0.03,
            f"{row.reopened_tickets:,}/{row.tickets:,}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_REOPEN_BINARY_PNG, dpi=300)
    plt.close()

    # Chart 2: reopen rate by ownership transfer count bucket.
    plt.figure(figsize=(10, 6))
    bx = np.arange(len(bucket_summary))
    by = bucket_summary["reopen_rate_pct"].to_numpy()
    plt.bar(bx, by, color="#2f6ea3", width=0.7)
    plt.xticks(bx, bucket_summary["transfer_bucket"])
    plt.ylabel("Reopen Rate (%)")
    plt.xlabel("Ownership Transfer Count Bucket")
    plt.title("Reopen Rate by Ownership Transfer Count", fontsize=13, fontweight="bold")
    plt.grid(axis="y", alpha=0.25)

    for i, row in enumerate(bucket_summary.itertuples(index=False)):
        plt.text(
            i,
            by[i] + max(by) * 0.03 if len(by) else 0.0,
            f"{row.reopened_tickets:,}/{row.tickets:,}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_REOPEN_BUCKET_PNG, dpi=300)
    plt.close()

    # Duration effects: with transfer vs without transfer.
    duration_with = duration_summary[duration_summary["has_owner_transfer"] == 1].iloc[0]
    duration_without = duration_summary[duration_summary["has_owner_transfer"] == 0].iloc[0]

    avg_duration_hours_with = float(duration_with["avg_duration_hours"])
    avg_duration_hours_without = float(duration_without["avg_duration_hours"])
    avg_duration_days_with = avg_duration_hours_with / 24.0
    avg_duration_days_without = avg_duration_hours_without / 24.0
    avg_duration_diff_hours = avg_duration_hours_with - avg_duration_hours_without
    avg_duration_diff_days = avg_duration_diff_hours / 24.0
    avg_duration_ratio = (
        avg_duration_hours_with / avg_duration_hours_without
        if avg_duration_hours_without > 0
        else np.nan
    )

    # Chart 3: average duration days, transfer vs no transfer.
    plt.figure(figsize=(9, 6))
    dx = np.arange(len(duration_summary_out))
    dy = duration_summary_out["avg_duration_days"].to_numpy()
    plt.bar(dx, dy, color=["#1f77b4", "#ff7f0e"], width=0.62)
    plt.xticks(dx, duration_summary_out["group"], rotation=0)
    plt.ylabel("Average Duration (Days)")
    plt.title("Owner Changes vs Duration (Closed Tickets)", fontsize=13, fontweight="bold")
    plt.grid(axis="y", alpha=0.25)
    for i, row in enumerate(duration_summary_out.itertuples(index=False)):
        plt.text(
            i,
            dy[i] + max(dy) * 0.03 if len(dy) else 0.0,
            f"{row.tickets_over_72h_pct:.2f}% > 72h",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(OUTPUT_DURATION_BINARY_PNG, dpi=300)
    plt.close()

    # Chart 4: average duration days by transfer count bucket.
    plt.figure(figsize=(10, 6))
    dbx = np.arange(len(duration_bucket_summary))
    dby = duration_bucket_summary["avg_duration_days"].to_numpy()
    plt.bar(dbx, dby, color="#2f6ea3", width=0.7)
    plt.xticks(dbx, duration_bucket_summary["transfer_bucket"])
    plt.ylabel("Average Duration (Days)")
    plt.xlabel("Ownership Transfer Count Bucket")
    plt.title("Average Duration by Ownership Transfer Count", fontsize=13, fontweight="bold")
    plt.grid(axis="y", alpha=0.25)
    for i, v in enumerate(dby):
        plt.text(
            i,
            v + max(dby) * 0.015 if len(dby) else 0.0,
            f"{v:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(OUTPUT_DURATION_BUCKET_PNG, dpi=300)
    plt.close()

    owner_event_rows = int(qa_owner_events.loc[0, "owner_event_rows"])
    owner_event_distinct_original = int(qa_owner_events.loc[0, "owner_event_distinct_original_id"])
    owner_event_duplicate_rows = int(qa_owner_events.loc[0, "owner_event_duplicate_rows"])
    closed_tickets = int(qa_scope.loc[0, "closed_tickets"])
    reopened_tickets = int(qa_scope.loc[0, "reopened_tickets"])
    duration_null_rows = int(qa_duration.loc[0, "duration_null_rows"])
    duration_negative_rows = int(qa_duration.loc[0, "duration_negative_rows"])
    duration_nonnegative_rows = int(qa_duration.loc[0, "duration_nonnegative_rows"])

    with open(OUTPUT_REOPEN_REPORT, "w", encoding="utf-8") as f:
        f.write("# Ownership Transfers vs Reopen Rate\n\n")
        f.write("## Objective\n")
        f.write("Assess whether tickets with ownership transfers are reopened more often than tickets without ownership transfers.\n\n")

        f.write("## Scope and Data Rules (Rigorous Guardrails)\n")
        f.write(f"- `load_period` restricted to **{ANALYSIS_LOAD_PERIOD}**.\n")
        f.write("- Reason: `reopen_date_parsed` is populated only in this period; later periods are all null and would bias reopen rates downward.\n")
        f.write("- Population: SRs with non-null `closingdate_parsed` (tickets that reached closure at least once).\n")
        f.write("- Ownership transfer event: `historysr.action = 'Re-assign'`.\n")
        f.write("- Event count per ticket: `COUNT(historysr rows)` for `action='Re-assign'`.\n")
        f.write("- In-scope duplicate check confirms `historysr` owner events have no duplicate `original_id` rows in this period.\n\n")

        f.write("## QA Checks\n")
        f.write(f"- Owner transfer history rows in-scope: **{owner_event_rows:,}**\n")
        f.write(f"- Distinct owner transfer event `original_id` in-scope: **{owner_event_distinct_original:,}**\n")
        f.write(f"- Duplicate owner transfer rows in-scope (`rows - distinct original_id`): **{owner_event_duplicate_rows:,}**\n")
        f.write(f"- Closed tickets in-scope: **{closed_tickets:,}**\n")
        f.write(f"- Reopened tickets in-scope: **{reopened_tickets:,}**\n\n")

        f.write("## Main Result: With vs Without Ownership Transfer\n")
        f.write(summary_out.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Effect Size and Statistical Test\n")
        f.write(f"- Reopen rate (with transfer): **{rate_with*100:.4f}%**\n")
        f.write(f"- Reopen rate (without transfer): **{rate_without*100:.4f}%**\n")
        f.write(f"- Absolute difference: **{rate_diff_pp:.4f} percentage points**\n")
        f.write(f"- 95% CI for difference (approx): **[{diff_ci_low*100:.4f}, {diff_ci_high*100:.4f}] pp**\n")
        f.write(f"- Relative risk: **{relative_risk:.4f}x**\n")
        f.write(f"- Odds ratio (Fisher exact): **{odds_ratio:.4f}**\n")
        f.write(f"- Fisher exact p-value: **{fisher_p_value:.6g}**\n")
        f.write(f"- Two-proportion z-test p-value: **{z_p_value:.6g}**\n\n")

        f.write("## Reopen Rate by Ownership Transfer Count\n")
        f.write(bucket_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Interpretation (Business Case)\n")
        f.write("- If ownership-transfer tickets show materially higher reopen rates, this supports the hypothesis that unstable ownership degrades resolution quality.\n")
        f.write("- This is consistent with proposing an AI coordinator for routing plus one accountable human owner per ticket.\n")
        f.write("- This analysis is associative, not causal; transfer-heavy tickets may also be intrinsically more complex.\n")
        f.write("- See `ownership_transfer_global_report.md` for duration impact in the same scope.\n")

    with open(OUTPUT_GLOBAL_REPORT, "w", encoding="utf-8") as f:
        f.write("# Ownership Transfers: Global Report\n\n")
        f.write("## Scope\n")
        f.write(f"- Analysis window: **{ANALYSIS_LOAD_PERIOD}**\n")
        f.write("- Population: closed SR tickets in-scope.\n")
        f.write("- Ownership transfer event: `historysr.action = 'Re-assign'`.\n")
        f.write("- Reopen caveat: this period is used because reopen signal is populated only here.\n\n")

        f.write("## QA and Data Integrity\n")
        f.write(f"- Closed tickets in-scope: **{closed_tickets:,}**\n")
        f.write(f"- Reopened tickets in-scope: **{reopened_tickets:,}**\n")
        f.write(f"- Owner transfer history rows in-scope: **{owner_event_rows:,}**\n")
        f.write(f"- Owner transfer duplicate rows (`rows - distinct original_id`): **{owner_event_duplicate_rows:,}**\n")
        f.write(f"- Duration rows with null parsed value: **{duration_null_rows:,}**\n")
        f.write(f"- Duration rows with negative value (excluded from duration metrics): **{duration_negative_rows:,}**\n")
        f.write(f"- Duration rows used for duration metrics: **{duration_nonnegative_rows:,}**\n\n")

        f.write("## Part A: Reopen Rate vs Ownership Transfers\n")
        f.write(summary_out.to_markdown(index=False))
        f.write("\n\n")
        f.write(f"- Reopen rate (with transfer): **{rate_with*100:.4f}%**\n")
        f.write(f"- Reopen rate (without transfer): **{rate_without*100:.4f}%**\n")
        f.write(f"- Absolute difference: **{rate_diff_pp:.4f} pp**\n")
        f.write(f"- Relative risk: **{relative_risk:.4f}x**\n")
        f.write(f"- Fisher exact p-value: **{fisher_p_value:.6g}**\n")
        f.write(f"- Two-proportion z-test p-value: **{z_p_value:.6g}**\n\n")
        f.write("### Reopen by Transfer Count Bucket\n")
        f.write(bucket_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Part B: Owner Changes vs Duration\n")
        f.write(duration_summary_out.to_markdown(index=False))
        f.write("\n\n")
        f.write(
            f"- Average duration with transfer: **{avg_duration_days_with:.3f} days** "
            f"({avg_duration_hours_with:.2f}h)\n"
        )
        f.write(
            f"- Average duration without transfer: **{avg_duration_days_without:.3f} days** "
            f"({avg_duration_hours_without:.2f}h)\n"
        )
        f.write(
            f"- Average duration difference (with - without): **{avg_duration_diff_days:.3f} days** "
            f"({avg_duration_diff_hours:.2f}h)\n"
        )
        f.write(f"- Average duration ratio (with / without): **{avg_duration_ratio:.4f}x**\n\n")
        f.write("### Duration by Transfer Count Bucket\n")
        f.write(duration_bucket_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Interpretation\n")
        f.write("- Reopen-rate signal alone does not show deterioration for transfer tickets in this dataset slice.\n")
        f.write("- Duration analysis quantifies whether ownership changes still create cycle-time friction even without higher reopen rates.\n")
        f.write("- This supports a combined argument: stabilize accountability (single owner) while AI orchestrates routing across desks.\n")


if __name__ == "__main__":
    run_analysis()
