#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mailslurp_client

from mailslurp_common import MailSlurpSettings, load_mailslurp_settings, upsert_env_key



def _build_api_client(api_key: str) -> mailslurp_client.ApiClient:
    config = mailslurp_client.Configuration()
    config.api_key["x-api-key"] = api_key
    return mailslurp_client.ApiClient(config)



def _ensure_inbox(settings: MailSlurpSettings, api_client: mailslurp_client.ApiClient):
    inbox_api = mailslurp_client.InboxControllerApi(api_client)

    if settings.inbox_id:
        try:
            inbox = inbox_api.get_inbox(settings.inbox_id)
            return inbox, False
        except Exception:
            # Fallback to create if stored inbox id is stale.
            pass

    create_opts = mailslurp_client.CreateInboxDto(
        name=settings.inbox_name,
        description=settings.inbox_description,
        use_domain_pool=True,
        tags=["bnp-bdd", "mvp"],
    )
    inbox = inbox_api.create_inbox_with_options(create_opts)
    return inbox, True



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or fetch MailSlurp inbox and optionally save to .env")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--no-write-env", action="store_true", help="Do not update .env with inbox id/email")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root)
    settings = load_mailslurp_settings(project_root)

    with _build_api_client(settings.api_key) as api_client:
        inbox, created = _ensure_inbox(settings, api_client)

    output = {
        "created": created,
        "inbox_id": inbox.id,
        "email_address": inbox.email_address,
        "name": getattr(inbox, "name", None),
        "description": getattr(inbox, "description", None),
    }

    if not args.no_write_env:
        env_path = project_root / ".env"
        upsert_env_key(env_path, "MAILSLURP_INBOX_ID", str(inbox.id))
        upsert_env_key(env_path, "MAILSLURP_INBOX_EMAIL", str(inbox.email_address))
        output["env_updated"] = str(env_path)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
