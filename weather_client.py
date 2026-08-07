"""
National Weather Service API client.

Responsibilities:
- Call NWS API
- Fetch alerts
- Fetch forecast
- Normalize responses into weather document schema
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


def normalize_timestamp(value):
    """
    Convert NWS timestamp values into database-friendly values.
    PostgreSQL TIMESTAMP accepts string/datetime, not dict.
    """

    if isinstance(value, str):
        return value

    return None


def get_gridpoint(lat, lon):
    """
    Resolve coordinates into NWS grid point.
    """

    url = (
        f"{BASE_URL}/points/{lat},{lon}"
    )

    return _get(url)


def get_alerts(state):
    """
    Fetch active weather alerts by state.
    """

    url = (
        f"{BASE_URL}/alerts/active"
        f"?area={state}"
    )

    return _get(url)


def get_forecast(url):
    """
    Fetch forecast data.
    """

    return _get(url)


def get_forecast_discussion(gridpoint_url):
    """
    Fetch area forecast discussion (AFD) - detailed weather analysis.
    """

    return _get(gridpoint_url)


def normalize_alert(
    alert,
    location
):
    """
    Convert NWS alert into weather document.
    """

    properties = alert.get(
        "properties",
        {}
    )

    text = ""

    if properties.get("description"):
        text += properties["description"]

    if properties.get("instruction"):

        text += "\n\n"

        text += properties["instruction"]


    return {

        "id":
            properties.get(
                "id"
            ),

        "location":
            location,

        "source_type":
            "alert",

        "headline":
            properties.get(
                "event"
            ),

        "narrative_text":
            text,

        "issued_at":
            normalize_timestamp(
                properties.get(
                    "effective"
                )
            ),

        "payload":
            alert
    }


def normalize_forecast(
    period,
    location
):
    """
    Convert forecast period into weather document.
    """

    text = period.get(
        "detailedForecast",
        ""
    )


    return {

        "id":
            generate_id(
                location
                +
                period.get("name", "")
                +
                text
            ),

        "location":
            location,

        "source_type":
            "forecast",

        "headline":
            period.get(
                "name"
            ),

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
    """
    Fetch and normalize weather documents.

    Returns:
        List[dict]
    """

    documents = []


    # -------------------------
    # 1. Weather Alerts
    # -------------------------

    alerts = get_alerts(
        state
    )


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


    # -------------------------
    # 2. Forecast
    # -------------------------

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


    periods = (
        forecast_data
        .get("properties", {})
        .get("periods", [])
    )


    for period in periods:

        documents.append(
            normalize_forecast(
                period,
                location
            )
        )


    return documents