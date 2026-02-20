# BNP Management Dashboard (Read-Only)

This dashboard provides a professional, live operational view of the MVP ticket system.

It is intentionally read-only:
- no ticket edits
- no reassignment actions
- no status mutation endpoints

## What it shows

- Overview KPIs:
  - total tickets
  - active workload
  - automatable rate
  - multi-desk ticket count
  - average resolution time
  - active tickets older than 24h
  - inbound email volume (last 15 minutes)
- Live ticket table with filters and search.
- Desk operations summary.
- Agent load panel.
- Recent email exchange activity.
- Drilldown per ticket:
  - snapshot
  - routing trace
  - desk plan and hops
  - assignment history
  - email exchange

## Data source

SQLite DB:
- default: `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db`
- override with env var: `DASHBOARD_DB_PATH`

## Run

```bash
cd /Users/milo/Desktop/BNP_BDD/solution/management_dashboard
source /Users/milo/Desktop/BNP_BDD/solution/openai_agents_mvp/.venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8100 --reload
```

Open:
- [http://127.0.0.1:8100](http://127.0.0.1:8100)

## Quick script

```bash
bash /Users/milo/Desktop/BNP_BDD/solution/management_dashboard/scripts/run_dashboard.sh
```

## Notes for demo day

- Keep this dashboard open while MailSlurp worker and routing API are running.
- Every new email that becomes a ticket should appear within a few seconds via polling.
- Ticket detail updates automatically while selected.
