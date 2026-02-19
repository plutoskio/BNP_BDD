#!/usr/bin/env bash
set -euo pipefail
cd /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp
source .venv/bin/activate
python email_adapter/mailslurp_setup.py "$@"
