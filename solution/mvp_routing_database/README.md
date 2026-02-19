# MVP Routing Database

This package builds a standalone SQLite database for your conception/MVP phase.

It is intentionally separate from production-like data (`/Users/milo/Desktop/BNP_BDD/hobart.db`) and can be used for AI-agent prototyping.

## Files

- `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/schema.sql`
- `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/build_database.py`
- `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db` (generated)
- `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/seed_summary.md` (generated)
- `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/explication/` (detailed handoff docs)

## Seeded Volumes

- 100 clients
- 150 cash accounts
- 400 positions
- 800 trades
- 300 tickets (mixed outcomes)

## Build

```bash
cd /Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database
python3 build_database.py
```

## Quick Validation

```bash
sqlite3 /Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db "SELECT COUNT(*) FROM clients;"
sqlite3 /Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db "SELECT COUNT(*) FROM cash_accounts;"
sqlite3 /Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db "SELECT COUNT(*) FROM positions;"
sqlite3 /Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db "SELECT COUNT(*) FROM trades;"
sqlite3 /Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db "SELECT COUNT(*) FROM tickets;"
```

## Useful Demo Queries

```sql
-- workload by agent (computed from open tickets)
SELECT *
FROM v_agent_open_load
WHERE is_active = 1
ORDER BY load_ratio ASC, available_slots DESC;

-- decision path for one ticket
SELECT step_seq, node_name, decision, actor_type, created_at
FROM v_ticket_decision_path
WHERE ticket_ref = 'TCK000120'
ORDER BY step_seq;

-- where multi-desk tickets are flowing
SELECT t.ticket_ref, d1.desk_code AS from_desk, d2.desk_code AS to_desk, h.hop_reason
FROM ticket_desk_hops h
JOIN tickets t ON t.ticket_id = h.ticket_id
LEFT JOIN desks d1 ON d1.desk_id = h.from_desk_id
JOIN desks d2 ON d2.desk_id = h.to_desk_id
WHERE t.requires_multi_desk = 1
ORDER BY t.ticket_id, h.hop_seq
LIMIT 50;
```
