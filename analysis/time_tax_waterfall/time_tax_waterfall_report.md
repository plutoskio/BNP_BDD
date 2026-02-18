# Time Tax Waterfall Report

## Objective
Decompose ticket duration at the median level into an additive baseline and three time-tax components: owner changes, desk transfers, and reopen events.

## Scope and Guardrails
- Load period: **2025-01_to_2025-09** (reopen field is reliably populated in this period).
- Population: tickets with valid parsed `creationdate_parsed` and `closingdate_parsed`.
- Duration definition: `closing_ts - creation_ts` in hours.
- Invalid durations: rows with negative duration are excluded from duration modeling.
- Outlier cap for stability and comparability: **p99 = 3024.39 hours (126.02 days)**.

## QA Counts
- Raw scoped rows (pre duration filter): **4,194,970**
- Negative-duration rows excluded: **348,795**
- Final analysis rows: **3,846,175**
- Reopened rows in analysis scope: **2,829**
- Owner-change event rows (`Re-assign`) in scope: **2,030,474**

## Model
Weighted least squares on aggregated cell medians (`month x issuer x owner_flag x transfer_flag x reopen_flag`).

Formula (capped hours):
`duration = b0 + b1*owner + b2*transfer + b3*reopen + month_effects + issuer_effects + error`

- Weighted R^2 (cell-level): **0.5815**
- Global raw median duration: **0.065 days**
- Global capped median duration: **0.065 days**
- Actual weighted cell-median duration: **0.342 days**
- Modeled median projection (capped): **0.342 days**
- Model gap (actual weighted cell medians - modeled): **0.000 days**

## Waterfall Components
| component                                                 |   per_ticket_effect_hours |   prevalence_rate |   population_contribution_hours |   per_ticket_effect_days |   population_contribution_days |
|:----------------------------------------------------------|--------------------------:|------------------:|--------------------------------:|-------------------------:|-------------------------------:|
| Baseline (no owner change / no desk transfer / no reopen) |                   0.95268 |       1           |                        0.95268  |                 0.039695 |                     0.039695   |
| Owner-change tax                                          |                  27.5015  |       0.243348    |                        6.69243  |                 1.14589  |                     0.278851   |
| Desk-transfer tax                                         |                 370.984   |       0.00119287  |                        0.442537 |                15.4577   |                     0.018439   |
| Reopen tax                                                |                 175.051   |       0.000735536 |                        0.128756 |                 7.29378  |                     0.00536484 |
| Modeled median projection (capped)                        |                   8.2164  |       1           |                        8.2164   |                 0.34235  |                     0.34235    |

## Quick Sanity Contrasts (Isolated Groups, Capped)
- Baseline none (`owner=0, transfer=0, reopen=0`): **0.035 days**
- Owner only (`owner=1, transfer=0, reopen=0`): **1.058 days**
- Transfer only (`owner=0, transfer=1, reopen=0`): **6.883 days**
- Reopen only (`owner=0, transfer=0, reopen=1`): **2.718 days**

## Interpretation
- Baseline represents expected duration with no ownership/transfer/reopen frictions under observed month+issuer mix.
- Each tax bar is an additive contribution to the modeled median projection.
- This is an associative decomposition (not causal identification), but it is operationally actionable.
