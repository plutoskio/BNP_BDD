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
- Average time saved per automatable ticket (cycle-time proxy): **6.77 days** (**162.57 hours**)
- Total time saved (cycle-time proxy): **13,546,284.82 days** (**325,110,835.68 hours**)

## Important Assumption
Time saved is estimated as historical ticket resolution duration (`closingdate_parsed - creationdate_parsed`) for eligible tickets.
This is a **cycle-time reduction proxy**, not direct labor time.
