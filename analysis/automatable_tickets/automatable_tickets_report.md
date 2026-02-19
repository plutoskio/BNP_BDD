# Automatable Tickets Report

## Objective
Estimate the size and time-impact of tickets suitable for first-line AI auto-response.

## Criteria Used
A ticket is labeled `automatable` when all of the following are true:
1. `transfer_count <= 1`
2. `comm_count <= 1`
3. `task_count <= 1`
4. `reopen_date_parsed IS NULL`

## Why These Criteria Are Justified
- `transfer_count <= 1`: simple tickets should not bounce across desks; allowing 1 transfer covers initial misrouting.
- `comm_count <= 1`: low back-and-forth indicates objective, low-ambiguity requests.
- `task_count <= 1`: multiple tasks indicate decomposition/escalation, which is usually non-simple work.
- `no reopen`: reduces risk by excluding tickets with known resolution fragility.

## Results
- Total tickets in population: **4,729,176**
- Automatable tickets: **2,160,544**
- Automatable share of total: **45.69%**
- Automatable tickets with valid date pair for time estimate: **1,999,790**
- Median time saved per automatable ticket (cycle-time proxy): **0.04 days** (**0.93 hours**)
- Robust total time saved (`tickets × median`): **77,214.11 days** (**1,853,138.73 hours**)
- Robust total time saved in years: **211.55 years**

## Visuals
- Share chart: `automatable_ticket_share_pie.png`
- Impact chart: `automatable_time_lost_impact.png`

## Important Assumption
Time saved is estimated from historical ticket resolution duration (`closingdate_parsed - creationdate_parsed`) for eligible tickets.
To reduce outlier skew, the total impact uses **number of tickets × median duration** (not the raw sum of all durations).
