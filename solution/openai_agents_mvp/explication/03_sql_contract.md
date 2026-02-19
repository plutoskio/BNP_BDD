# SQL Contract

## Read Tables
- `clients`: sender identity resolution
- `intents`, `routing_rules`: policy metadata
- `cash_accounts`, `positions`, `trades`: direct data answers
- `v_agent_open_load`, `agents`: owner assignment
- `desks`: desk-id/code mapping
- `v_ticket_decision_path`: status endpoint

## Write Tables
- `tickets`
- `routing_trace`
- `email_messages`
- `ticket_assignments` (non-automatable / escalation)
- `ticket_desk_plan` (non-automatable)
- `ticket_desk_hops` (non-automatable)

## Write Guarantees
- Parameterized SQL only.
- Single transaction per inbound request.
- Foreign keys enabled.
