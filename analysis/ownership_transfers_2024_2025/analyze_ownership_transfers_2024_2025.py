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
OUTPUT_DIR = BASE_DIR / "analysis" / "ownership_transfers_2024_2025"
OUTPUT_CSV = OUTPUT_DIR / "ownership_transfers_2024_2025.csv"
OUTPUT_MD = OUTPUT_DIR / "ownership_transfers_2024_2025_report.md"
OUTPUT_PNG = OUTPUT_DIR / "ownership_transfers_2024_2025_bar.png"

TARGET_YEARS = (2024, 2025)


def fetch_ownership_transfer_stats(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH sr_scoped AS (
        SELECT
            id AS sr_id,
            CAST('20' || substr(creationdate_parsed, 1, 2) AS INTEGER) AS creation_year
        FROM sr
        WHERE creationdate_parsed IS NOT NULL
          AND closingdate_parsed IS NOT NULL
          AND CAST('20' || substr(creationdate_parsed, 1, 2) AS INTEGER) IN (?, ?)
    ),
    year_ticket_totals AS (
        SELECT
            creation_year,
            COUNT(*) AS closed_tickets
        FROM sr_scoped
        GROUP BY creation_year
    ),
    year_transfer_totals AS (
        SELECT
            s.creation_year,
            COUNT(*) AS total_owner_transfers
        FROM historysr h
        JOIN sr_scoped s ON h.sr_id = s.sr_id
        WHERE h.action = 'Re-assign'
        GROUP BY s.creation_year
    )
    SELECT
        y.creation_year,
        y.closed_tickets,
        COALESCE(t.total_owner_transfers, 0) AS total_owner_transfers,
        1.0 * COALESCE(t.total_owner_transfers, 0) / y.closed_tickets AS avg_owner_transfers_per_ticket
    FROM year_ticket_totals y
    LEFT JOIN year_transfer_totals t ON y.creation_year = t.creation_year
    ORDER BY y.creation_year;
    """
    return pd.read_sql_query(query, conn, params=(TARGET_YEARS[0], TARGET_YEARS[1]))


def build_chart(df: pd.DataFrame) -> None:
    plt.figure(figsize=(8, 5))
    bars = plt.bar(
        df["creation_year"].astype(str),
        df["avg_owner_transfers_per_ticket"],
        color=["#2f6ea3", "#f28e2b"],
        width=0.6,
    )
    plt.title("Average ownership transfers per ticket - 2024 vs 2025", fontsize=13, fontweight="bold")
    plt.xlabel("Ticket creation year")
    plt.ylabel("Average ownership transfers per ticket")
    plt.grid(axis="y", alpha=0.25)

    for bar, row in zip(bars, df.itertuples(index=False)):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{row.avg_owner_transfers_per_ticket:.4f}\n({int(row.total_owner_transfers):,}/{int(row.closed_tickets):,})",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=300)
    plt.close()


def write_report(df: pd.DataFrame) -> None:
    row_2024 = df[df["creation_year"] == 2024].iloc[0]
    row_2025 = df[df["creation_year"] == 2025].iloc[0]

    abs_diff = row_2025["avg_owner_transfers_per_ticket"] - row_2024["avg_owner_transfers_per_ticket"]
    rel_change_pct = (
        abs_diff / row_2024["avg_owner_transfers_per_ticket"] * 100.0
        if row_2024["avg_owner_transfers_per_ticket"]
        else float("nan")
    )

    df_display = pd.DataFrame(
        {
            "creation_year": df["creation_year"].astype(int).astype(str),
            "closed_tickets": df["closed_tickets"].astype(int).map(lambda x: f"{x:,}"),
            "total_owner_transfers": df["total_owner_transfers"].astype(int).map(lambda x: f"{x:,}"),
            "avg_owner_transfers_per_ticket": df["avg_owner_transfers_per_ticket"].map(lambda x: f"{x:.4f}"),
        }
    )

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Ownership Transfers per Ticket - 2024 vs 2025\n\n")
        f.write("## Objective\n")
        f.write("Compare the average number of ownership transfers per ticket between 2024 and 2025.\n\n")

        f.write("## KPI Definition\n")
        f.write("- Population: closed tickets (`closingdate_parsed` is not null).\n")
        f.write("- Ownership transfer event: `historysr.action = 'Re-assign'`.\n")
        f.write("- Average ownership transfers per ticket = `total_owner_transfers / closed_tickets`.\n\n")

        f.write("## Results\n\n")
        f.write(df_display.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Comparison 2025 vs 2024\n")
        f.write(f"- Absolute difference (avg transfers per ticket): **{abs_diff:+.4f}**\n")
        f.write(f"- Relative change: **{rel_change_pct:+.2f}%**\n")


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    df = fetch_ownership_transfer_stats(conn)
    conn.close()

    if df.empty or len(df) != 2:
        raise RuntimeError("Could not compute both 2024 and 2025 rows.")

    df["avg_owner_transfers_per_ticket"] = df["avg_owner_transfers_per_ticket"].astype(float)

    df.to_csv(OUTPUT_CSV, index=False)
    build_chart(df)
    write_report(df)


if __name__ == "__main__":
    run()
