#!/usr/bin/env python3
from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "mvp_routing.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
SUMMARY_PATH = BASE_DIR / "seed_summary.md"

SEED = 20260219
REFERENCE_NOW = datetime(2026, 2, 19, 10, 0, 0)

TARGET_COUNTS = {
    "clients": 100,
    "cash_accounts": 150,
    "positions": 400,
    "trades": 800,
    "tickets": 300,
}

DESKS = [
    (1, "CS", "Client Services", "General client inquiry handling"),
    (2, "TRD", "Trade Support", "Trade execution and trade lifecycle support"),
    (3, "SET", "Settlements", "Settlement breaks and value date issues"),
    (4, "CASH", "Cash Operations", "Cash balance and funding operations"),
    (5, "CMP", "Compliance", "Sanctions and regulatory controls"),
    (6, "CA", "Corporate Actions", "Corporate action instructions and processing"),
    (7, "ACCT", "Account Services", "Account maintenance and closure workflows"),
]

INTENTS = [
    (
        1,
        "cash_balance",
        "Cash Balance Request",
        1,
        0,
        4,
        "Automated cash balance response generated from internal database.",
    ),
    (
        2,
        "position_summary",
        "Position Summary Request",
        1,
        0,
        1,
        "Automated position summary response generated from internal database.",
    ),
    (
        3,
        "trade_status",
        "Trade Status Check",
        1,
        0,
        2,
        "Automated trade status response generated from internal database.",
    ),
    (
        4,
        "settlement_eta",
        "Settlement ETA Request",
        1,
        0,
        3,
        "Automated settlement ETA response generated from internal database.",
    ),
    (
        5,
        "failed_trade_investigation",
        "Failed Trade Investigation",
        0,
        1,
        2,
        "Requires multi-desk investigation with AI coordinator and human owner.",
    ),
    (
        6,
        "trade_amendment_request",
        "Trade Amendment Request",
        0,
        0,
        2,
        "Requires human validation before trade amendment.",
    ),
    (
        7,
        "account_closure_request",
        "Account Closure Request",
        0,
        1,
        7,
        "Requires coordinated closure workflow across desks.",
    ),
    (
        8,
        "sanctions_review_query",
        "Sanctions Review Query",
        0,
        1,
        5,
        "Requires compliance-driven multi-desk review.",
    ),
    (
        9,
        "corporate_action_instruction",
        "Corporate Action Instruction",
        0,
        1,
        6,
        "Requires corporate actions and settlements coordination.",
    ),
    (
        10,
        "fee_dispute",
        "Fee Dispute",
        0,
        0,
        1,
        "Requires human investigation and client follow-up.",
    ),
]

INTENT_WEIGHTS = {
    "cash_balance": 0.20,
    "position_summary": 0.16,
    "trade_status": 0.20,
    "settlement_eta": 0.08,
    "failed_trade_investigation": 0.09,
    "trade_amendment_request": 0.08,
    "account_closure_request": 0.06,
    "sanctions_review_query": 0.03,
    "corporate_action_instruction": 0.04,
    "fee_dispute": 0.06,
}

MULTI_DESK_SEQUENCE = {
    "failed_trade_investigation": ["TRD", "SET", "CASH"],
    "account_closure_request": ["ACCT", "CMP", "CASH"],
    "sanctions_review_query": ["CMP", "TRD", "CS"],
    "corporate_action_instruction": ["CA", "SET", "TRD"],
}

FIRST_NAMES = [
    "Alex",
    "Jordan",
    "Taylor",
    "Morgan",
    "Cameron",
    "Riley",
    "Casey",
    "Jamie",
    "Avery",
    "Logan",
    "Parker",
    "Sydney",
    "Quinn",
    "Reese",
    "Harper",
    "Finley",
    "Rowan",
    "Blake",
    "Elliot",
    "Sage",
    "Drew",
    "Robin",
    "Sawyer",
    "Skyler",
]

LAST_NAMES = [
    "Campbell",
    "Morgan",
    "Bailey",
    "Patterson",
    "Sullivan",
    "Reid",
    "Hughes",
    "Bennett",
    "Donovan",
    "Murray",
    "Dawson",
    "Fraser",
    "Whitman",
    "Langford",
    "Prescott",
    "Carlisle",
    "Monroe",
    "Fletcher",
    "Hawkins",
    "Armstrong",
    "Keller",
    "Richmond",
    "Shepherd",
    "Callahan",
]

CLIENT_PREFIX = [
    "Northbridge",
    "Silverline",
    "Summit",
    "Atlas",
    "Crescent",
    "Harbor",
    "Oakridge",
    "Vantage",
    "Evergreen",
    "Granite",
    "Bluewater",
    "Sterling",
    "Ironwood",
    "Keystone",
    "Broadway",
    "Redwood",
    "Apex",
    "Clearview",
    "Pinecrest",
    "Windham",
]

CLIENT_SUFFIX = [
    "Capital",
    "Holdings",
    "Partners",
    "Advisors",
    "Investments",
    "Securities",
    "Trust",
    "Ventures",
    "Asset Group",
    "Treasury",
    "Markets",
    "Portfolio",
    "Solutions",
    "Financial",
    "Management",
    "Funds",
    "Strategies",
    "Equities",
    "Analytics",
    "Banking",
]

SYMBOLS = [
    ("AAPL", "EQUITY", 190.0),
    ("MSFT", "EQUITY", 420.0),
    ("NVDA", "EQUITY", 740.0),
    ("AMZN", "EQUITY", 185.0),
    ("META", "EQUITY", 500.0),
    ("GOOGL", "EQUITY", 165.0),
    ("JPM", "EQUITY", 195.0),
    ("XOM", "EQUITY", 115.0),
    ("SPY", "ETF", 510.0),
    ("QQQ", "ETF", 445.0),
    ("TLT", "ETF", 94.0),
    ("BND", "ETF", 71.0),
    ("US10Y", "BOND", 99.2),
    ("US30Y", "BOND", 97.4),
    ("FR10Y", "BOND", 101.1),
    ("DE10Y", "BOND", 100.3),
    ("EURUSD", "FX", 1.08),
    ("GBPUSD", "FX", 1.27),
    ("USDJPY", "FX", 149.2),
    ("USDCHF", "FX", 0.88),
]


def to_ts(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def random_dt(rng: random.Random, start_days_ago: int, end_days_ago: int = 0) -> datetime:
    start = REFERENCE_NOW - timedelta(days=start_days_ago)
    end = REFERENCE_NOW - timedelta(days=end_days_ago)
    total = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(total, 1)))


def select_best_agent(
    preferred_desk_id: int,
    active_agents: list[dict[str, Any]],
    projected_open: dict[int, int],
) -> dict[str, Any]:
    preferred = [a for a in active_agents if a["desk_id"] == preferred_desk_id]
    candidates = preferred if preferred else active_agents

    def score(agent: dict[str, Any]) -> tuple[float, int]:
        open_count = projected_open[agent["agent_id"]]
        load_ratio = open_count / agent["max_open_tickets"]
        available_slots = agent["max_open_tickets"] - open_count
        return (load_ratio, -available_slots)

    return sorted(candidates, key=score)[0]


def build_schema(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)


def seed_desks(conn: sqlite3.Connection) -> dict[str, int]:
    conn.executemany(
        """
        INSERT INTO desks (desk_id, desk_code, desk_name, specialty)
        VALUES (?, ?, ?, ?);
        """,
        DESKS,
    )
    return {code: desk_id for desk_id, code, _, _ in DESKS}


def seed_agents(conn: sqlite3.Connection, rng: random.Random) -> tuple[list[dict[str, Any]], dict[int, int]]:
    rows = []
    agents: list[dict[str, Any]] = []
    projected_open = defaultdict(int)
    agent_id = 1
    for desk_id, desk_code, _, _ in DESKS:
        for i in range(4):
            first = FIRST_NAMES[(agent_id + i) % len(FIRST_NAMES)]
            last = LAST_NAMES[(agent_id * 2 + i) % len(LAST_NAMES)]
            full_name = f"{first} {last}"
            agent_code = f"AGT{agent_id:04d}"
            email = f"{agent_code.lower()}@mvp.demo"
            is_active = 1 if i < 3 or rng.random() > 0.2 else 0
            max_open = rng.randint(14, 32)
            created_at = to_ts(random_dt(rng, 500, 120))
            rows.append(
                (agent_id, agent_code, full_name, email, desk_id, is_active, max_open, created_at)
            )
            agents.append(
                {
                    "agent_id": agent_id,
                    "agent_code": agent_code,
                    "email": email,
                    "desk_id": desk_id,
                    "is_active": bool(is_active),
                    "max_open_tickets": max_open,
                }
            )
            projected_open[agent_id] = rng.randint(0, max(1, max_open // 3))
            agent_id += 1

    conn.executemany(
        """
        INSERT INTO agents (
            agent_id, agent_code, full_name, email, desk_id,
            is_active, max_open_tickets, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    return agents, projected_open


def seed_intents_and_rules(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    conn.executemany(
        """
        INSERT INTO intents (intent_id, intent_code, intent_name)
        VALUES (?, ?, ?);
        """,
        [(i[0], i[1], i[2]) for i in INTENTS],
    )
    conn.executemany(
        """
        INSERT INTO routing_rules (
            intent_id, data_direct_available, default_multi_desk, primary_desk_id, auto_response_template
        ) VALUES (?, ?, ?, ?, ?);
        """,
        [(i[0], i[3], i[4], i[5], i[6]) for i in INTENTS],
    )
    return {
        i[0]: {
            "intent_code": i[1],
            "intent_name": i[2],
            "data_direct_available": bool(i[3]),
            "default_multi_desk": bool(i[4]),
            "primary_desk_id": i[5],
            "auto_response_template": i[6],
        }
        for i in INTENTS
    }


def seed_clients(conn: sqlite3.Connection, rng: random.Random) -> list[dict[str, Any]]:
    names = [f"{a} {b}" for a in CLIENT_PREFIX for b in CLIENT_SUFFIX]
    rng.shuffle(names)
    segments = ["Institutional", "Corporate", "AssetManager", "PrivateBanking"]
    seg_w = [0.33, 0.27, 0.24, 0.16]
    desk_ids = [d[0] for d in DESKS]
    desk_w = [0.26, 0.21, 0.11, 0.18, 0.09, 0.08, 0.07]

    rows = []
    clients = []
    for client_id in range(1, TARGET_COUNTS["clients"] + 1):
        client_code = f"CL{client_id:04d}"
        client_name = names[client_id - 1]
        email = f"ops.{client_code.lower()}@example-client.com"
        segment = rng.choices(segments, weights=seg_w, k=1)[0]
        primary_desk_id = rng.choices(desk_ids, weights=desk_w, k=1)[0]
        created_at = to_ts(random_dt(rng, 800, 150))
        rows.append((client_id, client_code, client_name, email, segment, primary_desk_id, created_at))
        clients.append(
            {
                "client_id": client_id,
                "client_code": client_code,
                "client_name": client_name,
                "email": email,
                "primary_desk_id": primary_desk_id,
            }
        )

    conn.executemany(
        """
        INSERT INTO clients (
            client_id, client_code, client_name, email, segment, primary_desk_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    return clients


def seed_cash_accounts(conn: sqlite3.Connection, rng: random.Random, clients: list[dict[str, Any]]) -> None:
    currencies = ["USD", "EUR", "GBP", "CHF", "JPY"]
    used_currency: dict[int, set[str]] = defaultdict(set)
    rows = []
    account_id = 1

    # one account per client (100)
    for c in clients:
        currency = rng.choice(currencies)
        used_currency[c["client_id"]].add(currency)
        bal = round(rng.uniform(70_000, 15_000_000), 2)
        held = round(bal * rng.uniform(0.01, 0.18), 2)
        avail = round(bal - held, 2)
        rows.append(
            (
                account_id,
                f"AC{c['client_id']:04d}01",
                c["client_id"],
                currency,
                bal,
                avail,
                held,
                to_ts(random_dt(rng, 45, 0)),
            )
        )
        account_id += 1

    # add 50 more
    extra_clients = rng.sample([c["client_id"] for c in clients], 50)
    for client_id in extra_clients:
        available = [cur for cur in currencies if cur not in used_currency[client_id]]
        currency = rng.choice(available) if available else rng.choice(currencies)
        used_currency[client_id].add(currency)
        bal = round(rng.uniform(50_000, 9_000_000), 2)
        held = round(bal * rng.uniform(0.01, 0.22), 2)
        avail = round(bal - held, 2)
        seq = len(used_currency[client_id])
        rows.append(
            (
                account_id,
                f"AC{client_id:04d}{seq:02d}",
                client_id,
                currency,
                bal,
                avail,
                held,
                to_ts(random_dt(rng, 45, 0)),
            )
        )
        account_id += 1

    conn.executemany(
        """
        INSERT INTO cash_accounts (
            cash_account_id, account_number, client_id, currency,
            cash_balance, available_cash, held_cash, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )


def seed_positions(
    conn: sqlite3.Connection, rng: random.Random, clients: list[dict[str, Any]]
) -> tuple[dict[int, list[int]], dict[int, dict[str, list[int]]]]:
    rows = []
    client_ids = [c["client_id"] for c in clients]
    client_position_ids: dict[int, list[int]] = defaultdict(list)
    client_symbol_positions: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    position_id = 1

    target_clients = client_ids + [rng.choice(client_ids) for _ in range(TARGET_COUNTS["positions"] - len(client_ids))]
    for client_id in target_clients:
        symbol, asset_class, base = rng.choice(SYMBOLS)
        if asset_class == "FX":
            qty = float(rng.randint(50_000, 3_000_000))
        elif asset_class == "BOND":
            qty = float(rng.randint(5, 2_500))
        else:
            qty = float(rng.randint(10, 10_000))
        avg_cost = round(base * rng.uniform(0.84, 1.15), 6)
        mkt_price = round(base * rng.uniform(0.78, 1.23), 6)
        mkt_value = round(qty * mkt_price, 2)
        as_of = to_ts(random_dt(rng, 8, 0))
        rows.append((position_id, client_id, symbol, asset_class, qty, avg_cost, mkt_price, mkt_value, as_of))
        client_position_ids[client_id].append(position_id)
        client_symbol_positions[client_id][symbol].append(position_id)
        position_id += 1

    conn.executemany(
        """
        INSERT INTO positions (
            position_id, client_id, symbol, asset_class,
            quantity, avg_cost, market_price, market_value, as_of_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    return client_position_ids, client_symbol_positions


def seed_trades(
    conn: sqlite3.Connection,
    rng: random.Random,
    clients: list[dict[str, Any]],
    client_symbol_positions: dict[int, dict[str, list[int]]],
) -> dict[int, list[int]]:
    status_pool = (
        ["EXECUTED"] * 420
        + ["CONFIRMED"] * 130
        + ["FAILED"] * 95
        + ["PENDING"] * 90
        + ["CANCELLED"] * 65
    )
    rng.shuffle(status_pool)
    fail_reasons = [
        "Insufficient cash",
        "Counterparty reject",
        "Instruction mismatch",
        "Compliance hold",
        "Late market cutoff",
    ]
    symbol_info = {s[0]: s for s in SYMBOLS}
    client_ids = [c["client_id"] for c in clients]
    rows = []
    trades_by_client: dict[int, list[int]] = defaultdict(list)

    for trade_id, status in enumerate(status_pool, start=1):
        client_id = rng.choice(client_ids)
        if client_symbol_positions[client_id] and rng.random() < 0.72:
            symbol = rng.choice(list(client_symbol_positions[client_id].keys()))
        else:
            symbol = rng.choice(SYMBOLS)[0]
        _, asset_class, base = symbol_info[symbol]
        position_candidates = client_symbol_positions[client_id].get(symbol, [])
        position_id = rng.choice(position_candidates) if position_candidates and rng.random() < 0.85 else None
        side = "BUY" if rng.random() < 0.57 else "SELL"
        if asset_class == "FX":
            qty = float(rng.randint(25_000, 2_200_000))
        elif asset_class == "BOND":
            qty = float(rng.randint(5, 1_500))
        else:
            qty = float(rng.randint(5, 5_000))
        price = round(base * rng.uniform(0.82, 1.22), 6)
        notional = round(qty * price, 2)
        submitted = random_dt(rng, 240, 1)
        confirmed = submitted + timedelta(minutes=rng.randint(5, 240))
        executed = None
        settlement = None
        fail_reason = None
        if status == "EXECUTED":
            executed = submitted + timedelta(minutes=rng.randint(8, 3_200))
            settlement = executed + timedelta(days=rng.randint(1, 3))
        elif status == "CONFIRMED":
            settlement = confirmed + timedelta(days=rng.randint(2, 4))
        elif status == "FAILED":
            fail_reason = rng.choice(fail_reasons)
        elif status == "CANCELLED" and rng.random() < 0.35:
            fail_reason = "Client cancellation"

        rows.append(
            (
                trade_id,
                f"TRD{trade_id:06d}",
                client_id,
                position_id,
                symbol,
                side,
                qty,
                price,
                notional,
                status,
                fail_reason,
                to_ts(submitted),
                to_ts(confirmed),
                to_ts(executed),
                to_ts(settlement),
            )
        )
        trades_by_client[client_id].append(trade_id)

    conn.executemany(
        """
        INSERT INTO trades (
            trade_id, trade_ref, client_id, position_id, symbol, side, quantity, price, notional,
            trade_status, fail_reason, submitted_at, confirmed_at, executed_at, settlement_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    return trades_by_client


def seed_tickets_and_ops(
    conn: sqlite3.Connection,
    rng: random.Random,
    clients: list[dict[str, Any]],
    intents: dict[int, dict[str, Any]],
    desk_code_to_id: dict[str, int],
    agents: list[dict[str, Any]],
    projected_open: dict[int, int],
    trades_by_client: dict[int, list[int]],
) -> None:
    ticket_status_pool = (
        ["CLOSED"] * 150
        + ["RESOLVED"] * 45
        + ["IN_PROGRESS"] * 50
        + ["WAITING_CLIENT"] * 25
        + ["OPEN"] * 20
        + ["ESCALATED"] * 10
    )
    rng.shuffle(ticket_status_pool)

    active_agents = [a for a in agents if a["is_active"]]
    intent_ids = sorted(intents.keys())
    intent_codes = [intents[i]["intent_code"] for i in intent_ids]
    intent_weights = [INTENT_WEIGHTS[intents[i]["intent_code"]] for i in intent_ids]
    trade_related = {
        "trade_status",
        "settlement_eta",
        "failed_trade_investigation",
        "trade_amendment_request",
        "corporate_action_instruction",
    }

    ticket_rows = []
    assignment_rows = []
    plan_rows = []
    hop_rows = []
    trace_rows = []
    message_rows = []

    assignment_id = 1
    plan_step_id = 1
    hop_id = 1
    trace_id = 1
    message_id = 1

    for ticket_id, status in enumerate(ticket_status_pool, start=1):
        ticket_ref = f"TCK{ticket_id:06d}"
        client = rng.choice(clients)
        client_id = client["client_id"]
        intent_id = rng.choices(intent_ids, weights=intent_weights, k=1)[0]
        intent = intents[intent_id]
        intent_code = intent["intent_code"]
        trade_id = rng.choice(trades_by_client[client_id]) if intent_code in trade_related and trades_by_client[client_id] else None

        subject = f"{intent['intent_name']} - {client['client_code']}"
        body = f"Request from {client['client_name']} regarding {intent['intent_name']}."
        channel = rng.choices(["EMAIL", "PORTAL", "PHONE"], weights=[0.75, 0.17, 0.08], k=1)[0]

        automatable = 1 if intent["data_direct_available"] and rng.random() < 0.86 else 0
        requires_multi = 1 if automatable == 0 and (intent["default_multi_desk"] or rng.random() < 0.16) else 0

        if intent_code in {"sanctions_review_query", "failed_trade_investigation"}:
            priority = "CRITICAL"
        elif requires_multi:
            priority = "HIGH"
        elif intent_code in {"trade_amendment_request", "fee_dispute"}:
            priority = "MEDIUM"
        else:
            priority = rng.choices(["LOW", "MEDIUM"], weights=[0.42, 0.58], k=1)[0]

        created_at = random_dt(rng, 140, 0)
        first_response_at = created_at + timedelta(
            minutes=(rng.randint(3, 15) if automatable else rng.randint(7, 25))
        )

        if status in {"RESOLVED", "CLOSED"}:
            # MVP demo target: keep overall resolution around 30-60 minutes.
            res_minutes = rng.randint(30, 60)
            resolved_at = created_at + timedelta(minutes=res_minutes)
            if resolved_at <= first_response_at:
                resolved_at = first_response_at + timedelta(minutes=rng.randint(3, 12))
            closed_at = (
                resolved_at + timedelta(minutes=rng.randint(2, 18))
                if status == "CLOSED"
                else None
            )
        else:
            resolved_at = None
            closed_at = None

        client_satisfied = None
        if automatable:
            client_satisfied = 0 if rng.random() < 0.14 else 1
        elif status in {"RESOLVED", "CLOSED"}:
            client_satisfied = 0 if rng.random() < 0.19 else 1

        owner_agent_id = None
        owner_agent_code = None
        owner_agent_email = None
        if automatable == 0 or client_satisfied == 0 or status in {"OPEN", "IN_PROGRESS", "WAITING_CLIENT", "ESCALATED"}:
            picked = select_best_agent(intent["primary_desk_id"], active_agents, projected_open)
            owner_agent_id = picked["agent_id"]
            owner_agent_code = picked["agent_code"]
            owner_agent_email = picked["email"]
            if status in {"OPEN", "IN_PROGRESS", "WAITING_CLIENT", "ESCALATED"}:
                projected_open[owner_agent_id] += 1

        if automatable == 1 and client_satisfied == 1 and status in {"RESOLVED", "CLOSED"}:
            owner_agent_id = None
            owner_agent_code = None
            owner_agent_email = None

        ticket_rows.append(
            (
                ticket_id,
                ticket_ref,
                client_id,
                trade_id,
                intent_id,
                client["email"],
                channel,
                subject,
                body,
                priority,
                automatable,
                requires_multi,
                status,
                intent["primary_desk_id"],
                owner_agent_id,
                to_ts(created_at),
                to_ts(first_response_at),
                to_ts(resolved_at),
                to_ts(closed_at),
                client_satisfied,
            )
        )

        trace_time = created_at + timedelta(minutes=1)
        step = 1
        trace_local = {}
        trace_local["step1"] = trace_id
        trace_rows.append(
            (
                trace_id,
                ticket_id,
                step,
                "Data directly available without interpretation?",
                "YES" if automatable else "NO",
                f"Intent '{intent_code}' direct-data flag and message checks evaluated.",
                "AI",
                None,
                to_ts(trace_time),
            )
        )
        trace_id += 1
        step += 1
        trace_time += timedelta(minutes=1)

        if automatable:
            trace_local["auto"] = trace_id
            trace_rows.append(
                (
                    trace_id,
                    ticket_id,
                    step,
                    "AI response using internal database",
                    "AUTO_RESPONSE_SENT",
                    intent["auto_response_template"],
                    "AI",
                    None,
                    to_ts(trace_time),
                )
            )
            trace_id += 1
            step += 1
            trace_time += timedelta(minutes=1)

            trace_local["satisfaction"] = trace_id
            trace_rows.append(
                (
                    trace_id,
                    ticket_id,
                    step,
                    "Client satisfied?",
                    "YES" if client_satisfied == 1 else "NO",
                    "If not satisfied, route to human owner.",
                    "SYSTEM",
                    None,
                    to_ts(trace_time),
                )
            )
            trace_id += 1
            step += 1
            trace_time += timedelta(minutes=1)

            if client_satisfied == 0 and owner_agent_id is not None:
                trace_local["human"] = trace_id
                trace_rows.append(
                    (
                        trace_id,
                        ticket_id,
                        step,
                        "Suggest best-fit human agent based on specialty, load, and queue risk",
                        f"ROUTE_TO_{owner_agent_code}",
                        "Automated response was not sufficient for client expectation.",
                        "AI",
                        owner_agent_id,
                        to_ts(trace_time),
                    )
                )
                trace_id += 1
        else:
            trace_local["multi"] = trace_id
            trace_rows.append(
                (
                    trace_id,
                    ticket_id,
                    step,
                    "Does this require multiple desks?",
                    "YES" if requires_multi else "NO",
                    "Complexity and routing-rule checks applied.",
                    "AI",
                    None,
                    to_ts(trace_time),
                )
            )
            trace_id += 1
            step += 1
            trace_time += timedelta(minutes=1)

            if requires_multi:
                trace_local["coord"] = trace_id
                trace_rows.append(
                    (
                        trace_id,
                        ticket_id,
                        step,
                        "AI multi-desk workflow coordinator",
                        "PLAN_CREATED",
                        "Coordinator generated desk sequence and checkpoints.",
                        "AI",
                        None,
                        to_ts(trace_time),
                    )
                )
                trace_id += 1
                step += 1
                trace_time += timedelta(minutes=1)

                if owner_agent_id is not None:
                    trace_local["owner"] = trace_id
                    trace_rows.append(
                        (
                            trace_id,
                            ticket_id,
                            step,
                            "Human ticket owner accountable",
                            f"OWNER_ASSIGNED_{owner_agent_code}",
                            "One accountable human owner retained across desk handoffs.",
                            "HUMAN",
                            owner_agent_id,
                            to_ts(trace_time),
                        )
                    )
                    trace_id += 1
            else:
                if owner_agent_id is not None:
                    trace_local["human"] = trace_id
                    trace_rows.append(
                        (
                            trace_id,
                            ticket_id,
                            step,
                            "Suggest best-fit human agent based on specialty, load, and queue risk",
                            f"ROUTE_TO_{owner_agent_code}",
                            "Single-desk non-automatable case.",
                            "AI",
                            owner_agent_id,
                            to_ts(trace_time),
                        )
                    )
                    trace_id += 1

        # Assignments.
        if owner_agent_id is not None:
            assignment_rows.append(
                (
                    assignment_id,
                    ticket_id,
                    owner_agent_id,
                    intent["primary_desk_id"],
                    "PRIMARY_OWNER",
                    "Primary owner assignment from routing decision.",
                    to_ts(created_at + timedelta(minutes=2)),
                    to_ts(resolved_at if status in {"RESOLVED", "CLOSED"} else None),
                )
            )
            assignment_id += 1

        # Desk plan (always at least one step).
        if requires_multi:
            desk_codes = MULTI_DESK_SEQUENCE.get(intent_code, [])
            plan_desks = [desk_code_to_id[c] for c in desk_codes if c in desk_code_to_id]
            if not plan_desks:
                plan_desks = [intent["primary_desk_id"]]
            if plan_desks[0] != intent["primary_desk_id"]:
                plan_desks = [intent["primary_desk_id"]] + [d for d in plan_desks if d != intent["primary_desk_id"]]
        else:
            plan_desks = [intent["primary_desk_id"]]

        for step_seq, desk_id in enumerate(plan_desks, start=1):
            plan_rows.append(
                (
                    plan_step_id,
                    ticket_id,
                    step_seq,
                    desk_id,
                    "Multi-desk planned step" if requires_multi else "Primary-desk handling",
                    1,
                )
            )
            plan_step_id += 1

        # Hops from plan.
        hop_rows.append(
            (
                hop_id,
                ticket_id,
                1,
                None,
                plan_desks[0],
                owner_agent_id,
                "Initial routing assignment",
                to_ts(created_at + timedelta(minutes=2)),
            )
        )
        hop_id += 1

        hop_seq = 2
        hop_time = created_at + timedelta(minutes=12)
        for idx in range(1, len(plan_desks)):
            hop_rows.append(
                (
                    hop_id,
                    ticket_id,
                    hop_seq,
                    plan_desks[idx - 1],
                    plan_desks[idx],
                    owner_agent_id,
                    "AI-coordinated desk transfer",
                    to_ts(hop_time),
                )
            )
            hop_id += 1
            hop_seq += 1
            hop_time += timedelta(minutes=9)

        # Non-multi desk occasional correction bounce.
        if not requires_multi and automatable == 0 and rng.random() < 0.12:
            alt_desk = rng.choice([d[0] for d in DESKS if d[0] != plan_desks[0]])
            hop_rows.append(
                (
                    hop_id,
                    ticket_id,
                    hop_seq,
                    plan_desks[0],
                    alt_desk,
                    owner_agent_id,
                    "Initial misroute correction",
                    to_ts(created_at + timedelta(minutes=22)),
                )
            )
            hop_id += 1
            hop_seq += 1
            hop_rows.append(
                (
                    hop_id,
                    ticket_id,
                    hop_seq,
                    alt_desk,
                    plan_desks[0],
                    owner_agent_id,
                    "Returned to primary desk",
                    to_ts(created_at + timedelta(minutes=31)),
                )
            )
            hop_id += 1

        # Email flow.
        ai_email = "ai-router@mvp.demo"
        support_email = "client-service@mvp.demo"
        owner_email = owner_agent_email or support_email

        message_rows.append(
            (
                message_id,
                ticket_id,
                "INBOUND",
                client["email"],
                support_email,
                subject,
                body,
                to_ts(created_at),
                0,
                "SENT",
                None,
            )
        )
        message_id += 1

        ack_trace = trace_local.get("auto") or trace_local.get("multi") or trace_local.get("step1")
        message_rows.append(
            (
                message_id,
                ticket_id,
                "OUTBOUND",
                ai_email,
                client["email"],
                f"Re: {subject}",
                "Acknowledged. Decision path and routing plan generated.",
                to_ts(first_response_at),
                1,
                "SENT",
                ack_trace,
            )
        )
        message_id += 1

        if owner_agent_id is not None:
            message_rows.append(
                (
                    message_id,
                    ticket_id,
                    "OUTBOUND",
                    owner_email,
                    client["email"],
                    f"Re: {subject}",
                    "Human owner assigned and working on your request.",
                    to_ts(first_response_at + timedelta(minutes=14)),
                    0,
                    "SENT",
                    trace_local.get("owner") or trace_local.get("human"),
                )
            )
            message_id += 1

        if status in {"RESOLVED", "CLOSED"} and resolved_at is not None:
            final_sender = ai_email if automatable == 1 and client_satisfied == 1 else owner_email
            final_trace = trace_local.get("satisfaction") or trace_local.get("owner") or trace_local.get("human")
            message_rows.append(
                (
                    message_id,
                    ticket_id,
                    "OUTBOUND",
                    final_sender,
                    client["email"],
                    f"Re: {subject}",
                    "Resolution delivered. Reply if more support is needed.",
                    to_ts(resolved_at),
                    1 if final_sender == ai_email else 0,
                    "SENT",
                    final_trace,
                )
            )
            message_id += 1

    conn.executemany(
        """
        INSERT INTO tickets (
            ticket_id, ticket_ref, client_id, trade_id, intent_id, requester_email,
            channel, subject, body, priority, automatable, requires_multi_desk, status,
            primary_desk_id, owner_agent_id, created_at, first_response_at,
            resolved_at, closed_at, client_satisfied
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ticket_rows,
    )
    conn.executemany(
        """
        INSERT INTO ticket_assignments (
            assignment_id, ticket_id, assigned_agent_id, assigned_desk_id, assignment_role,
            assignment_reason, assigned_at, released_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        assignment_rows,
    )
    conn.executemany(
        """
        INSERT INTO ticket_desk_plan (
            plan_step_id, ticket_id, step_seq, desk_id, step_reason, required_flag
        ) VALUES (?, ?, ?, ?, ?, ?);
        """,
        plan_rows,
    )
    conn.executemany(
        """
        INSERT INTO ticket_desk_hops (
            hop_id, ticket_id, hop_seq, from_desk_id, to_desk_id, hopped_by_agent_id, hop_reason, hopped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        hop_rows,
    )
    conn.executemany(
        """
        INSERT INTO routing_trace (
            trace_id, ticket_id, step_seq, node_name, decision, rationale,
            actor_type, decided_by_agent_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        trace_rows,
    )
    conn.executemany(
        """
        INSERT INTO email_messages (
            message_id, ticket_id, direction, sender_email, recipient_email, subject, body,
            sent_at, is_automated, delivery_status, related_trace_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        message_rows,
    )


def run_checks(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {}
    for table, expected in TARGET_COUNTS.items():
        actual = int(conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0])
        if actual != expected:
            raise RuntimeError(f"{table} count mismatch: expected {expected}, got {actual}")
        counts[table] = actual

    fk = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if fk:
        raise RuntimeError(f"Foreign key violations found: {fk[:3]}")

    # Every ticket should have trace, desk plan, hop, and at least one message.
    checks = [
        (
            "trace",
            """
            SELECT COUNT(*)
            FROM tickets t
            LEFT JOIN routing_trace rt ON rt.ticket_id = t.ticket_id
            WHERE rt.ticket_id IS NULL;
            """,
        ),
        (
            "plan",
            """
            SELECT COUNT(*)
            FROM tickets t
            LEFT JOIN ticket_desk_plan p ON p.ticket_id = t.ticket_id
            WHERE p.ticket_id IS NULL;
            """,
        ),
        (
            "hop",
            """
            SELECT COUNT(*)
            FROM tickets t
            LEFT JOIN ticket_desk_hops h ON h.ticket_id = t.ticket_id
            WHERE h.ticket_id IS NULL;
            """,
        ),
        (
            "message",
            """
            SELECT COUNT(*)
            FROM tickets t
            LEFT JOIN email_messages m ON m.ticket_id = t.ticket_id
            WHERE m.ticket_id IS NULL;
            """,
        ),
    ]
    for label, sql in checks:
        missing = int(conn.execute(sql).fetchone()[0])
        if missing != 0:
            raise RuntimeError(f"{missing} tickets missing {label} rows.")

    return counts


def write_summary(conn: sqlite3.Connection, counts: dict[str, int]) -> None:
    status_rows = conn.execute(
        "SELECT status, COUNT(*) FROM tickets GROUP BY status ORDER BY COUNT(*) DESC;"
    ).fetchall()
    auto_count = int(conn.execute("SELECT COUNT(*) FROM tickets WHERE automatable = 1;").fetchone()[0])
    multi_count = int(conn.execute("SELECT COUNT(*) FROM tickets WHERE requires_multi_desk = 1;").fetchone()[0])
    hop_rows = int(conn.execute("SELECT COUNT(*) FROM ticket_desk_hops;").fetchone()[0])
    trace_rows = int(conn.execute("SELECT COUNT(*) FROM routing_trace;").fetchone()[0])
    message_rows = int(conn.execute("SELECT COUNT(*) FROM email_messages;").fetchone()[0])

    lines = [
        "# MVP Routing Database Seed Summary",
        "",
        f"- Database: `{DB_PATH}`",
        f"- Seed: `{SEED}`",
        "",
        "## Required Volumes",
        "",
    ]
    for k in ["clients", "cash_accounts", "positions", "trades", "tickets"]:
        lines.append(f"- {k}: **{counts[k]}**")
    lines += [
        "",
        "## Routing Snapshot",
        "",
        f"- Automatable tickets: **{auto_count}**",
        f"- Multi-desk tickets: **{multi_count}**",
        f"- Routing trace rows: **{trace_rows}**",
        f"- Desk hop rows: **{hop_rows}**",
        f"- Email message rows: **{message_rows}**",
        "",
        "## Ticket Status Mix",
        "",
    ]
    lines.extend([f"- {status}: **{cnt}**" for status, cnt in status_rows])
    lines += [
        "",
        "## Integrity",
        "",
        "- Foreign keys: **PASS**",
        "- Every ticket has trace/plan/hop/message rows: **PASS**",
        "",
    ]
    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rng = random.Random(SEED)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        build_schema(conn)
        desk_code_to_id = seed_desks(conn)
        agents, projected_open = seed_agents(conn, rng)
        intents = seed_intents_and_rules(conn)
        clients = seed_clients(conn, rng)
        seed_cash_accounts(conn, rng, clients)
        _, client_symbol_positions = seed_positions(conn, rng, clients)
        trades_by_client = seed_trades(conn, rng, clients, client_symbol_positions)
        seed_tickets_and_ops(
            conn,
            rng,
            clients,
            intents,
            desk_code_to_id,
            agents,
            projected_open,
            trades_by_client,
        )
        counts = run_checks(conn)
        write_summary(conn, counts)
        conn.commit()
    finally:
        conn.close()

    print(f"Database created: {DB_PATH}")
    print(f"Summary created: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
