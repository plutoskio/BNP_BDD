# Operational Playbook

## Start
1. Activate virtual env.
2. Set `OPENAI_API_KEY` and verify `DB_PATH`.
3. Run smoke test.
4. Start API server.

## Verify
- `POST /inbound` returns `ok=true` and `ticket_ref`.
- `GET /ticket/{ticket_ref}` returns decision path rows.
- DB shows matching records across `tickets`, `routing_trace`, `email_messages`.

## Troubleshooting
- `unknown_client`: sender email not present in `clients`.
- `invalid_api_key`: rotate key and retry.
- empty direct-data result: client may not have relevant records.
- no owner available: ensure at least one active agent in `agents`.
