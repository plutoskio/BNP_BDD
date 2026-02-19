from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


@dataclass(frozen=True)
class GmailAdapterSettings:
    project_root: Path
    gmail_address: str
    client_secrets_path: Path
    token_path: Path
    router_api_base_url: str
    poll_seconds: int
    gmail_query: str
    gmail_max_batch: int
    skip_self: bool
    state_db_path: Path



def load_gmail_adapter_settings(project_root: Path) -> GmailAdapterSettings:
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path if env_path.exists() else None, override=False)

    import os

    gmail_address = os.getenv("GMAIL_ADDRESS", "").strip()
    client_secrets_path = Path(
        os.getenv(
            "GMAIL_OAUTH_CLIENT_SECRETS",
            str(project_root / "email_adapter" / "google_client_secret.json"),
        )
    ).expanduser()
    token_path = Path(
        os.getenv(
            "GMAIL_OAUTH_TOKEN_FILE",
            str(project_root / "email_adapter" / "google_token.json"),
        )
    ).expanduser()
    state_db_path = Path(
        os.getenv(
            "EMAIL_ADAPTER_STATE_DB",
            str(project_root / "email_adapter" / "adapter_state.db"),
        )
    ).expanduser()

    return GmailAdapterSettings(
        project_root=project_root,
        gmail_address=gmail_address,
        client_secrets_path=client_secrets_path,
        token_path=token_path,
        router_api_base_url=os.getenv("ROUTER_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        poll_seconds=max(int(os.getenv("GMAIL_POLL_SECONDS", "15")), 5),
        gmail_query=os.getenv("GMAIL_QUERY", "label:inbox is:unread -from:me"),
        gmail_max_batch=max(int(os.getenv("GMAIL_MAX_BATCH", "10")), 1),
        skip_self=os.getenv("GMAIL_SKIP_SELF", "1").strip() in {"1", "true", "True", "yes", "YES"},
        state_db_path=state_db_path,
    )



def get_gmail_credentials(settings: GmailAdapterSettings, force_reauth: bool = False) -> Credentials:
    creds: Credentials | None = None

    if force_reauth and settings.token_path.exists():
        settings.token_path.unlink()

    if settings.token_path.exists():
        creds = Credentials.from_authorized_user_file(str(settings.token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not settings.client_secrets_path.exists():
                raise FileNotFoundError(
                    f"OAuth client secrets file not found: {settings.client_secrets_path}\n"
                    "Download Desktop OAuth credentials from Google Cloud Console and place it there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(settings.client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")

        settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        settings.token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds



def build_gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)



def init_state_db(state_db_path: Path) -> None:
    state_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(state_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
                gmail_message_id TEXT PRIMARY KEY,
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



def has_processed(state_db_path: Path, gmail_message_id: str) -> bool:
    with sqlite3.connect(state_db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_messages WHERE gmail_message_id = ? LIMIT 1;",
            (gmail_message_id,),
        ).fetchone()
    return row is not None



def record_processed(
    state_db_path: Path,
    gmail_message_id: str,
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
                gmail_message_id,
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
                gmail_message_id,
                internet_message_id,
                sender_email,
                subject,
                ticket_ref,
                1 if processed_ok else 0,
                error_text,
                processed_at,
            ),
        )
