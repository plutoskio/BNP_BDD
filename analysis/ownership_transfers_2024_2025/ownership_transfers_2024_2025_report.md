# Ownership Transfers per Ticket - 2024 vs 2025

## Objective
Compare the average number of ownership transfers per ticket between 2024 and 2025.

## KPI Definition
- Population: closed tickets (`closingdate_parsed` is not null).
- Ownership transfer event: `historysr.action = 'Re-assign'`.
- Average ownership transfers per ticket = `total_owner_transfers / closed_tickets`.

## Results

|   creation_year | closed_tickets   | total_owner_transfers   |   avg_owner_transfers_per_ticket |
|----------------:|:-----------------|:------------------------|---------------------------------:|
|            2024 | 2,188,415        | 1,061,626               |                           0.4851 |
|            2025 | 2,540,246        | 1,152,793               |                           0.4538 |

## Comparison 2025 vs 2024
- Absolute difference (avg transfers per ticket): **-0.0313**
- Relative change: **-6.45%**
