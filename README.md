# Time Series Analysis and Forecasting

## Project Overview

This project explores time-series data analysis and forecasting through multiple tasks. It aims to identify patterns and trends in historical data, apply appropriate analytical and forecasting techniques, and evaluate model performance using relevant metrics.

Each part of the project focuses on its assigned analysis and methodology. The sections below document the datasets, approaches, findings, and results for each task.

---

# Part 1: Metro Interstate Traffic Volume Analysis and Forecasting

## 1. Objective

The objective of Part 1 is to analyze historical traffic volume data, identify temporal patterns and trends, and develop forecasting models using historical traffic observations.

## 2. Dataset

**Dataset:** Metro Interstate Traffic Volume

**Source:** [Metro Interstate Traffic Volume — Kaggle](https://www.kaggle.com/datasets/uciml/metro-interstate-traffic-volume)

The dataset contains 48,204 records and nine columns, including timestamps, traffic volume, weather conditions, and holiday information.

- **Target variable:** `traffic_volume`
- **Time column:** `date_time`

## 3. Data Preparation

The data preparation process included:

- Inspecting data types, missing values, and duplicate records.
- Investigating repeated timestamps and anomalous rainfall values.
- Handling missing values and consolidating repeated timestamps.
- Sorting observations chronologically.
- Preparing time-based and lag features for forecasting.

## 4. Exploratory Data Analysis

Six questions guided the exploratory analysis:

1. How does traffic volume vary by hour of the day?
2. How does average traffic differ between weekdays and weekends?
3. Which days of the week experience the highest and lowest traffic?
4. How does traffic volume vary by month?
5. What trends are visible through a moving average?
6. How strongly is traffic volume related to the previous available observation?

Visualizations were used to examine traffic patterns and communicate the findings.

## 5. Forecasting Methodology

Two regression models were developed and evaluated:

- **Linear Regression:** Baseline model.
- **Random Forest Regressor:** Model tuned using validation data.

The dataset was split chronologically into training (70%), validation (15%), and test (15%) sets to preserve temporal order. Model performance was assessed using Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and the coefficient of determination (R²).

## 6. Results

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Linear Regression | 487.17 | 676.41 | 0.8832 |
| Random Forest | 149.60 | 236.63 | 0.9857 |

The Random Forest model outperformed Linear Regression across all three test metrics, achieving lower prediction errors and a higher R² score.

## 7. Key Findings

- Average traffic volume was highest around 16:00 and lowest around 03:00.
- Weekday traffic was higher on average than weekend traffic.
- Friday had the highest average traffic by day of the week, while Sunday had the lowest.
- August had the highest average traffic by month, while December had the lowest.
- The Random Forest model captured traffic patterns effectively and achieved strong test performance.

## 8. Limitations

The dataset contains gaps and repeated timestamps. Consequently, lag features refer to previous available observations, which are not always exactly one hour apart. This limitation should be considered when interpreting the forecasting results.

