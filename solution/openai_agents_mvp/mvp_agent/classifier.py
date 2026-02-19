from __future__ import annotations

from pathlib import Path

from agents import Agent, ModelSettings, Runner
from agents.model_settings import Reasoning

from .models import INTENT_CODES, IntentClassification


INTENT_KEYWORDS: dict[str, list[str]] = {
    "cash_balance": ["cash balance", "available cash", "cash position", "liquidity"],
    "position_summary": ["position", "holdings", "portfolio", "exposure"],
    "trade_status": ["trade status", "execution status", "executed", "confirmed"],
    "settlement_eta": ["settlement", "value date", "when settle", "eta"],
    "failed_trade_investigation": ["failed trade", "investigation", "reconcile", "break"],
    "trade_amendment_request": ["amend", "amendment", "correct trade", "change quantity", "change price"],
    "account_closure_request": ["account closure", "close account", "terminate account"],
    "sanctions_review_query": ["sanctions", "aml", "watchlist", "restricted"],
    "corporate_action_instruction": ["corporate action", "dividend election", "rights issue", "tender"],
    "fee_dispute": ["fee dispute", "incorrect fee", "charge issue", "billing dispute"],
}

SUBJECTIVE_HINTS = {"advice", "recommend", "opinion", "best strategy", "what should we do"}
MULTI_HINTS = {"failed", "investigation", "sanctions", "corporate action", "reconcile", "closure"}


class IntentClassifier:
    def __init__(self, model: str, reasoning_effort: str, prompt_path: Path, has_api_key: bool) -> None:
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._prompt_path = prompt_path
        self._has_api_key = has_api_key
        self._agent: Agent[None] | None = None

    def classify(self, subject: str, body: str) -> IntentClassification:
        if self._has_api_key:
            try:
                return self._classify_with_agent(subject, body)
            except Exception:
                # Hard fallback keeps the workflow running for demo reliability.
                return self._heuristic(subject, body)
        return self._heuristic(subject, body)

    def _classify_with_agent(self, subject: str, body: str) -> IntentClassification:
        if self._agent is None:
            instructions = self._prompt_path.read_text(encoding="utf-8")
            self._agent = Agent(
                name="Intent Classifier",
                instructions=instructions,
                model=self._model,
                model_settings=ModelSettings(
                    temperature=0,
                    reasoning=Reasoning(effort=self._reasoning_effort),
                    verbosity="medium",
                ),
                output_type=IntentClassification,
            )

        prompt = f"Subject: {subject}\nBody:\n{body}"
        run_result = Runner.run_sync(self._agent, prompt, max_turns=3)
        parsed = run_result.final_output_as(IntentClassification)

        # Guardrail against accidental out-of-schema intent values.
        if parsed.intent_code not in INTENT_CODES:
            return self._heuristic(subject, body)
        return parsed

    def _heuristic(self, subject: str, body: str) -> IntentClassification:
        text = f"{subject} {body}".lower()

        best_intent = "fee_dispute"
        best_hits = 0
        for intent, keywords in INTENT_KEYWORDS.items():
            hits = sum(1 for keyword in keywords if keyword in text)
            if hits > best_hits:
                best_hits = hits
                best_intent = intent

        objective = not any(keyword in text for keyword in SUBJECTIVE_HINTS)
        requires_multi = any(keyword in text for keyword in MULTI_HINTS)

        if "urgent" in text or "critical" in text or "escalate" in text:
            priority = "CRITICAL"
        elif "failed" in text or "sanctions" in text:
            priority = "HIGH"
        elif "amend" in text or "dispute" in text:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        confidence = 0.55 if best_hits == 0 else min(0.55 + 0.12 * best_hits, 0.92)
        return IntentClassification(
            intent_code=best_intent,
            confidence=round(confidence, 2),
            objective_request=objective,
            requires_multi_desk_hint=requires_multi,
            priority=priority,
            reasoning_short="Heuristic fallback classifier used.",
        )
