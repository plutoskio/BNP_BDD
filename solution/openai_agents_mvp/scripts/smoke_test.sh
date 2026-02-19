#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp"
DB="${DB_PATH:-/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db}"
PY="$ROOT/.venv/bin/python"
CLI="$ROOT/cli.py"

if [[ ! -x "$PY" ]]; then
  echo "Missing venv python at $PY"
  exit 1
fi

run_case() {
  local label="$1"
  shift
  echo "\n=== $label ==="
  "$PY" "$CLI" inbound --db-path "$DB" "$@"
}

echo "Using DB: $DB"
"$PY" -m py_compile "$ROOT/cli.py" "$ROOT/api.py" "$ROOT/mvp_agent"/*.py

run_case "Direct data (automatable)" \
  --from-email ops.cl0004@example-client.com \
  --subject "Need cash balance" \
  --body "Please share available cash"

run_case "Single-desk human route" \
  --from-email ops.cl0003@example-client.com \
  --subject "Fee dispute on January custody charge" \
  --body "We see an incorrect fee and request review."

run_case "Multi-desk route" \
  --from-email ops.cl0002@example-client.com \
  --subject "Failed trade investigation TRD000005" \
  --body "Please investigate this failed trade and reconcile the break. Urgent."

echo "\n=== Escalation seed (same client) ==="
seed_json=$("$PY" "$CLI" inbound --db-path "$DB" \
  --from-email ops.cl0002@example-client.com \
  --subject "Need trade status for TRD000001" \
  --body "Can you confirm if this trade is executed?")
echo "$seed_json"

seed_ref=$("$PY" -c 'import json,sys; print(json.loads(sys.argv[1]).get("ticket_ref",""))' "$seed_json")
if [[ -n "$seed_ref" ]]; then
  run_case "Client NOT RESOLVED escalation" \
    --from-email ops.cl0002@example-client.com \
    --subject "NOT RESOLVED ${seed_ref}" \
    --body "NOT RESOLVED please escalate this issue to a human owner"
fi

echo "\n=== Latest tickets ==="
sqlite3 "$DB" "SELECT ticket_ref,status,automatable,requires_multi_desk,owner_agent_id,created_at FROM tickets ORDER BY ticket_id DESC LIMIT 10;"
