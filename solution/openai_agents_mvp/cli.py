#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from mvp_agent import InboundMessage, RoutingService, load_settings



def _parse_payload(args: argparse.Namespace) -> InboundMessage:
    if args.payload_b64:
        decoded = base64.b64decode(args.payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(decoded)
        return InboundMessage(
            from_email=payload["from_email"],
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            message_id=payload.get("message_id"),
            channel=payload.get("channel", "EMAIL"),
        )

    if not args.from_email:
        raise ValueError("--from-email is required when --payload-b64 is not used")

    return InboundMessage(
        from_email=args.from_email,
        subject=args.subject or "",
        body=args.body or "",
        message_id=args.message_id,
        channel=args.channel or "EMAIL",
    )



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenAI Agents + SQLite routing MVP")
    parser.add_argument("--db-path", help="Override DB path")

    sub = parser.add_subparsers(dest="command", required=True)

    inbound = sub.add_parser("inbound", help="Process a new inbound request")
    inbound.add_argument("--payload-b64", help="Base64-encoded JSON payload")
    inbound.add_argument("--from-email")
    inbound.add_argument("--subject")
    inbound.add_argument("--body")
    inbound.add_argument("--message-id")
    inbound.add_argument("--channel", default="EMAIL")

    status = sub.add_parser("status", help="Fetch ticket status and decision path")
    status.add_argument("--ticket-ref", required=True)

    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings()
    if args.db_path:
        settings = settings.__class__(
            db_path=Path(args.db_path).expanduser(),
            prompt_path=settings.prompt_path,
            openai_api_key=settings.openai_api_key,
            model=settings.model,
            reasoning_effort=settings.reasoning_effort,
            sender_email=settings.sender_email,
        )

    service = RoutingService(settings)

    try:
        if args.command == "inbound":
            payload = _parse_payload(args)
            result = service.process_inbound(payload)
            print(result.model_dump_json())
            return

        if args.command == "status":
            snapshot = service.get_ticket_status(args.ticket_ref)
            if snapshot is None:
                print(json.dumps({"ok": False, "error": "ticket_not_found"}))
                sys.exit(1)
            print(json.dumps({"ok": True, **snapshot}, default=str))
            return
    except Exception as exc:
        print(json.dumps({"ok": False, "error": "runtime_error", "detail": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
