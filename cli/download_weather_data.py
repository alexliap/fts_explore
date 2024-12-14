import argparse
import os

import openmeteo_requests
import pandas as pd
import requests_cache
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from retry_requests import retry


def load_hourly_values(response: WeatherApiResponse):
    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_rain = hourly.Variables(1).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
    hourly_wind_speed_100m = hourly.Variables(3).ValuesAsNumpy()
    hourly_wind_direction_10m = hourly.Variables(4).ValuesAsNumpy()
    hourly_wind_direction_100m = hourly.Variables(5).ValuesAsNumpy()
    hourly_wind_gusts_10m = hourly.Variables(6).ValuesAsNumpy()
    hourly_soil_temperature_0_to_7cm = hourly.Variables(7).ValuesAsNumpy()
    hourly_soil_temperature_7_to_28cm = hourly.Variables(8).ValuesAsNumpy()
    hourly_soil_temperature_28_to_100cm = hourly.Variables(9).ValuesAsNumpy()
    hourly_soil_temperature_100_to_255cm = hourly.Variables(10).ValuesAsNumpy()
    hourly_soil_moisture_0_to_7cm = hourly.Variables(11).ValuesAsNumpy()
    hourly_soil_moisture_7_to_28cm = hourly.Variables(12).ValuesAsNumpy()
    hourly_soil_moisture_28_to_100cm = hourly.Variables(13).ValuesAsNumpy()
    hourly_soil_moisture_100_to_255cm = hourly.Variables(14).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }

    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["rain"] = hourly_rain
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
    hourly_data["wind_speed_100m"] = hourly_wind_speed_100m
    hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
    hourly_data["wind_direction_100m"] = hourly_wind_direction_100m
    hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
    hourly_data["soil_temperature_0_to_7cm"] = hourly_soil_temperature_0_to_7cm
    hourly_data["soil_temperature_7_to_28cm"] = hourly_soil_temperature_7_to_28cm
    hourly_data["soil_temperature_28_to_100cm"] = hourly_soil_temperature_28_to_100cm
    hourly_data["soil_temperature_100_to_255cm"] = hourly_soil_temperature_100_to_255cm
    hourly_data["soil_moisture_0_to_7cm"] = hourly_soil_moisture_0_to_7cm
    hourly_data["soil_moisture_7_to_28cm"] = hourly_soil_moisture_7_to_28cm
    hourly_data["soil_moisture_28_to_100cm"] = hourly_soil_moisture_28_to_100cm
    hourly_data["soil_moisture_100_to_255cm"] = hourly_soil_moisture_100_to_255cm

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    return hourly_dataframe


def load_daily_values(response: WeatherApiResponse):
    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_temperature_2m_mean = daily.Variables(0).ValuesAsNumpy()
    daily_wind_speed_10m_max = daily.Variables(1).ValuesAsNumpy()
    daily_wind_gusts_10m_max = daily.Variables(2).ValuesAsNumpy()
    daily_wind_direction_10m_dominant = daily.Variables(3).ValuesAsNumpy()

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
    daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max
    daily_data["wind_gusts_10m_max"] = daily_wind_gusts_10m_max
    daily_data["wind_direction_10m_dominant"] = daily_wind_direction_10m_dominant

    daily_dataframe = pd.DataFrame(data=daily_data)

    return daily_dataframe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your program")
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=10)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"
    cities = ["Athens", "Napoli", "Palermo", "Smurni"]
    params = {
        "latitude": [37.9838, 40.8762, 38.132, 38.4127],
        "longitude": [23.7278, 14.5195, 13.3356, 27.1384],
        "start_date": "2020-01-01",
        "end_date": "2024-11-30",
        "hourly": [
            "temperature_2m",
            "rain",
            "wind_speed_10m",
            "wind_speed_100m",
            "wind_direction_10m",
            "wind_direction_100m",
            "wind_gusts_10m",
            "soil_temperature_0_to_7cm",
            "soil_temperature_7_to_28cm",
            "soil_temperature_28_to_100cm",
            "soil_temperature_100_to_255cm",
            "soil_moisture_0_to_7cm",
            "soil_moisture_7_to_28cm",
            "soil_moisture_28_to_100cm",
            "soil_moisture_100_to_255cm",
        ],
        "daily": [
            "temperature_2m_mean",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "wind_direction_10m_dominant",
        ],
    }
    responses = openmeteo.weather_api(url, params=params)

    for city, response in zip(cities, responses):
        hourly, daily = load_hourly_values(response), load_daily_values(response)

        hourly = hourly.rename({"date": "DateUTC"}, axis=1)
        hourly["DateUTC"] = hourly["DateUTC"].dt.tz_localize(None)

        daily = daily.rename({"date": "DateUTC"}, axis=1)
        daily["DateUTC"] = daily["DateUTC"].dt.tz_localize(None)

        hourly.to_csv(
            os.path.join(args.dir, f"weather_{city}_hourly_20_24.csv"), index=False
        )
        daily.to_csv(
            os.path.join(args.dir, f"weather_{city}_daily_20_24.csv"), index=False
        )
