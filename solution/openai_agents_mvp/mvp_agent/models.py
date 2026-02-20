from __future__ import annotations

from pydantic import BaseModel, Field


INTENT_CODES = [
    "cash_balance",
    "position_summary",
    "trade_status",
    "settlement_eta",
    "failed_trade_investigation",
    "trade_amendment_request",
    "account_closure_request",
    "sanctions_review_query",
    "corporate_action_instruction",
    "fee_dispute",
    "investment_advice_request",
    "portfolio_rebalancing_advice",
    "risk_profile_review",
    "tax_withholding_query",
    "tax_document_request",
    "capital_gains_tax_query",
    "platform_access_issue",
    "password_reset_request",
    "api_connectivity_issue",
]


class InboundMessage(BaseModel):
    from_email: str
    subject: str = ""
    body: str = ""
    message_id: str | None = None
    channel: str = "EMAIL"


class IntentClassification(BaseModel):
    intent_code: str = Field(pattern=r"^[a-z_]+$")
    confidence: float = Field(ge=0.0, le=1.0)
    objective_request: bool
    requires_multi_desk_hint: bool
    priority: str = Field(pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    reasoning_short: str


class RoutingOutput(BaseModel):
    ok: bool
    error: str | None = None
    ticket_id: int | None = None
    ticket_ref: str | None = None
    intent_code: str | None = None
    automatable: bool | None = None
    requires_multi_desk: bool | None = None
    priority: str | None = None
    status: str | None = None
    owner_agent_code: str | None = None
    to_email: str | None = None
    reply_subject: str | None = None
    reply_body: str | None = None
    decision_path: list[str] = Field(default_factory=list)
    classification: IntentClassification | None = None
