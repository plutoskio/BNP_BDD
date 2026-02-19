# Agent Playbook (How an AI Agent Should Use This DB)

## Objective

Use the database as both:

1. Knowledge source for direct answers.
2. Operational source-of-truth for routing non-automatable tickets.

## Runtime sequence

### Step A: Read and classify request

- Input: inbound message (subject/body/client identifier).
- Resolve client from `clients` (`client_code` or `email`).
- Determine intent (`intents.intent_code`).

### Step B: Evaluate direct-answer eligibility

- Read rule from `routing_rules`.
- If `data_direct_available = 1` and request is objective:
  - query data tables (`cash_accounts`, `positions`, `trades`)
  - generate answer
  - set ticket `automatable = 1`
- Else:
  - set `automatable = 0`

### Step C: Multi-desk decision

- If non-automatable:
  - if `default_multi_desk = 1` or complexity flags triggered -> `requires_multi_desk = 1`
  - else `requires_multi_desk = 0`

### Step D: Owner assignment

- Query `v_agent_open_load` for active candidates.
- Prefer agents in `primary_desk_id`.
- Pick lowest `load_ratio`; tie-breaker highest `available_slots`.
- Write:
  - `tickets.owner_agent_id`
  - `ticket_assignments` row (`PRIMARY_OWNER`)

### Step E: Coordination (if multi-desk)

- Insert ordered rows in `ticket_desk_plan`.
- Insert initial hop + subsequent hops in `ticket_desk_hops`.
- Keep primary owner unchanged unless escalation policy requires transfer.

### Step F: Explainability and communication

- Insert each decision node in `routing_trace`.
- Insert inbound/outbound records in `email_messages`.

## SQL safety rules

- Always use transactions (`BEGIN ... COMMIT`) for ticket creation flows.
- Always keep `PRAGMA foreign_keys = ON`.
- Use parameterized SQL; do not string-concatenate user text.

## Required post-write validation

- Ticket exists.
- At least one routing trace row exists.
- At least one message exists.
- If multi-desk: at least one desk plan row and one hop row exist.

## Suggested API/tool boundary for next AI step

- `create_ticket(request_payload) -> ticket_ref`
- `route_ticket(ticket_ref) -> routing_decision`
- `assign_owner(ticket_ref) -> agent_code`
- `plan_multi_desk(ticket_ref) -> desk_sequence`
- `send_client_update(ticket_ref, template_id)`
- `get_decision_path(ticket_ref) -> ordered trace`
