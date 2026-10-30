use("time_series_traffic");

const traffic = db.getCollection("traffic_observations");
const queryName = typeof selectedQuery === "undefined" ? "" : selectedQuery;

switch (queryName) {
  case "latest":
    print("Query 1: Latest observation");
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
    break;

  case "date-range":
    print("Query 2: Observations from 2016-01-01 to 2016-02-01");
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
    break;

  case "hourly-average":
    print("Query 3: Average traffic volume by hour");
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
    break;

  case "holiday-average":
    print("Query 4: Average traffic volume on holidays");
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
    break;

  default:
    throw new Error(
      "Choose one query: latest, date-range, hourly-average, or holiday-average."
    );
}