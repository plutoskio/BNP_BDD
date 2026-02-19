# OpenAI Agents SDK + SQLite Routing MVP

This package is a clean-slate implementation of your routing logic without email infrastructure.

It does:
- OpenAI Agents SDK intent classification (`gpt-5.2-2025-12-11` default).
- Deterministic decision-tree routing in Python.
- Parameterized SQLite queries against:
  - `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db`
- Transactional writes to `tickets`, `routing_trace`, `ticket_assignments`, `ticket_desk_plan`, `ticket_desk_hops`, and `email_messages`.
- CLI mode and HTTP API mode.

It does not yet do:
- real mailbox polling (IMAP)
- real outbound email delivery (SMTP/API)

## Architecture

1. `classifier.py`
- Uses OpenAI Agents SDK for structured intent output.
- Falls back to deterministic heuristic if API/key fails.

2. `service.py`
- Applies the decision tree deterministically.
- Reads direct data for simple objective requests.
- Routes to best-fit human owner for non-automatable requests.
- Builds multi-desk plans for complex requests.

3. `cli.py`
- Processes pseudo-email input locally.

4. `api.py`
- `POST /inbound` to process requests.
- `GET /ticket/{ticket_ref}` to inspect status/path.

## Decision Tree Implemented

1. `Data directly available without interpretation?`
- YES -> `AI response using internal database`
- If client says `NOT RESOLVED` -> handoff to human owner

2. If NO: `Does this require multiple desks?`
- YES -> `AI multi-desk workflow coordinator` + one accountable human owner
- NO -> `Suggest best-fit human agent based on specialty, load, and queue risk`

## Setup

```bash
cd /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy env template and set values:

```bash
cp .env.example .env
```

Required:
- `OPENAI_API_KEY`
- `DB_PATH` (default already points to MVP DB)

## CLI Usage

Process inbound request:

```bash
/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/.venv/bin/python \
  /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/cli.py \
  inbound \
  --from-email ops.cl0002@example-client.com \
  --subject "Need trade status for TRD000001" \
  --body "Can you confirm if this trade is executed?"
```

Check ticket status/path:

```bash
/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/.venv/bin/python \
  /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/cli.py \
  status --ticket-ref TCK000314
```

## API Usage

Run server:

```bash
cd /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp
source .venv/bin/activate
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Test inbound endpoint:

```bash
curl -s http://127.0.0.1:8000/inbound \
  -H 'Content-Type: application/json' \
  -d '{
    "from_email": "ops.cl0002@example-client.com",
    "subject": "Need trade status for TRD000001",
    "body": "Can you confirm if this trade is executed?"
  }' | jq
```

## Smoke Test

```bash
bash /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/scripts/smoke_test.sh
```

## Validate API Key Quickly

```bash
source /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/.venv/bin/activate
OPENAI_API_KEY=<your_key> python - <<'PY'
from agents import Agent, Runner
a = Agent(name="ping", instructions="Return exactly: pong")
r = Runner.run_sync(a, "ping", max_turns=1)
print(r.final_output)
PY
```

If this fails with `invalid_api_key`, rotate/regenerate the key and retry.

## Email (later)

Yes, this can send/receive email later.
- Send: SMTP or provider API (SendGrid/Mailgun/SES).
- Receive: IMAP poller or inbound webhook.
- Integration point: map inbound email into `/inbound` payload and use returned `reply_subject`/`reply_body` for outbound.

## Explication

- `/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/explication/00_index.md`
- `/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/debug_queries.sql`

## Security Notes

- Keep API keys in `.env` only; do not commit secrets.
- Rotate keys if they were shared in plain text.
- SQL is parameterized; no model-generated raw SQL is executed.
