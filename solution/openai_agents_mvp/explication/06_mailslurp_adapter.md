# MailSlurp Adapter (recommended MVP transport)

## Why this path
- No OAuth complexity.
- Fastest setup for MVP.
- Works directly with Python SDK.

## Files
- `email_adapter/mailslurp_common.py`
- `email_adapter/mailslurp_setup.py`
- `email_adapter/mailslurp_worker.py`
- `scripts/mailslurp_setup.sh`
- `scripts/mailslurp_worker_once.sh`
- `scripts/mailslurp_worker_loop.sh`

## Required `.env`
- `MAILSLURP_API_KEY`

Optional / recommended:
- `MAILSLURP_INBOX_ID` (auto-created by setup script)
- `MAILSLURP_INBOX_EMAIL` (auto-created by setup script)
- `MAILSLURP_POLL_SECONDS=15`
- `MAILSLURP_MAX_BATCH=10`
- `MAILSLURP_UNREAD_ONLY=1`
- `MAILSLURP_SKIP_SELF=1`
- `MAILSLURP_SEND_MODE=auto` (`auto|live|dry_run`)
- `MAILSLURP_OUTBOX_LOG=/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/email_adapter/mailslurp_outbox.jsonl`
- `MAILSLURP_STATE_DB=/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/email_adapter/mailslurp_state.db`
- `ROUTER_API_BASE_URL=http://127.0.0.1:8000`

## First setup
Create or fetch inbox and save to `.env`:

```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/mailslurp_setup.sh
```

Output includes:
- `inbox_id`
- `email_address` (this is the address to send test emails to)

## Run
Start API server first:

```bash
cd /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp
source .venv/bin/activate
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Process one batch:

```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/mailslurp_worker_once.sh
```

Run continuously:

```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/mailslurp_worker_loop.sh
```

## Behavior
- Fetches inbox emails from MailSlurp.
- Calls `/inbound` with sender + subject + body.
- Sends reply email using MailSlurp (or logs attempted send depending on `MAILSLURP_SEND_MODE`).
- Marks handled emails as read.
- Uses local state DB for idempotency.

## Send modes
- `auto`: attempt live send; if provider blocks sends (common on free-tier), continue processing and log the attempted outbound message.
- `live`: attempt live send and treat send errors as strict failures.
- `dry_run`: do not send through provider; only log outbound payloads to `MAILSLURP_OUTBOX_LOG`.
