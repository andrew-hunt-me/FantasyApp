"""Functions for retrieving public data from the Sleeper API."""

from typing import Any

import requests
import streamlit as st

from config import SLEEPER_API


def _request_json(
    url: str,
    timeout: int = 10,
) -> Any | None:
    """Request JSON data and return None when the request fails."""

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        return None


@st.cache_data(ttl=300)
def get_sleeper_user(username: str) -> dict | None:
    """Retrieve a Sleeper user by username or user ID."""

    username = username.strip()

    if not username:
        return None

    url = f"{SLEEPER_API}/user/{username}"
    return _request_json(url)


@st.cache_data(ttl=300)
def get_user_leagues(
    user_id: str,
    season: str,
) -> list[dict] | None:
    """Retrieve a user's NFL leagues for a season."""

    url = (
        f"{SLEEPER_API}/user/"
        f"{user_id}/leagues/nfl/{season}"
    )

    return _request_json(url)


@st.cache_data(ttl=120)
def get_league_drafts(
    league_id: str,
) -> list[dict] | None:
    """Retrieve the drafts associated with a league."""

    url = f"{SLEEPER_API}/league/{league_id}/drafts"
    return _request_json(url)


@st.cache_data(ttl=15)
def get_draft_picks(
    draft_id: str,
) -> list[dict] | None:
    """Retrieve completed picks from a draft."""

    url = f"{SLEEPER_API}/draft/{draft_id}/picks"
    return _request_json(url)


@st.cache_data(ttl=120)
def get_league_rosters(
    league_id: str,
) -> list[dict] | None:
    """Retrieve all rosters in a league."""

    url = f"{SLEEPER_API}/league/{league_id}/rosters"
    return _request_json(url)


@st.cache_data(ttl=86400)
def get_nfl_players() -> dict | None:
    """Retrieve Sleeper's complete NFL player directory."""

    url = f"{SLEEPER_API}/players/nfl"
    return _request_json(url, timeout=60)


@st.cache_data(ttl=300)
def get_trending_players(
    trend_type: str = "add",
    lookback_hours: int = 24,
    limit: int = 50,
) -> list[dict] | None:
    """Retrieve trending player adds or drops."""

    if trend_type not in {"add", "drop"}:
        raise ValueError(
            "trend_type must be either 'add' or 'drop'."
        )

    url = (
        f"{SLEEPER_API}/players/nfl/trending/"
        f"{trend_type}"
        f"?lookback_hours={lookback_hours}"
        f"&limit={limit}"
    )

    return _request_json(url)

@st.cache_data(ttl=60)
def get_league_matchups(
    league_id: str,
    week: int,
) -> list[dict] | None:
    """Retrieve every matchup entry for a league week."""

    try:
        week_number = int(week)
    except (TypeError, ValueError):
        return None

    if week_number < 1 or week_number > 18:
        return None

    url = (
        f"{SLEEPER_API}/league/"
        f"{league_id}/matchups/{week_number}"
    )

    return _request_json(url)

@st.cache_data(ttl=3600)
def get_weekly_projections(
    season: str,
    week: int,
) -> list[dict] | None:
    """Retrieve Sleeper NFL projections for one week."""

    try:
        week_number = int(week)
    except (TypeError, ValueError):
        return None

    if week_number < 1 or week_number > 18:
        return None

    url = (
        f"https://api.sleeper.com/projections/nfl/"
        f"{season}/{week_number}"
        f"?season_type=regular"
    )

    return _request_json(
        url,
        timeout=30,
    )
@st.cache_data(ttl=3600)
def get_weekly_stats(
    season: str,
    week: int,
) -> list[dict] | None:
    """Retrieve Sleeper NFL statistics for one completed week."""

    try:
        week_number = int(week)
    except (TypeError, ValueError):
        return None

    if week_number < 1 or week_number > 18:
        return None

    url = (
        f"https://api.sleeper.com/stats/nfl/"
        f"{season}/{week_number}"
        f"?season_type=regular"
    )

    return _request_json(
        url,
        timeout=30,
    )

@st.cache_data(ttl=1800)
def get_game_weather(
    latitude: float,
    longitude: float,
) -> dict | None:
    """Retrieve hourly weather for a stadium location."""

    url = "https://api.open-meteo.com/v1/forecast"

    parameters = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,"
            "precipitation_probability,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m,"
            "wind_gusts_10m"
        ),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "forecast_days": 16,
    }

    try:
        response = requests.get(
            url,
            params=parameters,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        return None

@st.cache_data(ttl=3600)
def get_nfl_schedule(
    season: str,
    season_type: str = "regular",
) -> list[dict] | None:
    """Retrieve the real NFL schedule from Sleeper."""

    normalized_season = str(season).strip()
    normalized_type = str(
        season_type
    ).lower().strip()

    if not normalized_season.isdigit():
        return None

    if normalized_type not in {
        "regular",
        "pre",
        "post",
    }:
        normalized_type = "regular"

    url = (
        f"https://api.sleeper.com/schedule/nfl/"
        f"{normalized_type}/{normalized_season}"
    )

    return _request_json(
        url,
        timeout=30,
    )

@st.cache_data(ttl=3600)
def get_nfl_week_schedule(
    season: str,
    week: int,
) -> list[dict] | None:
    """Retrieve one NFL week's schedule from ESPN."""

    try:
        season_value = int(season)
        week_value = int(week)
    except (TypeError, ValueError):
        return None

    if week_value < 1 or week_value > 18:
        return None

    url = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard"
    )

    parameters = {
        "dates": season_value,
        "seasontype": 2,
        "week": week_value,
        "limit": 100,
    }

    try:
        response = requests.get(
            url,
            params=parameters,
            timeout=30,
        )

        response.raise_for_status()
        response_data = response.json()

        return response_data.get(
            "events",
            [],
        )

    except (
        requests.RequestException,
        ValueError,
    ):
        return None