"""Weekly lineup and matchup calculations."""

from typing import Any

from draft_logic import normalize_position
from schedule_data import get_bye_week


def find_roster_matchup(
    matchups: list[dict] | None,
    roster_id: int | str | None,
) -> dict | None:
    """Find the weekly matchup record for one roster."""

    if roster_id is None:
        return None

    for matchup in matchups or []:
        if str(matchup.get("roster_id")) == str(roster_id):
            return matchup

    return None


def find_opponent_matchup(
    matchups: list[dict] | None,
    user_matchup: dict | None,
) -> dict | None:
    """Find the opponent sharing the user's matchup ID."""

    if not user_matchup:
        return None

    matchup_id = user_matchup.get("matchup_id")
    user_roster_id = user_matchup.get("roster_id")

    if matchup_id is None:
        return None

    for matchup in matchups or []:
        if matchup.get("matchup_id") != matchup_id:
            continue

        if str(matchup.get("roster_id")) == str(
            user_roster_id
        ):
            continue

        return matchup

    return None


def build_weekly_lineup_rows(
    matchup: dict | None,
    nfl_players: dict[str, dict] | None,
    selected_week: int,
) -> list[dict[str, Any]]:
    """Build starter and bench rows from a Sleeper matchup."""

    if not matchup or not nfl_players:
        return []

    player_ids = [
        str(player_id)
        for player_id in matchup.get("players") or []
        if player_id not in {None, "0", 0}
    ]

    starter_ids = {
        str(player_id)
        for player_id in matchup.get("starters") or []
        if player_id not in {None, "0", 0}
    }

    players_points = matchup.get("players_points") or {}

    lineup_rows = []

    for player_id in player_ids:
        player_data = nfl_players.get(player_id)

        if not isinstance(player_data, dict):
            continue

        position = normalize_position(
            player_data.get("position"),
            player_id,
        )

        first_name = player_data.get("first_name") or ""
        last_name = player_data.get("last_name") or ""

        if position == "DEF":
            player_name = (
                player_data.get("full_name")
                or player_data.get("team")
                or player_id
            )
        else:
            player_name = f"{first_name} {last_name}".strip()

        team = (
            player_data.get("team")
            or (
                player_id
                if position == "DEF"
                else ""
            )
        )

        points = players_points.get(player_id, 0)

        try:
            points = float(points)
        except (TypeError, ValueError):
            points = 0.0

        player_bye_week = get_bye_week(team)

        on_bye = (
            player_bye_week is not None
            and int(player_bye_week) == int(selected_week)
        )

        injury_status = (
            player_data.get("injury_status")
            or ""
        )

        lineup_rows.append(
            {
                "Lineup Status": (
                    "STARTER"
                    if player_id in starter_ids
                    else "BENCH"
                ),
                "Player Name": (
                    player_name
                    or player_id
                ),
                "Position": position,
                "NFL Team": team,
                "Bye Week": (
                    player_bye_week
                    if player_bye_week is not None
                    else "N/A"
                ),
                "On Bye": on_bye,
                "Injury Status": injury_status,
                "Week Points": round(points, 2),
                "Player ID": player_id,
            }
        )

    lineup_rows.sort(
        key=lambda player: (
            0
            if player["Lineup Status"] == "STARTER"
            else 1,
            player["Position"],
            player["Player Name"],
        )
    )

    return lineup_rows


def split_starters_and_bench(
    lineup_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate lineup rows into starters and bench."""

    starters = [
        player
        for player in lineup_rows
        if player.get("Lineup Status") == "STARTER"
    ]

    bench = [
        player
        for player in lineup_rows
        if player.get("Lineup Status") == "BENCH"
    ]

    return starters, bench