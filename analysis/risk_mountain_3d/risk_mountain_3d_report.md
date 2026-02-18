# Risk Mountain (Interactive 3D) - Report

## Business Objective
Create a high-impact visual showing where operational complexity clusters: owner changes (X), desk transfers (Y), and median resolution time (Z), with bubble size for volume and color for SLA-miss risk.

## Methodology
- Load period: **2025-01_to_2025-09**
- Ticket scope: tickets with desk activity records, then filtered to closed tickets with valid parsed creation/closing timestamps and non-negative duration.
- Owner changes: count of `historysr.action = "Re-assign"` events per ticket.
- Desk transfers: count of desk changes in `activity.jur_assignedgroup_id` in event-time order.
- SLA miss proxy: `duration_hours > 72`.
- Bucketing: counts capped at **6+** for visual stability.
- Stable-cell rule for interpretation focus: `tickets >= 100` (full chart still includes all cells).

## QA and Coverage
- SR rows in load period: **4,233,963**
- SR rows with desk activity records: **245,558**
- SR rows with parsed start/end: **4,194,970**
- Negative-duration rows excluded: **29,233**
- Final ticket rows analyzed: **213,830**
- Owner-change events (`Re-assign`): **2,030,474**
- Activity rows with desk assignment: **696,150**
- Overall median resolution: **1.002 days**
- Overall average resolution: **13.880 days**
- Overall SLA miss rate (> 72h): **37.41%**
- 3D cells (all): **47**
- Stable cells (`n >= 100`): **15** (coverage: **99.72%** of tickets)

## Top Cells by Expected SLA-Miss Burden
(Expected burden = `tickets * sla_miss_rate`)

| owner_bucket   |   transfer_bucket |   tickets |   median_duration_days |   sla_miss_pct |   expected_sla_miss_tickets |
|:---------------|------------------:|----------:|-----------------------:|---------------:|----------------------------:|
| 0              |                 0 |    146975 |                  0.112 |          26.23 |                       38552 |
| 1              |                 0 |     27019 |                  1.164 |          40.14 |                       10845 |
| 2              |                 0 |     14657 |                  6.397 |          63.64 |                        9328 |
| 6+             |                 0 |      8197 |                 56.257 |          94.22 |                        7723 |
| 3              |                 0 |      5613 |                 10.808 |          75.91 |                        4261 |
| 4              |                 0 |      4306 |                 17.079 |          81.49 |                        3509 |
| 5              |                 0 |      2475 |                 23.163 |          86.06 |                        2130 |
| 0              |                 1 |      2232 |                  6.102 |          69.67 |                        1555 |
| 1              |                 1 |       465 |                  9.764 |          84.52 |                         393 |
| 2              |                 1 |       345 |                 15.276 |          84.64 |                         292 |

## How to Read the Mountain
- Taller bubbles (higher Z) indicate slower median resolution.
- Warmer colors indicate higher SLA-miss risk.
- Larger bubbles indicate higher-volume pain points.
- High volume + high elevation + warm color clusters are the strongest candidates for AI coordination and stricter ownership governance.
