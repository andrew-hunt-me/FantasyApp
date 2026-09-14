"""Weather calculations for fantasy football decisions."""

from datetime import datetime
from typing import Any
from stadium_data import (
    get_stadium,
    is_weather_protected,
)
from zoneinfo import ZoneInfo



def find_nearest_forecast_hour(
    weather_data: dict | None,
    kickoff_time: datetime,
) -> dict[str, Any] | None:
    """Find the hourly forecast closest to kickoff."""

    if not weather_data:
        return None

    hourly = weather_data.get("hourly") or {}
    forecast_times = hourly.get("time") or []

    if not forecast_times:
        return None

    nearest_index = None
    nearest_difference = None

    for index, forecast_time in enumerate(forecast_times):
        try:
            parsed_time = datetime.fromisoformat(
                forecast_time
            )
        except (TypeError, ValueError):
            continue

        difference = abs(
            (
                parsed_time - kickoff_time
            ).total_seconds()
        )

        if (
            nearest_difference is None
            or difference < nearest_difference
        ):
            nearest_index = index
            nearest_difference = difference

    if nearest_index is None:
        return None

    def get_hourly_value(
        field_name: str,
        default: float = 0.0,
    ) -> float:
        values = hourly.get(field_name) or []

        if nearest_index >= len(values):
            return default

        try:
            return float(
                values[nearest_index] or default
            )
        except (TypeError, ValueError):
            return default

    return {
        "Forecast Time": forecast_times[nearest_index],
        "Temperature F": get_hourly_value(
            "temperature_2m"
        ),
        "Precipitation Probability": get_hourly_value(
            "precipitation_probability"
        ),
        "Precipitation Inches": get_hourly_value(
            "precipitation"
        ),
        "Wind Speed MPH": get_hourly_value(
            "wind_speed_10m"
        ),
        "Wind Gust MPH": get_hourly_value(
            "wind_gusts_10m"
        ),
        "Weather Code": get_hourly_value(
            "weather_code"
        ),
    }


def calculate_weather_adjustment(
    position: str,
    temperature_f: float,
    precipitation_probability: float,
    wind_speed_mph: float,
    wind_gust_mph: float,
    indoor_game: bool = False,
) -> tuple[float, str]:
    """Calculate a modest fantasy adjustment for game weather."""

    if indoor_game:
        return 0.0, "Indoor or weather-protected game"

    position = str(position or "").upper().strip()

    adjustment = 0.0
    reasons = []

    if wind_speed_mph >= 20 or wind_gust_mph >= 30:
        if position == "QB":
            adjustment -= 5.0
            reasons.append("High wind affects passing")

        elif position == "WR":
            adjustment -= 4.0
            reasons.append("High wind affects receiving")

        elif position == "TE":
            adjustment -= 2.0
            reasons.append("High wind affects receiving")

        elif position == "K":
            adjustment -= 8.0
            reasons.append("High wind affects kicking")

        elif position == "RB":
            adjustment += 1.0
            reasons.append("High wind may favor rushing")

        elif position == "DEF":
            adjustment += 2.0
            reasons.append(
                "High wind may increase offensive mistakes"
            )

    elif wind_speed_mph >= 15 or wind_gust_mph >= 25:
        if position == "QB":
            adjustment -= 2.0
            reasons.append("Moderate wind")

        elif position == "WR":
            adjustment -= 1.5
            reasons.append("Moderate wind")

        elif position == "K":
            adjustment -= 3.0
            reasons.append("Moderate wind affects kicking")

    if precipitation_probability >= 70:
        if position == "QB":
            adjustment -= 2.0
        elif position == "WR":
            adjustment -= 2.0
        elif position == "K":
            adjustment -= 2.0
        elif position == "RB":
            adjustment += 1.0
        elif position == "DEF":
            adjustment += 1.0

        reasons.append("High precipitation risk")

    if temperature_f <= 20:
        if position in {"QB", "WR", "TE", "K"}:
            adjustment -= 2.0

        reasons.append("Extreme cold")

    elif temperature_f >= 95:
        adjustment -= 1.0
        reasons.append("Extreme heat")

    adjustment = max(
        min(adjustment, 5.0),
        -10.0,
    )

    if not reasons:
        reasons.append("No significant weather impact")

    return (
        round(adjustment, 1),
        ", ".join(dict.fromkeys(reasons)),
    )

def get_team_weather_location(
    team: str,
) -> tuple[float, float] | None:
    """Return stadium coordinates."""

    stadium = get_stadium(team)

    if not stadium:
        return None

    return (
        stadium["latitude"],
        stadium["longitude"],
    )

def classify_weather_risk(
    wind_speed_mph: float,
    wind_gust_mph: float,
    precipitation_probability: float,
    indoor_game: bool,
) -> str:
    """Convert weather data into a simple fantasy risk level."""

    if indoor_game:
        return "NONE"

    risk_score = 0

    if wind_speed_mph >= 20:
        risk_score += 3

    elif wind_speed_mph >= 15:
        risk_score += 1

    if wind_gust_mph >= 30:
        risk_score += 2

    if precipitation_probability >= 70:
        risk_score += 2

    elif precipitation_probability >= 40:
        risk_score += 1

    if risk_score >= 5:
        return "HIGH"

    if risk_score >= 2:
        return "MEDIUM"

    return "LOW"

def normalize_team_abbreviation(
    team: str | None,
) -> str:
    """Normalize team abbreviations used by schedule data."""

    normalized_team = str(
        team or ""
    ).upper().strip()

    aliases = {
        "JAC": "JAX",
        "WSH": "WAS",
        "LA": "LAR",
    }

    return aliases.get(
        normalized_team,
        normalized_team,
    )

def find_team_schedule_game(
    schedule_rows: list[dict] | None,
    team: str,
    week: int,
) -> dict | None:
    """Find one team's scheduled NFL game for a week."""

    selected_team = normalize_team_abbreviation(
        team
    )

    try:
        selected_week = int(week)
    except (TypeError, ValueError):
        return None

    for game in schedule_rows or []:
        if not isinstance(game, dict):
            continue

        try:
            game_week = int(
                game.get("week", 0) or 0
            )
        except (TypeError, ValueError):
            continue

        if game_week != selected_week:
            continue

        home_team = normalize_team_abbreviation(
            game.get("home")
            or game.get("home_team")
        )

        away_team = normalize_team_abbreviation(
            game.get("away")
            or game.get("away_team")
        )

        if selected_team not in {
            home_team,
            away_team,
        }:
            continue

        return {
            "home_team": home_team,
            "away_team": away_team,
            "week": game_week,
            "raw_game": game,
        }

    return None
def parse_sleeper_kickoff(
    game: dict | None,
) -> datetime | None:
    """Parse a Sleeper game kickoff as an aware UTC datetime."""

    if not game:
        return None

    raw_game = game.get(
        "raw_game",
        game,
    )

    timestamp_fields = [
        "start_time",
        "start_time_ms",
        "kickoff",
        "kickoff_time",
        "date",
    ]

    raw_value = None

    for field_name in timestamp_fields:
        value = raw_game.get(field_name)

        if value is not None:
            raw_value = value
            break

    if raw_value is None:
        return None

    if isinstance(raw_value, (int, float)):
        numeric_timestamp = float(raw_value)

        if numeric_timestamp > 10_000_000_000:
            numeric_timestamp /= 1000.0

        return datetime.fromtimestamp(
            numeric_timestamp,
            tz=ZoneInfo("UTC"),
        )

    raw_text = str(raw_value).strip()

    if raw_text.isdigit():
        numeric_timestamp = float(raw_text)

        if numeric_timestamp > 10_000_000_000:
            numeric_timestamp /= 1000.0

        return datetime.fromtimestamp(
            numeric_timestamp,
            tz=ZoneInfo("UTC"),
        )

    try:
        normalized_text = raw_text.replace(
            "Z",
            "+00:00",
        )

        parsed_datetime = datetime.fromisoformat(
            normalized_text
        )

        if parsed_datetime.tzinfo is None:
            parsed_datetime = parsed_datetime.replace(
                tzinfo=ZoneInfo("UTC")
            )

        return parsed_datetime.astimezone(
            ZoneInfo("UTC")
        )

    except ValueError:
        return None

def build_team_game_context(
    team: str,
    schedule_events: list[dict] | None,
) -> dict:
    """Build schedule and venue context for one NFL team."""

    selected_team = normalize_team_abbreviation(
        team
    )

    scheduled_game = find_team_espn_game(
        schedule_events=schedule_events,
        team=selected_team,
    )

    if scheduled_game is None:
        return {
            "Opponent": "",
            "Matchup": "",
            "Home or Away": "",
            "Home Team": "",
            "Away Team": "",
            "Stadium Team": "",
            "Stadium": "",
            "Stadium City": "",
            "Roof Type": "Unknown",
            "Indoor": False,
            "Kickoff UTC": None,
            "Kickoff Houston": "",
            "Kickoff Stadium": "",
            "Scheduled Game": None,
        }

    home_team = scheduled_game["home_team"]
    away_team = scheduled_game["away_team"]

    if selected_team == home_team:
        home_or_away = "HOME"
        opponent = away_team
    else:
        home_or_away = "AWAY"
        opponent = home_team

    stadium_metadata = get_stadium(
        home_team
    ) or {}

    kickoff_utc = scheduled_game.get(
        "kickoff_utc"
    )

    stadium_timezone_name = stadium_metadata.get(
        "timezone",
        "America/Chicago",
    )

    kickoff_houston_text = ""
    kickoff_stadium_text = ""

    if kickoff_utc is not None:
        houston_kickoff = kickoff_utc.astimezone(
            ZoneInfo("America/Chicago")
        )

        stadium_kickoff = kickoff_utc.astimezone(
            ZoneInfo(stadium_timezone_name)
        )

        kickoff_houston_text = (
            houston_kickoff.strftime(
                "%a %b %d, %I:%M %p %Z"
            )
        )

        kickoff_stadium_text = (
            stadium_kickoff.strftime(
                "%a %b %d, %I:%M %p %Z"
            )
        )

    espn_indoor = scheduled_game.get(
        "indoor",
        False,
    )

    roof_type = stadium_metadata.get(
        "roof_type",
        "",
    )

    if not roof_type and espn_indoor:
        roof_type = "indoor"
    elif not roof_type:
        roof_type = "unknown"

    return {
        "Opponent": opponent,
        "Matchup": f"{away_team} at {home_team}",
        "Home or Away": home_or_away,
        "Home Team": home_team,
        "Away Team": away_team,
        "Stadium Team": home_team,
        "Stadium": (
            scheduled_game.get("stadium")
            or stadium_metadata.get("stadium")
            or ""
        ),
        "Stadium City": (
            scheduled_game.get("stadium_city")
            or stadium_metadata.get("city")
            or ""
        ),
        "Roof Type": str(roof_type).title(),
        "Indoor": bool(
            espn_indoor
            or roof_type == "dome"
        ),
        "Kickoff UTC": kickoff_utc,
        "Kickoff Houston": kickoff_houston_text,
        "Kickoff Stadium": kickoff_stadium_text,
        "Scheduled Game": scheduled_game,
    }
def get_espn_team_abbreviation(
    competitor: dict | None,
) -> str:
    """Return a normalized team abbreviation from ESPN data."""

    competitor = competitor or {}
    team_data = competitor.get("team") or {}

    abbreviation = (
        team_data.get("abbreviation")
        or team_data.get("shortDisplayName")
        or ""
    )

    return normalize_team_abbreviation(
        abbreviation
    )

def parse_espn_schedule_event(
    event: dict | None,
) -> dict | None:
    """Normalize one ESPN NFL schedule event."""

    if not isinstance(event, dict):
        return None

    competitions = event.get("competitions") or []

    if not competitions:
        return None

    competition = competitions[0]

    competitors = competition.get(
        "competitors",
        [],
    )

    home_team = ""
    away_team = ""

    for competitor in competitors:
        team_abbreviation = (
            get_espn_team_abbreviation(
                competitor
            )
        )

        home_away = str(
            competitor.get("homeAway") or ""
        ).lower()

        if home_away == "home":
            home_team = team_abbreviation
        elif home_away == "away":
            away_team = team_abbreviation

    raw_kickoff = (
        competition.get("date")
        or event.get("date")
    )

    kickoff_utc = None

    if raw_kickoff:
        try:
            normalized_kickoff = str(
                raw_kickoff
            ).replace(
                "Z",
                "+00:00",
            )

            kickoff_utc = datetime.fromisoformat(
                normalized_kickoff
            )

            if kickoff_utc.tzinfo is None:
                kickoff_utc = kickoff_utc.replace(
                    tzinfo=ZoneInfo("UTC")
                )

            kickoff_utc = kickoff_utc.astimezone(
                ZoneInfo("UTC")
            )

        except ValueError:
            kickoff_utc = None

    venue = competition.get("venue") or {}

    address = venue.get("address") or {}

    city = address.get("city") or ""
    state = address.get("state") or ""

    venue_location = ", ".join(
        part
        for part in [city, state]
        if part
    )

    return {
        "event_id": str(event.get("id") or ""),
        "event_name": (
            event.get("name")
            or (
                f"{away_team} at {home_team}"
                if away_team and home_team
                else ""
            )
        ),
        "home_team": home_team,
        "away_team": away_team,
        "kickoff_utc": kickoff_utc,
        "stadium": venue.get("fullName") or "",
        "stadium_city": venue_location,
        "indoor": bool(venue.get("indoor", False)),
        "raw_event": event,
    }

def find_team_espn_game(
    schedule_events: list[dict] | None,
    team: str,
) -> dict | None:
    """Find one NFL team's game in an ESPN weekly schedule."""

    selected_team = normalize_team_abbreviation(
        team
    )

    for event in schedule_events or []:
        normalized_event = (
            parse_espn_schedule_event(
                event
            )
        )

        if not normalized_event:
            continue

        if selected_team in {
            normalized_event["home_team"],
            normalized_event["away_team"],
        }:
            return normalized_event

    return None