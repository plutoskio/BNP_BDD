# Global Volume vs Median Wait Report

## Objective
Assess whether higher total ticket volume (all desks combined) is associated with longer median wait time for automatable tickets.

## Population Definition
- Closed tickets only (`closingdate_parsed` populated)
- Automatable criteria:
1. `transfer_count <= 1`
2. `comm_count <= 1`
3. `task_count <= 1`
4. `reopen_date_parsed IS NULL`
- Analysis window starts on: `2024-01-01`

## Daily Analysis
- Number of daily periods analyzed: **730**
- Pearson correlation (volume vs median wait): **-0.3233**
- Spearman correlation (volume vs median wait): **-0.8470**

### Daily Volume Quintile Summary

| volume_quintile   |   periods |   avg_total_volume |   median_wait_hours |   p90_wait_hours |
|:------------------|----------:|-------------------:|--------------------:|-----------------:|
| Q1 (Low)          |       145 |            90.2483 |           48.546    |        51.3796   |
| Q2                |       147 |          2634.37   |           23.3386   |       837.443    |
| Q3                |       146 |          8267.67   |            1.22896  |         1.40701  |
| Q4                |       146 |          9445.37   |            0.264444 |         1.36778  |
| Q5 (High)         |       146 |         12387.1    |            0.165694 |         0.278681 |

## Weekly Analysis
- Number of weekly periods analyzed: **105**
- Pearson correlation (volume vs median wait): **-0.5598**
- Spearman correlation (volume vs median wait): **-0.7174**

### Weekly Volume Quintile Summary

| volume_quintile   |   periods |   avg_total_volume |   median_wait_hours |   p90_wait_hours |
|:------------------|----------:|-------------------:|--------------------:|-----------------:|
| Q1 (Low)          |        21 |            26887.2 |            1.28667  |       960.189    |
| Q2                |        21 |            41503.4 |            1.25222  |         1.39819  |
| Q3                |        21 |            45615.9 |            1.20222  |         1.33472  |
| Q4                |        21 |            49927   |            0.194861 |         1.29042  |
| Q5 (High)         |        21 |            64397.9 |            0.17     |         0.217639 |

## Interpretation Guidance
- Positive correlation: higher volume tends to increase median wait.
- Near-zero correlation: weak or no linear/monotonic association.
- Negative correlation: higher volume coincides with lower median wait (possible process/capacity effects).
