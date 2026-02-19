from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class MailSlurpSettings:
    project_root: Path
    api_key: str
    inbox_id: str | None
    inbox_email: str | None
    router_api_base_url: str
    poll_seconds: int
    max_batch: int
    unread_only: bool
    skip_self: bool
    send_mode: str
    outbox_log_path: Path
    state_db_path: Path
    inbox_name: str
    inbox_description: str



def load_mailslurp_settings(project_root: Path) -> MailSlurpSettings:
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path if env_path.exists() else None, override=False)

    import os

    api_key = os.getenv("MAILSLURP_API_KEY", "").strip()
    if not api_key:
        raise ValueError("MAILSLURP_API_KEY is not set in .env")

    inbox_id = os.getenv("MAILSLURP_INBOX_ID", "").strip() or None
    inbox_email = os.getenv("MAILSLURP_INBOX_EMAIL", "").strip() or None
    router_api_base_url = os.getenv("ROUTER_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    state_db_path = Path(
        os.getenv(
            "MAILSLURP_STATE_DB",
            str(project_root / "email_adapter" / "mailslurp_state.db"),
        )
    ).expanduser()
    outbox_log_path = Path(
        os.getenv(
            "MAILSLURP_OUTBOX_LOG",
            str(project_root / "email_adapter" / "mailslurp_outbox.jsonl"),
        )
    ).expanduser()
    send_mode = os.getenv("MAILSLURP_SEND_MODE", "auto").strip().lower()
    if send_mode not in {"auto", "live", "dry_run"}:
        send_mode = "auto"

    return MailSlurpSettings(
        project_root=project_root,
        api_key=api_key,
        inbox_id=inbox_id,
        inbox_email=inbox_email,
        router_api_base_url=router_api_base_url,
        poll_seconds=max(int(os.getenv("MAILSLURP_POLL_SECONDS", "15")), 5),
        max_batch=max(int(os.getenv("MAILSLURP_MAX_BATCH", "10")), 1),
        unread_only=os.getenv("MAILSLURP_UNREAD_ONLY", "1").strip() in {"1", "true", "True", "yes", "YES"},
        skip_self=os.getenv("MAILSLURP_SKIP_SELF", "1").strip() in {"1", "true", "True", "yes", "YES"},
        send_mode=send_mode,
        outbox_log_path=outbox_log_path,
        state_db_path=state_db_path,
        inbox_name=os.getenv("MAILSLURP_INBOX_NAME", "BNP BDD MVP Router Inbox").strip(),
        inbox_description=os.getenv("MAILSLURP_INBOX_DESCRIPTION", "MVP routing demo inbox").strip(),
    )



def init_state_db(state_db_path: Path) -> None:
    state_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(state_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id TEXT PRIMARY KEY,
                internet_message_id TEXT,
                sender_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                ticket_ref TEXT,
                processed_ok INTEGER NOT NULL,
                error_text TEXT,
                processed_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_processed_messages_processed_at
            ON processed_messages(processed_at);
            """
        )



def has_processed(state_db_path: Path, message_id: str) -> bool:
    with sqlite3.connect(state_db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_messages WHERE message_id = ? LIMIT 1;",
            (message_id,),
        ).fetchone()
    return row is not None



def record_processed(
    state_db_path: Path,
    message_id: str,
    internet_message_id: str | None,
    sender_email: str,
    subject: str,
    ticket_ref: str | None,
    processed_ok: bool,
    error_text: str | None,
) -> None:
    processed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(state_db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_messages (
                message_id,
                internet_message_id,
                sender_email,
                subject,
                ticket_ref,
                processed_ok,
                error_text,
                processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                message_id,
                internet_message_id,
                sender_email,
                subject,
                ticket_ref,
                1 if processed_ok else 0,
                error_text,
                processed_at,
            ),
        )



def upsert_env_key(env_path: Path, key: str, value: str) -> None:
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    target = f"{key}="
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(target):
            lines[idx] = f"{key}={value}"
            updated = True
            break

    if not updated:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
