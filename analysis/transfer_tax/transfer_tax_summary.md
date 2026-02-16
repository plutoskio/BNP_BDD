# Transfer Tax Summary

Resolution-time statistics by number of desk transfers.

- Population analyzed: 236,009 closed tickets with valid parsed dates.
- Histogram cap: 99th percentile at 216.97 days for visual clarity.

| transfer_bucket   |   count |   avg_days |   median_days |      p90 |
|:------------------|--------:|-----------:|--------------:|---------:|
| 0 transfers       |  231196 |    13.2085 |      0.978443 |  30.9309 |
| 1 transfer        |    3824 |    29.0912 |      8.249    |  74.0959 |
| 2-3 transfers     |     885 |    58.2001 |     24.8336   | 158.638  |
| 4+ transfers      |     104 |    97.1329 |     78.8263   | 198.127  |

## Average Resolution by Transfer Count (0 to 6+)

| transfer_label   |   count |   avg_days |   median_days |
|:-----------------|--------:|-----------:|--------------:|
| 0                |  231196 |    13.2085 |      0.978443 |
| 1                |    3824 |    29.0912 |      8.249    |
| 2                |     737 |    55.933  |     23.724    |
| 3                |     148 |    69.4899 |     30.9714   |
| 4                |      60 |    74.4833 |     45.7139   |
| 5                |      18 |   107.052  |    106.797    |
| 6+               |      26 |   142.534  |    112.078    |
