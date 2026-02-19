PRAGMA foreign_keys = ON;

CREATE TABLE desks (
    desk_id INTEGER PRIMARY KEY,
    desk_code TEXT NOT NULL UNIQUE,
    desk_name TEXT NOT NULL,
    specialty TEXT NOT NULL
);

CREATE TABLE agents (
    agent_id INTEGER PRIMARY KEY,
    agent_code TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    desk_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    max_open_tickets INTEGER NOT NULL CHECK (max_open_tickets > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (desk_id) REFERENCES desks(desk_id)
);

CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY,
    client_code TEXT NOT NULL UNIQUE,
    client_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    segment TEXT NOT NULL CHECK (segment IN ('Institutional', 'Corporate', 'AssetManager', 'PrivateBanking')),
    primary_desk_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (primary_desk_id) REFERENCES desks(desk_id)
);

CREATE TABLE cash_accounts (
    cash_account_id INTEGER PRIMARY KEY,
    account_number TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL,
    currency TEXT NOT NULL CHECK (currency IN ('USD', 'EUR', 'GBP', 'CHF', 'JPY')),
    cash_balance REAL NOT NULL CHECK (cash_balance >= 0),
    available_cash REAL NOT NULL CHECK (available_cash >= 0),
    held_cash REAL NOT NULL CHECK (held_cash >= 0),
    updated_at TEXT NOT NULL,
    CHECK (ABS((available_cash + held_cash) - cash_balance) < 0.01),
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE positions (
    position_id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL CHECK (asset_class IN ('EQUITY', 'BOND', 'FX', 'ETF')),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    avg_cost REAL NOT NULL CHECK (avg_cost >= 0),
    market_price REAL NOT NULL CHECK (market_price >= 0),
    market_value REAL NOT NULL CHECK (market_value >= 0),
    as_of_date TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE trades (
    trade_id INTEGER PRIMARY KEY,
    trade_ref TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL,
    position_id INTEGER,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity REAL NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price > 0),
    notional REAL NOT NULL CHECK (notional > 0),
    trade_status TEXT NOT NULL CHECK (trade_status IN ('CONFIRMED', 'EXECUTED', 'FAILED', 'PENDING', 'CANCELLED')),
    fail_reason TEXT,
    submitted_at TEXT NOT NULL,
    confirmed_at TEXT,
    executed_at TEXT,
    settlement_date TEXT,
    CHECK ((trade_status = 'FAILED' AND fail_reason IS NOT NULL) OR trade_status != 'FAILED'),
    CHECK ((trade_status = 'EXECUTED' AND executed_at IS NOT NULL) OR trade_status != 'EXECUTED'),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (position_id) REFERENCES positions(position_id)
);

CREATE TABLE intents (
    intent_id INTEGER PRIMARY KEY,
    intent_code TEXT NOT NULL UNIQUE,
    intent_name TEXT NOT NULL
);

CREATE TABLE routing_rules (
    intent_id INTEGER PRIMARY KEY,
    data_direct_available INTEGER NOT NULL CHECK (data_direct_available IN (0, 1)),
    default_multi_desk INTEGER NOT NULL CHECK (default_multi_desk IN (0, 1)),
    primary_desk_id INTEGER NOT NULL,
    auto_response_template TEXT NOT NULL,
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id),
    FOREIGN KEY (primary_desk_id) REFERENCES desks(desk_id)
);

CREATE TABLE tickets (
    ticket_id INTEGER PRIMARY KEY,
    ticket_ref TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL,
    trade_id INTEGER,
    intent_id INTEGER NOT NULL,
    requester_email TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('EMAIL', 'PORTAL', 'PHONE')),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    automatable INTEGER NOT NULL CHECK (automatable IN (0, 1)),
    requires_multi_desk INTEGER NOT NULL CHECK (requires_multi_desk IN (0, 1)),
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CLIENT', 'RESOLVED', 'CLOSED', 'ESCALATED')),
    primary_desk_id INTEGER NOT NULL,
    owner_agent_id INTEGER,
    created_at TEXT NOT NULL,
    first_response_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    client_satisfied INTEGER CHECK (client_satisfied IN (0, 1)),
    CHECK (first_response_at IS NULL OR first_response_at >= created_at),
    CHECK (
        (status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CLIENT', 'ESCALATED') AND resolved_at IS NULL AND closed_at IS NULL)
        OR (status = 'RESOLVED' AND resolved_at IS NOT NULL AND closed_at IS NULL)
        OR (status = 'CLOSED' AND resolved_at IS NOT NULL AND closed_at IS NOT NULL AND closed_at >= resolved_at)
    ),
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id),
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id),
    FOREIGN KEY (primary_desk_id) REFERENCES desks(desk_id),
    FOREIGN KEY (owner_agent_id) REFERENCES agents(agent_id)
);

CREATE TABLE ticket_assignments (
    assignment_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    assigned_agent_id INTEGER NOT NULL,
    assigned_desk_id INTEGER NOT NULL,
    assignment_role TEXT NOT NULL CHECK (assignment_role IN ('PRIMARY_OWNER', 'CONTRIBUTOR')),
    assignment_reason TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    released_at TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (assigned_desk_id) REFERENCES desks(desk_id)
);

CREATE TABLE ticket_desk_plan (
    plan_step_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    step_seq INTEGER NOT NULL CHECK (step_seq > 0),
    desk_id INTEGER NOT NULL,
    step_reason TEXT NOT NULL,
    required_flag INTEGER NOT NULL CHECK (required_flag IN (0, 1)),
    UNIQUE (ticket_id, step_seq),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (desk_id) REFERENCES desks(desk_id)
);

CREATE TABLE ticket_desk_hops (
    hop_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    hop_seq INTEGER NOT NULL CHECK (hop_seq > 0),
    from_desk_id INTEGER,
    to_desk_id INTEGER NOT NULL,
    hopped_by_agent_id INTEGER,
    hop_reason TEXT NOT NULL,
    hopped_at TEXT NOT NULL,
    UNIQUE (ticket_id, hop_seq),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (from_desk_id) REFERENCES desks(desk_id),
    FOREIGN KEY (to_desk_id) REFERENCES desks(desk_id),
    FOREIGN KEY (hopped_by_agent_id) REFERENCES agents(agent_id)
);

CREATE TABLE routing_trace (
    trace_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    step_seq INTEGER NOT NULL CHECK (step_seq > 0),
    node_name TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('SYSTEM', 'AI', 'HUMAN')),
    decided_by_agent_id INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (ticket_id, step_seq),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (decided_by_agent_id) REFERENCES agents(agent_id)
);

CREATE TABLE email_messages (
    message_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('INBOUND', 'OUTBOUND')),
    sender_email TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    is_automated INTEGER NOT NULL CHECK (is_automated IN (0, 1)),
    delivery_status TEXT NOT NULL CHECK (delivery_status IN ('QUEUED', 'SENT', 'FAILED')),
    related_trace_id INTEGER,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (related_trace_id) REFERENCES routing_trace(trace_id)
);

CREATE INDEX idx_agents_desk_id ON agents(desk_id);
CREATE INDEX idx_clients_primary_desk_id ON clients(primary_desk_id);
CREATE INDEX idx_cash_accounts_client_id ON cash_accounts(client_id);
CREATE INDEX idx_positions_client_id ON positions(client_id);
CREATE INDEX idx_trades_client_id ON trades(client_id);
CREATE INDEX idx_trades_status ON trades(trade_status);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_owner_agent ON tickets(owner_agent_id);
CREATE INDEX idx_tickets_client_id ON tickets(client_id);
CREATE INDEX idx_tickets_intent_id ON tickets(intent_id);
CREATE INDEX idx_ticket_assignments_ticket_id ON ticket_assignments(ticket_id);
CREATE INDEX idx_ticket_desk_plan_ticket_id ON ticket_desk_plan(ticket_id);
CREATE INDEX idx_ticket_desk_hops_ticket_id ON ticket_desk_hops(ticket_id);
CREATE INDEX idx_routing_trace_ticket_id ON routing_trace(ticket_id);
CREATE INDEX idx_email_messages_ticket_id ON email_messages(ticket_id);

CREATE VIEW v_agent_open_load AS
SELECT
    a.agent_id,
    a.agent_code,
    a.full_name,
    a.is_active,
    a.desk_id,
    d.desk_code,
    d.specialty,
    a.max_open_tickets,
    COALESCE(t.open_ticket_count, 0) AS open_ticket_count,
    (a.max_open_tickets - COALESCE(t.open_ticket_count, 0)) AS available_slots,
    ROUND(
        CASE
            WHEN a.max_open_tickets = 0 THEN 1.0
            ELSE COALESCE(t.open_ticket_count, 0) * 1.0 / a.max_open_tickets
        END,
        4
    ) AS load_ratio
FROM agents a
JOIN desks d ON d.desk_id = a.desk_id
LEFT JOIN (
    SELECT owner_agent_id AS agent_id, COUNT(*) AS open_ticket_count
    FROM tickets
    WHERE owner_agent_id IS NOT NULL
      AND status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CLIENT', 'ESCALATED')
    GROUP BY owner_agent_id
) t ON t.agent_id = a.agent_id;

CREATE VIEW v_ticket_decision_path AS
SELECT
    t.ticket_id,
    t.ticket_ref,
    rt.step_seq,
    rt.node_name,
    rt.decision,
    rt.actor_type,
    rt.created_at
FROM tickets t
JOIN routing_trace rt ON rt.ticket_id = t.ticket_id
ORDER BY t.ticket_id, rt.step_seq;
