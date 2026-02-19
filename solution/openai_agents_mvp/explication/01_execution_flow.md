# Execution Flow

1. Receive inbound payload (`from_email`, `subject`, `body`).
2. Resolve `clients.email` -> `client_id`.
3. If message contains `NOT RESOLVED` + `TCKxxxxxx`, execute escalation path.
4. Else classify intent via OpenAI Agents SDK.
5. Apply deterministic routing policy:
   - direct data path
   - single-desk human path
   - multi-desk coordinated path
6. Persist audit trail transactionally.
7. Return structured JSON output with `ticket_ref`, `decision_path`, and `reply_body`.

## Failure Handling
- Unknown client: safe error response, no ticket insert.
- Invalid NOT RESOLVED reference: safe error response, no ticket insert.
- OpenAI failure: fallback heuristic classifier keeps workflow operational.
