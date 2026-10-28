# Time Series Data Pipeline

## Project overview

This project uses the Metro Interstate Traffic Volume dataset to study traffic patterns, evaluate forecasting models, implement SQL and MongoDB databases, and expose RESTful CRUD and time-series query endpoints. This README documents the completed work for **Part 1: Time-Series Analysis and Forecasting**, **Part 2: SQL and MongoDB Database Design**, and **Part 3: CRUD and Time-Series Query Endpoints**.

## Dataset

- **Dataset:** [Metro Interstate Traffic Volume — Kaggle](https://www.kaggle.com/datasets/uciml/metro-interstate-traffic-volume)
- **Alternative public source:** [Metro Interstate Traffic Volume — UCI](https://archive.ics.uci.edu/dataset/492/metro+interstate+traffic+volume)
- **Target:** `traffic_volume`
- **Timestamp:** `date_time`
- **Source data:** 48,204 rows and nine columns: holiday, weather measurements and descriptions, timestamp, and traffic volume.

The observations are hourly-oriented but the series is not a complete regular hourly grid; the source has gaps as well as repeated timestamps. Part 1 consolidates duplicate timestamps, and lag features should therefore be described as previous-observation lags unless a fixed interval is explicitly verified.

The dataset that we used for this assignment is in the data/ folder:

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

## Part 3: CRUD and Time-Series Query API (FastAPI)

The `api/` package implements a FastAPI service providing full CRUD (`POST`, `GET`, `PUT`, `DELETE`) and time-series query endpoints (`latest`, `recent`, `date-range`) for **both** the relational MySQL database (`traffic_observations`, `weather_observations`, `holidays`) and the non-relational MongoDB collection (`traffic_observations`).

### Endpoints Summary

| Operation | MySQL Endpoint | MongoDB Endpoint | Description |
|---|---|---|---|
| **Create (POST)** | `POST /api/sql/records` | `POST /api/mongodb/records` | Insert a new traffic & weather observation |
| **Latest Record (GET)** | `GET /api/sql/records/latest` | `GET /api/mongodb/records/latest` | Fetch the most recent observation (`date_time DESC, source_row DESC`) |
| **Recent N Records (GET)** | `GET /api/sql/records/recent?limit=25` | `GET /api/mongodb/records/recent?limit=25` | Fetch the newest `N` records (supports Task 4 lag-24 / moving-average features) |
| **Date Range (GET)** | `GET /api/sql/records/date-range?start=...&end=...` | `GET /api/mongodb/records/date-range?start=...&end=...` | Fetch observations in half-open interval `[start, end)` |
| **List Records (GET)** | `GET /api/sql/records?limit=100&offset=0` | `GET /api/mongodb/records?limit=100&offset=0` | Paginated chronological list of observations |
| **Get by ID (GET)** | `GET /api/sql/records/{source_row}` | `GET /api/mongodb/records/{source_row}` | Retrieve a single observation by `source_row` |
| **Update (PUT)** | `PUT /api/sql/records/{source_row}` | `PUT /api/mongodb/records/{source_row}` | Update traffic volume, timestamp, holiday, or weather fields |
| **Delete (DELETE)** | `DELETE /api/sql/records/{source_row}` | `DELETE /api/mongodb/records/{source_row}` | Delete an observation by `source_row` |

### Starting the API Server

Make sure your `.env` file (or environment variables) is configured for MySQL and MongoDB, then run:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI / Swagger documentation is available at:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### Verifying Task 3 Endpoints

Run [verify_task3_api.py](scripts/verify_task3_api.py) to execute end-to-end tests of all MySQL and MongoDB CRUD and time-series endpoints and generate [task3_api_results.md](outputs/task3_api_results.md):

```bash
python scripts/verify_task3_api.py
```

To verify directly against live MySQL and MongoDB containers, pass `--live`:

```bash
python scripts/verify_task3_api.py --live
```

### Part 4: Prediction script

predict.py connects the earlier parts. It:

fetches the 24 most recent observations from the API (/api/sql/records/recent or /api/mongodb/records/recent),
rebuilds the Part 1 features: hour, day of week, month, lag-1, lag-24 and the 24-observation moving average,
loads the trained Random Forest from models/random_forest.joblib,
predicts the traffic volume of the next observation (one hour after the latest record by default).

The notebook does not save its model, so train_model.py repeats the Part 1 feature engineering, chronological split and tuned Random Forest settings (200 trees, depth 20) and saves the result. It reproduces the Part 1 test results (MAE 149.60, RMSE 236.63, R² 0.9857).

```bash
pip install -r requirements.txt
python scripts/prepare_data.py Data/Metro_Interstate_Traffic_Volume.csv
python scripts/train_model.py
uvicorn api.main:app --host 127.0.0.1 --port 8000     # in a second terminal
python scripts/predict.py --database mongodb          # or --database sql
```
Options: --api-url (default http://127.0.0.1:8000), --model-path, and --target-time to forecast a specific timestamp after the latest record, for example --target-time "2018-10-01 08:00".

Example output:

```text
Source: mongodb endpoint at http://127.0.0.1:8000
Observations used: 24 (2018-09-30 00:00:00 to 2018-09-30 23:00:00)
Latest traffic volume: 954
Forecast for: 2018-10-01 00:00:00
 hour  day_of_week  month  traffic_lag_1  traffic_lag_24  traffic_ma_24
    0            0     10          954.0          1826.0        2504.29
Predicted traffic volume: 533
```

Because the dataset has gaps, lag-1 and lag-24 mean "previous observation" and "24 observations back", as in Part 1. The script prints a note when the 24 observations are not exactly one hour apart.

## Repository contents

```text
.
├── docker-compose.yml
├── README.md
├── requirements.txt
├── api/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   ├── mongodb_crud.py
│   ├── schemas.py
│   └── sql_crud.py
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
│   ├── query_actual_data.py
│   ├── verify_task3_api.py
│   ├── train_model.py
│   └── predict.py
├── outputs/
│   ├── task2_query_results.md
│   └── task3_api_results.md
└── data/                  # Local only; excluded from Git
    ├── Metro_Interstate_Traffic_Volume.csv
    └── cleaned_traffic.csv
```

## Part 1, Part 2, and Part 3 deliverables

The completed work documented here consists of the Part 1 traffic analysis and forecasting results, the Part 2 database schema, ERD, MongoDB document design, loaders, and query examples, and the Part 3 FastAPI CRUD and time-series query endpoints for both MySQL and MongoDB. The repository also includes reproducible query-equivalent results calculated from the cleaned dataset in [task2_query_results.md](outputs/task2_query_results.md) and full API endpoint verification outputs in [task3_api_results.md](outputs/task3_api_results.md).

The assignment submission is a PDF report and a link to the GitHub repository. The report for these completed parts should explain the Part 1 dataset preparation, analytical questions, visual findings and model experiments, the Part 2 schema, ERD, MongoDB design, and query results, the Part 3 CRUD and time-series API endpoints, and team contributions. Keep local data and database credentials private, and use clear commits to document contributions.
