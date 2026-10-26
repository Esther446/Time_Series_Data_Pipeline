# Task 2 query results from the Part 1 cleaned dataset

- Input: `data\cleaned_traffic.csv`
- Cleaned observations: **40,575**
- The SQL results below were executed using SQLite against an in-memory relational copy of the actual cleaned CSV. The MongoDB aggregation equivalents are computed from the same CSV. Neither live MySQL nor MongoDB is installed in this environment; the repository's MySQL and MongoDB query files still need to be run against the respective servers for database-execution evidence.
- Date range: 2016-01-01 inclusive to 2016-02-01 exclusive.

## SQL query 1 — Latest observation

| date_time | traffic_volume | holiday_name | temp | rain_1h | snow_1h | clouds_all | weather_main | weather_description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2018-09-30 23:00:00 | 954 | NULL | 282.120 | 0.000 | 0.000 | 90 | Clouds | overcast clouds |

## SQL query 2 — Date-range observations

Matching rows: **461**. First five rows:

| date_time | traffic_volume | holiday_name | weather_main | weather_description |
| --- | --- | --- | --- | --- |
| 2016-01-01 00:00:00 | 1513 | New Years Day | Haze | haze |
| 2016-01-01 01:00:00 | 1550 | NULL | Snow | light snow |
| 2016-01-01 03:00:00 | 719 | NULL | Snow | light snow |
| 2016-01-01 04:00:00 | 533 | NULL | Clouds | overcast clouds |
| 2016-01-01 05:00:00 | 586 | NULL | Clouds | overcast clouds |

## SQL query 3 — Average traffic by hour

| hour_of_day | average_traffic_volume | observation_count |
| --- | --- | --- |
| 0 | 844.854 | 1723 |
| 1 | 521.319 | 1710 |
| 2 | 392.637 | 1697 |
| 3 | 373.210 | 1669 |
| 4 | 701.318 | 1703 |
| 5 | 2103.667 | 1685 |
| 6 | 4172.058 | 1683 |
| 7 | 4769.831 | 1672 |
| 8 | 4593.600 | 1689 |
| 9 | 4394.779 | 1639 |
| 10 | 4204.877 | 1705 |
| 11 | 4498.459 | 1667 |
| 12 | 4739.119 | 1692 |
| 13 | 4741.578 | 1673 |
| 14 | 4957.023 | 1697 |
| 15 | 5271.738 | 1663 |
| 16 | 5708.615 | 1707 |
| 17 | 5350.831 | 1664 |
| 18 | 4306.467 | 1682 |
| 19 | 3311.021 | 1683 |
| 20 | 2869.704 | 1709 |
| 21 | 2699.361 | 1704 |
| 22 | 2224.419 | 1719 |
| 23 | 1490.710 | 1740 |

## SQL query 4 — Average traffic on holidays

| holiday_name | average_traffic_volume | observation_count |
| --- | --- | --- |
| New Years Day | 1324.600 | 5 |
| Memorial Day | 1107.600 | 5 |
| Independence Day | 1076.000 | 5 |
| Labor Day | 1013.200 | 5 |
| Thanksgiving Day | 953.600 | 5 |
| Christmas Day | 846.600 | 5 |
| Veterans Day | 691.400 | 5 |
| Washingtons Birthday | 635.200 | 5 |
| State Fair | 634.800 | 5 |
| Martin Luther King Jr Day | 592.667 | 3 |
| Columbus Day | 519.400 | 5 |

## MongoDB aggregation 1 — Average traffic by hour

| _id | average_traffic_volume | observation_count |
| --- | --- | --- |
| 0 | 844.854 | 1723 |
| 1 | 521.319 | 1710 |
| 2 | 392.637 | 1697 |
| 3 | 373.210 | 1669 |
| 4 | 701.318 | 1703 |
| 5 | 2103.667 | 1685 |
| 6 | 4172.058 | 1683 |
| 7 | 4769.831 | 1672 |
| 8 | 4593.600 | 1689 |
| 9 | 4394.779 | 1639 |
| 10 | 4204.877 | 1705 |
| 11 | 4498.459 | 1667 |
| 12 | 4739.119 | 1692 |
| 13 | 4741.578 | 1673 |
| 14 | 4957.023 | 1697 |
| 15 | 5271.738 | 1663 |
| 16 | 5708.615 | 1707 |
| 17 | 5350.831 | 1664 |
| 18 | 4306.467 | 1682 |
| 19 | 3311.021 | 1683 |
| 20 | 2869.704 | 1709 |
| 21 | 2699.361 | 1704 |
| 22 | 2224.419 | 1719 |
| 23 | 1490.710 | 1740 |

## MongoDB aggregation 2 — Average traffic on holidays

| _id | average_traffic_volume | observation_count |
| --- | --- | --- |
| New Years Day | 1324.600 | 5 |
| Memorial Day | 1107.600 | 5 |
| Independence Day | 1076.000 | 5 |
| Labor Day | 1013.200 | 5 |
| Thanksgiving Day | 953.600 | 5 |
| Christmas Day | 846.600 | 5 |
| Veterans Day | 691.400 | 5 |
| Washingtons Birthday | 635.200 | 5 |
| State Fair | 634.800 | 5 |
| Martin Luther King Jr Day | 592.667 | 3 |
| Columbus Day | 519.400 | 5 |

## MongoDB query 1 — Latest observation

| date_time | traffic_volume | holiday | temp | rain_1h | snow_1h | clouds_all | weather_main | weather_description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2018-09-30 23:00:00 | 954 | NULL | 282.120 | 0.000 | 0.000 | 90 | Clouds | overcast clouds |

## MongoDB query 2 — Date-range observations

Matching documents: **461**. First five documents:

| date_time | traffic_volume | holiday | weather_main | weather_description |
| --- | --- | --- | --- | --- |
| 2016-01-01 00:00:00 | 1513 | New Years Day | Haze | haze |
| 2016-01-01 01:00:00 | 1550 | NULL | Snow | light snow |
| 2016-01-01 03:00:00 | 719 | NULL | Snow | light snow |
| 2016-01-01 04:00:00 | 533 | NULL | Clouds | overcast clouds |
| 2016-01-01 05:00:00 | 586 | NULL | Clouds | overcast clouds |

The MongoDB query script returns every document matching the date range; this report shows five rows to keep the output readable.
