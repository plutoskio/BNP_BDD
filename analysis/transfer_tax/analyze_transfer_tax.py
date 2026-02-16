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
OUTPUT_DIR = BASE_DIR / "analysis" / "transfer_tax"
OUTPUT_PNG = OUTPUT_DIR / "transfer_tax_histogram.png"
OUTPUT_AVG_PNG = OUTPUT_DIR / "avg_resolution_vs_transfers.png"
OUTPUT_MD = OUTPUT_DIR / "transfer_tax_summary.md"


def parse_hobart_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%y-%m-%d %H.%M.%S", errors="coerce")


def build_transfer_tax_histogram() -> None:
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
    )
    SELECT
        s.id AS sr_id,
        tc.transfer_count,
        s.creationdate_parsed,
        s.closingdate_parsed
    FROM transfer_counts tc
    JOIN sr s
        ON s.id = tc.sr_id
    WHERE s.creationdate_parsed IS NOT NULL
      AND s.closingdate_parsed IS NOT NULL;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise RuntimeError("No rows returned for transfer-tax analysis.")

    df["start"] = parse_hobart_date(df["creationdate_parsed"])
    df["end"] = parse_hobart_date(df["closingdate_parsed"])
    df = df.dropna(subset=["start", "end"])

    df["resolution_days"] = (df["end"] - df["start"]).dt.total_seconds() / 86400.0
    df = df[df["resolution_days"] >= 0]

    # Buckets sized for presentation readability.
    df["transfer_bucket"] = pd.cut(
        df["transfer_count"],
        bins=[-1, 0, 1, 3, 10_000],
        labels=["0 transfers", "1 transfer", "2-3 transfers", "4+ transfers"],
    )

    # Trim extreme outliers for cleaner histogram view.
    p99 = df["resolution_days"].quantile(0.99)
    plot_df = df[df["resolution_days"] <= p99].copy()

    plt.figure(figsize=(13, 8))
    plt.grid(alpha=0.25)
    for bucket, bucket_df in plot_df.groupby("transfer_bucket", observed=True):
        plt.hist(
            bucket_df["resolution_days"],
            bins=60,
            density=True,
            histtype="step",
            linewidth=2,
            label=str(bucket),
        )
    plt.title("Transfer Tax Histogram: Resolution Time by Desk-Transfer Bucket", fontsize=16, fontweight="bold")
    plt.xlabel("Resolution Time (Days)")
    plt.ylabel("Density")
    plt.legend(title="Transfer Bucket")
    plt.xlim(left=0)
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=300)
    plt.close()

    # Presentation chart requested: average resolution time vs number of transfers.
    # Cap at 6+, so the x-axis stays readable and robust.
    df["transfer_count_cap"] = df["transfer_count"].clip(upper=6)
    avg_by_transfer = (
        df.groupby("transfer_count_cap", observed=True)["resolution_days"]
        .agg(["count", "mean", "median"])
        .reset_index()
        .rename(columns={"mean": "avg_days", "median": "median_days"})
    )
    avg_by_transfer["transfer_label"] = avg_by_transfer["transfer_count_cap"].astype(str)
    avg_by_transfer.loc[avg_by_transfer["transfer_count_cap"] == 6, "transfer_label"] = "6+"

    x = avg_by_transfer["transfer_count_cap"].astype(float).to_numpy()
    y = avg_by_transfer["avg_days"].to_numpy()

    plt.figure(figsize=(11, 7))
    plt.grid(axis="y", alpha=0.25)
    plt.bar(x, y, color="#2f6ea3", width=0.72)
    plt.title("Average Resolution Time vs Number of Transfers", fontsize=16, fontweight="bold")
    plt.xlabel("Number of Desk Transfers (capped at 6+)")
    plt.ylabel("Average Resolution Time (Days)")
    plt.xticks(x, avg_by_transfer["transfer_label"])
    for i, v in enumerate(y):
        plt.text(x[i], v + 0.5, f"{v:.1f}", ha="center", va="bottom", fontsize=10)
    plt.tight_layout()
    plt.savefig(OUTPUT_AVG_PNG, dpi=300)
    plt.close()

    summary = (
        df.groupby("transfer_bucket", observed=True)["resolution_days"]
        .agg(["count", "mean", "median", "quantile"])
        .reset_index()
    )

    # Recompute p90 cleanly for reporting.
    p90 = (
        df.groupby("transfer_bucket", observed=True)["resolution_days"]
        .quantile(0.9)
        .rename("p90")
        .reset_index()
    )
    summary = summary.drop(columns=["quantile"]).merge(p90, on="transfer_bucket", how="left")
    summary = summary.rename(columns={"mean": "avg_days", "median": "median_days"})

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Transfer Tax Summary\n\n")
        f.write("Resolution-time statistics by number of desk transfers.\n\n")
        f.write(f"- Population analyzed: {len(df):,} closed tickets with valid parsed dates.\n")
        f.write(f"- Histogram cap: 99th percentile at {p99:.2f} days for visual clarity.\n\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n## Average Resolution by Transfer Count (0 to 6+)\n\n")
        f.write(avg_by_transfer[["transfer_label", "count", "avg_days", "median_days"]].to_markdown(index=False))
        f.write("\n")


if __name__ == "__main__":
    build_transfer_tax_histogram()
