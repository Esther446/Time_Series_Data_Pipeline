use("time_series_traffic");

const traffic = db.getCollection("traffic_observations");

// 1. Latest observation.
traffic.find(
  {},
  {
    _id: 0,
    date_time: 1,
    traffic_volume: 1,
    holiday: 1,
    weather: 1
  }
).sort({ date_time: -1, source_row: -1 }).limit(1);

// 2. Observations in a half-open date range [start, end).
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
).sort({ date_time: 1, source_row: 1 });

// 3. Average traffic volume by hour of day.
traffic.aggregate([
  {
    $group: {
      _id: { $hour: "$date_time" },
      average_traffic_volume: { $avg: "$traffic_volume" },
      observation_count: { $sum: 1 }
    }
  },
  { $sort: { _id: 1 } }
]);

// 4. Average traffic volume for observations recorded on holidays.
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
]);
