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