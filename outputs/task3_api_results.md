# Task 3 API CRUD & Time-Series Endpoint Verification Results

- **Dataset input:** `data/cleaned_traffic.csv` (40,575 cleaned observations)
- **Execution mode:** FastAPI TestClient against full 40,575-row MySQL & MongoDB fixtures

## MySQL Endpoints (`/api/sql/records`)

### 1. Latest Record — `GET /api/sql/records/latest`
- **Status:** `200 OK`
```json
{
  "source_row": 40575,
  "date_time": "2018-09-30T23:00:00",
  "traffic_volume": 954,
  "holiday": null,
  "weather": {
    "temp": 282.12,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 90.0,
    "weather_main": "Clouds",
    "weather_description": "overcast clouds"
  }
}
```

### 2. Records by Date Range — `GET /api/sql/records/date-range?start=2016-01-01T00:00:00&end=2016-02-01T00:00:00`
- **Status:** `200 OK`
- **Matching records returned:** **461**
- **First 2 records in range:**
```json
[
  {
    "source_row": 17492,
    "date_time": "2016-01-01T00:00:00",
    "traffic_volume": 1513,
    "holiday": "New Years Day",
    "weather": {
      "temp": 265.94,
      "rain_1h": 0.0,
      "snow_1h": 0.0,
      "clouds_all": 90.0,
      "weather_main": "Haze",
      "weather_description": "haze"
    }
  },
  {
    "source_row": 17493,
    "date_time": "2016-01-01T01:00:00",
    "traffic_volume": 1550,
    "holiday": null,
    "weather": {
      "temp": 266.0,
      "rain_1h": 0.0,
      "snow_1h": 0.0,
      "clouds_all": 90.0,
      "weather_main": "Snow",
      "weather_description": "light snow"
    }
  }
]
```

### 3. Create Record (POST) — `POST /api/sql/records`
- **Status:** `201 Created`
```json
{
  "source_row": 40576,
  "date_time": "2018-10-01T00:00:00",
  "traffic_volume": 1240,
  "holiday": null,
  "weather": {
    "temp": 282.45,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 75.0,
    "weather_main": "Clouds",
    "weather_description": "broken clouds"
  }
}
```

### 4. Read Record by ID (GET) — `GET /api/sql/records/40576`
- **Status:** `200 OK`
```json
{
  "source_row": 40576,
  "date_time": "2018-10-01T00:00:00",
  "traffic_volume": 1240,
  "holiday": null,
  "weather": {
    "temp": 282.45,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 75.0,
    "weather_main": "Clouds",
    "weather_description": "broken clouds"
  }
}
```

### 5. Update Record (PUT) — `PUT /api/sql/records/40576`
- **Status:** `200 OK`
```json
{
  "source_row": 40576,
  "date_time": "2018-10-01T00:00:00",
  "traffic_volume": 1580,
  "holiday": "Test Regional Holiday",
  "weather": {
    "temp": 284.0,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 20.0,
    "weather_main": "Clear",
    "weather_description": "sky is clear"
  }
}
```

### 6. Delete Record (DELETE) — `DELETE /api/sql/records/40576`
- **Status:** `200 OK` (subsequent GET verified `404 Not Found`)
```json
{
  "database": "mysql",
  "source_row": 40576,
  "deleted": true,
  "message": "Deleted traffic observation source_row=40576 from MySQL."
}
```

## MongoDB Endpoints (`/api/mongodb/records`)

### 1. Latest Record — `GET /api/mongodb/records/latest`
- **Status:** `200 OK`
```json
{
  "source_row": 40575,
  "date_time": "2018-09-30T23:00:00",
  "traffic_volume": 954,
  "holiday": null,
  "weather": {
    "temp": 282.12,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 90.0,
    "weather_main": "Clouds",
    "weather_description": "overcast clouds"
  }
}
```

### 2. Records by Date Range — `GET /api/mongodb/records/date-range?start=2016-01-01T00:00:00&end=2016-02-01T00:00:00`
- **Status:** `200 OK`
- **Matching records returned:** **461**
- **First 2 records in range:**
```json
[
  {
    "source_row": 17492,
    "date_time": "2016-01-01T00:00:00",
    "traffic_volume": 1513,
    "holiday": "New Years Day",
    "weather": {
      "temp": 265.94,
      "rain_1h": 0.0,
      "snow_1h": 0.0,
      "clouds_all": 90.0,
      "weather_main": "Haze",
      "weather_description": "haze"
    }
  },
  {
    "source_row": 17493,
    "date_time": "2016-01-01T01:00:00",
    "traffic_volume": 1550,
    "holiday": null,
    "weather": {
      "temp": 266.0,
      "rain_1h": 0.0,
      "snow_1h": 0.0,
      "clouds_all": 90.0,
      "weather_main": "Snow",
      "weather_description": "light snow"
    }
  }
]
```

### 3. Create Record (POST) — `POST /api/mongodb/records`
- **Status:** `201 Created`
```json
{
  "source_row": 40576,
  "date_time": "2018-10-01T00:00:00",
  "traffic_volume": 1240,
  "holiday": null,
  "weather": {
    "temp": 282.45,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 75.0,
    "weather_main": "Clouds",
    "weather_description": "broken clouds"
  }
}
```

### 4. Read Record by ID (GET) — `GET /api/mongodb/records/40576`
- **Status:** `200 OK`
```json
{
  "source_row": 40576,
  "date_time": "2018-10-01T00:00:00",
  "traffic_volume": 1240,
  "holiday": null,
  "weather": {
    "temp": 282.45,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 75.0,
    "weather_main": "Clouds",
    "weather_description": "broken clouds"
  }
}
```

### 5. Update Record (PUT) — `PUT /api/mongodb/records/40576`
- **Status:** `200 OK`
```json
{
  "source_row": 40576,
  "date_time": "2018-10-01T00:00:00",
  "traffic_volume": 1580,
  "holiday": "Test Regional Holiday",
  "weather": {
    "temp": 284.0,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 20.0,
    "weather_main": "Clear",
    "weather_description": "sky is clear"
  }
}
```

### 6. Delete Record (DELETE) — `DELETE /api/mongodb/records/40576`
- **Status:** `200 OK` (subsequent GET verified `404 Not Found`)
```json
{
  "database": "mongodb",
  "source_row": 40576,
  "deleted": true,
  "message": "Deleted traffic observation source_row=40576 from MongoDB."
}
```
