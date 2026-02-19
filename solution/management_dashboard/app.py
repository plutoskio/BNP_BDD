from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
DEFAULT_DB_PATH = APP_ROOT.parent / "mvp_routing_database" / "mvp_routing.db"

OPEN_STATUSES = ("OPEN", "IN_PROGRESS", "WAITING_CLIENT", "ESCALATED")
TS_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)


def _db_path() -> Path:
    raw = os.getenv("DASHBOARD_DB_PATH", str(DEFAULT_DB_PATH)).strip()
    return Path(raw).expanduser()


def _get_conn() -> sqlite3.Connection:
    db = _db_path()
    if not db.exists():
        raise HTTPException(status_code=500, detail=f"dashboard_db_not_found: {db}")

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None

    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _age_minutes(value: str | None) -> int | None:
    ts = _parse_ts(value)
    if ts is None:
        return None
    now = datetime.now(UTC).replace(tzinfo=None)
    return max(int((now - ts).total_seconds() // 60), 0)


def _to_bool(value: Any) -> bool:
    return bool(int(value)) if value is not None else False


def _row_to_ticket_summary(row: sqlite3.Row) -> dict[str, Any]:
    created_at = row["created_at"]
    last_event_at = row["last_event_at"]
    return {
        "ticket_ref": row["ticket_ref"],
        "status": row["status"],
        "priority": row["priority"],
        "automatable": _to_bool(row["automatable"]),
        "requires_multi_desk": _to_bool(row["requires_multi_desk"]),
        "requester_email": row["requester_email"],
        "subject": row["subject"],
        "created_at": created_at,
        "created_age_min": _age_minutes(created_at),
        "last_event_at": last_event_at,
        "last_event_age_min": _age_minutes(last_event_at),
        "client_name": row["client_name"],
        "intent_code": row["intent_code"],
        "intent_name": row["intent_name"],
        "primary_desk_code": row["primary_desk_code"],
        "primary_desk_name": row["primary_desk_name"],
        "current_desk_code": row["current_desk_code"] or row["primary_desk_code"],
        "current_desk_name": row["current_desk_name"] or row["primary_desk_name"],
        "owner_agent_code": row["owner_agent_code"],
        "owner_agent_name": row["owner_agent_name"],
    }


app = FastAPI(title="BNP Service Management Dashboard", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


@app.get("/")
def dashboard_home() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    db = _db_path()
    return {
        "status": "ok" if db.exists() else "degraded",
        "db_path": str(db),
    }


@app.get("/api/overview")
def api_overview() -> dict[str, Any]:
    with _get_conn() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_tickets,
                SUM(CASE WHEN status IN ('OPEN','IN_PROGRESS','WAITING_CLIENT','ESCALATED') THEN 1 ELSE 0 END) AS active_tickets,
                SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_tickets,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) AS closed_tickets,
                SUM(CASE WHEN automatable = 1 THEN 1 ELSE 0 END) AS automatable_tickets,
                SUM(CASE WHEN requires_multi_desk = 1 THEN 1 ELSE 0 END) AS multi_desk_tickets,
                SUM(
                    CASE
                        WHEN status IN ('OPEN','IN_PROGRESS','WAITING_CLIENT','ESCALATED')
                         AND created_at <= datetime('now','-1 day')
                        THEN 1 ELSE 0
                    END
                ) AS active_over_24h,
                AVG(
                    CASE
                        WHEN first_response_at IS NOT NULL
                        THEN (julianday(first_response_at) - julianday(created_at)) * 24.0 * 60.0
                    END
                ) AS avg_first_response_min,
                AVG(
                    CASE
                        WHEN resolved_at IS NOT NULL
                        THEN (julianday(resolved_at) - julianday(created_at)) * 24.0
                    END
                ) AS avg_resolution_hours
            FROM tickets;
            """
        ).fetchone()

        inbound_recent = conn.execute(
            """
            SELECT COUNT(*) AS inbound_last_15m
            FROM email_messages
            WHERE direction = 'INBOUND'
              AND sent_at >= datetime('now','-15 minutes');
            """
        ).fetchone()

    total_tickets = int(totals["total_tickets"] or 0)
    automatable_tickets = int(totals["automatable_tickets"] or 0)
    return {
        "total_tickets": total_tickets,
        "active_tickets": int(totals["active_tickets"] or 0),
        "resolved_tickets": int(totals["resolved_tickets"] or 0),
        "closed_tickets": int(totals["closed_tickets"] or 0),
        "automatable_tickets": automatable_tickets,
        "automatable_rate_pct": round((automatable_tickets / total_tickets * 100.0), 1) if total_tickets else 0.0,
        "multi_desk_tickets": int(totals["multi_desk_tickets"] or 0),
        "active_over_24h": int(totals["active_over_24h"] or 0),
        "avg_first_response_min": round(float(totals["avg_first_response_min"] or 0.0), 1),
        "avg_resolution_hours": round(float(totals["avg_resolution_hours"] or 0.0), 2),
        "inbound_last_15m": int(inbound_recent["inbound_last_15m"] or 0),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


@app.get("/api/tickets")
def api_tickets(
    limit: int = 200,
    status: str | None = None,
    desk: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_500")

    clauses: list[str] = []
    params: list[Any] = []

    if status:
        clauses.append("t.status = ?")
        params.append(status.strip().upper())

    if desk:
        clauses.append("COALESCE(cd.desk_code, pd.desk_code) = ?")
        params.append(desk.strip().upper())

    if query:
        q = f"%{query.strip().lower()}%"
        clauses.append(
            "(" 
            "lower(t.ticket_ref) LIKE ? OR "
            "lower(t.requester_email) LIKE ? OR "
            "lower(c.client_name) LIKE ? OR "
            "lower(t.subject) LIKE ? OR "
            "lower(i.intent_code) LIKE ?"
            ")"
        )
        params.extend([q, q, q, q, q])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sql = f"""
    WITH last_hop AS (
        SELECT h.ticket_id, h.to_desk_id
        FROM ticket_desk_hops h
        JOIN (
            SELECT ticket_id, MAX(hop_seq) AS max_hop_seq
            FROM ticket_desk_hops
            GROUP BY ticket_id
        ) x ON x.ticket_id = h.ticket_id AND x.max_hop_seq = h.hop_seq
    ),
    latest_event AS (
        SELECT ticket_id, MAX(event_at) AS last_event_at
        FROM (
            SELECT ticket_id, created_at AS event_at FROM tickets
            UNION ALL
            SELECT ticket_id, created_at AS event_at FROM routing_trace
            UNION ALL
            SELECT ticket_id, sent_at AS event_at FROM email_messages
        ) e
        GROUP BY ticket_id
    )
    SELECT
        t.ticket_ref,
        t.status,
        t.priority,
        t.automatable,
        t.requires_multi_desk,
        t.requester_email,
        t.subject,
        t.created_at,
        le.last_event_at,
        c.client_name,
        i.intent_code,
        i.intent_name,
        pd.desk_code AS primary_desk_code,
        pd.desk_name AS primary_desk_name,
        cd.desk_code AS current_desk_code,
        cd.desk_name AS current_desk_name,
        a.agent_code AS owner_agent_code,
        a.full_name AS owner_agent_name
    FROM tickets t
    JOIN clients c ON c.client_id = t.client_id
    JOIN intents i ON i.intent_id = t.intent_id
    JOIN desks pd ON pd.desk_id = t.primary_desk_id
    LEFT JOIN last_hop lh ON lh.ticket_id = t.ticket_id
    LEFT JOIN desks cd ON cd.desk_id = lh.to_desk_id
    LEFT JOIN agents a ON a.agent_id = t.owner_agent_id
    LEFT JOIN latest_event le ON le.ticket_id = t.ticket_id
    {where_sql}
    ORDER BY t.ticket_id DESC
    LIMIT ?;
    """

    params.append(limit)

    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    tickets = [_row_to_ticket_summary(row) for row in rows]
    return {
        "count": len(tickets),
        "tickets": tickets,
    }


@app.get("/api/desks/summary")
def api_desks_summary() -> dict[str, Any]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            WITH last_hop AS (
                SELECT h.ticket_id, h.to_desk_id
                FROM ticket_desk_hops h
                JOIN (
                    SELECT ticket_id, MAX(hop_seq) AS max_hop_seq
                    FROM ticket_desk_hops
                    GROUP BY ticket_id
                ) x ON x.ticket_id = h.ticket_id AND x.max_hop_seq = h.hop_seq
            ),
            ticket_desk AS (
                SELECT
                    t.ticket_id,
                    COALESCE(lh.to_desk_id, t.primary_desk_id) AS desk_id,
                    t.status,
                    t.requires_multi_desk,
                    t.created_at
                FROM tickets t
                LEFT JOIN last_hop lh ON lh.ticket_id = t.ticket_id
            ),
            desk_ticket_stats AS (
                SELECT
                    desk_id,
                    COUNT(*) AS total_tickets,
                    SUM(CASE WHEN status IN ('OPEN','IN_PROGRESS','WAITING_CLIENT','ESCALATED') THEN 1 ELSE 0 END) AS active_tickets,
                    SUM(CASE WHEN status = 'ESCALATED' THEN 1 ELSE 0 END) AS escalated_tickets,
                    SUM(CASE WHEN status IN ('OPEN','IN_PROGRESS','WAITING_CLIENT','ESCALATED') AND requires_multi_desk = 1 THEN 1 ELSE 0 END) AS active_multi_desk,
                    AVG(
                        CASE WHEN status IN ('OPEN','IN_PROGRESS','WAITING_CLIENT','ESCALATED')
                        THEN (julianday('now') - julianday(created_at)) * 24.0 END
                    ) AS avg_active_age_hours
                FROM ticket_desk
                GROUP BY desk_id
            ),
            desk_agent_stats AS (
                SELECT desk_id, COUNT(*) AS active_agents
                FROM agents
                WHERE is_active = 1
                GROUP BY desk_id
            )
            SELECT
                d.desk_code,
                d.desk_name,
                d.specialty,
                COALESCE(ts.total_tickets, 0) AS total_tickets,
                COALESCE(ts.active_tickets, 0) AS active_tickets,
                COALESCE(ts.escalated_tickets, 0) AS escalated_tickets,
                COALESCE(ts.active_multi_desk, 0) AS active_multi_desk,
                COALESCE(ts.avg_active_age_hours, 0.0) AS avg_active_age_hours,
                COALESCE(ags.active_agents, 0) AS active_agents
            FROM desks d
            LEFT JOIN desk_ticket_stats ts ON ts.desk_id = d.desk_id
            LEFT JOIN desk_agent_stats ags ON ags.desk_id = d.desk_id
            ORDER BY d.desk_id;
            """
        ).fetchall()

    payload: list[dict[str, Any]] = []
    for row in rows:
        payload.append(
            {
                "desk_code": row["desk_code"],
                "desk_name": row["desk_name"],
                "specialty": row["specialty"],
                "total_tickets": int(row["total_tickets"] or 0),
                "active_tickets": int(row["active_tickets"] or 0),
                "escalated_tickets": int(row["escalated_tickets"] or 0),
                "active_multi_desk": int(row["active_multi_desk"] or 0),
                "avg_active_age_hours": round(float(row["avg_active_age_hours"] or 0.0), 2),
                "active_agents": int(row["active_agents"] or 0),
            }
        )

    return {"desks": payload}


@app.get("/api/agents/load")
def api_agents_load() -> dict[str, Any]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                v.agent_code,
                v.full_name,
                v.desk_code,
                d.desk_name,
                v.specialty,
                v.open_ticket_count,
                v.max_open_tickets,
                v.available_slots,
                v.load_ratio,
                v.is_active
            FROM v_agent_open_load v
            JOIN desks d ON d.desk_id = v.desk_id
            ORDER BY v.load_ratio DESC, v.open_ticket_count DESC, v.agent_code ASC;
            """
        ).fetchall()

    agents: list[dict[str, Any]] = []
    for row in rows:
        agents.append(
            {
                "agent_code": row["agent_code"],
                "full_name": row["full_name"],
                "desk_code": row["desk_code"],
                "desk_name": row["desk_name"],
                "specialty": row["specialty"],
                "open_ticket_count": int(row["open_ticket_count"] or 0),
                "max_open_tickets": int(row["max_open_tickets"] or 0),
                "available_slots": int(row["available_slots"] or 0),
                "load_ratio": float(row["load_ratio"] or 0.0),
                "is_active": _to_bool(row["is_active"]),
            }
        )

    return {"agents": agents}


@app.get("/api/events/recent")
def api_recent_events(limit: int = 20) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_100")

    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                em.sent_at,
                em.direction,
                em.sender_email,
                em.recipient_email,
                em.subject,
                em.delivery_status,
                t.ticket_ref,
                t.status AS ticket_status
            FROM email_messages em
            JOIN tickets t ON t.ticket_id = em.ticket_id
            ORDER BY em.message_id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "sent_at": row["sent_at"],
                "direction": row["direction"],
                "sender_email": row["sender_email"],
                "recipient_email": row["recipient_email"],
                "subject": row["subject"],
                "delivery_status": row["delivery_status"],
                "ticket_ref": row["ticket_ref"],
                "ticket_status": row["ticket_status"],
            }
        )

    return {"events": events}


@app.get("/api/tickets/{ticket_ref}")
def api_ticket_detail(ticket_ref: str) -> dict[str, Any]:
    ref = ticket_ref.strip().upper()
    with _get_conn() as conn:
        ticket = conn.execute(
            """
            WITH last_hop AS (
                SELECT h.ticket_id, h.to_desk_id
                FROM ticket_desk_hops h
                JOIN (
                    SELECT ticket_id, MAX(hop_seq) AS max_hop_seq
                    FROM ticket_desk_hops
                    GROUP BY ticket_id
                ) x ON x.ticket_id = h.ticket_id AND x.max_hop_seq = h.hop_seq
            )
            SELECT
                t.ticket_id,
                t.ticket_ref,
                t.status,
                t.priority,
                t.automatable,
                t.requires_multi_desk,
                t.requester_email,
                t.subject,
                t.body,
                t.channel,
                t.created_at,
                t.first_response_at,
                t.resolved_at,
                t.closed_at,
                c.client_code,
                c.client_name,
                i.intent_code,
                i.intent_name,
                pd.desk_code AS primary_desk_code,
                pd.desk_name AS primary_desk_name,
                cd.desk_code AS current_desk_code,
                cd.desk_name AS current_desk_name,
                a.agent_code AS owner_agent_code,
                a.full_name AS owner_agent_name,
                a.email AS owner_agent_email
            FROM tickets t
            JOIN clients c ON c.client_id = t.client_id
            JOIN intents i ON i.intent_id = t.intent_id
            JOIN desks pd ON pd.desk_id = t.primary_desk_id
            LEFT JOIN last_hop lh ON lh.ticket_id = t.ticket_id
            LEFT JOIN desks cd ON cd.desk_id = lh.to_desk_id
            LEFT JOIN agents a ON a.agent_id = t.owner_agent_id
            WHERE t.ticket_ref = ?
            LIMIT 1;
            """,
            (ref,),
        ).fetchone()

        if ticket is None:
            raise HTTPException(status_code=404, detail="ticket_not_found")

        trace_rows = conn.execute(
            """
            SELECT
                rt.step_seq,
                rt.node_name,
                rt.decision,
                rt.rationale,
                rt.actor_type,
                rt.created_at,
                a.agent_code,
                a.full_name
            FROM routing_trace rt
            LEFT JOIN agents a ON a.agent_id = rt.decided_by_agent_id
            WHERE rt.ticket_id = ?
            ORDER BY rt.step_seq;
            """,
            (int(ticket["ticket_id"]),),
        ).fetchall()

        plan_rows = conn.execute(
            """
            SELECT
                p.step_seq,
                d.desk_code,
                d.desk_name,
                p.step_reason,
                p.required_flag
            FROM ticket_desk_plan p
            JOIN desks d ON d.desk_id = p.desk_id
            WHERE p.ticket_id = ?
            ORDER BY p.step_seq;
            """,
            (int(ticket["ticket_id"]),),
        ).fetchall()

        hop_rows = conn.execute(
            """
            SELECT
                h.hop_seq,
                df.desk_code AS from_desk_code,
                df.desk_name AS from_desk_name,
                dt.desk_code AS to_desk_code,
                dt.desk_name AS to_desk_name,
                h.hop_reason,
                h.hopped_at,
                a.agent_code,
                a.full_name
            FROM ticket_desk_hops h
            LEFT JOIN desks df ON df.desk_id = h.from_desk_id
            JOIN desks dt ON dt.desk_id = h.to_desk_id
            LEFT JOIN agents a ON a.agent_id = h.hopped_by_agent_id
            WHERE h.ticket_id = ?
            ORDER BY h.hop_seq;
            """,
            (int(ticket["ticket_id"]),),
        ).fetchall()

        assignment_rows = conn.execute(
            """
            SELECT
                ta.assignment_role,
                ta.assignment_reason,
                ta.assigned_at,
                ta.released_at,
                a.agent_code,
                a.full_name,
                a.email,
                d.desk_code,
                d.desk_name
            FROM ticket_assignments ta
            JOIN agents a ON a.agent_id = ta.assigned_agent_id
            JOIN desks d ON d.desk_id = ta.assigned_desk_id
            WHERE ta.ticket_id = ?
            ORDER BY ta.assigned_at DESC;
            """,
            (int(ticket["ticket_id"]),),
        ).fetchall()

        message_rows = conn.execute(
            """
            SELECT
                message_id,
                direction,
                sender_email,
                recipient_email,
                subject,
                body,
                sent_at,
                is_automated,
                delivery_status
            FROM email_messages
            WHERE ticket_id = ?
            ORDER BY message_id ASC;
            """,
            (int(ticket["ticket_id"]),),
        ).fetchall()

    ticket_payload = {
        "ticket_ref": ticket["ticket_ref"],
        "status": ticket["status"],
        "priority": ticket["priority"],
        "automatable": _to_bool(ticket["automatable"]),
        "requires_multi_desk": _to_bool(ticket["requires_multi_desk"]),
        "requester_email": ticket["requester_email"],
        "subject": ticket["subject"],
        "body": ticket["body"],
        "channel": ticket["channel"],
        "created_at": ticket["created_at"],
        "first_response_at": ticket["first_response_at"],
        "resolved_at": ticket["resolved_at"],
        "closed_at": ticket["closed_at"],
        "client_code": ticket["client_code"],
        "client_name": ticket["client_name"],
        "intent_code": ticket["intent_code"],
        "intent_name": ticket["intent_name"],
        "primary_desk_code": ticket["primary_desk_code"],
        "primary_desk_name": ticket["primary_desk_name"],
        "current_desk_code": ticket["current_desk_code"] or ticket["primary_desk_code"],
        "current_desk_name": ticket["current_desk_name"] or ticket["primary_desk_name"],
        "owner_agent_code": ticket["owner_agent_code"],
        "owner_agent_name": ticket["owner_agent_name"],
        "owner_agent_email": ticket["owner_agent_email"],
        "age_minutes": _age_minutes(ticket["created_at"]),
    }

    traces = [
        {
            "step_seq": int(row["step_seq"]),
            "node_name": row["node_name"],
            "decision": row["decision"],
            "rationale": row["rationale"],
            "actor_type": row["actor_type"],
            "agent_code": row["agent_code"],
            "agent_name": row["full_name"],
            "created_at": row["created_at"],
        }
        for row in trace_rows
    ]

    plans = [
        {
            "step_seq": int(row["step_seq"]),
            "desk_code": row["desk_code"],
            "desk_name": row["desk_name"],
            "step_reason": row["step_reason"],
            "required": _to_bool(row["required_flag"]),
        }
        for row in plan_rows
    ]

    hops = [
        {
            "hop_seq": int(row["hop_seq"]),
            "from_desk_code": row["from_desk_code"],
            "from_desk_name": row["from_desk_name"],
            "to_desk_code": row["to_desk_code"],
            "to_desk_name": row["to_desk_name"],
            "hop_reason": row["hop_reason"],
            "hopped_at": row["hopped_at"],
            "agent_code": row["agent_code"],
            "agent_name": row["full_name"],
        }
        for row in hop_rows
    ]

    assignments = [
        {
            "assignment_role": row["assignment_role"],
            "assignment_reason": row["assignment_reason"],
            "assigned_at": row["assigned_at"],
            "released_at": row["released_at"],
            "agent_code": row["agent_code"],
            "agent_name": row["full_name"],
            "agent_email": row["email"],
            "desk_code": row["desk_code"],
            "desk_name": row["desk_name"],
        }
        for row in assignment_rows
    ]

    messages = [
        {
            "message_id": int(row["message_id"]),
            "direction": row["direction"],
            "sender_email": row["sender_email"],
            "recipient_email": row["recipient_email"],
            "subject": row["subject"],
            "body": row["body"],
            "sent_at": row["sent_at"],
            "is_automated": _to_bool(row["is_automated"]),
            "delivery_status": row["delivery_status"],
        }
        for row in message_rows
    ]

    return {
        "ticket": ticket_payload,
        "routing_trace": traces,
        "desk_plan": plans,
        "desk_hops": hops,
        "assignments": assignments,
        "messages": messages,
    }
