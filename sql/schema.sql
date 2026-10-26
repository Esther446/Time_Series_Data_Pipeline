CREATE DATABASE IF NOT EXISTS time_series_traffic
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE time_series_traffic;

CREATE TABLE IF NOT EXISTS holidays (
    holiday_id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    holiday_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (holiday_id),
    UNIQUE KEY uq_holidays_name (holiday_name)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS weather_observations (
    weather_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    temp DECIMAL(12, 8) NULL,
    rain_1h DECIMAL(12, 8) NULL,
    snow_1h DECIMAL(12, 8) NULL,
    clouds_all DECIMAL(12, 8) NULL,
    weather_main VARCHAR(50) NULL,
    weather_description VARCHAR(255) NULL,
    PRIMARY KEY (weather_id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS traffic_observations (
    traffic_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_row BIGINT UNSIGNED NOT NULL,
    date_time DATETIME NOT NULL,
    traffic_volume INT UNSIGNED NOT NULL,
    holiday_id SMALLINT UNSIGNED NULL,
    weather_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (traffic_id),
    UNIQUE KEY uq_traffic_source_row (source_row),
    KEY idx_traffic_date_time (date_time),
    CONSTRAINT fk_traffic_holiday
        FOREIGN KEY (holiday_id) REFERENCES holidays (holiday_id),
    CONSTRAINT fk_traffic_weather
        FOREIGN KEY (weather_id) REFERENCES weather_observations (weather_id)
) ENGINE = InnoDB;
