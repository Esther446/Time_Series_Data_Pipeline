USE time_series_traffic;

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
