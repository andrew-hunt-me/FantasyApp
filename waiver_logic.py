"""Waiver-wire calculations for the Fantasy Football Assistant."""

from typing import Any

from config import ROSTER_LIMITS
from draft_logic import normalize_position
from schedule_data import get_bye_week


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


def calculate_waiver_priority_score(
    trend_count: int,
    sleeper_rank_score: float,
    position: str,
    position_counts: dict[str, int],
    injury_status: str,
    trend_type: str,
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

    position = normalize_position(position)
    roster_count = position_counts.get(position, 0)
    roster_limit = ROSTER_LIMITS.get(position, 0)

    # Trend counts can be extremely large, so cap their contribution.
    trend_score = min(trend_count / 1000.0, 25.0)

    rank_component = 0.60 * sleeper_rank_score

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
        trend_score
        + rank_component
        + need_bonus
        - injury_penalty
        + trend_direction_adjustment
    )

    final_score = round(
        max(score, 0.0),
        1,
    )

    return {
        "waiver_score": final_score,
        "trend_score": round(trend_score, 1),
        "rank_component": round(rank_component, 1),
        "need_bonus": round(need_bonus, 1),
        "injury_penalty": round(injury_penalty, 1),
        "trend_adjustment": round(
            trend_direction_adjustment,
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
) -> list[dict[str, Any]]:
    """Build waiver candidates who are unrostered in the selected league."""

    if not trending_players or not nfl_players:
        return []

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
            position=position,
            position_counts=position_counts,
            injury_status=injury_status,
            trend_type=trend_type,
        )

        waiver_score = score_breakdown[
            "waiver_score"
        ]

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
                "Trend Score": score_breakdown[
                    "trend_score"
                ],
                "Player Quality Score": score_breakdown[
                    "rank_component"
                ],
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
                "Suggested FAAB": suggest_faab_range(
                    waiver_score,
                    position,
                ),
                "Injury Status": injury_status,
                "Player ID": player_id,
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