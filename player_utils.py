"""Shared player and team normalization utilities."""

from config import NFL_TEAM_ABBREVIATIONS


def normalize_team_abbreviation(
    team: str | None,
) -> str:
    """Return a consistent NFL team abbreviation."""

    normalized_team = str(team or "").upper().strip()

    team_aliases = {
        "JAC": "JAX",
        "WSH": "WAS",
        "LA": "LAR",
    }

    return team_aliases.get(
        normalized_team,
        normalized_team,
    )


def normalize_position(
    position: str | None,
    player_id: str | None = None,
) -> str:
    """Return a consistent fantasy position."""

    normalized_position = str(
        position or ""
    ).upper().strip()

    normalized_player_id = normalize_team_abbreviation(
        player_id
    )

    if normalized_position in {
        "D/ST",
        "DST",
        "DEFENSE",
    }:
        return "DEF"

    if normalized_player_id in NFL_TEAM_ABBREVIATIONS:
        return "DEF"

    return normalized_position


def format_player_name(
    player_data: dict | None,
    player_id: str | None = None,
) -> str:
    """Return a player's best available display name."""

    player_data = player_data or {}
    normalized_player_id = str(player_id or "")

    position = normalize_position(
        player_data.get("position"),
        normalized_player_id,
    )

    if position == "DEF":
        return (
            player_data.get("full_name")
            or player_data.get("team")
            or normalized_player_id
        )

    first_name = player_data.get("first_name") or ""
    last_name = player_data.get("last_name") or ""

    full_name = f"{first_name} {last_name}".strip()

    return (
        full_name
        or player_data.get("full_name")
        or normalized_player_id
    )


def normalize_injury_status(
    injury_status: str | None,
) -> str:
    """Return a consistent injury-status abbreviation."""

    normalized_status = str(
        injury_status or ""
    ).upper().strip()

    status_aliases = {
        "QUESTIONABLE": "Q",
        "DOUBTFUL": "D",
        "OUT": "OUT",
        "INJURED RESERVE": "IR",
        "PUP": "PUP",
    }

    return status_aliases.get(
        normalized_status,
        normalized_status,
    )