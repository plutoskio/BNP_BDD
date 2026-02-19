# Decision Tree Mapping

## Node 1: Data directly available without interpretation?
Code criteria:
- `routing_rules.data_direct_available = 1`
- `classification.objective_request = true`
- direct query returns data (`cash_accounts`, `positions`, or `trades`)

If true:
- `tickets.automatable = 1`
- `tickets.status = RESOLVED`
- Trace node: `AI response using internal database`

## Node 2: Does this require multiple desks?
Code criteria:
- non-automatable path only
- `routing_rules.default_multi_desk = 1` OR `classification.requires_multi_desk_hint = true`

If true:
- AI builds `ticket_desk_plan`
- AI logs `ticket_desk_hops`
- one accountable human owner is assigned

If false:
- single best-fit owner selected from `v_agent_open_load`

## Escalation Node: Client satisfied?
When client replies `NOT RESOLVED TCKxxxxxx`:
- reopen to `IN_PROGRESS`
- assign human owner
- trace: `Client satisfied? = NO`
