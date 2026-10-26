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

[queries.sql](sql/queries.sql) and [queries.js](mongodb/queries.js) each provide four queries: latest observation, date range, average traffic by hour, and average traffic on holidays.

[task2_query_results.md](outputs/task2_query_results.md) records results calculated using the actual cleaned dataset. For reproducibility in this workspace, the SQL-equivalent results were run against an in-memory SQLite copy, and the MongoDB-style results were computed from the same dataset. **Those results are not evidence that the SQL and MongoDB scripts have been run on live MySQL and MongoDB servers.** Run the live query commands below and capture their outputs or screenshots for the final report.

The example date range is half-open: 2016-01-01 inclusive to 2016-02-01 exclusive. It matches **461 observations** in the cleaned dataset. The latest row is 2018-09-30 23:00, with traffic volume 954.

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

```powershell
docker compose cp .\mongodb\queries.js mongodb:/tmp/queries.js
docker compose exec mongodb mongosh `
  --username $mongoUser `
  --password $mongoPassword `
  --authenticationDatabase admin `
  --file /tmp/queries.js
```

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
