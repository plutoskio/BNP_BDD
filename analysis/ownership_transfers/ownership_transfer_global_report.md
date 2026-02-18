# Ownership Transfers: Global Report

## Scope
- Analysis window: **2025-01_to_2025-09**
- Population: closed SR tickets in-scope.
- Ownership transfer event: `historysr.action = 'Re-assign'`.
- Reopen caveat: this period is used because reopen signal is populated only here.

## QA and Data Integrity
- Closed tickets in-scope: **4,194,970**
- Reopened tickets in-scope: **3,018**
- Owner transfer history rows in-scope: **2,030,474**
- Owner transfer duplicate rows (`rows - distinct original_id`): **0**
- Duration rows with null parsed value: **0**
- Duration rows with negative value (excluded from duration metrics): **348,795**
- Duration rows used for duration metrics: **3,846,175**

## Part A: Reopen Rate vs Ownership Transfers
| group                   |   tickets |   reopened_tickets |   reopen_rate |   reopen_rate_pct |   reopen_rate_ci_low |   reopen_rate_ci_high |   reopen_rate_ci_low_pct |   reopen_rate_ci_high_pct |   avg_owner_transfer_events |
|:------------------------|----------:|-------------------:|--------------:|------------------:|---------------------:|----------------------:|-------------------------:|--------------------------:|----------------------------:|
| No Ownership Transfer   |   3166213 |               2335 |   0.000737474 |         0.0737474 |          0.000708172 |           0.000767988 |                0.0708172 |                 0.0767988 |                     0       |
| With Ownership Transfer |   1028757 |                683 |   0.000663908 |         0.0663908 |          0.000615963 |           0.000715582 |                0.0615963 |                 0.0715582 |                     1.93047 |

- Reopen rate (with transfer): **0.0664%**
- Reopen rate (without transfer): **0.0737%**
- Absolute difference: **-0.0074 pp**
- Relative risk: **0.9002x**
- Fisher exact p-value: **0.0158218**
- Two-proportion z-test p-value: **0.0156194**

### Reopen by Transfer Count Bucket
| transfer_bucket   |   tickets |   reopened_tickets |   reopen_rate |   reopen_rate_pct |   reopen_rate_ci_low |   reopen_rate_ci_high |   reopen_rate_ci_low_pct |   reopen_rate_ci_high_pct |
|:------------------|----------:|-------------------:|--------------:|------------------:|---------------------:|----------------------:|-------------------------:|--------------------------:|
| 0                 |   3166213 |               2335 |   0.000737474 |         0.0737474 |          0.000708172 |           0.000767988 |                0.0708172 |                 0.0767988 |
| 1                 |    662810 |                370 |   0.000558229 |         0.0558229 |          0.000504185 |           0.000618063 |                0.0504185 |                 0.0618063 |
| 2                 |    192054 |                155 |   0.000807065 |         0.0807065 |          0.000689653 |           0.000944446 |                0.0689653 |                 0.0944446 |
| 3                 |     67696 |                 53 |   0.000782912 |         0.0782912 |          0.000598652 |           0.00102383  |                0.0598652 |                 0.102383  |
| 4                 |     38483 |                 45 |   0.00116935  |         0.116935  |          0.000874085 |           0.00156419  |                0.0874085 |                 0.156419  |
| 5+                |     67714 |                 60 |   0.00088608  |         0.088608  |          0.000688509 |           0.00114028  |                0.0688509 |                 0.114028  |

## Part B: Owner Changes vs Duration
| group                   |   tickets |   avg_duration_hours |   avg_duration_days |   avg_duration_hours_capped_168 |   avg_duration_days_capped_168 |   tickets_over_24h |   tickets_over_24h_pct |   tickets_over_72h |   tickets_over_72h_pct |   tickets_over_168h |   tickets_over_168h_pct |
|:------------------------|----------:|---------------------:|--------------------:|--------------------------------:|-------------------------------:|-------------------:|-----------------------:|-------------------:|-----------------------:|--------------------:|------------------------:|
| No Ownership Transfer   |   2910216 |              94.8522 |             3.95217 |                         31.4122 |                        1.30884 |             843015 |                28.9674 |             519861 |                17.8633 |              287426 |                 9.87645 |
| With Ownership Transfer |    935959 |             337.928  |            14.0803  |                         64.8967 |                        2.70403 |             484087 |                51.721  |             358155 |                38.2661 |              242927 |                25.9549  |

- Average duration with transfer: **14.080 days** (337.93h)
- Average duration without transfer: **3.952 days** (94.85h)
- Average duration difference (with - without): **10.128 days** (243.08h)
- Average duration ratio (with / without): **3.5627x**

### Duration by Transfer Count Bucket
| transfer_bucket   |   tickets |   avg_duration_hours |   avg_duration_days |   avg_duration_hours_capped_168 |   tickets_over_24h |   tickets_over_72h |   tickets_over_168h |   tickets_over_24h_pct |   tickets_over_72h_pct |   tickets_over_168h_pct |   avg_duration_days_capped_168 |
|:------------------|----------:|---------------------:|--------------------:|--------------------------------:|-------------------:|-------------------:|--------------------:|-----------------------:|-----------------------:|------------------------:|-------------------------------:|
| 0                 |   2910216 |              94.8522 |             3.95217 |                         31.4122 |             843015 |             519861 |              287426 |                28.9674 |                17.8633 |                 9.87645 |                        1.30884 |
| 1                 |    598997 |             160.219  |             6.67578 |                         44.0542 |             231577 |             152295 |               90266 |                38.6608 |                25.425  |                15.0695  |                        1.83559 |
| 2                 |    171856 |             374.797  |            15.6165  |                         81.2583 |             110674 |              82998 |               55788 |                64.3993 |                48.2951 |                32.4621  |                        3.38576 |
| 3                 |     62516 |             553.414  |            23.0589  |                        103.408  |              48400 |              38913 |               27454 |                77.4202 |                62.2449 |                43.9152  |                        4.30868 |
| 4                 |     36416 |             806.759  |            33.615   |                        121.799  |              31479 |              26828 |               20387 |                86.4428 |                73.6709 |                55.9836  |                        5.07494 |
| 5+                |     66174 |            1389.2    |            57.8833  |                        143.372  |              61957 |              57121 |               49032 |                93.6274 |                86.3194 |                74.0956  |                        5.97385 |

## Interpretation
- Reopen-rate signal alone does not show deterioration for transfer tickets in this dataset slice.
- Duration analysis quantifies whether ownership changes still create cycle-time friction even without higher reopen rates.
- This supports a combined argument: stabilize accountability (single owner) while AI orchestrates routing across desks.
