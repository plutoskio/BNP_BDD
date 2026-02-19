# Routing Contract (Decision Tree Mapping)

## Target decision tree

1. `Data directly available without interpretation?`
- YES -> `AI response using internal database`
- NO -> step 2

2. `Does this require multiple desks?`
- YES -> `AI multi-desk workflow coordinator` + one accountable human owner
- NO -> `Suggest best-fit human agent based on specialty, load, and queue risk`

3. If client is not satisfied with an AI response:
- immediate handoff to a human owner

## How to map this to tables

### Classification inputs
- Read request content from inbound message (`email_messages`) or external channel payload.
- Map to `intents.intent_code`.

### Rule lookup
- Read `routing_rules` by `intent_id`.
- Determine:
  - `automatable` candidate (`data_direct_available`)
  - `requires_multi_desk` candidate (`default_multi_desk`)
  - `primary_desk_id`

### Assignment strategy
- Use `v_agent_open_load` filtered by `desks.specialty` / `primary_desk_id`.
- Pick active agent with best capacity (`lowest load_ratio`, `highest available_slots`).
- Persist owner in `tickets.owner_agent_id`.
- Write row in `ticket_assignments` (`PRIMARY_OWNER`).

### Multi-desk strategy
- Generate `ticket_desk_plan` with ordered desks.
- Persist actual transitions in `ticket_desk_hops`.
- Keep the same primary owner accountable even if desk hops occur.

### Explainability
- Persist every decision in `routing_trace` with:
  - `node_name`
  - `decision`
  - `rationale`
  - `actor_type` (`AI` or `HUMAN`)

### Client communication
- Log all messages in `email_messages`.
- Link message to decision when possible via `related_trace_id`.

## Minimal required writes for one new ticket

1. insert `tickets`
2. insert `routing_trace` (at least 2 steps)
3. insert `ticket_assignments` (if human owner)
4. insert `ticket_desk_plan` + `ticket_desk_hops` (if multi-desk)
5. insert outbound `email_messages`

## Do not do

- Do not overwrite past trace rows.
- Do not overwrite assignment history; append assignment events instead.
- Do not update `ticket_desk_hops` retroactively; insert new hop rows.
