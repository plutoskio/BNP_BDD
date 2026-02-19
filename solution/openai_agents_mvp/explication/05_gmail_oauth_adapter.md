# Gmail OAuth Adapter (for `thebardalar@gmail.com`)

## Goal
Connect real Gmail inbound/outbound email to the existing routing API:
- inbound email -> `/inbound`
- API response (`reply_subject`, `reply_body`) -> Gmail reply

## Files
- `email_adapter/gmail_auth.py`: one-time OAuth token bootstrap
- `email_adapter/gmail_worker.py`: worker that processes unread inbox emails
- `scripts/gmail_oauth_setup.sh`
- `scripts/gmail_worker_once.sh`
- `scripts/gmail_worker_loop.sh`

## Google Cloud Console Steps
1. Create/select a Google Cloud project.
2. Enable **Gmail API**.
3. Configure OAuth consent screen:
- User type: `External`
- Add test user: `thebardalar@gmail.com`
4. Create OAuth Client ID:
- Application type: `Desktop app`
5. Download client secret JSON and place it at:
- `/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/email_adapter/google_client_secret.json`

## Env Setup (`.env`)
Add:
- `GMAIL_ADDRESS=thebardalar@gmail.com`
- `GMAIL_OAUTH_CLIENT_SECRETS=/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/email_adapter/google_client_secret.json`
- `GMAIL_OAUTH_TOKEN_FILE=/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/email_adapter/google_token.json`
- `ROUTER_API_BASE_URL=http://127.0.0.1:8000`
- `GMAIL_POLL_SECONDS=15`
- `GMAIL_QUERY=label:inbox is:unread -from:me`
- `GMAIL_MAX_BATCH=10`
- `GMAIL_SKIP_SELF=1`
- `EMAIL_ADAPTER_STATE_DB=/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/email_adapter/adapter_state.db`

## First-Time OAuth
Run:
```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/gmail_oauth_setup.sh
```
A browser window opens; approve Gmail permissions. Token is saved to `google_token.json`.

## Run Worker
Start API first:
```bash
cd /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp
source .venv/bin/activate
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Process one batch:
```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/gmail_worker_once.sh
```

Run continuously:
```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/gmail_worker_loop.sh
```

## Safety / Idempotency
- Processed Gmail message IDs are tracked in `adapter_state.db`.
- Messages are marked read after successful handling.
- Self-sent emails are skipped when `GMAIL_SKIP_SELF=1`.
