#!/usr/bin/env bash
set -euo pipefail

cd /Users/milo/Desktop/BNP_BDD/solution/management_dashboard
source /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/.venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8100 --reload
