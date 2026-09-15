"""Waiver-wire calculations for the Fantasy Football Assistant."""

from typing import Any

from config import ROSTER_LIMITS
from player_utils import normalize_position
from schedule_data import get_bye_week
from weather_logic import calculate_weather_adjustment


def get_rostered_player_ids(
    league_rosters: list[dict] | None,
) -> set[str]:
    """Return all player IDs currently rostered in the league."""

    rostered_player_ids = set()

    for roster in league_rosters or []:
        player_lists = [
            roster.get("players") or [],
            roster.get("starters") or [],
            roster.get("reserve") or [],
            roster.get("taxi") or [],
        ]

        for player_list in player_lists:
            for player_id in player_list:
                if player_id is not None:
                    rostered_player_ids.add(str(player_id))

    return rostered_player_ids

def calculate_projection_score(
    projected_points: float,
) -> float:
    """Convert projected fantasy points into a 0-100 score."""

    try:
        projected_points = float(projected_points)
    except (TypeError, ValueError):
        projected_points = 0.0

    score = (
        projected_points / 25.0
    ) * 100.0

    return round(
        max(min(score, 100.0), 0.0),
        1,
    )
def calculate_recent_performance_score(
    three_week_average: float,
) -> float:
    """Convert three-week average to a 0-100 score."""

    try:
        average = float(
            three_week_average
        )
    except (TypeError, ValueError):
        average = 0.0

    score = (
        average / 25.0
    ) * 100.0

    return round(
        max(min(score, 100.0), 0.0),
        1,
    )
def calculate_waiver_priority_score(
    trend_count: int,
    sleeper_rank_score: float,
    projected_points: float,
    three_week_average: float,
    games_included: int,
    position: str,
    position_counts: dict[str, int],
    injury_status: str,
    trend_type: str,
    weather_adjustment: float = 0.0,
) -> dict[str, float]:
    """Calculate a preliminary waiver priority score."""

    try:
        trend_count = max(int(trend_count), 0)
    except (TypeError, ValueError):
        trend_count = 0

    try:
        sleeper_rank_score = float(sleeper_rank_score)
    except (TypeError, ValueError):
        sleeper_rank_score = 0.0

    try:
        weather_component = float(
            weather_adjustment
        )
    except (TypeError, ValueError):
        weather_component = 0.0

    weather_component = max(
        min(weather_component, 5.0),
        -10.0,
    )
    position = normalize_position(position)
    roster_count = position_counts.get(position, 0)
    roster_limit = ROSTER_LIMITS.get(position, 0)

    # Trend counts can be extremely large, so cap their contribution.
    trend_score = min(trend_count / 1000.0, 25.0)
    projection_score = (
        calculate_projection_score(
            projected_points
        )
    )

    recent_score = (
        calculate_recent_performance_score(
            three_week_average
        )
    )
    player_quality_component = (
            0.35 * sleeper_rank_score
    )

    projection_component = (
            0.35 * projection_score
    )

    try:
        completed_games = max(
            int(games_included),
            0,
        )
    except (TypeError, ValueError):
        completed_games = 0

    recent_sample_factor = min(
        completed_games / 3.0,
        1.0,
    )

    recent_component = (
            0.20
            * recent_score
            * recent_sample_factor
    )

    need_bonus = 0.0

    if position == "RB":
        if roster_count < 4:
            need_bonus = 15.0
        elif roster_count < roster_limit:
            need_bonus = 7.0

    elif position == "WR":
        if roster_count < 4:
            need_bonus = 15.0
        elif roster_count < roster_limit:
            need_bonus = 7.0

    elif position == "QB":
        if roster_count == 0:
            need_bonus = 12.0
        elif roster_count == 1:
            need_bonus = 3.0

    elif position == "TE":
        if roster_count == 0:
            need_bonus = 12.0
        elif roster_count == 1:
            need_bonus = 3.0

    elif position in {"K", "DEF"}:
        if roster_count == 0:
            need_bonus = 4.0

    injury_penalty = 0.0
    normalized_injury = str(injury_status or "").upper()

    if normalized_injury in {"IR", "OUT"}:
        injury_penalty = 20.0
    elif normalized_injury in {"DOUBTFUL", "D"}:
        injury_penalty = 10.0
    elif normalized_injury in {"QUESTIONABLE", "Q"}:
        injury_penalty = 3.0

    if trend_type == "drop":
        trend_direction_adjustment = -10.0
    else:
        trend_direction_adjustment = 0.0

    score = (
            player_quality_component
            + projection_component
            + recent_component
            + trend_score
            + need_bonus
            - injury_penalty
            + trend_direction_adjustment
            + weather_component
    )

    final_score = round(
        max(score, 0.0),
        1,
    )

    return {
        "waiver_score": final_score,
        "trend_score": round(
            trend_score,
            1,
        ),
        "player_quality_score": round(
            player_quality_component,
            1,
        ),
        "projection_score": round(
            projection_component,
            1,
        ),
        "recent_score": round(
            recent_component,
            1,
        ),
        "need_bonus": round(
            need_bonus,
            1,
        ),
        "injury_penalty": round(
            injury_penalty,
            1,
        ),
        "trend_adjustment": round(
            trend_direction_adjustment,
            1,
        ),
        "weather_adjustment": round(
            weather_component,
            1,
        ),
    }


def suggest_faab_range(
    waiver_score: float,
    position: str,
) -> str:
    """Return a conservative preliminary FAAB recommendation."""

    position = normalize_position(position)

    if position in {"K", "DEF"}:
        return "0-2%"

    if waiver_score >= 75:
        return "15-25%"
    if waiver_score >= 60:
        return "8-15%"
    if waiver_score >= 45:
        return "3-8%"
    if waiver_score >= 30:
        return "1-3%"

    return "0-1%"


def build_waiver_watch_rows(
    trending_players: list[dict] | None,
    nfl_players: dict[str, dict] | None,
    league_rosters: list[dict] | None,
    position_counts: dict[str, int],
    sleeper_rank_scores: dict[str, float],
    trend_type: str = "add",
    projection_lookup: dict[str, float] | None = None,
    performance_lookup: dict[str, dict] | None = None,
    player_game_contexts: dict[str, dict] | None = None,
) -> list[dict[str, Any]]:
    """Build waiver candidates who are unrostered in the selected league."""

    if not trending_players or not nfl_players:
        return []

    projection_lookup = projection_lookup or {}
    performance_lookup = performance_lookup or {}
    player_game_contexts = player_game_contexts or {}

    rostered_player_ids = get_rostered_player_ids(
        league_rosters
    )

    waiver_rows = []

    for trend_entry in trending_players:
        player_id = str(
            trend_entry.get("player_id") or ""
        )

        if not player_id:
            continue

        if player_id in rostered_player_ids:
            continue

        player_data = nfl_players.get(player_id)

        if not isinstance(player_data, dict):
            continue

        try:
            projected_points = float(
                projection_lookup.get(
                    player_id,
                    0.0,
                )
            )
        except (TypeError, ValueError):
            projected_points = 0.0

        player_performance = performance_lookup.get(
            player_id,
            {},
        )

        try:
            last_game_points = float(
                player_performance.get(
                    "Last Game Points",
                    0.0,
                )
            )
        except (TypeError, ValueError):
            last_game_points = 0.0

        try:
            three_week_average = float(
                player_performance.get(
                    "Three Week Average",
                    0.0,
                )
            )
        except (TypeError, ValueError):
            three_week_average = 0.0

        recent_trend = player_performance.get(
            "Recent Trend",
            "No trend",
        )

        try:
            games_included = int(
                player_performance.get(
                    "Games Included",
                    0,
                )
            )
        except (TypeError, ValueError):
            games_included = 0



        position = normalize_position(
            player_data.get("position"),
            player_id,
        )

        if position not in ROSTER_LIMITS:
            continue

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

        game_context = player_game_contexts.get(
            team,
            {},
        )

        opponent = game_context.get(
            "Opponent",
            "",
        )

        matchup = game_context.get(
            "Matchup",
            "",
        )

        kickoff_houston = game_context.get(
            "Kickoff Houston",
            "",
        )

        game_location = game_context.get(
            "Stadium City",
            "",
        )

        roof_type = game_context.get(
            "Roof Type",
            "Unknown",
        )

        weather_risk = game_context.get(
            "Weather Risk",
            "N/A",
        )

        weather_available = game_context.get(
            "Weather Available",
            False,
        )

        weather_protected = game_context.get(
            "Weather Protected",
            False,
        )

        if weather_available:
            temperature_f = game_context.get(
                "Temperature F"
            )

            wind_speed_mph = game_context.get(
                "Wind Speed MPH"
            )

            wind_gust_mph = game_context.get(
                "Wind Gust MPH"
            )

            precipitation_probability = game_context.get(
                "Precipitation Probability"
            )

            weather_adjustment, weather_reason = (
                calculate_weather_adjustment(
                    position=position,
                    temperature_f=(
                        temperature_f
                        if temperature_f is not None
                        else 70.0
                    ),
                    precipitation_probability=(
                        precipitation_probability
                        if precipitation_probability is not None
                        else 0.0
                    ),
                    wind_speed_mph=(
                        wind_speed_mph
                        if wind_speed_mph is not None
                        else 0.0
                    ),
                    wind_gust_mph=(
                        wind_gust_mph
                        if wind_gust_mph is not None
                        else 0.0
                    ),
                    indoor_game=weather_protected,
                )
            )
        else:
            weather_adjustment = 0.0

            weather_reason = game_context.get(
                "Weather Unavailable Reason",
                "Weather forecast unavailable",
            )

        trend_count = trend_entry.get("count", 0)

        injury_status = (
            player_data.get("injury_status")
            or ""
        )

        sleeper_rank = player_data.get("search_rank")

        sleeper_rank_score = sleeper_rank_scores.get(
            player_id,
            0.0,
        )

        score_breakdown = calculate_waiver_priority_score(
            trend_count=trend_count,
            sleeper_rank_score=sleeper_rank_score,
            projected_points=projected_points,
            three_week_average=three_week_average,
            games_included=games_included,
            position=position,
            position_counts=position_counts,
            injury_status=injury_status,
            trend_type=trend_type,
            weather_adjustment=weather_adjustment,
        )

        waiver_score = score_breakdown[
            "waiver_score"
        ]

        waiver_tier, waiver_label = (
            classify_waiver_tier(
                waiver_score
            )
        )

        waiver_reason = build_waiver_reason(
            projected_points=projected_points,
            three_week_average=three_week_average,
            recent_trend=recent_trend,
            need_bonus=score_breakdown.get(
                "need_bonus",
                0.0,
            ),
            injury_penalty=score_breakdown.get(
                "injury_penalty",
                0.0,
            ),
            trend_score=score_breakdown.get(
                "trend_score",
                0.0,
            ),
            weather_adjustment=score_breakdown.get(
                "weather_adjustment",
                0.0,
            ),
        )

        waiver_rows.append(
            {
                "Player Name": (
                    player_name
                    or player_id
                ),
                "Position": position,
                "NFL Team": team,
                "Bye Week": get_bye_week(team) or "N/A",
                "Trend Type": trend_type.upper(),
                "Trend Count": trend_count,
                "Sleeper Rank": (
                    sleeper_rank
                    if sleeper_rank is not None
                    else "N/A"
                ),
                "Sleeper Rank Score": round(
                    sleeper_rank_score,
                    1,
                ),
                "Projected Points": round(
                    projected_points,
                    2,
                ),
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
                "Trend Score": score_breakdown[
                    "trend_score"
                ],
                "Player Quality Score": score_breakdown[
                    "player_quality_score"
                ],
                "Projection Score": score_breakdown.get(
                    "projection_score",
                    0.0,
                ),
                "Recent Performance Score": score_breakdown.get(
                    "recent_score",
                    0.0,
                ),
                "Roster Need Bonus": score_breakdown[
                    "need_bonus"
                ],
                "Injury Penalty": score_breakdown[
                    "injury_penalty"
                ],
                "Trend Adjustment": score_breakdown[
                    "trend_adjustment"
                ],
                "Waiver Score": waiver_score,
                "Waiver Tier": waiver_tier,
                "Waiver Label": waiver_label,
                "Waiver Reason": waiver_reason,
                "Waiver Score": waiver_score,
                "Suggested FAAB": suggest_faab_range(
                    waiver_score,
                    position,
                ),
                "Injury Status": injury_status,
                "Player ID": player_id,
                "Opponent": opponent,
                "Matchup": matchup,
                "Kickoff Houston": kickoff_houston,
                "Game Location": game_location,
                "Roof Type": roof_type,
                "Weather Risk": weather_risk,
                "Weather Adjustment": score_breakdown.get(
                    "weather_adjustment",
                    0.0,
                ),
                "Weather Reason": weather_reason,
            }

        )

    waiver_rows.sort(
        key=lambda player: (
            -player["Waiver Score"],
            -int(player["Trend Count"] or 0),
            player["Player Name"],
        )
    )

    for waiver_rank, player in enumerate(
        waiver_rows,
        start=1,
    ):
        player["Waiver Rank"] = waiver_rank

    return waiver_rows

def classify_waiver_tier(
    waiver_score: float,
) -> tuple[str, str]:
    """Classify a waiver candidate into an actionable tier."""

    try:
        score = float(waiver_score)
    except (TypeError, ValueError):
        score = 0.0

    if score >= 75:
        return (
            "TIER 1",
            "Priority Add",
        )

    if score >= 60:
        return (
            "TIER 2",
            "Strong Add",
        )

    if score >= 45:
        return (
            "TIER 3",
            "Useful Depth",
        )

    if score >= 30:
        return (
            "TIER 4",
            "Bench Stash",
        )

    return (
        "TIER 5",
        "Watch List",
    )

def build_waiver_reason(
    projected_points: float,
    three_week_average: float,
    recent_trend: str,
    need_bonus: float,
    injury_penalty: float,
    trend_score: float,
    weather_adjustment: float,
) -> str:
    """Build a concise explanation for a waiver recommendation."""

    reasons = []

    if projected_points >= 15:
        reasons.append(
            "Strong weekly projection"
        )
    elif projected_points >= 10:
        reasons.append(
            "Useful weekly projection"
        )

    if three_week_average >= 15:
        reasons.append(
            "Strong recent production"
        )
    elif three_week_average >= 10:
        reasons.append(
            "Productive recent stretch"
        )

    normalized_trend = str(
        recent_trend or ""
    ).lower()

    if normalized_trend == "improving":
        reasons.append(
            "Recent production improving"
        )
    elif normalized_trend == "declining":
        reasons.append(
            "Recent production declining"
        )

    if need_bonus >= 10:
        reasons.append(
            "Fills a significant roster need"
        )
    elif need_bonus > 0:
        reasons.append(
            "Adds roster depth"
        )

    if trend_score >= 15:
        reasons.append(
            "Strong add activity"
        )

    if injury_penalty >= 10:
        reasons.append(
            "Significant injury concern"
        )
    elif injury_penalty > 0:
        reasons.append(
            "Monitor injury status"
        )

    if weather_adjustment <= -3:
        reasons.append(
            "Adverse game weather"
        )
    elif weather_adjustment > 0:
        reasons.append(
            "Weather may favor this position"
        )

    if not reasons:
        reasons.append(
            "Speculative waiver option"
        )

    return ", ".join(
        dict.fromkeys(reasons)
    )