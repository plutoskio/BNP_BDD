# MVP Routing Database Seed Summary

- Database: `/Users/milo/Desktop/BNP_BDD/solution/mvp_routing_database/mvp_routing.db`
- Seed: `20260219`

## Required Volumes

- clients: **100**
- cash_accounts: **150**
- positions: **400**
- trades: **800**
- tickets: **300**

## Routing Snapshot

- Automatable tickets: **171**
- Multi-desk tickets: **74**
- Routing trace rows: **992**
- Desk hop rows: **460**
- Email message rows: **1002**

## Ticket Status Mix

- CLOSED: **150**
- IN_PROGRESS: **50**
- RESOLVED: **45**
- WAITING_CLIENT: **25**
- OPEN: **20**
- ESCALATED: **10**

## Integrity

- Foreign keys: **PASS**
- Every ticket has trace/plan/hop/message rows: **PASS**
