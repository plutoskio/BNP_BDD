#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from gmail_oauth import build_gmail_service, get_gmail_credentials, load_gmail_adapter_settings



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Gmail OAuth consent flow and persist token.json")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--force-reauth", action="store_true", help="Delete existing token and re-run consent")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    settings = load_gmail_adapter_settings(Path(args.project_root))

    creds = get_gmail_credentials(settings, force_reauth=args.force_reauth)
    service = build_gmail_service(creds)
    profile = service.users().getProfile(userId="me").execute()

    email = profile.get("emailAddress", "")
    print("OAuth setup complete.")
    print(f"Token file: {settings.token_path}")
    print(f"Authenticated Gmail account: {email}")


if __name__ == "__main__":
    main()
