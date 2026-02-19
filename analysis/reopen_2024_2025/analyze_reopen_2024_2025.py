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
OUTPUT_DIR = BASE_DIR / "analysis" / "reopen_2024_2025"
OUTPUT_CSV = OUTPUT_DIR / "reopen_rate_2024_2025.csv"
OUTPUT_MD = OUTPUT_DIR / "reopen_rate_2024_2025_report.md"
OUTPUT_PNG = OUTPUT_DIR / "reopen_rate_2024_2025_bar.png"

# Reopen signal reliability caveat in this dataset:
# reopen_date_parsed is populated in load_period 2025-01_to_2025-09.
RELIABLE_LOAD_PERIOD = "2025-01_to_2025-09"
TARGET_YEARS = (2024, 2025)


def fetch_reopen_rates(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH scoped AS (
        SELECT
            CAST('20' || substr(creationdate_parsed, 1, 2) AS INTEGER) AS creation_year,
            CASE WHEN reopen_date_parsed IS NOT NULL THEN 1 ELSE 0 END AS is_reopened
        FROM sr
        WHERE creationdate_parsed IS NOT NULL
          AND closingdate_parsed IS NOT NULL
          AND load_period = ?
    )
    SELECT
        creation_year,
        COUNT(*) AS closed_tickets,
        SUM(is_reopened) AS reopened_tickets,
        100.0 * SUM(is_reopened) / COUNT(*) AS reopen_rate_pct
    FROM scoped
    WHERE creation_year IN (?, ?)
    GROUP BY creation_year
    ORDER BY creation_year;
    """
    return pd.read_sql_query(
        query,
        conn,
        params=(RELIABLE_LOAD_PERIOD, TARGET_YEARS[0], TARGET_YEARS[1]),
    )


def build_chart(df: pd.DataFrame) -> None:
    plt.figure(figsize=(8, 5))
    bars = plt.bar(
        df["creation_year"].astype(str),
        df["reopen_rate_pct"],
        color=["#2f6ea3", "#f28e2b"],
        width=0.6,
    )

    plt.title("Taux de tickets reouverts - 2024 vs 2025", fontsize=13, fontweight="bold")
    plt.xlabel("Annee de creation du ticket")
    plt.ylabel("Taux de reouverture (%)")
    plt.grid(axis="y", alpha=0.25)

    for bar, row in zip(bars, df.itertuples(index=False)):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.003,
            f"{row.reopen_rate_pct:.3f}%\\n({int(row.reopened_tickets):,}/{int(row.closed_tickets):,})",
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

    df_display = pd.DataFrame(
        {
            "creation_year": df["creation_year"].astype(int).astype(str),
            "closed_tickets": df["closed_tickets"].astype(int).map(lambda x: f"{x:,}"),
            "reopened_tickets": df["reopened_tickets"].astype(int).map(lambda x: f"{x:,}"),
            "reopen_rate_pct": df["reopen_rate_pct"].map(lambda x: f"{x:.4f}%"),
        }
    )

    abs_diff_pp = row_2025["reopen_rate_pct"] - row_2024["reopen_rate_pct"]
    rel_change_pct = (abs_diff_pp / row_2024["reopen_rate_pct"] * 100.0) if row_2024["reopen_rate_pct"] else float("nan")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Reopen Rate 2024 vs 2025\n\n")
        f.write("## Objectif\n")
        f.write("Comparer le taux de tickets reouverts entre 2024 et 2025 pour evaluer la qualite de reponse Hobart.\n\n")

        f.write("## Definition KPI\n")
        f.write("- Population: tickets fermes (`closingdate_parsed` non nul).\n")
        f.write("- Ticket reouvert: `reopen_date_parsed` non nul.\n")
        f.write("- Taux de reouverture = `reopened_tickets / closed_tickets`.\n\n")

        f.write("## Guardrail Data\n")
        f.write(
            f"Pour eviter un biais de nullite sur le champ `reopen_date_parsed`, l'analyse est restreinte au load period **{RELIABLE_LOAD_PERIOD}** (zone ou le signal de reopen est renseigne).\n\n"
        )

        f.write("## Resultats\n\n")
        f.write(df_display.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Comparaison 2025 vs 2024\n")
        f.write(f"- Difference absolue: **{abs_diff_pp:+.4f} points**\n")
        f.write(f"- Variation relative: **{rel_change_pct:+.2f}%**\n")


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    df = fetch_reopen_rates(conn)
    conn.close()

    if df.empty or len(df) != 2:
        raise RuntimeError("Impossible de calculer les deux annees 2024 et 2025.")

    df["reopen_rate_pct"] = df["reopen_rate_pct"].astype(float)

    df.to_csv(OUTPUT_CSV, index=False)
    build_chart(df)
    write_report(df)


if __name__ == "__main__":
    run()
