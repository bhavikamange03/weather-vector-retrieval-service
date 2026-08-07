"""
National Weather Service API client.

Responsibilities:
- Call NWS API
- Fetch alerts
- Fetch forecast
- Normalize response
"""

import hashlib
from datetime import datetime

import requests


BASE_URL = "https://api.weather.gov"


HEADERS = {
    "User-Agent": "databricks-weather-intelligence-app"
}


def _get(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    return response.json()



def generate_id(value):

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()



def get_gridpoint(lat, lon):
    """
    Resolve coordinates into NWS grid.
    """

    url = (
        f"{BASE_URL}/points/{lat},{lon}"
    )

    return _get(url)



def get_alerts(state):

    """
    Fetch active alerts by state.
    """

    url = (
        f"{BASE_URL}/alerts/active"
        f"?area={state}"
    )

    return _get(url)



def get_forecast(url):

    return _get(url)



def normalize_alert(
    alert,
    location
):

    properties = alert["properties"]


    text = ""


    if properties.get("description"):
        text += properties["description"]


    if properties.get("instruction"):

        text += "\n\n"

        text += properties["instruction"]



    return {

        "id":
            properties["id"],

        "location":
            location,

        "source_type":
            "alert",

        "headline":
            properties.get("event"),


        "narrative_text":
            text,


        "issued_at":
            properties.get("effective"),


        "payload":
            alert
    }



def normalize_forecast(
    period,
    location
):

    text = period["detailedForecast"]


    return {

        "id":
            generate_id(
                location
                +
                period["name"]
                +
                text
            ),


        "location":
            location,


        "source_type":
            "forecast",


        "headline":
            period["name"],


        "narrative_text":
            text,


        "issued_at":
            datetime.utcnow(),


        "payload":
            period
    }



def fetch_weather_documents(
        location,
        lat,
        lon,
        state
):

    documents = []


    # 1. Alerts

    alerts = get_alerts(state)


    for item in alerts.get(
        "features",
        []
    ):

        documents.append(
            normalize_alert(
                item,
                location
            )
        )


    # 2. Forecast

    point = get_gridpoint(
        lat,
        lon
    )


    forecast_url = (
        point["properties"]
        ["forecast"]
    )


    forecast_data = get_forecast(
        forecast_url
    )


    for period in (
        forecast_data["properties"]["periods"]
    ):

        documents.append(
            normalize_forecast(
                period,
                location
            )
        )


    return documents