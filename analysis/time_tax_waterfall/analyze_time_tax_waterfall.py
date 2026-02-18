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


BASE_DIR = Path("/Users/milo/Desktop/BNP_BDD")
DB_PATH = BASE_DIR / "hobart.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "time_tax_waterfall"

OUTPUT_REPORT = OUTPUT_DIR / "time_tax_waterfall_report.md"
OUTPUT_COMPONENTS_CSV = OUTPUT_DIR / "time_tax_waterfall_components.csv"
OUTPUT_CELLS_CSV = OUTPUT_DIR / "time_tax_waterfall_cells.csv"
OUTPUT_CHART = OUTPUT_DIR / "time_tax_waterfall.png"

ANALYSIS_LOAD_PERIOD = "2025-01_to_2025-09"


def build_design_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    month_levels = sorted(df["creation_month"].dropna().astype(str).unique().tolist())
    issuer_levels = sorted(df["issuer"].dropna().astype(str).unique().tolist())

    feature_names = ["intercept", "has_owner_change", "has_desk_transfer", "reopened"]
    feature_names += [f"month__{m}" for m in month_levels[1:]]
    feature_names += [f"issuer__{i}" for i in issuer_levels[1:]]

    x_rows = []
    for row in df.itertuples(index=False):
        month_value = str(row.creation_month)
        issuer_value = str(row.issuer)
        feats = [
            1.0,
            float(row.has_owner_change),
            float(row.has_desk_transfer),
            float(row.reopened),
        ]
        feats += [1.0 if month_value == m else 0.0 for m in month_levels[1:]]
        feats += [1.0 if issuer_value == i else 0.0 for i in issuer_levels[1:]]
        x_rows.append(feats)

    return np.asarray(x_rows, dtype=float), feature_names


def fit_weighted_least_squares(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    # Weighted normal equation: beta = (X'WX)^(-1) X'Wy
    x_tw = x.T * w
    xtwx = x_tw @ x
    xtwy = x_tw @ y
    return np.linalg.pinv(xtwx) @ xtwy


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


def run_analysis() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # 1) Closed-ticket scope with parsed creation/close datetimes and duration in hours.
    conn.execute(
        """
        CREATE TEMP TABLE sr_scope_raw AS
        WITH parsed AS (
            SELECT
                id AS sr_id,
                COALESCE(issuer, 'UNKNOWN') AS issuer,
                '20' || substr(creationdate_parsed, 1, 2) || '-' || substr(creationdate_parsed, 4, 2) AS creation_month,
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
              AND creationdate_parsed IS NOT NULL
              AND closingdate_parsed IS NOT NULL
        )
        SELECT
            sr_id,
            issuer,
            creation_month,
            reopened,
            (julianday(closing_dt) - julianday(creation_dt)) * 24.0 AS duration_hours
        FROM parsed
        WHERE creation_dt IS NOT NULL
          AND closing_dt IS NOT NULL;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_sr_scope_raw_sr_id ON sr_scope_raw(sr_id);")

    # 2) Ownership changes from history (re-assign events).
    conn.execute(
        """
        CREATE TEMP TABLE reassign_events AS
        SELECT sr_id
        FROM historysr
        WHERE action = 'Re-assign'
          AND load_period = ?;
        """,
        (ANALYSIS_LOAD_PERIOD,),
    )
    conn.execute("CREATE INDEX idx_reassign_events_sr_id ON reassign_events(sr_id);")

    conn.execute(
        """
        CREATE TEMP TABLE owner_change_counts AS
        SELECT
            sr_id,
            COUNT(*) AS owner_change_count
        FROM reassign_events
        GROUP BY sr_id;
        """
    )
    conn.execute("CREATE INDEX idx_owner_change_counts_sr_id ON owner_change_counts(sr_id);")

    # 3) Desk transfer counts from activity stream.
    conn.execute(
        """
        CREATE TEMP TABLE desk_transfer_counts AS
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
        )
        SELECT
            sr_id,
            SUM(
                CASE
                    WHEN prev_group IS NOT NULL
                     AND jur_assignedgroup_id != prev_group
                    THEN 1
                    ELSE 0
                END
            ) AS desk_transfer_count
        FROM ordered_activity
        GROUP BY sr_id;
        """
    )
    conn.execute("CREATE INDEX idx_desk_transfer_counts_sr_id ON desk_transfer_counts(sr_id);")

    # 4) Final model base table (duration >= 0 only).
    conn.execute(
        """
        CREATE TEMP TABLE analysis_base AS
        SELECT
            s.sr_id,
            s.issuer,
            s.creation_month,
            s.reopened,
            s.duration_hours,
            COALESCE(o.owner_change_count, 0) AS owner_change_count,
            COALESCE(d.desk_transfer_count, 0) AS desk_transfer_count,
            CASE WHEN COALESCE(o.owner_change_count, 0) > 0 THEN 1 ELSE 0 END AS has_owner_change,
            CASE WHEN COALESCE(d.desk_transfer_count, 0) > 0 THEN 1 ELSE 0 END AS has_desk_transfer
        FROM sr_scope_raw s
        LEFT JOIN owner_change_counts o ON s.sr_id = o.sr_id
        LEFT JOIN desk_transfer_counts d ON s.sr_id = d.sr_id
        WHERE s.duration_hours >= 0;
        """
    )
    conn.execute("CREATE INDEX idx_analysis_base_duration ON analysis_base(duration_hours);")

    qa = pd.read_sql_query(
        """
        SELECT
            (SELECT COUNT(*) FROM sr_scope_raw) AS raw_rows,
            (SELECT COUNT(*) FROM sr_scope_raw WHERE duration_hours < 0) AS negative_duration_rows,
            (SELECT COUNT(*) FROM analysis_base) AS analysis_rows,
            (SELECT SUM(reopened) FROM analysis_base) AS reopened_rows,
            (SELECT COUNT(*) FROM reassign_events) AS owner_event_rows;
        """,
        conn,
    )

    n_rows = int(qa.loc[0, "analysis_rows"])
    if n_rows == 0:
        raise RuntimeError("No rows in analysis scope.")

    p99_offset = int((n_rows - 1) * 0.99)
    duration_cap = float(
        conn.execute(
            "SELECT duration_hours FROM analysis_base ORDER BY duration_hours LIMIT 1 OFFSET ?;",
            (p99_offset,),
        ).fetchone()[0]
    )

    conn.execute(
        """
        CREATE TEMP TABLE analysis_base_capped AS
        SELECT
            *,
            CASE WHEN duration_hours > ? THEN ? ELSE duration_hours END AS duration_capped_hours
        FROM analysis_base;
        """,
        (duration_cap, duration_cap),
    )
    conn.execute("CREATE INDEX idx_analysis_base_capped_duration ON analysis_base_capped(duration_capped_hours);")

    cells = pd.read_sql_query(
        """
        WITH ranked AS (
            SELECT
                creation_month,
                issuer,
                has_owner_change,
                has_desk_transfer,
                reopened,
                duration_capped_hours,
                ROW_NUMBER() OVER (
                    PARTITION BY creation_month, issuer, has_owner_change, has_desk_transfer, reopened
                    ORDER BY duration_capped_hours
                ) AS rn,
                COUNT(*) OVER (
                    PARTITION BY creation_month, issuer, has_owner_change, has_desk_transfer, reopened
                ) AS cnt
            FROM analysis_base_capped
        )
        SELECT
            creation_month,
            issuer,
            has_owner_change,
            has_desk_transfer,
            reopened,
            MAX(cnt) AS n,
            AVG(duration_capped_hours) AS median_duration_capped_hours
        FROM ranked
        WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
        GROUP BY creation_month, issuer, has_owner_change, has_desk_transfer, reopened
        ORDER BY creation_month, issuer, has_owner_change, has_desk_transfer, reopened;
        """,
        conn,
    )

    rates = pd.read_sql_query(
        """
        SELECT
            AVG(has_owner_change) AS owner_rate,
            AVG(has_desk_transfer) AS transfer_rate,
            AVG(reopened) AS reopen_rate
        FROM analysis_base_capped;
        """,
        conn,
    )

    global_median_raw_hours = sql_median(conn, "analysis_base", "duration_hours")
    global_median_capped_hours = sql_median(conn, "analysis_base_capped", "duration_capped_hours")

    baseline_none_hours = sql_median(
        conn,
        "analysis_base_capped",
        "duration_capped_hours",
        "has_owner_change = 0 AND has_desk_transfer = 0 AND reopened = 0",
    )
    owner_only_hours = sql_median(
        conn,
        "analysis_base_capped",
        "duration_capped_hours",
        "has_owner_change = 1 AND has_desk_transfer = 0 AND reopened = 0",
    )
    transfer_only_hours = sql_median(
        conn,
        "analysis_base_capped",
        "duration_capped_hours",
        "has_owner_change = 0 AND has_desk_transfer = 1 AND reopened = 0",
    )
    reopen_only_hours = sql_median(
        conn,
        "analysis_base_capped",
        "duration_capped_hours",
        "has_owner_change = 0 AND has_desk_transfer = 0 AND reopened = 1",
    )
    conn.close()

    # 5) Weighted regression on aggregated cells.
    x, feature_names = build_design_matrix(cells)
    y = cells["median_duration_capped_hours"].to_numpy(dtype=float)
    w = cells["n"].to_numpy(dtype=float)

    beta = fit_weighted_least_squares(x, y, w)

    # Goodness of fit at cell level (weighted).
    y_hat = x @ beta
    y_bar = np.average(y, weights=w)
    sse = np.sum(w * (y - y_hat) ** 2)
    sst = np.sum(w * (y - y_bar) ** 2)
    weighted_r2 = 1.0 - (sse / sst if sst > 0 else 0.0)

    # Standardized baseline: set all friction flags to 0 while keeping month/issuer mix.
    x_baseline = x.copy()
    x_baseline[:, 1] = 0.0
    x_baseline[:, 2] = 0.0
    x_baseline[:, 3] = 0.0
    baseline_cf_hours = float(np.average(x_baseline @ beta, weights=w))

    owner_effect_hours = float(beta[1])
    transfer_effect_hours = float(beta[2])
    reopen_effect_hours = float(beta[3])

    owner_rate = float(rates.loc[0, "owner_rate"])
    transfer_rate = float(rates.loc[0, "transfer_rate"])
    reopen_rate = float(rates.loc[0, "reopen_rate"])

    owner_contrib_hours = owner_effect_hours * owner_rate
    transfer_contrib_hours = transfer_effect_hours * transfer_rate
    reopen_contrib_hours = reopen_effect_hours * reopen_rate

    modeled_median_projection_hours = baseline_cf_hours + owner_contrib_hours + transfer_contrib_hours + reopen_contrib_hours
    actual_weighted_cell_median_hours = float(np.average(y, weights=w))
    model_gap_hours = actual_weighted_cell_median_hours - modeled_median_projection_hours

    components = pd.DataFrame(
        [
            {
                "component": "Baseline (no owner change / no desk transfer / no reopen)",
                "per_ticket_effect_hours": baseline_cf_hours,
                "prevalence_rate": 1.0,
                "population_contribution_hours": baseline_cf_hours,
            },
            {
                "component": "Owner-change tax",
                "per_ticket_effect_hours": owner_effect_hours,
                "prevalence_rate": owner_rate,
                "population_contribution_hours": owner_contrib_hours,
            },
            {
                "component": "Desk-transfer tax",
                "per_ticket_effect_hours": transfer_effect_hours,
                "prevalence_rate": transfer_rate,
                "population_contribution_hours": transfer_contrib_hours,
            },
            {
                "component": "Reopen tax",
                "per_ticket_effect_hours": reopen_effect_hours,
                "prevalence_rate": reopen_rate,
                "population_contribution_hours": reopen_contrib_hours,
            },
            {
                "component": "Modeled median projection (capped)",
                "per_ticket_effect_hours": modeled_median_projection_hours,
                "prevalence_rate": 1.0,
                "population_contribution_hours": modeled_median_projection_hours,
            },
        ]
    )
    components["per_ticket_effect_days"] = components["per_ticket_effect_hours"] / 24.0
    components["population_contribution_days"] = components["population_contribution_hours"] / 24.0
    components.to_csv(OUTPUT_COMPONENTS_CSV, index=False)

    cells.to_csv(OUTPUT_CELLS_CSV, index=False)

    # 6) Waterfall chart in days.
    baseline_days = baseline_cf_hours / 24.0
    owner_days = owner_contrib_hours / 24.0
    transfer_days = transfer_contrib_hours / 24.0
    reopen_days = reopen_contrib_hours / 24.0
    modeled_days = modeled_median_projection_hours / 24.0

    labels = [
        "Baseline\n(no frictions)",
        "Owner-change\ntax",
        "Desk-transfer\ntax",
        "Reopen\ntax",
        "Modeled\nmedian",
    ]

    increments = [baseline_days, owner_days, transfer_days, reopen_days]
    cumulative = [baseline_days]
    cumulative.append(cumulative[-1] + owner_days)
    cumulative.append(cumulative[-1] + transfer_days)
    cumulative.append(cumulative[-1] + reopen_days)

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.grid(axis="y", alpha=0.25)

    # Baseline bar.
    ax.bar(0, baseline_days, color="#4c78a8", width=0.65)

    # Incremental bars.
    colors = ["#f58518", "#54a24b", "#e45756"]
    for i, inc in enumerate([owner_days, transfer_days, reopen_days], start=1):
        bottom = cumulative[i - 1] - inc if inc < 0 else cumulative[i - 1]
        ax.bar(i, inc, bottom=bottom, color=colors[i - 1], width=0.65)

    # Final modeled median bar.
    ax.bar(4, modeled_days, color="#2f4b7c", width=0.65)

    # Add vertical headroom so value labels do not collide with the title area.
    y_points = [0.0, baseline_days, cumulative[1], cumulative[2], cumulative[3], modeled_days]
    y_min = float(min(y_points))
    y_max = float(max(y_points))
    y_span = max(y_max - y_min, 1.0)
    ax.set_ylim(y_min - 0.12 * y_span, y_max + 0.22 * y_span)

    values = [baseline_days, owner_days, transfer_days, reopen_days, modeled_days]
    positions = [baseline_days, cumulative[1], cumulative[2], cumulative[3], modeled_days]
    y_top = ax.get_ylim()[1]
    y_offset = 0.02 * y_span
    safe_top = y_top - 0.06 * y_span
    for i, val in enumerate(values):
        y_text = min(positions[i] + y_offset, safe_top)
        ax.text(
            i,
            y_text,
            f"{val:+.2f}d" if i in (1, 2, 3) else f"{val:.2f}d",
            ha="center",
            va="bottom",
            fontsize=10,
            clip_on=True,
        )

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Duration (Days)")
    ax.set_title("Time Tax Waterfall (Median-Based Decomposition)", fontsize=14, fontweight="bold", pad=16)
    plt.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    plt.savefig(OUTPUT_CHART, dpi=300)
    plt.close()

    # 7) Report.
    raw_rows = int(qa.loc[0, "raw_rows"])
    negative_rows = int(qa.loc[0, "negative_duration_rows"])
    analysis_rows = int(qa.loc[0, "analysis_rows"])
    reopened_rows = int(qa.loc[0, "reopened_rows"]) if pd.notna(qa.loc[0, "reopened_rows"]) else 0
    owner_event_rows = int(qa.loc[0, "owner_event_rows"])

    baseline_none = baseline_none_hours / 24.0 if pd.notna(baseline_none_hours) else np.nan
    owner_only = owner_only_hours / 24.0 if pd.notna(owner_only_hours) else np.nan
    transfer_only = transfer_only_hours / 24.0 if pd.notna(transfer_only_hours) else np.nan
    reopen_only = reopen_only_hours / 24.0 if pd.notna(reopen_only_hours) else np.nan

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("# Time Tax Waterfall Report\n\n")
        f.write("## Objective\n")
        f.write(
            "Decompose ticket duration at the median level into an additive baseline and three time-tax components: "
            "owner changes, desk transfers, and reopen events.\n\n"
        )

        f.write("## Scope and Guardrails\n")
        f.write(f"- Load period: **{ANALYSIS_LOAD_PERIOD}** (reopen field is reliably populated in this period).\n")
        f.write("- Population: tickets with valid parsed `creationdate_parsed` and `closingdate_parsed`.\n")
        f.write("- Duration definition: `closing_ts - creation_ts` in hours.\n")
        f.write("- Invalid durations: rows with negative duration are excluded from duration modeling.\n")
        f.write(
            f"- Outlier cap for stability and comparability: **p99 = {duration_cap:.2f} hours ({duration_cap/24.0:.2f} days)**.\n\n"
        )

        f.write("## QA Counts\n")
        f.write(f"- Raw scoped rows (pre duration filter): **{raw_rows:,}**\n")
        f.write(f"- Negative-duration rows excluded: **{negative_rows:,}**\n")
        f.write(f"- Final analysis rows: **{analysis_rows:,}**\n")
        f.write(f"- Reopened rows in analysis scope: **{reopened_rows:,}**\n")
        f.write(f"- Owner-change event rows (`Re-assign`) in scope: **{owner_event_rows:,}**\n\n")

        f.write("## Model\n")
        f.write(
            "Weighted least squares on aggregated cell medians "
            "(`month x issuer x owner_flag x transfer_flag x reopen_flag`).\n\n"
        )
        f.write("Formula (capped hours):\n")
        f.write("`duration = b0 + b1*owner + b2*transfer + b3*reopen + month_effects + issuer_effects + error`\n\n")
        f.write(f"- Weighted R^2 (cell-level): **{weighted_r2:.4f}**\n")
        f.write(f"- Global raw median duration: **{global_median_raw_hours/24.0:.3f} days**\n")
        f.write(f"- Global capped median duration: **{global_median_capped_hours/24.0:.3f} days**\n")
        f.write(
            f"- Actual weighted cell-median duration: **{actual_weighted_cell_median_hours/24.0:.3f} days**\n"
        )
        f.write(f"- Modeled median projection (capped): **{modeled_days:.3f} days**\n")
        f.write(f"- Model gap (actual weighted cell medians - modeled): **{model_gap_hours/24.0:.3f} days**\n\n")

        f.write("## Waterfall Components\n")
        f.write(components.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Quick Sanity Contrasts (Isolated Groups, Capped)\n")
        f.write(f"- Baseline none (`owner=0, transfer=0, reopen=0`): **{baseline_none:.3f} days**\n")
        f.write(f"- Owner only (`owner=1, transfer=0, reopen=0`): **{owner_only:.3f} days**\n")
        f.write(f"- Transfer only (`owner=0, transfer=1, reopen=0`): **{transfer_only:.3f} days**\n")
        f.write(f"- Reopen only (`owner=0, transfer=0, reopen=1`): **{reopen_only:.3f} days**\n\n")

        f.write("## Interpretation\n")
        f.write("- Baseline represents expected duration with no ownership/transfer/reopen frictions under observed month+issuer mix.\n")
        f.write("- Each tax bar is an additive contribution to the modeled median projection.\n")
        f.write("- This is an associative decomposition (not causal identification), but it is operationally actionable.\n")


if __name__ == "__main__":
    run_analysis()
