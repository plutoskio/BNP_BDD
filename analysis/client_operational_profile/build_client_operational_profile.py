import os
import sqlite3
import time
from pathlib import Path

# Keep matplotlib cache writable in sandboxed runs.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path("/Users/milo/Desktop/BNP_BDD")
DB_PATH = BASE_DIR / "hobart.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "client_operational_profile"

CLIENT_PROFILE_CSV = OUTPUT_DIR / "client_profile_operational.csv"
CLIENT_TOP_CONTACTS_CSV = OUTPUT_DIR / "client_top_contacts_operational.csv"
REPORT_MD = OUTPUT_DIR / "client_operational_profile_report.md"
HANDOFF_EMAIL_MD = OUTPUT_DIR / "handoff_email_suzana_william.md"
TOP_CLIENTS_CHART = OUTPUT_DIR / "top_clients_operational_priority.png"

CHART_COLOR = "#01925c"


def log_step(message: str, start_ts: float) -> None:
    elapsed = time.time() - start_ts
    print(f"[{elapsed:7.1f}s] {message}", flush=True)


def build_temp_tables(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -200000;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    started_at = time.time()

    # Unique client-ticket map.
    log_step("Building temp.client_sr", started_at)
    conn.execute("DROP TABLE IF EXISTS temp.client_sr;")
    conn.execute(
        """
        CREATE TEMP TABLE client_sr AS
        SELECT
            customer_id,
            sr_id
        FROM client_query
        WHERE customer_id IS NOT NULL
          AND sr_id IS NOT NULL
        GROUP BY customer_id, sr_id;
        """
    )
    conn.execute("CREATE INDEX idx_temp_client_sr_customer ON client_sr(customer_id);")
    conn.execute("CREATE INDEX idx_temp_client_sr_sr ON client_sr(sr_id);")

    # Client-contact mappings for outreach readiness.
    log_step("Building temp.client_contact_map", started_at)
    conn.execute("DROP TABLE IF EXISTS temp.client_contact_map;")
    conn.execute(
        """
        CREATE TEMP TABLE client_contact_map AS
        SELECT
            customer_id,
            customer_contact_id,
            COUNT(*) AS contact_mapping_rows
        FROM client_query
        WHERE customer_id IS NOT NULL
          AND customer_contact_id IS NOT NULL
        GROUP BY customer_id, customer_contact_id;
        """
    )
    conn.execute(
        "CREATE INDEX idx_temp_client_contact_map_customer ON client_contact_map(customer_id);"
    )
    conn.execute(
        "CREATE INDEX idx_temp_client_contact_map_contact ON client_contact_map(customer_contact_id);"
    )
    log_step("Temp tables ready", started_at)


def fetch_client_profile(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH base AS (
        SELECT
            cs.customer_id,
            cs.sr_id,
            s.creationdate_parsed,
            s.closingdate_parsed,
            s.reopen_date_parsed,
            COALESCE(s.issuer, 'UNKNOWN') AS issuer,
            s.jur_desk_id,
            COALESCE(cat.name, 'Unknown') AS category_name
        FROM client_sr cs
        JOIN sr s
          ON s.id = cs.sr_id
        LEFT JOIN category cat
          ON cat.id = s.category_id
    ),
    agg AS (
        SELECT
            customer_id,
            COUNT(*) AS total_tickets,
            SUM(CASE WHEN closingdate_parsed IS NOT NULL THEN 1 ELSE 0 END) AS closed_tickets,
            SUM(CASE WHEN closingdate_parsed IS NULL THEN 1 ELSE 0 END) AS open_tickets,
            SUM(CASE WHEN reopen_date_parsed IS NOT NULL THEN 1 ELSE 0 END) AS reopened_tickets,
            SUM(CASE WHEN lower(category_name) LIKE '%cash%' THEN 1 ELSE 0 END) AS cash_related_tickets,
            SUM(CASE WHEN lower(category_name) LIKE '%account%' THEN 1 ELSE 0 END) AS account_related_tickets,
            SUM(
                CASE
                    WHEN lower(category_name) LIKE '%position%'
                      OR lower(category_name) LIKE '%holding%'
                    THEN 1 ELSE 0
                END
            ) AS position_related_tickets,
            SUM(CASE WHEN issuer = 'CLIENT' THEN 1 ELSE 0 END) AS issuer_client_tickets,
            SUM(CASE WHEN issuer = 'INTERNAL' THEN 1 ELSE 0 END) AS issuer_internal_tickets,
            SUM(CASE WHEN issuer = 'THIRD_PARTY' THEN 1 ELSE 0 END) AS issuer_third_party_tickets,
            MIN(creationdate_parsed) AS first_ticket_created,
            MAX(creationdate_parsed) AS latest_ticket_created,
            MAX(closingdate_parsed) AS latest_ticket_closed
        FROM base
        GROUP BY customer_id
    ),
    contact_counts AS (
        SELECT
            customer_id,
            COUNT(*) AS unique_customer_contacts
        FROM client_contact_map
        GROUP BY customer_id
    ),
    desk_rank AS (
        SELECT
            cs.customer_id,
            s.jur_desk_id AS primary_desk_id,
            COUNT(*) AS primary_desk_ticket_count,
            ROW_NUMBER() OVER (
                PARTITION BY cs.customer_id
                ORDER BY COUNT(*) DESC, s.jur_desk_id
            ) AS rn
        FROM client_sr cs
        JOIN sr s
          ON s.id = cs.sr_id
        WHERE s.jur_desk_id IS NOT NULL
        GROUP BY cs.customer_id, s.jur_desk_id
    ),
    category_rank AS (
        SELECT
            cs.customer_id,
            COALESCE(cat.name, 'Unknown') AS top_category,
            COUNT(*) AS top_category_ticket_count,
            ROW_NUMBER() OVER (
                PARTITION BY cs.customer_id
                ORDER BY COUNT(*) DESC, COALESCE(cat.name, 'Unknown')
            ) AS rn
        FROM client_sr cs
        JOIN sr s
          ON s.id = cs.sr_id
        LEFT JOIN category cat
          ON cat.id = s.category_id
        GROUP BY cs.customer_id, COALESCE(cat.name, 'Unknown')
    )
    SELECT
        a.customer_id,
        COALESCE(cc.unique_customer_contacts, 0) AS unique_customer_contacts,
        a.total_tickets,
        a.closed_tickets,
        a.open_tickets,
        a.reopened_tickets,
        a.cash_related_tickets,
        a.account_related_tickets,
        a.position_related_tickets,
        a.issuer_client_tickets,
        a.issuer_internal_tickets,
        a.issuer_third_party_tickets,
        a.first_ticket_created,
        a.latest_ticket_created,
        a.latest_ticket_closed,
        d.primary_desk_id,
        d.primary_desk_ticket_count,
        k.top_category,
        k.top_category_ticket_count
    FROM agg a
    LEFT JOIN contact_counts cc
      ON cc.customer_id = a.customer_id
    LEFT JOIN desk_rank d
      ON d.customer_id = a.customer_id
     AND d.rn = 1
    LEFT JOIN category_rank k
      ON k.customer_id = a.customer_id
     AND k.rn = 1
    ORDER BY a.total_tickets DESC, a.customer_id;
    """
    return pd.read_sql_query(query, conn)


def fetch_top_contacts(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH contact_counts AS (
        SELECT
            customer_id,
            customer_contact_id,
            contact_mapping_rows
        FROM client_contact_map
    ),
    ranked AS (
        SELECT
            customer_id,
            customer_contact_id,
            ROW_NUMBER() OVER (
                PARTITION BY customer_id
                ORDER BY contact_mapping_rows DESC, customer_contact_id
            ) AS rn
            ,contact_mapping_rows
        FROM contact_counts
    )
    SELECT
        customer_id,
        customer_contact_id,
        contact_mapping_rows AS contact_linked_tickets,
        contact_mapping_rows,
        rn
    FROM ranked
    WHERE rn <= 3
    ORDER BY customer_id, rn;
    """
    return pd.read_sql_query(query, conn)


def enrich_client_profile(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in [
        "unique_customer_contacts",
        "total_tickets",
        "closed_tickets",
        "open_tickets",
        "reopened_tickets",
        "cash_related_tickets",
        "account_related_tickets",
        "position_related_tickets",
        "issuer_client_tickets",
        "issuer_internal_tickets",
        "issuer_third_party_tickets",
        "primary_desk_ticket_count",
        "top_category_ticket_count",
    ]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    df["reopened_rate_pct"] = (
        (df["reopened_tickets"] / df["closed_tickets"].replace(0, pd.NA)) * 100.0
    ).fillna(0.0)
    df["cash_related_pct"] = (
        (df["cash_related_tickets"] / df["total_tickets"].replace(0, pd.NA)) * 100.0
    ).fillna(0.0)
    df["account_related_pct"] = (
        (df["account_related_tickets"] / df["total_tickets"].replace(0, pd.NA)) * 100.0
    ).fillna(0.0)
    df["position_related_pct"] = (
        (df["position_related_tickets"] / df["total_tickets"].replace(0, pd.NA)) * 100.0
    ).fillna(0.0)

    # Operational prioritization for outreach and monitoring.
    df["operational_priority_score"] = (
        df["open_tickets"] * 8.0
        + df["reopened_tickets"] * 5.0
        + df["account_related_tickets"] * 1.5
        + df["cash_related_tickets"] * 1.3
        + df["position_related_tickets"] * 1.2
    )
    return df


def pivot_top_contacts(top_contacts_df: pd.DataFrame) -> pd.DataFrame:
    if top_contacts_df.empty:
        return pd.DataFrame(columns=["customer_id"])

    pivot = top_contacts_df.pivot(index="customer_id", columns="rn")
    pivot.columns = [f"{c[0]}_{c[1]}" for c in pivot.columns]
    pivot = pivot.reset_index()

    rename_map = {
        "customer_contact_id_1": "top_contact_id_1",
        "customer_contact_id_2": "top_contact_id_2",
        "customer_contact_id_3": "top_contact_id_3",
        "contact_linked_tickets_1": "top_contact_tickets_1",
        "contact_linked_tickets_2": "top_contact_tickets_2",
        "contact_linked_tickets_3": "top_contact_tickets_3",
        "contact_mapping_rows_1": "top_contact_mappings_1",
        "contact_mapping_rows_2": "top_contact_mappings_2",
        "contact_mapping_rows_3": "top_contact_mappings_3",
    }
    pivot = pivot.rename(columns=rename_map)
    return pivot


def create_top_clients_chart(client_df: pd.DataFrame) -> None:
    top = (
        client_df.sort_values("operational_priority_score", ascending=False)
        .head(15)
        .sort_values("operational_priority_score", ascending=True)
    )

    plt.figure(figsize=(12, 8))
    bars = plt.barh(
        top["customer_id"].astype(str),
        top["operational_priority_score"],
        color=CHART_COLOR,
        alpha=0.95,
    )

    plt.title("Top 15 Clients by Operational Priority Score", fontsize=15, fontweight="bold")
    plt.xlabel("Priority Score")
    plt.ylabel("Customer ID")
    plt.grid(axis="x", alpha=0.25)

    for bar, row in zip(bars, top.itertuples(index=False)):
        plt.text(
            bar.get_width() * 0.99 if bar.get_width() > 0 else 0.0,
            bar.get_y() + bar.get_height() / 2,
            f"Open:{row.open_tickets}  Reopen:{row.reopened_tickets}",
            va="center",
            ha="right",
            color="white",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(TOP_CLIENTS_CHART, dpi=300)
    plt.close()


def write_report(client_df: pd.DataFrame, top_contacts_df: pd.DataFrame) -> None:
    total_clients = len(client_df)
    total_contacts = int(top_contacts_df["customer_contact_id"].nunique()) if not top_contacts_df.empty else 0
    total_tickets = int(client_df["total_tickets"].sum())
    clients_with_cash = int((client_df["cash_related_tickets"] > 0).sum())
    clients_with_account = int((client_df["account_related_tickets"] > 0).sum())
    clients_with_position = int((client_df["position_related_tickets"] > 0).sum())

    top_clients = client_df.sort_values("operational_priority_score", ascending=False).head(15)

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("# Client Operational Profile Pack\n\n")
        f.write("## Objective\n")
        f.write(
            "Build an operational client profile with account/cash/position signals and ticket dynamics "
            "to support client outreach and day-to-day execution.\n\n"
        )

        f.write("## Key Coverage\n")
        f.write(f"- Clients profiled: **{total_clients:,}**\n")
        f.write(f"- Distinct client contacts (mapped in Hobart): **{total_contacts:,}**\n")
        f.write(f"- Client-linked tickets analyzed: **{total_tickets:,}**\n")
        f.write(f"- Clients with cash-related activity: **{clients_with_cash:,}**\n")
        f.write(f"- Clients with account-related activity: **{clients_with_account:,}**\n")
        f.write(f"- Clients with position/holding-related activity: **{clients_with_position:,}**\n\n")

        f.write("## Important Data Note\n")
        f.write(
            "This Hobart dataset does **not** contain direct client email address fields. "
            "Operational outreach should map `customer_contact_id` to a trusted external contact master.\n\n"
        )
        f.write(
            "Top contacts are ranked by frequency of customer/contact mappings in Hobart (`contact_mapping_rows`), "
            "which is robust for prioritization but not equivalent to a validated CRM activity score.\n\n"
        )

        f.write("## Top Clients by Operational Priority\n\n")
        f.write(
            top_clients[
                [
                    "customer_id",
                    "total_tickets",
                    "open_tickets",
                    "reopened_tickets",
                    "cash_related_tickets",
                    "account_related_tickets",
                    "position_related_tickets",
                    "top_category",
                    "primary_desk_id",
                    "operational_priority_score",
                ]
            ].to_markdown(index=False)
        )
        f.write("\n\n")

        f.write("## Generated Files\n")
        f.write("- `client_profile_operational.csv`\n")
        f.write("- `client_top_contacts_operational.csv`\n")
        f.write("- `top_clients_operational_priority.png`\n")


def write_handoff_email_template() -> None:
    with open(HANDOFF_EMAIL_MD, "w", encoding="utf-8") as f:
        f.write("To: suzana.tadic@bnpparibas.com; william.aumont@bnpparibas.com\n")
        f.write("Subject: Client operational profile package (cash/account/position + contact readiness)\n\n")
        f.write("Hi Suzana, hi William,\n\n")
        f.write(
            "Please find attached the operational client profile package built from Hobart data. "
            "It includes a client-level profile and a top-contact extraction view with account/cash/position signals, "
            "ticket workload, reopen/open indicators, primary desk, and top category.\n\n"
        )
        f.write("Deliverables:\n")
        f.write("- client_profile_operational.csv\n")
        f.write("- client_top_contacts_operational.csv\n")
        f.write("- client_operational_profile_report.md\n")
        f.write("- top_clients_operational_priority.png\n\n")
        f.write(
            "Note: Hobart data here does not carry direct client email address fields; "
            "use `customer_contact_id` to map against the official contact master for outbound campaigns.\n\n"
        )
        f.write("Best regards,\n")
        f.write("Data Team\n")


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = time.time()

    log_step("Opening SQLite connection", started_at)
    conn = sqlite3.connect(DB_PATH)
    build_temp_tables(conn)

    log_step("Fetching client profile", started_at)
    client_profile_df = fetch_client_profile(conn)
    log_step("Fetching top contacts", started_at)
    top_contacts_df = fetch_top_contacts(conn)
    conn.close()
    log_step("SQL extraction complete", started_at)

    if client_profile_df.empty:
        raise RuntimeError("Client profile extraction returned no rows.")

    client_profile_df = enrich_client_profile(client_profile_df)
    top_contacts_wide = pivot_top_contacts(top_contacts_df)
    client_profile_df = client_profile_df.merge(top_contacts_wide, on="customer_id", how="left")

    log_step("Writing CSV outputs", started_at)
    client_profile_df.to_csv(CLIENT_PROFILE_CSV, index=False)
    top_contacts_df.to_csv(CLIENT_TOP_CONTACTS_CSV, index=False)

    log_step("Rendering chart and markdown outputs", started_at)
    create_top_clients_chart(client_profile_df)
    write_report(client_profile_df, top_contacts_df)
    write_handoff_email_template()
    log_step("Done", started_at)


if __name__ == "__main__":
    run()
