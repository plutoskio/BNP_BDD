from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_DB_PATH = Path("/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db")
DEFAULT_PROMPT_PATH = Path("/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/prompts/intent_classifier_system.txt")


@dataclass(frozen=True)
class Settings:
    db_path: Path
    prompt_path: Path
    openai_api_key: str | None
    model: str
    reasoning_effort: str
    sender_email: str



def load_settings() -> Settings:
    load_dotenv()

    db_path = Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
    prompt_path = Path(os.getenv("PROMPT_PATH", str(DEFAULT_PROMPT_PATH))).expanduser()

    model = os.getenv("OPENAI_MODEL", "gpt-5.2-2025-12-11")
    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "high")
    sender_email = os.getenv("SERVICE_SENDER_EMAIL", "ai-router@mvp.demo")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key

    return Settings(
        db_path=db_path,
        prompt_path=prompt_path,
        openai_api_key=openai_api_key,
        model=model,
        reasoning_effort=reasoning_effort,
        sender_email=sender_email,
    )
