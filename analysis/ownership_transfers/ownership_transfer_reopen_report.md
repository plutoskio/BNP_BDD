# Ownership Transfers vs Reopen Rate

## Objective
Assess whether tickets with ownership transfers are reopened more often than tickets without ownership transfers.

## Scope and Data Rules (Rigorous Guardrails)
- `load_period` restricted to **2025-01_to_2025-09**.
- Reason: `reopen_date_parsed` is populated only in this period; later periods are all null and would bias reopen rates downward.
- Population: SRs with non-null `closingdate_parsed` (tickets that reached closure at least once).
- Ownership transfer event: `historysr.action = 'Re-assign'`.
- Event count per ticket: `COUNT(historysr rows)` for `action='Re-assign'`.
- In-scope duplicate check confirms `historysr` owner events have no duplicate `original_id` rows in this period.

## QA Checks
- Owner transfer history rows in-scope: **2,030,474**
- Distinct owner transfer event `original_id` in-scope: **2,030,474**
- Duplicate owner transfer rows in-scope (`rows - distinct original_id`): **0**
- Closed tickets in-scope: **4,194,970**
- Reopened tickets in-scope: **3,018**

## Main Result: With vs Without Ownership Transfer
| group                   |   tickets |   reopened_tickets |   reopen_rate |   reopen_rate_pct |   reopen_rate_ci_low |   reopen_rate_ci_high |   reopen_rate_ci_low_pct |   reopen_rate_ci_high_pct |   avg_owner_transfer_events |
|:------------------------|----------:|-------------------:|--------------:|------------------:|---------------------:|----------------------:|-------------------------:|--------------------------:|----------------------------:|
| No Ownership Transfer   |   3166213 |               2335 |   0.000737474 |         0.0737474 |          0.000708172 |           0.000767988 |                0.0708172 |                 0.0767988 |                     0       |
| With Ownership Transfer |   1028757 |                683 |   0.000663908 |         0.0663908 |          0.000615963 |           0.000715582 |                0.0615963 |                 0.0715582 |                     1.93047 |

## Effect Size and Statistical Test
- Reopen rate (with transfer): **0.0664%**
- Reopen rate (without transfer): **0.0737%**
- Absolute difference: **-0.0074 percentage points**
- 95% CI for difference (approx): **[-0.0132, -0.0016] pp**
- Relative risk: **0.9002x**
- Odds ratio (Fisher exact): **0.9002**
- Fisher exact p-value: **0.0158218**
- Two-proportion z-test p-value: **0.0156194**

## Reopen Rate by Ownership Transfer Count
| transfer_bucket   |   tickets |   reopened_tickets |   reopen_rate |   reopen_rate_pct |   reopen_rate_ci_low |   reopen_rate_ci_high |   reopen_rate_ci_low_pct |   reopen_rate_ci_high_pct |
|:------------------|----------:|-------------------:|--------------:|------------------:|---------------------:|----------------------:|-------------------------:|--------------------------:|
| 0                 |   3166213 |               2335 |   0.000737474 |         0.0737474 |          0.000708172 |           0.000767988 |                0.0708172 |                 0.0767988 |
| 1                 |    662810 |                370 |   0.000558229 |         0.0558229 |          0.000504185 |           0.000618063 |                0.0504185 |                 0.0618063 |
| 2                 |    192054 |                155 |   0.000807065 |         0.0807065 |          0.000689653 |           0.000944446 |                0.0689653 |                 0.0944446 |
| 3                 |     67696 |                 53 |   0.000782912 |         0.0782912 |          0.000598652 |           0.00102383  |                0.0598652 |                 0.102383  |
| 4                 |     38483 |                 45 |   0.00116935  |         0.116935  |          0.000874085 |           0.00156419  |                0.0874085 |                 0.156419  |
| 5+                |     67714 |                 60 |   0.00088608  |         0.088608  |          0.000688509 |           0.00114028  |                0.0688509 |                 0.114028  |

## Interpretation (Business Case)
- If ownership-transfer tickets show materially higher reopen rates, this supports the hypothesis that unstable ownership degrades resolution quality.
- This is consistent with proposing an AI coordinator for routing plus one accountable human owner per ticket.
- This analysis is associative, not causal; transfer-heavy tickets may also be intrinsically more complex.
- See `ownership_transfer_global_report.md` for duration impact in the same scope.
