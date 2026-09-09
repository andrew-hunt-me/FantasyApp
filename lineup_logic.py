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
    projection_lookup: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Build starter and bench rows from a Sleeper matchup."""
    projection_lookup = projection_lookup or {}

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
        sleeper_rank = player_data.get(
            "search_rank"
        )

        projected_points = float(
            projection_lookup.get(
                player_id,
                0.0,
            )
        )

        lineup_value = calculate_lineup_value(
            sleeper_rank=sleeper_rank,
            injury_status=injury_status,
            on_bye=on_bye,
            projected_points=projected_points,
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
                "Projected Points": round(
                    projected_points,
                    2,
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
                "Sleeper Rank": (
                    sleeper_rank
                    if sleeper_rank is not None
                    else "N/A"
                ),
                "Lineup Value": lineup_value,
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

def calculate_lineup_value(
    sleeper_rank: int | float | None,
    injury_status: str,
    on_bye: bool,
    projected_points: float = 0.0,
) -> float:
    """Calculate a preliminary weekly lineup value."""

    try:
        numeric_rank = float(sleeper_rank)
    except (TypeError, ValueError):
        numeric_rank = 300.0

    rank_score = 100.0 * (
        300.0 - numeric_rank
    ) / 299.0

    rank_score = max(
        min(rank_score, 100.0),
        0.0,
    )

    normalized_injury = str(
        injury_status or ""
    ).upper()

    if normalized_injury in {"IR", "OUT"}:
        injury_penalty = 100.0
    elif normalized_injury in {"DOUBTFUL", "D"}:
        injury_penalty = 35.0
    elif normalized_injury in {"QUESTIONABLE", "Q"}:
        injury_penalty = 8.0
    else:
        injury_penalty = 0.0

    bye_penalty = 100.0 if on_bye else 0.0

    try:
        projection_value = max(
            float(projected_points),
            0.0,
        )
    except (TypeError, ValueError):
        projection_value = 0.0

    lineup_value = (
            0.35 * rank_score
            + 3.0 * projection_value
            - injury_penalty
            - bye_penalty
    )

    return round(
        max(lineup_value, 0.0),
        1,
    )

def optimize_weekly_lineup(
    lineup_rows: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Recommend starters for the configured lineup."""

    eligible_players = [
        player.copy()
        for player in lineup_rows
        if not player.get("On Bye", False)
        and str(
            player.get("Injury Status", "")
        ).upper() not in {"IR", "OUT"}
    ]

    eligible_players.sort(
        key=lambda player: (
            -float(player.get("Lineup Value", 0.0)),
            player.get("Player Name", ""),
        )
    )

    recommended_starters = []
    selected_player_ids = set()

    def select_players(
        position: str,
        quantity: int,
    ) -> None:
        candidates = [
            player
            for player in eligible_players
            if player.get("Position") == position
            and player.get("Player ID")
            not in selected_player_ids
        ]

        for player in candidates[:quantity]:
            recommended_starters.append(
                player.copy()
            )

            selected_player_ids.add(
                player.get("Player ID")
            )

    select_players("QB", 1)
    select_players("RB", 2)
    select_players("WR", 2)
    select_players("TE", 1)

    flex_candidates = [
        player
        for player in eligible_players
        if player.get("Position")
        in {"RB", "WR", "TE"}
        and player.get("Player ID")
        not in selected_player_ids
    ]

    for player in flex_candidates[:2]:
        flex_player = player.copy()
        flex_player["Recommended Slot"] = "FLEX"

        recommended_starters.append(
            flex_player
        )

        selected_player_ids.add(
            player.get("Player ID")
        )

    select_players("K", 1)
    select_players("DEF", 1)

    for player in recommended_starters:
        if "Recommended Slot" not in player:
            player["Recommended Slot"] = (
                player.get("Position", "")
            )

    recommended_bench = [
        player.copy()
        for player in lineup_rows
        if player.get("Player ID")
        not in selected_player_ids
    ]

    return recommended_starters, recommended_bench

def build_lineup_change_rows(
    current_starters: list[dict[str, Any]],
    recommended_starters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare the current lineup with the recommended lineup."""

    current_starter_ids = {
        str(player.get("Player ID"))
        for player in current_starters
    }

    recommended_starter_ids = {
        str(player.get("Player ID"))
        for player in recommended_starters
    }

    players_to_start = [
        player
        for player in recommended_starters
        if str(player.get("Player ID"))
        not in current_starter_ids
    ]

    players_to_bench = [
        player
        for player in current_starters
        if str(player.get("Player ID"))
        not in recommended_starter_ids
    ]

    change_rows = []

    maximum_changes = max(
        len(players_to_start),
        len(players_to_bench),
    )

    for index in range(maximum_changes):
        start_player = (
            players_to_start[index]
            if index < len(players_to_start)
            else {}
        )

        bench_player = (
            players_to_bench[index]
            if index < len(players_to_bench)
            else {}
        )

        start_value = float(
            start_player.get("Lineup Value", 0.0)
        )

        bench_value = float(
            bench_player.get("Lineup Value", 0.0)
        )

        change_rows.append(
            {
                "Start": start_player.get(
                    "Player Name",
                    "",
                ),
                "Start Position": start_player.get(
                    "Recommended Slot",
                    start_player.get("Position", ""),
                ),
                "Start Value": start_value,
                "Bench": bench_player.get(
                    "Player Name",
                    "",
                ),
                "Bench Position": bench_player.get(
                    "Position",
                    "",
                ),
                "Bench Value": bench_value,
                "Estimated Improvement": round(
                    start_value - bench_value,
                    1,
                ),
            }
        )

    return change_rows

def calculate_projected_fantasy_points(
    projected_stats: dict | None,
    scoring_settings: dict | None,
) -> float:
    """Calculate projected points using league scoring."""

    stats = projected_stats or {}
    scoring = scoring_settings or {}

    stat_to_scoring_key = {
        "pass_yd": "pass_yd",
        "pass_td": "pass_td",
        "pass_int": "pass_int",
        "pass_2pt": "pass_2pt",
        "rush_yd": "rush_yd",
        "rush_td": "rush_td",
        "rush_2pt": "rush_2pt",
        "rec": "rec",
        "rec_yd": "rec_yd",
        "rec_td": "rec_td",
        "rec_2pt": "rec_2pt",
        "fum_lost": "fum_lost",
        "xpm": "xpm",
        "xpmiss": "xpmiss",
        "fgm_0_19": "fgm_0_19",
        "fgm_20_29": "fgm_20_29",
        "fgm_30_39": "fgm_30_39",
        "fgm_40_49": "fgm_40_49",
        "fgm_50p": "fgm_50p",
        "fgmiss": "fgmiss",
        "sack": "sack",
        "int": "int",
        "fum_rec": "fum_rec",
        "ff": "ff",
        "safe": "safe",
        "blk_kick": "blk_kick",
        "def_td": "def_td",
        "def_st_td": "def_st_td",
    }

    projected_points = 0.0

    for stat_key, scoring_key in stat_to_scoring_key.items():
        try:
            stat_value = float(
                stats.get(stat_key, 0) or 0
            )

            point_value = float(
                scoring.get(scoring_key, 0) or 0
            )
        except (TypeError, ValueError):
            continue

        projected_points += stat_value * point_value

    return round(projected_points, 2)

def build_projection_lookup(
    projection_rows: list[dict] | None,
    scoring_settings: dict | None,
) -> dict[str, float]:
    """Map Sleeper player IDs to projected fantasy points."""

    projection_lookup = {}

    for projection in projection_rows or []:
        if not isinstance(projection, dict):
            continue

        player_id = str(
            projection.get("player_id")
            or projection.get("player", {}).get(
                "player_id",
                "",
            )
        )

        if not player_id:
            continue

        projected_stats = (
            projection.get("stats")
            or projection.get("projection")
            or {}
        )

        projected_points = (
            calculate_projected_fantasy_points(
                projected_stats=projected_stats,
                scoring_settings=scoring_settings,
            )
        )

        projection_lookup[player_id] = (
            projected_points
        )

    return projection_lookup