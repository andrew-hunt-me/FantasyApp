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
    performance_lookup: dict[str, dict] | None = None,
) -> list[dict[str, Any]]:
    """Build starter and bench rows from a Sleeper matchup."""
    projection_lookup = projection_lookup or {}
    performance_lookup = performance_lookup or {}

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
        recent_performance = performance_lookup.get(
            player_id,
            {},
        )

        last_game_points = float(
            recent_performance.get(
                "Last Game Points",
                0.0,
            )
        )

        three_week_average = float(
            recent_performance.get(
                "Three Week Average",
                0.0,
            )
        )

        recent_trend = recent_performance.get(
            "Recent Trend",
            "No trend",
        )

        games_included = int(
            recent_performance.get(
                "Games Included",
                0,
            )
        )

        lineup_value = calculate_lineup_value(
            sleeper_rank=sleeper_rank,
            injury_status=injury_status,
            on_bye=on_bye,
            projected_points=projected_points,
            three_week_average=three_week_average,
            games_included=games_included,
        )

        confidence_label, confidence_score, confidence_reason = (
            calculate_advisor_confidence(
                projected_points=projected_points,
                three_week_average=three_week_average,
                games_included=games_included,
                sleeper_rank=sleeper_rank,
                injury_status=injury_status,
                on_bye=on_bye,
            )
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
                "Advisor Confidence": confidence_label,
                "Confidence Score": confidence_score,
                "Confidence Reason": confidence_reason,
                "Week Points": round(points, 2),
                "Player ID": player_id,
                "Last Game Points": round(
                    last_game_points,
                    2,
                ),
                "Three Week Average": round(
                    three_week_average,
                    2,
                ),
                "Recent Trend": recent_trend,
                "Games Included": games_included,

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
    three_week_average: float = 0.0,
    games_included: int = 0,
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

    try:
        recent_average = max(
            float(three_week_average),
            0.0,
        )
    except (TypeError, ValueError):
        recent_average = 0.0

    try:
        completed_games = max(
            int(games_included),
            0,
        )
    except (TypeError, ValueError):
        completed_games = 0

    if completed_games == 0:
        recent_weight = 0.0
    elif completed_games == 1:
        recent_weight = 0.5
    elif completed_games == 2:
        recent_weight = 1.0
    else:
        recent_weight = 1.5

    lineup_value = (
            0.30 * rank_score
            + 3.0 * projection_value
            + recent_weight * recent_average
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
                "Start Confidence": start_player.get(
                    "Advisor Confidence",
                    "LOW",
                ),
                "Bench Confidence": bench_player.get(
                    "Advisor Confidence",
                    "LOW",
                ),
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

def build_weekly_points_lookup(
    stats_rows: list[dict] | None,
    scoring_settings: dict | None,
) -> dict[str, float]:
    """Map player IDs to actual fantasy points for one week."""

    points_lookup = {}

    for stat_record in stats_rows or []:
        if not isinstance(stat_record, dict):
            continue

        player_id = str(
            stat_record.get("player_id")
            or (
                stat_record.get("player") or {}
            ).get("player_id")
            or ""
        )

        if not player_id:
            continue

        actual_stats = (
            stat_record.get("stats")
            or stat_record.get("stat")
            or {}
        )

        actual_points = calculate_projected_fantasy_points(
            projected_stats=actual_stats,
            scoring_settings=scoring_settings,
        )

        points_lookup[player_id] = actual_points

    return points_lookup

def build_recent_performance_lookup(
    weekly_points_lookups: list[
        tuple[int, dict[str, float]]
    ],
) -> dict[str, dict[str, float | str]]:
    """Calculate recent fantasy production and direction."""

    player_weekly_points = {}

    for week, points_lookup in weekly_points_lookups:
        for player_id, points in points_lookup.items():
            player_id = str(player_id)

            if player_id not in player_weekly_points:
                player_weekly_points[player_id] = []

            player_weekly_points[player_id].append(
                {
                    "week": int(week),
                    "points": float(points),
                }
            )

    performance_lookup = {}

    for player_id, weekly_results in player_weekly_points.items():
        weekly_results.sort(
            key=lambda result: result["week"]
        )

        point_values = [
            result["points"]
            for result in weekly_results
        ]

        last_game_points = (
            point_values[-1]
            if point_values
            else 0.0
        )

        last_three = point_values[-3:]

        three_week_average = (
            sum(last_three) / len(last_three)
            if last_three
            else 0.0
        )

        trend = "No trend"

        if len(last_three) >= 2:
            first_value = last_three[0]
            last_value = last_three[-1]
            difference = last_value - first_value

            if difference >= 5:
                trend = "Improving"
            elif difference <= -5:
                trend = "Declining"
            else:
                trend = "Stable"

        performance_lookup[player_id] = {
            "Last Game Points": round(
                last_game_points,
                2,
            ),
            "Three Week Average": round(
                three_week_average,
                2,
            ),
            "Recent Trend": trend,
            "Games Included": len(
                point_values
            ),
        }

    return performance_lookup

def calculate_advisor_confidence(
    projected_points: float,
    three_week_average: float,
    games_included: int,
    sleeper_rank: int | float | None,
    injury_status: str,
    on_bye: bool,
) -> tuple[str, int, str]:
    """Estimate confidence in a weekly lineup recommendation."""

    confidence_score = 0
    reasons = []

    try:
        projection_value = max(
            float(projected_points),
            0.0,
        )
    except (TypeError, ValueError):
        projection_value = 0.0

    try:
        recent_average = max(
            float(three_week_average),
            0.0,
        )
    except (TypeError, ValueError):
        recent_average = 0.0

    try:
        completed_games = max(
            int(games_included),
            0,
        )
    except (TypeError, ValueError):
        completed_games = 0

    try:
        numeric_rank = float(sleeper_rank)
        has_valid_rank = numeric_rank > 0
    except (TypeError, ValueError):
        has_valid_rank = False

    normalized_injury = str(
        injury_status or ""
    ).upper()

    if projection_value > 0:
        confidence_score += 35
        reasons.append("weekly projection available")
    else:
        reasons.append("no weekly projection")

    if completed_games >= 3:
        confidence_score += 30
        reasons.append("three recent games available")
    elif completed_games == 2:
        confidence_score += 20
        reasons.append("two recent games available")
    elif completed_games == 1:
        confidence_score += 10
        reasons.append("one recent game available")
    else:
        reasons.append("no recent-game history")

    if has_valid_rank:
        confidence_score += 20
        reasons.append("Sleeper rank available")
    else:
        reasons.append("Sleeper rank unavailable")

    if projection_value > 0 and recent_average > 0:
        difference = abs(
            projection_value - recent_average
        )

        if difference <= 3:
            confidence_score += 15
            reasons.append(
                "projection agrees with recent production"
            )
        elif difference <= 7:
            confidence_score += 8
            reasons.append(
                "projection is reasonably close to recent production"
            )
        else:
            confidence_score -= 5
            reasons.append(
                "projection and recent production disagree"
            )

    if normalized_injury in {
        "QUESTIONABLE",
        "Q",
        "DOUBTFUL",
        "D",
    }:
        confidence_score -= 15
        reasons.append("injury designation adds uncertainty")

    elif normalized_injury in {"OUT", "IR"}:
        confidence_score = 0
        reasons.append("player is unavailable")

    if on_bye:
        confidence_score = 0
        reasons.append("player is on bye")

    confidence_score = max(
        min(confidence_score, 100),
        0,
    )

    if confidence_score >= 75:
        confidence_label = "HIGH"
    elif confidence_score >= 45:
        confidence_label = "MEDIUM"
    else:
        confidence_label = "LOW"

    confidence_reason = ", ".join(
        dict.fromkeys(reasons)
    )

    return (
        confidence_label,
        confidence_score,
        confidence_reason,
    )