# Time Series Data Pipeline

## Project overview

This project uses the Metro Interstate Traffic Volume dataset to study traffic patterns, evaluate forecasting models, and implement SQL and MongoDB databases. This README documents the completed work for **Part 1: Time-Series Analysis and Forecasting** and **Part 2: SQL and MongoDB Database Design**.

## Dataset

- **Dataset:** [Metro Interstate Traffic Volume — Kaggle](https://www.kaggle.com/datasets/uciml/metro-interstate-traffic-volume)
- **Alternative public source:** [Metro Interstate Traffic Volume — UCI](https://archive.ics.uci.edu/dataset/492/metro+interstate+traffic+volume)
- **Target:** `traffic_volume`
- **Timestamp:** `date_time`
- **Source data:** 48,204 rows and nine columns: holiday, weather measurements and descriptions, timestamp, and traffic volume.

The observations are hourly-oriented but the series is not a complete regular hourly grid; the source has gaps as well as repeated timestamps. Part 1 consolidates duplicate timestamps, and lag features should therefore be described as previous-observation lags unless a fixed interval is explicitly verified.

The source and prepared CSV files are kept under the locally ignored `data/` directory; they are not included in Git. Download the source CSV and place it at:

```text
data/Metro_Interstate_Traffic_Volume.csv
```

## Part 1: Time-series analysis and forecasting

The Part 1 analysis documented for this project covers traffic by hour, weekday versus weekend, day of week, month, 24-observation moving average, and lag-1 relationship. Its data-preparation notes describe chronological sorting, duplicate-timestamp investigation, cleaning the anomalous rainfall value, and aggregating repeated timestamps.

The existing analysis summary reports Linear Regression and tuned Random Forest experiments using a chronological 70%/15%/15% train/validation/test split:

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Linear Regression | 487.17 | 676.41 | 0.8832 |
| Random Forest | 149.60 | 236.63 | 0.9857 |

The analysis uses six questions covering hourly, weekday/weekend, day-of-week, monthly, moving-average, and lag-1 patterns. The notebook results report visualizations and interpretations for these questions, including the required moving-average and lagged-feature analyses.

## Part 2: Database design and implementation

### Cleaning and reproducible row counts

Run [prepare_data.py](scripts/prepare_data.py) to apply the Part 1 cleaning rules to the original CSV:

- Fill missing holiday labels with `"None"`.
- Treat rainfall `9831.3` as invalid.
- Group repeated timestamps, averaging numeric columns and keeping the first holiday/weather labels.
- Sort the results chronologically.
- Fill missing rainfall with the median rainfall.

For the supplied Metro Interstate dataset, this produces **40,575 observations** from 48,204 source rows, consolidating 7,629 repeated-timestamp rows. The resulting range is **2012-10-02 09:00:00 through 2018-09-30 23:00:00**. `prepare_data.py` writes `data/cleaned_traffic.csv`, which is the common input to both database loaders.

### MySQL relational design

[schema.sql](sql/schema.sql) creates the `time_series_traffic` database and three InnoDB tables:

- `traffic_observations`: timestamp, traffic volume, stable source-row number, and foreign keys.
- `weather_observations`: the weather values and labels for each prepared observation.
- `holidays`: distinct holiday names; non-holiday observations have a `NULL` holiday foreign key.

Each prepared row receives one traffic row and one associated weather row. `source_row` distinguishes the observations and is unique. The timestamp is indexed for date-range queries. `clouds_all` uses a decimal type because averaging duplicate timestamps can produce fractional values.

### MongoDB document design

MongoDB stores one `traffic_observations` document per prepared row. Weather fields are embedded in the observation document, and `source_row` is used as the stable `_id`. The loader creates a `date_time` index for time-series lookups. A sample is provided in [sample_document.json](mongodb/sample_document.json).

The source timestamps contain no timezone information. The loader keeps them as naive wall-clock values; PyMongo encodes naive Python datetimes as UTC for BSON storage. This is a storage convention and does not establish that the source observations were collected in UTC.

### ERD

```mermaid
erDiagram
    HOLIDAYS o|--o{ TRAFFIC_OBSERVATIONS : labels
    WEATHER_OBSERVATIONS ||--o{ TRAFFIC_OBSERVATIONS : describes

    HOLIDAYS {
        SMALLINT holiday_id PK
        VARCHAR holiday_name UK
    }
    WEATHER_OBSERVATIONS {
        BIGINT weather_id PK
        DECIMAL temp
        DECIMAL rain_1h
        DECIMAL snow_1h
        DECIMAL clouds_all
        VARCHAR weather_main
        VARCHAR weather_description
    }
    TRAFFIC_OBSERVATIONS {
        BIGINT traffic_id PK
        BIGINT source_row UK
        DATETIME date_time
        INT traffic_volume
        SMALLINT holiday_id FK
        BIGINT weather_id FK
    }
```

### Task 2 query evidence

[queries.sql](sql/queries.sql) and [queries.js](mongodb/queries.js) contain the four Task 2 queries for each database: latest observation, date range, average traffic by hour, and average traffic on holidays. The date-range interval is half-open: 2016-01-01 inclusive to 2016-02-01 exclusive.

<details>
<summary>MySQL queries</summary>

```sql
-- 1. Latest observation, including its related holiday and weather data.
SELECT
    t.date_time,
    t.traffic_volume,
    h.holiday_name,
    w.temp,
    w.rain_1h,
    w.snow_1h,
    w.clouds_all,
    w.weather_main,
    w.weather_description
FROM traffic_observations AS t
JOIN weather_observations AS w ON w.weather_id = t.weather_id
LEFT JOIN holidays AS h ON h.holiday_id = t.holiday_id
ORDER BY t.date_time DESC, t.source_row DESC
LIMIT 1;

-- 2. Observations in a half-open date range [start, end).
SELECT
    t.date_time,
    t.traffic_volume,
    h.holiday_name,
    w.weather_main,
    w.weather_description
FROM traffic_observations AS t
JOIN weather_observations AS w ON w.weather_id = t.weather_id
LEFT JOIN holidays AS h ON h.holiday_id = t.holiday_id
WHERE t.date_time >= '2016-01-01 00:00:00'
  AND t.date_time <  '2016-02-01 00:00:00'
ORDER BY t.date_time, t.source_row;

-- 3. Average traffic volume by hour of day.
SELECT
    HOUR(date_time) AS hour_of_day,
    AVG(traffic_volume) AS average_traffic_volume,
    COUNT(*) AS observation_count
FROM traffic_observations
GROUP BY HOUR(date_time)
ORDER BY hour_of_day;

-- 4. Average traffic volume for observations recorded on holidays.
SELECT
    h.holiday_name,
    AVG(t.traffic_volume) AS average_traffic_volume,
    COUNT(*) AS observation_count
FROM traffic_observations AS t
JOIN holidays AS h ON h.holiday_id = t.holiday_id
GROUP BY h.holiday_id, h.holiday_name
ORDER BY average_traffic_volume DESC;
```

</details>

<details>
<summary>MongoDB queries</summary>

```javascript
use("time_series_traffic");

const traffic = db.getCollection("traffic_observations");

// 1. Latest observation.
printjson(
  traffic.find(
    {},
    {
      _id: 0,
      date_time: 1,
      traffic_volume: 1,
      holiday: 1,
      weather: 1
    }
  ).sort({ date_time: -1, source_row: -1 }).limit(1).toArray()
);

// 2. Observations in a half-open date range [start, end).
printjson(
  traffic.find(
    {
      date_time: {
        $gte: ISODate("2016-01-01T00:00:00Z"),
        $lt: ISODate("2016-02-01T00:00:00Z")
      }
    },
    {
      _id: 0,
      date_time: 1,
      traffic_volume: 1,
      holiday: 1,
      "weather.weather_main": 1,
      "weather.weather_description": 1
    }
  ).sort({ date_time: 1, source_row: 1 }).toArray()
);

// 3. Average traffic volume by hour of day.
printjson(
  traffic.aggregate([
    {
      $group: {
        _id: { $hour: "$date_time" },
        average_traffic_volume: { $avg: "$traffic_volume" },
        observation_count: { $sum: 1 }
      }
    },
    { $sort: { _id: 1 } }
  ]).toArray()
);

// 4. Average traffic volume for observations recorded on holidays.
printjson(
  traffic.aggregate([
    { $match: { holiday: { $ne: null } } },
    {
      $group: {
        _id: "$holiday",
        average_traffic_volume: { $avg: "$traffic_volume" },
        observation_count: { $sum: 1 }
      }
    },
    { $sort: { average_traffic_volume: -1 } }
  ]).toArray()
);
```

</details>

#### Recorded query outputs

[task2_query_results.md](outputs/task2_query_results.md) contains the detailed result tables for all eight queries. The SQL-equivalent and MongoDB-style outputs agree on the cleaned dataset. The recorded outputs are:

- **Latest observation:** `2018-09-30 23:00:00`, traffic volume **954**, no holiday, weather `Clouds / overcast clouds`, temperature `282.120`, rainfall and snowfall `0.000`, cloud cover `90`.
- **Date range:** **461 observations**. The first five, in timestamp order:

  | date_time | traffic_volume | holiday | weather_main | weather_description |
  | --- | ---: | --- | --- | --- |
  | 2016-01-01 00:00:00 | 1513 | New Years Day | Haze | haze |
  | 2016-01-01 01:00:00 | 1550 | NULL | Snow | light snow |
  | 2016-01-01 03:00:00 | 719 | NULL | Snow | light snow |
  | 2016-01-01 04:00:00 | 533 | NULL | Clouds | overcast clouds |
  | 2016-01-01 05:00:00 | 586 | NULL | Clouds | overcast clouds |

- **Average traffic by hour:** SQL and MongoDB report the same 24 groups:

  | hour | average_traffic_volume | observation_count |
  | ---: | ---: | ---: |
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

- **Average traffic on holidays:** SQL and MongoDB report the same 11 groups:

  | holiday | average_traffic_volume | observation_count |
  | --- | ---: | ---: |
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

The results report documents the execution method: SQL results were run against an in-memory SQLite copy of the cleaned CSV, and MongoDB-style results were computed from that same CSV. **These dataset-derived equivalents are not evidence of live MySQL or MongoDB server execution.** Run the live query commands below to capture database-execution evidence.

#### Part 2 repository changes

The database work in this repository includes:

- [sql/schema.sql](sql/schema.sql) and [sql/queries.sql](sql/queries.sql) for the normalized MySQL schema and four relational queries.
- [mongodb/sample_document.json](mongodb/sample_document.json) and [mongodb/queries.js](mongodb/queries.js) for the MongoDB document shape and four document/aggregation queries.
- [scripts/load_sql.py](scripts/load_sql.py) and [scripts/load_mongodb.py](scripts/load_mongodb.py) to validate and load the prepared CSV into each database.
- [scripts/prepare_data.py](scripts/prepare_data.py) to clean and consolidate the source CSV into the shared database input.
- [docker-compose.yml](docker-compose.yml), [.env.example](.env.example), and [.gitignore](.gitignore) for local database services and secret handling.
- [outputs/task2_query_results.md](outputs/task2_query_results.md) for the full recorded query-result tables and execution notes.

### Task 2 local setup (Windows PowerShell)

Run commands from the repository root. You need Docker Desktop with its engine running, Python, and the original CSV at the path above.

#### 1. Install Python dependencies and prepare the data

```powershell
python -m pip install -r requirements.txt
python scripts\prepare_data.py
```

The preparation command should report 40,575 rows and create `data\cleaned_traffic.csv`.

#### 2. Configure local database passwords

If you do not already have a `.env` file, create one from the example. If `.env` already exists, keep it and edit it only if necessary—do not overwrite your passwords. Use unique local passwords made from letters and numbers, since the MongoDB connection URI below uses those values directly.

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
notepad .env
```

`.env` is excluded by [.gitignore](.gitignore); do not commit it. The public template is [.env.example](.env.example).

#### 3. Start the database servers

```powershell
docker info
docker compose config --quiet
docker compose up -d
docker compose ps
```

Wait for the MySQL and MongoDB services to become healthy. Host ports are configured by `MYSQL_PORT_HOST` and `MONGODB_PORT_HOST` in `.env`; `docker compose ps` shows the published ports. If Docker reports a port conflict, change the relevant host port in `.env`, then run `docker compose up -d` again.

#### 4. Set connection variables in the current PowerShell session

Run this in the same terminal for the Python loaders. If you open another terminal, repeat this step.

```powershell
$settings = @{}
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $settings[$matches[1]] = $matches[2]
    }
}

$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = $settings["MYSQL_PORT_HOST"]
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = $settings["MYSQL_ROOT_PASSWORD"]
$env:MYSQL_DATABASE = "time_series_traffic"

$mongoUser = $settings["MONGODB_ROOT_USERNAME"]
$mongoPassword = $settings["MONGODB_ROOT_PASSWORD"]
$env:MONGODB_URI = "mongodb://$mongoUser`:$mongoPassword@127.0.0.1:$($settings['MONGODB_PORT_HOST'])/?authSource=admin"
$env:MONGODB_DATABASE = "time_series_traffic"
```

#### 5. Create the MySQL schema

```powershell
docker compose cp .\sql\schema.sql mysql:/tmp/schema.sql
docker compose exec mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" < /tmp/schema.sql'
```

#### 6. Load the cleaned data into both databases

```powershell
python scripts\load_sql.py "data\cleaned_traffic.csv"
python scripts\load_mongodb.py "data\cleaned_traffic.csv"
```

Both loaders should report 40,575 observations. The MySQL loader requires an empty `traffic_observations` table. The MongoDB loader upserts by source-row `_id`; if a replacement CSV has fewer rows, remove stale documents intentionally before treating it as a complete refresh.

#### 7. Run the SQL queries on live MySQL

```powershell
docker compose cp .\sql\queries.sql mysql:/tmp/queries.sql
docker compose exec mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" < /tmp/queries.sql'
```

#### 8. Run the MongoDB queries on live MongoDB

Copy the query script into the container once:

```powershell
docker compose cp .\mongodb\queries.js mongodb:/tmp/queries.js
```

Run **one command at a time** to execute just that query and print only its result:

```powershell
docker compose exec mongodb mongosh --quiet --username $mongoUser --password $mongoPassword --authenticationDatabase admin --eval "var selectedQuery = 'latest'; void load('/tmp/queries.js')"
```

```powershell
docker compose exec mongodb mongosh --quiet --username $mongoUser --password $mongoPassword --authenticationDatabase admin --eval "var selectedQuery = 'date-range'; void load('/tmp/queries.js')"
```

```powershell
docker compose exec mongodb mongosh --quiet --username $mongoUser --password $mongoPassword --authenticationDatabase admin --eval "var selectedQuery = 'hourly-average'; void load('/tmp/queries.js')"
```

```powershell
docker compose exec mongodb mongosh --quiet --username $mongoUser --password $mongoPassword --authenticationDatabase admin --eval "var selectedQuery = 'holiday-average'; void load('/tmp/queries.js')"
```

The date-range command returns all matching documents (461 for the example interval), so its output is longer than the other queries.

Save the terminal output or screenshots of at least three successful queries per database and include them in the report. The query result file already contains locally calculated equivalents, but live database evidence is still needed.

#### 9. Stop or reset the database services

Stop the containers while preserving data:

```powershell
docker compose stop
```

Start them again:

```powershell
docker compose start
docker compose ps
```

Only if you intend to delete **all** stored database data and start over, remove the containers and volumes:

```powershell
docker compose down -v
```

## Repository contents

```text
.
├── docker-compose.yml
├── README.md
├── requirements.txt
├── sql/
│   ├── schema.sql
│   └── queries.sql
├── mongodb/
│   ├── sample_document.json
│   └── queries.js
├── scripts/
│   ├── prepare_data.py
│   ├── load_sql.py
│   ├── load_mongodb.py
│   └── query_actual_data.py
├── outputs/
│   └── task2_query_results.md
└── data/                  # Local only; excluded from Git
    ├── Metro_Interstate_Traffic_Volume.csv
    └── cleaned_traffic.csv
```

## Part 1 and Part 2 deliverables

The completed work documented here consists of the Part 1 traffic analysis and forecasting results, and the Part 2 database schema, ERD, MongoDB document design, loaders, and query examples. The repository also includes reproducible query-equivalent results calculated from the cleaned dataset in [task2_query_results.md](outputs/task2_query_results.md). For final evidence of the database implementation, run the supplied query files against the live MySQL and MongoDB services and include their results in the report.

The assignment submission is a PDF report and a link to the GitHub repository. The report for these completed parts should explain the Part 1 dataset preparation, analytical questions, visual findings and model experiments, then the Part 2 schema, ERD, MongoDB design, query results, and team contributions. Keep local data and database credentials private, and use clear commits to document contributions.
