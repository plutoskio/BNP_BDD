#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from email.utils import parseaddr
from pathlib import Path
from typing import Any

import mailslurp_client
from mailslurp_client.exceptions import ApiException

from mailslurp_common import (
    MailSlurpSettings,
    has_processed,
    init_state_db,
    load_mailslurp_settings,
    record_processed,
)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MailSlurp worker: poll inbox, route, and reply")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    return parser.parse_args()



def _build_api_client(api_key: str) -> mailslurp_client.ApiClient:
    config = mailslurp_client.Configuration()
    config.api_key["x-api-key"] = api_key
    return mailslurp_client.ApiClient(config)



def _call_router_api(api_base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{api_base_url}/inbound",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "error": f"router_http_{exc.code}",
            "reply_subject": "Routing Error",
            "reply_body": f"Routing API returned HTTP {exc.code}. Body: {body[:400]}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": "router_unreachable",
            "reply_subject": "Routing Error",
            "reply_body": f"Routing API call failed: {exc}",
        }



def _ensure_inbox(settings: MailSlurpSettings, inbox_api: mailslurp_client.InboxControllerApi):
    if not settings.inbox_id:
        raise ValueError(
            "MAILSLURP_INBOX_ID is not set. Run: scripts/mailslurp_setup.sh first."
        )
    return inbox_api.get_inbox(settings.inbox_id)



def _get_body_text(email: mailslurp_client.Email) -> str:
    if email.body and email.body.strip():
        return email.body.strip()
    if email.text_excerpt and email.text_excerpt.strip():
        return email.text_excerpt.strip()
    return "(empty email body)"



def _send_reply(
    settings: MailSlurpSettings,
    inbox_api: mailslurp_client.InboxControllerApi,
    inbox_id: str,
    to_email: str,
    reply_subject: str,
    reply_body: str,
) -> tuple[bool, str | None]:
    payload = {
        "to_email": to_email,
        "subject": reply_subject,
        "body": reply_body,
        "send_mode": settings.send_mode,
    }

    if settings.send_mode == "dry_run":
        _log_outbox(settings.outbox_log_path, payload | {"status": "dry_run"})
        return True, "dry_run_logged"

    send_opts = mailslurp_client.SendEmailOptions(
        to=[to_email],
        subject=reply_subject,
        body=reply_body,
    )
    try:
        inbox_api.send_email(inbox_id, send_opts)
        _log_outbox(settings.outbox_log_path, payload | {"status": "sent"})
        return True, None
    except ApiException as exc:
        # Free plan may block sending; in auto mode we keep processing and log.
        if settings.send_mode == "auto":
            msg = f"send_blocked_api_exception_{exc.status}"
            _log_outbox(settings.outbox_log_path, payload | {"status": msg, "detail": str(exc)})
            return False, msg
        raise


def _log_outbox(outbox_log_path: Path, payload: dict[str, Any]) -> None:
    outbox_log_path.parent.mkdir(parents=True, exist_ok=True)
    with outbox_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")



def _mark_read(email_api: mailslurp_client.EmailControllerApi, email_id: str) -> None:
    email_api.mark_as_read(email_id, read=True)



def _process_one(
    settings: MailSlurpSettings,
    inbox: mailslurp_client.InboxDto,
    inbox_api: mailslurp_client.InboxControllerApi,
    email_api: mailslurp_client.EmailControllerApi,
    preview: mailslurp_client.EmailPreview,
) -> dict[str, Any]:
    message_id = str(preview.id)
    if has_processed(settings.state_db_path, message_id):
        _mark_read(email_api, message_id)
        return {"status": "skipped_already_processed", "message_id": message_id}

    email = email_api.get_email(message_id)
    subject = email.subject or "(no subject)"
    from_raw = email._from or ""
    from_email = parseaddr(from_raw)[1].strip().lower()
    body_text = _get_body_text(email)

    if settings.skip_self and from_email and inbox.email_address and from_email.lower() == inbox.email_address.lower():
        _mark_read(email_api, message_id)
        record_processed(
            settings.state_db_path,
            message_id,
            email.message_id,
            from_email,
            subject,
            ticket_ref=None,
            processed_ok=True,
            error_text="skipped_self_message",
        )
        return {"status": "skipped_self", "message_id": message_id, "from_email": from_email}

    if not from_email:
        _mark_read(email_api, message_id)
        record_processed(
            settings.state_db_path,
            message_id,
            email.message_id,
            "unknown",
            subject,
            ticket_ref=None,
            processed_ok=False,
            error_text="missing_from_email",
        )
        return {"status": "failed", "message_id": message_id, "error": "missing_from_email"}

    routed = _call_router_api(
        settings.router_api_base_url,
        {
            "from_email": from_email,
            "subject": subject,
            "body": body_text,
            "message_id": email.message_id or message_id,
            "channel": "EMAIL",
        },
    )

    reply_subject = routed.get("reply_subject") or f"Re: {subject}"
    reply_body = routed.get("reply_body") or "Routing completed, but no response body was generated."

    send_ok, send_error = _send_reply(settings, inbox_api, str(inbox.id), from_email, reply_subject, reply_body)
    _mark_read(email_api, message_id)

    routing_error = routed.get("error")
    combined_error = routing_error
    if send_error:
        combined_error = f"{routing_error}; {send_error}" if routing_error else send_error

    record_processed(
        settings.state_db_path,
        message_id,
        email.message_id,
        from_email,
        subject,
        ticket_ref=routed.get("ticket_ref"),
        processed_ok=bool(routed.get("ok", False)) and send_ok,
        error_text=combined_error,
    )

    return {
        "status": "processed",
        "message_id": message_id,
        "from_email": from_email,
        "ticket_ref": routed.get("ticket_ref"),
        "ok": routed.get("ok", False),
        "send_ok": send_ok,
        "error": combined_error,
    }



def process_batch(
    settings: MailSlurpSettings,
    inbox: mailslurp_client.InboxDto,
    inbox_api: mailslurp_client.InboxControllerApi,
    email_api: mailslurp_client.EmailControllerApi,
) -> list[dict[str, Any]]:
    previews = inbox_api.get_emails(
        str(inbox.id),
        limit=settings.max_batch,
        sort="ASC",
        unread_only=settings.unread_only,
        min_count=0,
    )

    results: list[dict[str, Any]] = []
    for preview in previews or []:
        try:
            results.append(_process_one(settings, inbox, inbox_api, email_api, preview))
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "status": "failed",
                    "message_id": getattr(preview, "id", None),
                    "error": str(exc),
                }
            )
    return results



def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root)
    settings = load_mailslurp_settings(project_root)
    init_state_db(settings.state_db_path)

    with _build_api_client(settings.api_key) as api_client:
        inbox_api = mailslurp_client.InboxControllerApi(api_client)
        email_api = mailslurp_client.EmailControllerApi(api_client)

        inbox = _ensure_inbox(settings, inbox_api)

        if args.once:
            results = process_batch(settings, inbox, inbox_api, email_api)
            print(json.dumps({"inbox": inbox.email_address, "processed": len(results), "results": results}, indent=2))
            return

        print(
            f"MailSlurp worker started for {inbox.email_address}. "
            f"Polling every {settings.poll_seconds}s."
        )
        while True:
            try:
                results = process_batch(settings, inbox, inbox_api, email_api)
                if results:
                    print(json.dumps({"processed": len(results), "results": results}, indent=2))
            except KeyboardInterrupt:
                print("Stopping MailSlurp worker.")
                return
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"error": f"worker_loop_failure: {exc}"}))
            time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
