from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from .classifier import IntentClassifier
from .config import Settings
from .models import InboundMessage, IntentClassification, RoutingOutput


TRADE_REF_RE = re.compile(r"\bTRD\d{6}\b", re.IGNORECASE)
TICKET_REF_RE = re.compile(r"\bTCK\d{6}\b", re.IGNORECASE)

MULTI_DESK_SEQUENCE: dict[str, list[str]] = {
    "failed_trade_investigation": ["TRD", "SET", "CASH"],
    "account_closure_request": ["ACCT", "CMP", "CASH"],
    "sanctions_review_query": ["CMP", "TRD", "CS"],
    "corporate_action_instruction": ["CA", "SET", "TRD"],
}


class RoutingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._classifier = IntentClassifier(
            model=settings.model,
            reasoning_effort=settings.reasoning_effort,
            prompt_path=settings.prompt_path,
            has_api_key=bool(settings.openai_api_key),
        )

    def process_inbound(self, payload: InboundMessage) -> RoutingOutput:
        with self._get_conn(self._settings.db_path) as conn:
            client = self._resolve_client(conn, payload.from_email)
            if client is None:
                return RoutingOutput(
                    ok=False,
                    error="unknown_client",
                    to_email=payload.from_email,
                    reply_subject=f"Re: {payload.subject}",
                    reply_body=(
                        "We could not match your sender email to a client profile. "
                        "Please provide your client code so we can route your request."
                    ),
                )

            escalated = self._handle_not_resolved_reply(conn, payload, client)
            if escalated is not None:
                return escalated

            classification = self._classifier.classify(payload.subject, payload.body)
            return self._create_ticket_and_route(conn, payload, client, classification)

    def get_ticket_status(self, ticket_ref: str) -> dict[str, Any] | None:
        with self._get_conn(self._settings.db_path) as conn:
            ticket = conn.execute(
                """
                SELECT
                    t.ticket_id,
                    t.ticket_ref,
                    t.status,
                    t.automatable,
                    t.requires_multi_desk,
                    t.priority,
                    t.requester_email,
                    a.agent_code AS owner_agent_code,
                    a.email AS owner_agent_email,
                    t.created_at,
                    t.first_response_at,
                    t.resolved_at,
                    t.closed_at
                FROM tickets t
                LEFT JOIN agents a ON a.agent_id = t.owner_agent_id
                WHERE t.ticket_ref = ?
                LIMIT 1;
                """,
                (ticket_ref,),
            ).fetchone()
            if ticket is None:
                return None

            path_rows = conn.execute(
                """
                SELECT step_seq, node_name, decision, actor_type, created_at
                FROM v_ticket_decision_path
                WHERE ticket_ref = ?
                ORDER BY step_seq;
                """,
                (ticket_ref,),
            ).fetchall()

            return {
                "ticket": dict(ticket),
                "decision_path": [dict(row) for row in path_rows],
            }

    @staticmethod
    def _get_conn(db_path: Path) -> sqlite3.Connection:
        if not db_path.exists():
            raise FileNotFoundError(f"DB not found: {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    @staticmethod
    def _now_ts() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None, microsecond=0)

    @staticmethod
    def _to_ts(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _resolve_client(conn: sqlite3.Connection, from_email: str) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT client_id, client_code, client_name, email
            FROM clients
            WHERE lower(email) = lower(?);
            """,
            (from_email,),
        ).fetchone()

    @staticmethod
    def _load_intent_rule(conn: sqlite3.Connection, intent_code: str) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT
                i.intent_id,
                i.intent_code,
                i.intent_name,
                rr.data_direct_available,
                rr.default_multi_desk,
                rr.primary_desk_id,
                rr.auto_response_template
            FROM intents i
            JOIN routing_rules rr ON rr.intent_id = i.intent_id
            WHERE i.intent_code = ?;
            """,
            (intent_code,),
        ).fetchone()

        if row is not None:
            return row

        fallback = conn.execute(
            """
            SELECT
                i.intent_id,
                i.intent_code,
                i.intent_name,
                rr.data_direct_available,
                rr.default_multi_desk,
                rr.primary_desk_id,
                rr.auto_response_template
            FROM intents i
            JOIN routing_rules rr ON rr.intent_id = i.intent_id
            WHERE i.intent_code = 'fee_dispute';
            """
        ).fetchone()

        if fallback is None:
            raise RuntimeError("Intent routing rules missing in database.")
        return fallback

    @staticmethod
    def _extract_trade_ref(subject: str, body: str) -> str | None:
        text = f"{subject} {body}"
        match = TRADE_REF_RE.search(text)
        return match.group(0).upper() if match else None

    def _fetch_direct_data(
        self,
        conn: sqlite3.Connection,
        client_id: int,
        intent_code: str,
        subject: str,
        body: str,
    ) -> tuple[bool, str, int | None]:
        if intent_code == "cash_balance":
            rows = conn.execute(
                """
                SELECT account_number, currency, cash_balance, available_cash, held_cash
                FROM cash_accounts
                WHERE client_id = ?
                ORDER BY cash_balance DESC;
                """,
                (client_id,),
            ).fetchall()
            if not rows:
                return False, "No cash account found for this client.", None

            lines = ["Cash account snapshot:"]
            for row in rows[:4]:
                lines.append(
                    f"- {row['account_number']} ({row['currency']}): balance={row['cash_balance']:.2f}, "
                    f"available={row['available_cash']:.2f}, held={row['held_cash']:.2f}"
                )
            return True, "\n".join(lines), None

        if intent_code == "position_summary":
            rows = conn.execute(
                """
                SELECT symbol, asset_class, quantity, market_price, market_value, as_of_date
                FROM positions
                WHERE client_id = ?
                ORDER BY market_value DESC
                LIMIT 5;
                """,
                (client_id,),
            ).fetchall()
            if not rows:
                return False, "No positions found for this client.", None

            lines = ["Top positions by market value:"]
            for row in rows:
                lines.append(
                    f"- {row['symbol']} ({row['asset_class']}): qty={row['quantity']:.2f}, "
                    f"px={row['market_price']:.4f}, mv={row['market_value']:.2f} (as of {row['as_of_date']})"
                )
            return True, "\n".join(lines), None

        if intent_code in {"trade_status", "settlement_eta"}:
            trade_ref = self._extract_trade_ref(subject, body)
            if trade_ref:
                row = conn.execute(
                    """
                    SELECT
                        trade_id,
                        trade_ref,
                        symbol,
                        side,
                        quantity,
                        price,
                        trade_status,
                        fail_reason,
                        submitted_at,
                        confirmed_at,
                        executed_at,
                        settlement_date
                    FROM trades
                    WHERE client_id = ?
                      AND upper(trade_ref) = upper(?)
                    LIMIT 1;
                    """,
                    (client_id, trade_ref),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT
                        trade_id,
                        trade_ref,
                        symbol,
                        side,
                        quantity,
                        price,
                        trade_status,
                        fail_reason,
                        submitted_at,
                        confirmed_at,
                        executed_at,
                        settlement_date
                    FROM trades
                    WHERE client_id = ?
                    ORDER BY submitted_at DESC, trade_id DESC
                    LIMIT 1;
                    """,
                    (client_id,),
                ).fetchone()

            if row is None:
                return False, "No trade found for this client.", None

            lines = [
                f"Trade {row['trade_ref']} ({row['symbol']} {row['side']}) status: {row['trade_status']}",
                f"- qty={row['quantity']:.2f}, price={row['price']:.4f}, submitted_at={row['submitted_at']}",
            ]
            if row["confirmed_at"]:
                lines.append(f"- confirmed_at={row['confirmed_at']}")
            if row["executed_at"]:
                lines.append(f"- executed_at={row['executed_at']}")
            if row["settlement_date"]:
                lines.append(f"- settlement_date={row['settlement_date']}")
            if row["fail_reason"]:
                lines.append(f"- fail_reason={row['fail_reason']}")

            return True, "\n".join(lines), int(row["trade_id"])

        return False, "Direct data retrieval is not configured for this intent.", None

    @staticmethod
    def _best_owner_agent(conn: sqlite3.Connection, primary_desk_id: int) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT
                l.agent_id,
                l.agent_code,
                l.full_name,
                a.email,
                l.desk_id,
                l.desk_code,
                l.load_ratio,
                l.available_slots
            FROM v_agent_open_load l
            JOIN agents a ON a.agent_id = l.agent_id
            WHERE l.is_active = 1
              AND l.desk_id = ?
            ORDER BY l.load_ratio ASC, l.available_slots DESC, l.agent_id ASC
            LIMIT 1;
            """,
            (primary_desk_id,),
        ).fetchone()

        if row is not None:
            return row

        fallback = conn.execute(
            """
            SELECT
                l.agent_id,
                l.agent_code,
                l.full_name,
                a.email,
                l.desk_id,
                l.desk_code,
                l.load_ratio,
                l.available_slots
            FROM v_agent_open_load l
            JOIN agents a ON a.agent_id = l.agent_id
            WHERE l.is_active = 1
            ORDER BY l.load_ratio ASC, l.available_slots DESC, l.agent_id ASC
            LIMIT 1;
            """
        ).fetchone()

        if fallback is None:
            raise RuntimeError("No active agent available.")
        return fallback

    @staticmethod
    def _desk_code_map(conn: sqlite3.Connection) -> dict[str, int]:
        rows = conn.execute("SELECT desk_id, desk_code FROM desks;").fetchall()
        return {str(row["desk_code"]): int(row["desk_id"]) for row in rows}

    def _insert_trace(
        self,
        conn: sqlite3.Connection,
        ticket_id: int,
        node_name: str,
        decision: str,
        rationale: str,
        actor_type: str,
        created_at: datetime,
        decided_by_agent_id: int | None = None,
    ) -> int:
        step_seq = int(
            conn.execute(
                "SELECT COALESCE(MAX(step_seq), 0) + 1 FROM routing_trace WHERE ticket_id = ?;",
                (ticket_id,),
            ).fetchone()[0]
        )

        cur = conn.execute(
            """
            INSERT INTO routing_trace (
                ticket_id,
                step_seq,
                node_name,
                decision,
                rationale,
                actor_type,
                decided_by_agent_id,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ticket_id,
                step_seq,
                node_name,
                decision,
                rationale,
                actor_type,
                decided_by_agent_id,
                self._to_ts(created_at),
            ),
        )
        return int(cur.lastrowid)

    def _insert_email_message(
        self,
        conn: sqlite3.Connection,
        ticket_id: int,
        direction: str,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
        sent_at: datetime,
        is_automated: int,
        related_trace_id: int | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO email_messages (
                ticket_id,
                direction,
                sender_email,
                recipient_email,
                subject,
                body,
                sent_at,
                is_automated,
                delivery_status,
                related_trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SENT', ?);
            """,
            (
                ticket_id,
                direction,
                sender_email,
                recipient_email,
                subject,
                body,
                self._to_ts(sent_at),
                is_automated,
                related_trace_id,
            ),
        )

    def _create_ticket_and_route(
        self,
        conn: sqlite3.Connection,
        payload: InboundMessage,
        client: sqlite3.Row,
        classification: IntentClassification,
    ) -> RoutingOutput:
        created = self._now_ts()
        intent_code = classification.intent_code

        if classification.confidence < 0.65:
            intent_code = "fee_dispute"
            classification.objective_request = False
            classification.requires_multi_desk_hint = True

        rule = self._load_intent_rule(conn, intent_code)

        automatable_candidate = bool(rule["data_direct_available"]) and classification.objective_request
        requires_multi_candidate = (
            False
            if automatable_candidate
            else bool(rule["default_multi_desk"]) or classification.requires_multi_desk_hint
        )

        priority = classification.priority
        if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            priority = "MEDIUM"

        data_ok = False
        data_text = ""
        trade_id: int | None = None
        if automatable_candidate:
            data_ok, data_text, trade_id = self._fetch_direct_data(
                conn,
                int(client["client_id"]),
                str(rule["intent_code"]),
                payload.subject,
                payload.body,
            )

        automatable_final = 1 if (automatable_candidate and data_ok) else 0
        requires_multi_final = 0 if automatable_final == 1 else int(requires_multi_candidate)

        owner_agent = None
        owner_agent_id: int | None = None
        owner_agent_code: str | None = None
        owner_email: str | None = None

        if automatable_final == 0:
            owner_agent = self._best_owner_agent(conn, int(rule["primary_desk_id"]))
            owner_agent_id = int(owner_agent["agent_id"])
            owner_agent_code = str(owner_agent["agent_code"])
            owner_email = str(owner_agent["email"])

        if automatable_final == 1:
            status = "RESOLVED"
            resolved_at = created + timedelta(minutes=15)
            client_satisfied = 1
            first_response_at = created + timedelta(minutes=8)
        else:
            status = "ESCALATED" if (requires_multi_final == 1 and priority in {"HIGH", "CRITICAL"}) else "IN_PROGRESS"
            resolved_at = None
            client_satisfied = None
            first_response_at = created + timedelta(minutes=30)

        tmp_ref = f"TMP-{uuid4().hex[:12].upper()}"
        cur = conn.execute(
            """
            INSERT INTO tickets (
                ticket_ref,
                client_id,
                trade_id,
                intent_id,
                requester_email,
                channel,
                subject,
                body,
                priority,
                automatable,
                requires_multi_desk,
                status,
                primary_desk_id,
                owner_agent_id,
                created_at,
                first_response_at,
                resolved_at,
                closed_at,
                client_satisfied
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?);
            """,
            (
                tmp_ref,
                int(client["client_id"]),
                trade_id,
                int(rule["intent_id"]),
                payload.from_email,
                payload.channel,
                payload.subject,
                payload.body,
                priority,
                automatable_final,
                requires_multi_final,
                status,
                int(rule["primary_desk_id"]),
                owner_agent_id,
                self._to_ts(created),
                self._to_ts(first_response_at),
                self._to_ts(resolved_at),
                client_satisfied,
            ),
        )

        ticket_id = int(cur.lastrowid)
        ticket_ref = f"TCK{ticket_id:06d}"
        conn.execute("UPDATE tickets SET ticket_ref = ? WHERE ticket_id = ?;", (ticket_ref, ticket_id))

        if owner_agent_id is not None:
            conn.execute(
                """
                INSERT INTO ticket_assignments (
                    ticket_id,
                    assigned_agent_id,
                    assigned_desk_id,
                    assignment_role,
                    assignment_reason,
                    assigned_at,
                    released_at
                ) VALUES (?, ?, ?, 'PRIMARY_OWNER', ?, ?, ?);
                """,
                (
                    ticket_id,
                    owner_agent_id,
                    int(rule["primary_desk_id"]),
                    "Assigned by AI routing based on specialty and workload.",
                    self._to_ts(created + timedelta(minutes=2)),
                    self._to_ts(resolved_at) if resolved_at else None,
                ),
            )

        trace_time = created + timedelta(minutes=1)
        self._insert_trace(
            conn,
            ticket_id,
            "Data directly available without interpretation?",
            "YES" if automatable_final == 1 else "NO",
            "Routing rule + objective check + data availability verification.",
            "AI",
            trace_time,
        )
        trace_time += timedelta(minutes=1)

        decision_path: list[str] = []
        related_trace_id: int | None = None

        if automatable_final == 1:
            trace_auto = self._insert_trace(
                conn,
                ticket_id,
                "AI response using internal database",
                "AUTO_RESPONSE_SENT",
                str(rule["auto_response_template"]),
                "AI",
                trace_time,
            )
            trace_time += timedelta(minutes=1)
            self._insert_trace(
                conn,
                ticket_id,
                "Client satisfied?",
                "YES",
                "Initial response delivered with direct objective data.",
                "SYSTEM",
                trace_time,
            )

            related_trace_id = trace_auto
            decision_path = [
                "1) Data directly available: YES",
                "2) AI response using internal database: SENT",
                "3) Client satisfied: assumed YES (initial request)",
            ]
            response_body = (
                f"Hello {client['client_name']},\n\n"
                f"{data_text}\n\n"
                "Decision Path:\n"
                + "\n".join(decision_path)
                + f"\n\nTicket Reference: {ticket_ref}\n"
                "If this does not resolve your request, reply with NOT RESOLVED."
            )
        else:
            self._insert_trace(
                conn,
                ticket_id,
                "Does this require multiple desks?",
                "YES" if requires_multi_final == 1 else "NO",
                "Intent complexity and routing hints applied.",
                "AI",
                trace_time,
            )
            trace_time += timedelta(minutes=1)

            if requires_multi_final == 1:
                trace_coord = self._insert_trace(
                    conn,
                    ticket_id,
                    "AI multi-desk workflow coordinator",
                    "PLAN_CREATED",
                    "Created desk sequence and handoff plan.",
                    "AI",
                    trace_time,
                )
                trace_time += timedelta(minutes=1)
                self._insert_trace(
                    conn,
                    ticket_id,
                    "Human ticket owner accountable",
                    f"OWNER_ASSIGNED_{owner_agent_code}",
                    "One human owner remains accountable across desks.",
                    "HUMAN",
                    trace_time,
                    owner_agent_id,
                )

                code_map = self._desk_code_map(conn)
                sequence_codes = MULTI_DESK_SEQUENCE.get(str(rule["intent_code"]), [])
                sequence_ids = [code_map[code] for code in sequence_codes if code in code_map]
                if not sequence_ids:
                    sequence_ids = [int(rule["primary_desk_id"])]
                if sequence_ids[0] != int(rule["primary_desk_id"]):
                    sequence_ids = [int(rule["primary_desk_id"])] + [
                        desk_id for desk_id in sequence_ids if desk_id != int(rule["primary_desk_id"])
                    ]

                for idx, desk_id in enumerate(sequence_ids, start=1):
                    conn.execute(
                        """
                        INSERT INTO ticket_desk_plan (ticket_id, step_seq, desk_id, step_reason, required_flag)
                        VALUES (?, ?, ?, ?, 1);
                        """,
                        (ticket_id, idx, desk_id, "AI-generated multi-desk plan step"),
                    )

                hop_time = created + timedelta(minutes=2)
                conn.execute(
                    """
                    INSERT INTO ticket_desk_hops (
                        ticket_id,
                        hop_seq,
                        from_desk_id,
                        to_desk_id,
                        hopped_by_agent_id,
                        hop_reason,
                        hopped_at
                    ) VALUES (?, 1, NULL, ?, ?, 'Initial routing assignment', ?);
                    """,
                    (ticket_id, sequence_ids[0], owner_agent_id, self._to_ts(hop_time)),
                )

                for idx in range(1, len(sequence_ids)):
                    hop_time += timedelta(hours=1)
                    conn.execute(
                        """
                        INSERT INTO ticket_desk_hops (
                            ticket_id,
                            hop_seq,
                            from_desk_id,
                            to_desk_id,
                            hopped_by_agent_id,
                            hop_reason,
                            hopped_at
                        ) VALUES (?, ?, ?, ?, ?, 'AI-coordinated desk transfer', ?);
                        """,
                        (
                            ticket_id,
                            idx + 1,
                            sequence_ids[idx - 1],
                            sequence_ids[idx],
                            owner_agent_id,
                            self._to_ts(hop_time),
                        ),
                    )

                related_trace_id = trace_coord
                decision_path = [
                    "1) Data directly available: NO",
                    "2) Requires multiple desks: YES",
                    "3) AI multi-desk workflow coordinator: PLAN_CREATED",
                    f"4) Human owner assigned: {owner_agent_code}",
                ]
                response_body = (
                    f"Hello {client['client_name']},\n\n"
                    "Your request requires coordinated processing across multiple desks.\n"
                    f"Accountable owner: {owner_agent_code} ({owner_email}).\n\n"
                    "Decision Path:\n"
                    + "\n".join(decision_path)
                    + f"\n\nTicket Reference: {ticket_ref}\n"
                    "You will receive progress updates as each desk step completes."
                )
            else:
                trace_route = self._insert_trace(
                    conn,
                    ticket_id,
                    "Suggest best-fit human agent based on specialty, load, and queue risk",
                    f"ROUTE_TO_{owner_agent_code}",
                    "Single-desk expert route based on active workload.",
                    "AI",
                    trace_time,
                    owner_agent_id,
                )

                conn.execute(
                    """
                    INSERT INTO ticket_desk_plan (ticket_id, step_seq, desk_id, step_reason, required_flag)
                    VALUES (?, 1, ?, 'Primary desk handling', 1);
                    """,
                    (ticket_id, int(rule["primary_desk_id"])),
                )
                conn.execute(
                    """
                    INSERT INTO ticket_desk_hops (
                        ticket_id,
                        hop_seq,
                        from_desk_id,
                        to_desk_id,
                        hopped_by_agent_id,
                        hop_reason,
                        hopped_at
                    ) VALUES (?, 1, NULL, ?, ?, 'Initial routing assignment', ?);
                    """,
                    (ticket_id, int(rule["primary_desk_id"]), owner_agent_id, self._to_ts(created + timedelta(minutes=2))),
                )

                related_trace_id = trace_route
                decision_path = [
                    "1) Data directly available: NO",
                    "2) Requires multiple desks: NO",
                    f"3) Best-fit human owner assigned: {owner_agent_code}",
                ]
                response_body = (
                    f"Hello {client['client_name']},\n\n"
                    "Your request requires human review.\n"
                    f"Assigned owner: {owner_agent_code} ({owner_email}).\n\n"
                    "Decision Path:\n"
                    + "\n".join(decision_path)
                    + f"\n\nTicket Reference: {ticket_ref}"
                )

        self._insert_email_message(
            conn,
            ticket_id=ticket_id,
            direction="INBOUND",
            sender_email=payload.from_email,
            recipient_email="client-service@mvp.demo",
            subject=payload.subject,
            body=payload.body,
            sent_at=created,
            is_automated=0,
            related_trace_id=None,
        )

        self._insert_email_message(
            conn,
            ticket_id=ticket_id,
            direction="OUTBOUND",
            sender_email=self._settings.sender_email,
            recipient_email=payload.from_email,
            subject=f"Re: {payload.subject}",
            body=response_body,
            sent_at=first_response_at,
            is_automated=1,
            related_trace_id=related_trace_id,
        )

        return RoutingOutput(
            ok=True,
            ticket_id=ticket_id,
            ticket_ref=ticket_ref,
            intent_code=str(rule["intent_code"]),
            automatable=bool(automatable_final),
            requires_multi_desk=bool(requires_multi_final),
            priority=priority,
            status=status,
            owner_agent_code=owner_agent_code,
            to_email=payload.from_email,
            reply_subject=f"Re: {payload.subject}",
            reply_body=response_body,
            decision_path=decision_path,
            classification=classification,
        )

    def _handle_not_resolved_reply(
        self,
        conn: sqlite3.Connection,
        payload: InboundMessage,
        client: sqlite3.Row,
    ) -> RoutingOutput | None:
        text = f"{payload.subject} {payload.body}".upper()
        if "NOT RESOLVED" not in text:
            return None

        match = TICKET_REF_RE.search(text)
        if match is None:
            return RoutingOutput(
                ok=False,
                error="missing_ticket_reference",
                to_email=str(client["email"]),
                reply_subject=f"Re: {payload.subject}",
                reply_body=(
                    "We detected a NOT RESOLVED request but could not find a ticket reference. "
                    "Please include your ticket reference in the format TCKxxxxxx."
                ),
            )

        ticket_ref = match.group(0).upper()
        ticket = conn.execute(
            """
            SELECT ticket_id, ticket_ref, primary_desk_id
            FROM tickets
            WHERE ticket_ref = ?
              AND client_id = ?
            LIMIT 1;
            """,
            (ticket_ref, int(client["client_id"])),
        ).fetchone()

        if ticket is None:
            return RoutingOutput(
                ok=False,
                error="ticket_not_found_for_client",
                to_email=str(client["email"]),
                reply_subject=f"Re: {payload.subject}",
                reply_body=(
                    f"We could not find ticket {ticket_ref} for your client profile. "
                    "Please verify the reference and resend."
                ),
            )

        owner = self._best_owner_agent(conn, int(ticket["primary_desk_id"]))
        owner_id = int(owner["agent_id"])
        owner_code = str(owner["agent_code"])
        owner_email = str(owner["email"])
        now = self._now_ts()

        conn.execute(
            """
            UPDATE tickets
            SET automatable = 0,
                status = 'IN_PROGRESS',
                owner_agent_id = ?,
                client_satisfied = 0,
                resolved_at = NULL,
                closed_at = NULL
            WHERE ticket_id = ?;
            """,
            (owner_id, int(ticket["ticket_id"])),
        )

        conn.execute(
            """
            INSERT INTO ticket_assignments (
                ticket_id,
                assigned_agent_id,
                assigned_desk_id,
                assignment_role,
                assignment_reason,
                assigned_at,
                released_at
            ) VALUES (?, ?, ?, 'PRIMARY_OWNER', 'Client not resolved escalation', ?, NULL);
            """,
            (int(ticket["ticket_id"]), owner_id, int(ticket["primary_desk_id"]), self._to_ts(now)),
        )

        trace_escalation = self._insert_trace(
            conn,
            int(ticket["ticket_id"]),
            "Client satisfied?",
            "NO",
            "Client explicitly replied NOT RESOLVED.",
            "SYSTEM",
            now,
        )
        self._insert_trace(
            conn,
            int(ticket["ticket_id"]),
            "Suggest best-fit human agent based on specialty, load, and queue risk",
            f"ROUTE_TO_{owner_code}",
            "Escalation from AI response to human owner.",
            "AI",
            now + timedelta(minutes=1),
            owner_id,
        )

        self._insert_email_message(
            conn,
            ticket_id=int(ticket["ticket_id"]),
            direction="INBOUND",
            sender_email=str(client["email"]),
            recipient_email="client-service@mvp.demo",
            subject=payload.subject,
            body=payload.body,
            sent_at=now,
            is_automated=0,
            related_trace_id=trace_escalation,
        )

        reply_body = (
            f"Hello {client['client_name']},\n\n"
            "Thanks for your update. Your ticket has been escalated to a human owner.\n"
            f"Assigned owner: {owner_code} ({owner_email})\n\n"
            "Decision Path:\n"
            "1) Client satisfied: NO\n"
            "2) Human handoff: COMPLETED\n"
            f"\nTicket Reference: {ticket_ref}"
        )

        self._insert_email_message(
            conn,
            ticket_id=int(ticket["ticket_id"]),
            direction="OUTBOUND",
            sender_email=self._settings.sender_email,
            recipient_email=str(client["email"]),
            subject=f"Re: {payload.subject}",
            body=reply_body,
            sent_at=now + timedelta(minutes=5),
            is_automated=1,
            related_trace_id=trace_escalation,
        )

        return RoutingOutput(
            ok=True,
            ticket_id=int(ticket["ticket_id"]),
            ticket_ref=ticket_ref,
            intent_code=None,
            automatable=False,
            requires_multi_desk=False,
            priority=None,
            status="IN_PROGRESS",
            owner_agent_code=owner_code,
            to_email=str(client["email"]),
            reply_subject=f"Re: {payload.subject}",
            reply_body=reply_body,
            decision_path=[
                "1) Client satisfied: NO",
                "2) Human handoff: COMPLETED",
            ],
            classification=None,
        )
