"""Recommendation and value-based drafting calculations."""

from collections import defaultdict
from typing import Any

from config import (
    DEFAULT_REPLACEMENT_LEVELS,
    ROSTER_LIMITS,
)
from draft_logic import (
    is_position_at_limit,
    normalize_position,
)
from schedule_data import get_bye_week

def calculate_position_need_score(
    position: str,
    position_counts: dict[str, int],
    current_round: int,
) -> float:
    """Calculate roster need for a position."""

    position = normalize_position(position)
    current_count = position_counts.get(position, 0)

    if is_position_at_limit(current_count, position):
        return -999.0

    qb_count = position_counts.get("QB", 0)
    rb_count = position_counts.get("RB", 0)
    wr_count = position_counts.get("WR", 0)
    te_count = position_counts.get("TE", 0)
    k_count = position_counts.get("K", 0)
    def_count = position_counts.get("DEF", 0)

    need_score = 0.0

    if position == "QB":
        if qb_count == 0:
            need_score = 15.0
        elif qb_count == 1:
            need_score = 3.0
        else:
            need_score = 0.0

    elif position == "RB":
        if rb_count == 0:
            need_score = 40.0
        elif rb_count == 1:
            need_score = 35.0
        elif rb_count < 4:
            need_score = 22.0
        else:
            need_score = 10.0

    elif position == "WR":
        if wr_count == 0:
            need_score = 42.0
        elif wr_count == 1:
            need_score = 37.0
        elif wr_count < 4:
            need_score = 25.0
        else:
            need_score = 12.0

    elif position == "TE":
        if te_count == 0:
            need_score = 20.0
        elif te_count == 1:
            need_score = 4.0
        else:
            need_score = 0.0

    elif position == "K":
        need_score = 8.0 if k_count == 0 else 0.0

    elif position == "DEF":
        need_score = 8.0 if def_count == 0 else 0.0

    if current_round <= 6:
        if position == "RB":
            need_score += 15.0
        elif position == "WR":
            need_score += 17.0
        elif position == "QB":
            need_score -= 7.0
        elif position == "TE":
            need_score -= 3.0
        elif position in {"K", "DEF"}:
            need_score -= 100.0

    elif current_round <= 10:
        if position == "RB":
            need_score += 8.0
        elif position == "WR":
            need_score += 10.0
        elif position == "QB" and qb_count == 0:
            need_score += 18.0
        elif position == "TE" and te_count == 0:
            need_score += 14.0
        elif position in {"K", "DEF"}:
            need_score -= 100.0

    elif current_round <= 12:
        if position == "QB" and qb_count == 0:
            need_score += 20.0
        elif position == "TE" and te_count == 0:
            need_score += 16.0
        elif position in {"K", "DEF"}:
            need_score -= 25.0

    else:
        if position == "K":
            need_score += 20.0 if k_count == 0 else -10.0
        elif position == "DEF":
            need_score += 20.0 if def_count == 0 else -10.0

    return max(min(need_score, 60.0), -999.0)


def calculate_raw_vbd_score(
    positional_rank: int | None,
    replacement_level: int | None,
) -> float:
    """Calculate rank-based value above replacement."""

    try:
        rank = int(positional_rank)
        replacement = int(replacement_level)
    except (TypeError, ValueError):
        return 0.0

    if rank < 1 or replacement < 1:
        return 0.0

    return float(max(replacement - rank + 1, 0))


def calculate_flex_bonus(
    position: str,
    position_counts: dict[str, int],
) -> float:
    """Calculate the two-FLEX roster-construction bonus."""

    position = normalize_position(position)
    count = position_counts.get(position, 0)
    maximum = ROSTER_LIMITS.get(position, 0)

    if count >= maximum:
        return 0.0

    if position == "RB":
        return 10.0 if count < 4 else 5.0

    if position == "WR":
        return 10.0 if count < 4 else 5.0

    if position == "TE":
        return 3.0 if count < 2 else 0.0

    return 0.0


def build_fixed_positional_ranks(
    nfl_players: dict[str, dict],
) -> dict[str, int]:
    """Assign fixed positional ranks before drafted players are removed."""

    players_by_position: dict[str, list[tuple[str, float]]] = defaultdict(list)

    for player_id, player_data in nfl_players.items():
        if not isinstance(player_data, dict):
            continue

        if not player_data.get("active", False):
            continue

        position = normalize_position(
            player_data.get("position"),
            player_id,
        )

        if position not in ROSTER_LIMITS:
            continue

        search_rank = player_data.get("search_rank")

        try:
            numeric_rank = float(search_rank)
        except (TypeError, ValueError):
            continue

        players_by_position[position].append(
            (str(player_id), numeric_rank)
        )

    positional_ranks: dict[str, int] = {}

    for players in players_by_position.values():
        players.sort(key=lambda item: item[1])

        for positional_rank, player_entry in enumerate(
            players,
            start=1,
        ):
            player_id = player_entry[0]
            positional_ranks[player_id] = positional_rank

    return positional_ranks

def build_available_player_pool(
    nfl_players: dict[str, dict],
    completed_picks: list[dict] | None,
    fixed_positional_ranks: dict[str, int],
) -> list[dict[str, Any]]:
    """Build fantasy-relevant players who remain undrafted."""

    drafted_player_ids = {
        str(pick.get("player_id"))
        for pick in completed_picks or []
        if pick.get("player_id") is not None
    }

    available_players = []

    for player_id, player_data in nfl_players.items():
        if not isinstance(player_data, dict):
            continue

        player_id = str(player_id)

        if player_id in drafted_player_ids:
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

        try:
            sleeper_rank = float(
                player_data.get("search_rank")
            )
        except (TypeError, ValueError):
            sleeper_rank = None

        team = (
                player_data.get("team")
                or (
                    player_id
                    if position == "DEF"
                    else ""
                )
        )

        bye_week = get_bye_week(team)

        available_players.append(
            {
                "Player ID": player_id,
                "Player Name": player_name,
                "Position": position,
                "NFL Team": team,
                "Bye Week": bye_week,
                "Active": bool(
                    player_data.get("active", False)
                ),
                "Status": (
                    player_data.get("status")
                    or ""
                ),
                "Injury Status": (
                    player_data.get("injury_status")
                    or ""
                ),
                "Sleeper Search Rank": sleeper_rank,
                "Sleeper Rank": sleeper_rank,
                "Positional Rank": (
                    fixed_positional_ranks.get(
                        player_id
                    )
                ),
            }
        )

    available_players.sort(
        key=lambda player: (
            player["Sleeper Rank"] is None,
            (
                player["Sleeper Rank"]
                if player["Sleeper Rank"] is not None
                else float("inf")
            ),
            player["Player Name"],
        )
    )

    return available_players
def add_sleeper_rank_scores(
    players: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add a zero-to-100 Sleeper Rank Score.

    The score is anchored to the top 300 fantasy players so that
    elite players receive distinguishable scores rather than all
    rounding to 100.
    """

    fantasy_rank_cutoff = 300.0

    for player in players:
        try:
            sleeper_rank = float(
                player.get("Sleeper Rank")
            )
        except (TypeError, ValueError):
            player["Sleeper Rank Score"] = 0.0
            continue

        if sleeper_rank < 1:
            player["Sleeper Rank Score"] = 0.0
            continue

        score = 100.0 * (
            fantasy_rank_cutoff - sleeper_rank
        ) / (
            fantasy_rank_cutoff - 1.0
        )

        player["Sleeper Rank Score"] = round(
            max(min(score, 100.0), 0.0),
            1,
        )

    return players


def add_vbd_scores(
    players: list[dict[str, Any]],
    replacement_levels: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Add raw and normalized VBD scores."""

    levels = replacement_levels or DEFAULT_REPLACEMENT_LEVELS
    maximum_raw_vbd = 0.0

    for player in players:
        position = normalize_position(
            player.get("Position"),
            player.get("Player ID"),
        )

        replacement_level = levels.get(position, 0)
        positional_rank = player.get("Positional Rank")

        raw_vbd = calculate_raw_vbd_score(
            positional_rank,
            replacement_level,
        )

        player["Replacement Level"] = replacement_level
        player["Raw VBD Score"] = raw_vbd
        maximum_raw_vbd = max(maximum_raw_vbd, raw_vbd)

    for player in players:
        raw_vbd = player.get("Raw VBD Score", 0.0)

        if maximum_raw_vbd > 0:
            vbd_score = 100.0 * raw_vbd / maximum_raw_vbd
        else:
            vbd_score = 0.0

        player["VBD Score"] = round(vbd_score, 1)

    return players


def calculate_position_scarcity_score(
    position: str,
    above_replacement_available: int,
    number_of_teams: int,
    position_counts: dict[str, int],
    current_round: int,
) -> float:
    """Calculate position scarcity from zero to 25."""

    position = normalize_position(position)
    roster_count = position_counts.get(position, 0)

    if is_position_at_limit(roster_count, position):
        return 0.0

    if position in {"K", "DEF"} and current_round < 13:
        return 0.0

    safe_team_count = max(int(number_of_teams), 1)

    replacement_supply = max(
        above_replacement_available,
        0,
    )

    scarcity_ratio = 1.0 / (
            1.0
            + replacement_supply / safe_team_count
    )

    if position == "QB":
        need_factor = 1.0 if roster_count == 0 else 0.4

        if roster_count >= 2:
            need_factor = 0.1

    elif position == "RB":
        if roster_count < 2:
            need_factor = 1.0
        elif roster_count < 4:
            need_factor = 0.8
        else:
            need_factor = 0.4

    elif position == "WR":
        if roster_count < 2:
            need_factor = 1.0
        elif roster_count < 4:
            need_factor = 0.9
        else:
            need_factor = 0.5

    elif position == "TE":
        need_factor = 1.0 if roster_count == 0 else 0.4

        if roster_count >= 2:
            need_factor = 0.1

    elif position in {"K", "DEF"}:
        need_factor = 0.5 if roster_count == 0 else 0.1

    else:
        need_factor = 0.0

    scarcity_score = 25.0 * scarcity_ratio * need_factor

    return round(
        max(min(scarcity_score, 25.0), 0.0),
        1,
    )


def normalize_rank_weights(
    sleeper_weight_percent: int,
    vbd_weight_percent: int,
) -> tuple[float, float, bool]:
    """Normalize rank weights when their sum exceeds 100 percent."""

    sleeper_weight = max(float(sleeper_weight_percent), 0.0)
    vbd_weight = max(float(vbd_weight_percent), 0.0)

    total = sleeper_weight + vbd_weight
    weights_were_normalized = total > 100.0

    if total == 0:
        return 0.0, 0.0, False

    if total > 100.0:
        sleeper_weight = sleeper_weight / total
        vbd_weight = vbd_weight / total
    else:
        sleeper_weight = sleeper_weight / 100.0
        vbd_weight = vbd_weight / 100.0

    return (
        sleeper_weight,
        vbd_weight,
        weights_were_normalized,
    )


def calculate_recommendation_score(
    sleeper_rank_score: float,
    vbd_score: float,
    position_need_score: float,
    scarcity_score: float,
    flex_bonus: float,
    sleeper_weight: float,
    vbd_weight: float,
    position_need_multiplier: float = 1.0,
    scarcity_multiplier: float = 1.0,
    flex_multiplier: float = 1.0,
) -> float:
    """Calculate the final recommendation score."""

    score = (
        sleeper_weight * sleeper_rank_score
        + vbd_weight * vbd_score
        + position_need_multiplier * position_need_score
        + scarcity_multiplier * scarcity_score
        + flex_multiplier * flex_bonus
    )

    return round(score, 1)

def build_recommendation_reason(
    position: str,
    position_counts: dict[str, int],
    current_round: int,
    sleeper_rank_score: float,
    raw_vbd_score: float,
    scarcity_score: float,
) -> str:
    """Build a concise explanation for a player recommendation."""

    position = normalize_position(position)
    reasons = []

    if sleeper_rank_score >= 95:
        reasons.append("Elite available value")
    elif sleeper_rank_score >= 80:
        reasons.append("Strong Sleeper value")

    if raw_vbd_score > 0:
        reasons.append("Above replacement value")

    if scarcity_score >= 15:
        reasons.append("Position becoming scarce")

    if position == "RB":
        rb_count = position_counts.get("RB", 0)

        if rb_count < 2:
            reasons.append("Starting RB needed")
        elif rb_count < 4:
            reasons.append("Two-FLEX depth")
        else:
            reasons.append("RB depth")

    elif position == "WR":
        wr_count = position_counts.get("WR", 0)

        if wr_count < 2:
            reasons.append("Starting WR needed")
        elif wr_count < 4:
            reasons.append("Two-FLEX depth")
        else:
            reasons.append("WR depth")

    elif position == "QB":
        qb_count = position_counts.get("QB", 0)

        if qb_count == 0:
            reasons.append("Starting QB needed")
        elif current_round <= 10:
            reasons.append("Wait on backup QB")
        else:
            reasons.append("QB depth")

    elif position == "TE":
        te_count = position_counts.get("TE", 0)

        if te_count == 0:
            reasons.append("Starting TE needed")
        elif current_round <= 10:
            reasons.append("Wait on backup TE")
        else:
            reasons.append("TE depth")

    elif position == "K" and current_round >= 13:
        reasons.append("Late-round kicker")

    elif position == "DEF" and current_round >= 13:
        reasons.append("Late-round defense")

    if not reasons:
        reasons.append("Available roster value")


    return ", ".join(dict.fromkeys(reasons))
def build_position_statistics(
    players: list[dict[str, Any]],
    replacement_levels: dict[str, int],
    active_only: bool = True,
) -> dict[str, dict[str, int]]:
    """Summarize available players by fantasy position."""

    statistics = {}

    for position in ROSTER_LIMITS:
        position_players = [
            player
            for player in players
            if player.get("Position") == position
            and (
                not active_only
                or player.get("Active", False)
            )
        ]

        replacement_level = replacement_levels.get(
            position,
            0,
        )

        above_replacement_count = 0

        for player in position_players:
            positional_rank = player.get("Positional Rank")

            try:
                numeric_rank = int(positional_rank)
            except (TypeError, ValueError):
                continue

            if numeric_rank <= replacement_level:
                above_replacement_count += 1

        statistics[position] = {
            "available": len(position_players),
            "above_replacement": above_replacement_count,
        }

    return statistics

def calculate_bye_week_penalty(
    bye_week: int | None,
    position: str,
    bye_week_counts: dict[int, int],
    position_bye_weeks: dict[str, set[int]],
) -> tuple[float, str]:
    """Calculate a modest penalty for bye-week concentration."""

    if bye_week is None:
        return 0.0, ""

    existing_count = bye_week_counts.get(
        bye_week,
        0,
    )

    if existing_count <= 1:
        penalty = 0.0
    elif existing_count == 2:
        penalty = 1.0
    elif existing_count == 3:
        penalty = 3.0
    elif existing_count == 4:
        penalty = 6.0
    else:
        penalty = 10.0

    normalized_position = normalize_position(
        position
    )

    same_position_byes = position_bye_weeks.get(
        normalized_position,
        set(),
    )

    warning = ""

    if normalized_position == "QB":
        if bye_week in same_position_byes:
            penalty += 4.0
            warning = "QB bye conflict"

    elif normalized_position == "TE":
        if bye_week in same_position_byes:
            penalty += 3.0
            warning = "TE bye conflict"

    if not warning and existing_count >= 3:
        warning = "Heavy bye-week concentration"
    elif not warning and existing_count == 2:
        warning = "Bye-week concentration"

    return round(penalty, 1), warning

def build_draft_recommendations(
    players: list[dict[str, Any]],
    position_statistics: dict[str, dict[str, int]],
    position_counts: dict[str, int],
    replacement_levels: dict[str, int],
    current_round: int,
    number_of_teams: int,
    sleeper_weight: float,
    vbd_weight: float,
    position_need_multiplier: float,
    scarcity_multiplier: float,
    flex_multiplier: float,
    bye_week_counts: dict[int, int] | None = None,
    position_bye_weeks: dict[str, set[int]] | None = None,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    """Build, score, sort, and rank the complete draft board."""

    recommendations = []
    bye_week_counts = bye_week_counts or {}

    position_bye_weeks = position_bye_weeks or {
        "QB": set(),
        "RB": set(),
        "WR": set(),
        "TE": set(),
        "K": set(),
        "DEF": set(),
    }


    for player in players:
        if not include_inactive and not player.get("Active", False):
            continue

        position = normalize_position(
            player.get("Position"),
            player.get("Player ID"),
        )

        player_id = str(
            player.get("Player ID") or ""
        )

        if position not in ROSTER_LIMITS:
            continue

        if is_position_at_limit(
            position_counts.get(position, 0),
            position,
        ):
            continue

        if current_round < 13 and position in {"K", "DEF"}:
            continue

        positional_rank = player.get("Positional Rank")

        replacement_level = replacement_levels.get(
            position,
            0,
        )

        sleeper_rank_score = float(
            player.get("Sleeper Rank Score", 0.0)
        )

        raw_vbd_score = float(
            player.get("Raw VBD Score", 0.0)
        )

        vbd_score = float(
            player.get("VBD Score", 0.0)
        )

        position_need_score = calculate_position_need_score(
            position=position,
            position_counts=position_counts,
            current_round=current_round,
        )

        if position_need_score < 0:
            continue

        flex_bonus = calculate_flex_bonus(
            position=position,
            position_counts=position_counts,
        )

        above_replacement_available = (
            position_statistics
            .get(position, {})
            .get("above_replacement", 0)
        )

        scarcity_score = calculate_position_scarcity_score(
            position=position,
            above_replacement_available=(
                above_replacement_available
            ),
            number_of_teams=number_of_teams,
            position_counts=position_counts,
            current_round=current_round,
        )

        recommendation_score = calculate_recommendation_score(
            sleeper_rank_score=sleeper_rank_score,
            vbd_score=vbd_score,
            position_need_score=position_need_score,
            scarcity_score=scarcity_score,
            flex_bonus=flex_bonus,
            sleeper_weight=sleeper_weight,
            vbd_weight=vbd_weight,
            position_need_multiplier=(
                position_need_multiplier
            ),
            scarcity_multiplier=scarcity_multiplier,
            flex_multiplier=flex_multiplier,
        )

        bye_week = player.get("Bye Week")

        bye_week_penalty, bye_week_warning = (
            calculate_bye_week_penalty(
                bye_week=bye_week,
                position=position,
                bye_week_counts=bye_week_counts,
                position_bye_weeks=position_bye_weeks,
            )
        )

        adjusted_recommendation_score = (
                recommendation_score
                - bye_week_penalty
        )
        recommendation_reason = build_recommendation_reason(
            position=position,
            position_counts=position_counts,
            current_round=current_round,
            sleeper_rank_score=sleeper_rank_score,
            raw_vbd_score=raw_vbd_score,
            scarcity_score=scarcity_score,
        )

        if bye_week_warning:
            recommendation_reason = (
                f"{recommendation_reason}, "
                f"{bye_week_warning}"
            )

        sleeper_rank = player.get("Sleeper Rank")

        if sleeper_rank is None:
            sleeper_rank = "N/A"

        if positional_rank is None:
            displayed_positional_rank = "N/A"
        else:
            displayed_positional_rank = positional_rank

        recommendations.append(
            {
                "Player Name": player.get(
                    "Player Name",
                    "Unknown Player",
                ),
                "Position": position,
                "NFL Team": player.get("NFL Team", ""),
                "Bye Week": (
                    bye_week
                    if bye_week is not None
                    else "N/A"
                ),
                "Players on Same Bye": (
                    bye_week_counts.get(bye_week, 0)
                    if bye_week is not None
                    else 0
                ),
                "Bye Week Penalty": bye_week_penalty,
                "Bye Week Warning": bye_week_warning,
                "Sleeper Rank": sleeper_rank,
                "Positional Rank": displayed_positional_rank,
                "Replacement Level": replacement_level,
                "Sleeper Rank Score": round(
                    sleeper_rank_score,
                    1,
                ),
                "Raw VBD Score": round(
                    raw_vbd_score,
                    1,
                ),
                "VBD Score": round(
                    vbd_score,
                    1,
                ),
                "Position Need Score": round(
                    position_need_score,
                    1,
                ),
                "Position Scarcity Score": round(
                    scarcity_score,
                    1,
                ),
                "Two FLEX Bonus": round(
                    flex_bonus,
                    1,
                ),
                "Base Recommendation Score": round(
                    recommendation_score,
                    1,
                ),
                "Recommendation Score": round(
                    adjusted_recommendation_score,
                    1,
                ),

                "Recommendation Reason": (
                    recommendation_reason
                ),
                "Injury Status": player.get(
                    "Injury Status",
                    "",
                ),
                "Player ID": player_id,
            }
        )

    recommendations.sort(
        key=lambda recommendation: (
            -recommendation["Recommendation Score"],
            (
                recommendation["Sleeper Rank"]
                if isinstance(
                    recommendation["Sleeper Rank"],
                    (int, float),
                )
                else 9999
            ),
            recommendation["Player Name"],
        )
    )

    for recommendation_rank, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        recommendation["Recommendation Rank"] = (
            recommendation_rank
        )

    return recommendations

def filter_recommendations(
    recommendations: list[dict[str, Any]],
    selected_positions: list[str] | None = None,
    player_search: str = "",
    maximum_results: int | None = None,
) -> list[dict[str, Any]]:
    """Filter the recommendation table without changing overall ranks."""

    filtered_recommendations = [
        recommendation.copy()
        for recommendation in recommendations
    ]

    if selected_positions:
        filtered_recommendations = [
            recommendation
            for recommendation in filtered_recommendations
            if recommendation.get("Position")
            in selected_positions
        ]

    normalized_search = player_search.strip().lower()

    if normalized_search:
        filtered_recommendations = [
            recommendation
            for recommendation in filtered_recommendations
            if normalized_search
            in recommendation.get(
                "Player Name",
                "",
            ).lower()
        ]

    if maximum_results is not None:
        try:
            result_limit = max(
                int(maximum_results),
                0,
            )
        except (TypeError, ValueError):
            result_limit = 0

        filtered_recommendations = (
            filtered_recommendations[:result_limit]
        )

    return filtered_recommendations