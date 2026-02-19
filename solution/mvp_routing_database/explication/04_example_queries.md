# Example Queries (For Development and Demo)

## 1) Check core volumes

```sql
SELECT 'clients' AS table_name, COUNT(*) AS cnt FROM clients
UNION ALL SELECT 'cash_accounts', COUNT(*) FROM cash_accounts
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'trades', COUNT(*) FROM trades
UNION ALL SELECT 'tickets', COUNT(*) FROM tickets;
```

## 2) Show automatable vs non-automatable ticket mix

```sql
SELECT automatable, requires_multi_desk, COUNT(*) AS tickets
FROM tickets
GROUP BY automatable, requires_multi_desk
ORDER BY automatable DESC, requires_multi_desk DESC;
```

## 3) Agent workload (assignment input)

```sql
SELECT *
FROM v_agent_open_load
WHERE is_active = 1
ORDER BY load_ratio ASC, available_slots DESC;
```

## 4) Decision path for one ticket

```sql
SELECT step_seq, node_name, decision, rationale, actor_type, created_at
FROM routing_trace
WHERE ticket_id = 120
ORDER BY step_seq;
```

## 5) Multi-desk transfer map

```sql
SELECT
    t.ticket_ref,
    h.hop_seq,
    d_from.desk_code AS from_desk,
    d_to.desk_code AS to_desk,
    h.hop_reason,
    h.hopped_at
FROM ticket_desk_hops h
JOIN tickets t ON t.ticket_id = h.ticket_id
LEFT JOIN desks d_from ON d_from.desk_id = h.from_desk_id
JOIN desks d_to ON d_to.desk_id = h.to_desk_id
WHERE t.requires_multi_desk = 1
ORDER BY t.ticket_id, h.hop_seq
LIMIT 200;
```

## 6) Pending workload by desk

```sql
SELECT
    d.desk_code,
    d.desk_name,
    COUNT(*) AS active_tickets
FROM tickets t
JOIN desks d ON d.desk_id = t.primary_desk_id
WHERE t.status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CLIENT', 'ESCALATED')
GROUP BY d.desk_id
ORDER BY active_tickets DESC;
```

## 7) AI-response candidates not yet closed

```sql
SELECT
    t.ticket_ref,
    c.client_code,
    i.intent_code,
    t.status,
    t.created_at
FROM tickets t
JOIN clients c ON c.client_id = t.client_id
JOIN intents i ON i.intent_id = t.intent_id
WHERE t.automatable = 1
  AND t.status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CLIENT', 'ESCALATED')
ORDER BY t.created_at DESC;
```

## 8) Identify loop patterns in hops (A->B->A)

```sql
WITH hop_pairs AS (
    SELECT
        h1.ticket_id,
        h1.from_desk_id AS desk_a,
        h1.to_desk_id AS desk_b,
        h2.to_desk_id AS desk_c
    FROM ticket_desk_hops h1
    JOIN ticket_desk_hops h2
      ON h2.ticket_id = h1.ticket_id
     AND h2.hop_seq = h1.hop_seq + 1
    WHERE h1.from_desk_id IS NOT NULL
)
SELECT COUNT(*) AS loop_count
FROM hop_pairs
WHERE desk_a = desk_c;
```
