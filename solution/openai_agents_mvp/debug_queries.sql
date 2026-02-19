-- Latest routed tickets
SELECT ticket_id, ticket_ref, requester_email, priority, automatable, requires_multi_desk, status, owner_agent_id, created_at
FROM tickets
ORDER BY ticket_id DESC
LIMIT 20;

-- Decision path for one ticket
-- Replace TCK000001
SELECT t.ticket_ref, rt.step_seq, rt.node_name, rt.decision, rt.actor_type, rt.created_at
FROM tickets t
JOIN routing_trace rt ON rt.ticket_id = t.ticket_id
WHERE t.ticket_ref = 'TCK000001'
ORDER BY rt.step_seq;

-- Multi-desk plan/hops
SELECT t.ticket_ref, p.step_seq, d.desk_code, p.step_reason
FROM ticket_desk_plan p
JOIN tickets t ON t.ticket_id = p.ticket_id
JOIN desks d ON d.desk_id = p.desk_id
WHERE t.ticket_ref = 'TCK000001'
ORDER BY p.step_seq;

SELECT t.ticket_ref, h.hop_seq, d1.desk_code AS from_desk, d2.desk_code AS to_desk, h.hop_reason, h.hopped_at
FROM ticket_desk_hops h
JOIN tickets t ON t.ticket_id = h.ticket_id
LEFT JOIN desks d1 ON d1.desk_id = h.from_desk_id
JOIN desks d2 ON d2.desk_id = h.to_desk_id
WHERE t.ticket_ref = 'TCK000001'
ORDER BY h.hop_seq;

-- Owner load ranking
SELECT l.agent_code, l.desk_code, l.open_ticket_count, l.available_slots, l.load_ratio
FROM v_agent_open_load l
WHERE l.is_active = 1
ORDER BY l.load_ratio ASC, l.available_slots DESC;
