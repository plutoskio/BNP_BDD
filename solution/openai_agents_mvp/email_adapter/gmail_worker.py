#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import time
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from gmail_oauth import (
    build_gmail_service,
    get_gmail_credentials,
    has_processed,
    init_state_db,
    load_gmail_adapter_settings,
    record_processed,
)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gmail OAuth worker: poll unread, route, and reply")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    parser.add_argument("--force-reauth", action="store_true")
    return parser.parse_args()



def _headers_to_map(headers: list[dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for header in headers:
        name = header.get("name", "").strip().lower()
        value = header.get("value", "")
        if name and name not in out:
            out[name] = value
    return out



def _decode_b64url(data: str | None) -> str:
    if not data:
        return ""
    data = data.replace("-", "+").replace("_", "/")
    padding = "=" * ((4 - len(data) % 4) % 4)
    try:
        raw = base64.b64decode(data + padding)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""



def _extract_text_from_payload(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return _decode_b64url(data).strip()

    text_chunks: list[str] = []
    html_chunks: list[str] = []

    for part in payload.get("parts", []) or []:
        part_text = _extract_text_from_payload(part)
        if not part_text:
            continue
        if part.get("mimeType") == "text/plain":
            text_chunks.append(part_text)
        else:
            html_chunks.append(part_text)

    if text_chunks:
        return "\n\n".join(text_chunks).strip()

    if data:
        decoded = _decode_b64url(data)
        if decoded:
            html_chunks.append(decoded)

    if html_chunks:
        text = "\n\n".join(html_chunks)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    return ""



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



def _send_reply(
    gmail_service,
    to_email: str,
    from_email: str,
    reply_subject: str,
    reply_body: str,
    thread_id: str | None,
    internet_message_id: str | None,
) -> None:
    mime = MIMEText(reply_body, "plain", "utf-8")
    mime["To"] = to_email
    mime["From"] = from_email
    mime["Subject"] = reply_subject
    if internet_message_id:
        mime["In-Reply-To"] = internet_message_id
        mime["References"] = internet_message_id

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
    body: dict[str, Any] = {"raw": raw}
    if thread_id:
        body["threadId"] = thread_id

    gmail_service.users().messages().send(userId="me", body=body).execute()



def _mark_read(gmail_service, gmail_message_id: str) -> None:
    gmail_service.users().messages().modify(
        userId="me",
        id=gmail_message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()



def _process_message(gmail_service, settings, gmail_message_id: str) -> dict[str, Any]:
    if has_processed(settings.state_db_path, gmail_message_id):
        _mark_read(gmail_service, gmail_message_id)
        return {"status": "skipped_already_processed", "gmail_message_id": gmail_message_id}

    message = gmail_service.users().messages().get(userId="me", id=gmail_message_id, format="full").execute()
    payload = message.get("payload", {})
    headers = _headers_to_map(payload.get("headers", []))

    subject = headers.get("subject", "(no subject)")
    from_raw = headers.get("from", "")
    internet_message_id = headers.get("message-id")
    from_email = parseaddr(from_raw)[1].strip().lower()
    body_text = _extract_text_from_payload(payload)
    if not body_text:
        body_text = "(empty email body)"

    if settings.skip_self and from_email and settings.gmail_address and from_email.lower() == settings.gmail_address.lower():
        _mark_read(gmail_service, gmail_message_id)
        record_processed(
            settings.state_db_path,
            gmail_message_id,
            internet_message_id,
            from_email or "unknown",
            subject,
            ticket_ref=None,
            processed_ok=True,
            error_text="skipped_self_message",
        )
        return {"status": "skipped_self", "gmail_message_id": gmail_message_id, "from_email": from_email}

    if not from_email:
        _mark_read(gmail_service, gmail_message_id)
        record_processed(
            settings.state_db_path,
            gmail_message_id,
            internet_message_id,
            "unknown",
            subject,
            ticket_ref=None,
            processed_ok=False,
            error_text="missing_from_email",
        )
        return {"status": "failed", "gmail_message_id": gmail_message_id, "error": "missing_from_email"}

    router_payload = {
        "from_email": from_email,
        "subject": subject,
        "body": body_text,
        "message_id": internet_message_id or gmail_message_id,
        "channel": "EMAIL",
    }
    routed = _call_router_api(settings.router_api_base_url, router_payload)

    reply_subject = routed.get("reply_subject") or f"Re: {subject}"
    reply_body = routed.get("reply_body") or "Routing completed, but no response body was generated."

    _send_reply(
        gmail_service=gmail_service,
        to_email=from_email,
        from_email=settings.gmail_address or "me",
        reply_subject=reply_subject,
        reply_body=reply_body,
        thread_id=message.get("threadId"),
        internet_message_id=internet_message_id,
    )
    _mark_read(gmail_service, gmail_message_id)

    record_processed(
        settings.state_db_path,
        gmail_message_id,
        internet_message_id,
        from_email,
        subject,
        ticket_ref=routed.get("ticket_ref"),
        processed_ok=bool(routed.get("ok", False)),
        error_text=routed.get("error"),
    )

    return {
        "status": "processed",
        "gmail_message_id": gmail_message_id,
        "from_email": from_email,
        "ticket_ref": routed.get("ticket_ref"),
        "ok": routed.get("ok", False),
        "error": routed.get("error"),
    }



def process_batch(gmail_service, settings) -> list[dict[str, Any]]:
    response = gmail_service.users().messages().list(
        userId="me",
        q=settings.gmail_query,
        maxResults=settings.gmail_max_batch,
    ).execute()

    messages = response.get("messages", []) or []
    results: list[dict[str, Any]] = []

    for item in messages:
        gmail_message_id = item.get("id")
        if not gmail_message_id:
            continue
        result = _process_message(gmail_service, settings, gmail_message_id)
        results.append(result)

    return results



def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root)
    settings = load_gmail_adapter_settings(project_root)

    if not settings.gmail_address:
        raise ValueError("GMAIL_ADDRESS is not set in .env")

    creds = get_gmail_credentials(settings, force_reauth=args.force_reauth)
    gmail_service = build_gmail_service(creds)
    init_state_db(settings.state_db_path)

    if args.once:
        results = process_batch(gmail_service, settings)
        print(json.dumps({"processed": len(results), "results": results}, indent=2))
        return

    print(
        f"Gmail worker started for {settings.gmail_address}. "
        f"Polling every {settings.poll_seconds}s with query: {settings.gmail_query}"
    )
    while True:
        try:
            results = process_batch(gmail_service, settings)
            if results:
                print(json.dumps({"processed": len(results), "results": results}, indent=2))
        except KeyboardInterrupt:
            print("Stopping Gmail worker.")
            return
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": f"worker_loop_failure: {exc}"}))
        time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
