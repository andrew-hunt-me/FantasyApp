"""Draft, roster, and lineup calculations."""

from typing import Any

from config import (
    NFL_TEAM_ABBREVIATIONS,
    ROSTER_LIMITS,
    STARTING_LINEUP,
)
from collections import defaultdict
from schedule_data import get_bye_week

def normalize_position(
    position: str | None,
    player_id: str | None = None,
) -> str:
    """Return a consistent fantasy position."""

    normalized_position = str(position or "").upper().strip()
    normalized_player_id = str(player_id or "").upper().strip()

    if normalized_position in {"D/ST", "DST", "DEFENSE"}:
        return "DEF"

    if normalized_player_id in NFL_TEAM_ABBREVIATIONS:
        return "DEF"

    return normalized_position


def calculate_snake_picks(
    draft_position: int,
    number_of_teams: int,
    number_of_rounds: int,
) -> list[dict]:
    """Calculate a team's overall selections in a snake draft."""

    picks = []

    for round_number in range(1, number_of_rounds + 1):
        if round_number % 2 == 1:
            position_in_round = draft_position
        else:
            position_in_round = (
                number_of_teams - draft_position + 1
            )

        overall_pick = (
            (round_number - 1) * number_of_teams
            + position_in_round
        )

        picks.append(
            {
                "Round": round_number,
                "Overall Pick": overall_pick,
            }
        )

    return picks


def is_position_at_limit(
    position_count: int,
    position: str,
) -> bool:
    """Return True when a position has reached its maximum."""

    maximum = ROSTER_LIMITS.get(position, 0)
    return position_count >= maximum


def find_user_draft_slot(
    draft: dict,
    user_id: str,
    fallback_slot: int,
) -> int:
    """Find the user's assigned draft slot."""

    draft_order = draft.get("draft_order") or {}

    slot = draft_order.get(str(user_id))

    if slot is None:
        slot = draft_order.get(user_id)

    try:
        return int(slot)
    except (TypeError, ValueError):
        return int(fallback_slot)


def find_user_roster_id(
    draft: dict,
    user_id: str,
    league_rosters: list[dict] | None,
) -> int | str | None:
    """Find the user's roster ID using draft and league data."""

    draft_order = draft.get("draft_order") or {}
    slot_to_roster_id = draft.get("slot_to_roster_id") or {}

    draft_slot = draft_order.get(str(user_id))

    if draft_slot is None:
        draft_slot = draft_order.get(user_id)

    possible_slot_keys = {
        draft_slot,
        str(draft_slot) if draft_slot is not None else None,
    }

    for slot_key in possible_slot_keys:
        if slot_key in slot_to_roster_id:
            return slot_to_roster_id[slot_key]

    for roster in league_rosters or []:
        owner_id = roster.get("owner_id")

        if str(owner_id) == str(user_id):
            return roster.get("roster_id")

    return None


def build_position_counts(
    completed_picks: list[dict] | None,
    roster_id: int | str | None,
) -> dict[str, int]:
    """Count drafted players by position for one roster."""

    position_counts = {
        position: 0
        for position in ROSTER_LIMITS
    }

    if roster_id is None:
        return position_counts

    for pick in completed_picks or []:
        if str(pick.get("roster_id")) != str(roster_id):
            continue

        metadata = pick.get("metadata") or {}
        player_id = pick.get("player_id")

        position = normalize_position(
            metadata.get("position"),
            player_id,
        )

        if position in position_counts:
            position_counts[position] += 1

    return position_counts

def build_roster_bye_context(
    completed_picks: list[dict] | None,
    roster_id: int | str | None,
) -> dict:
    """Count bye weeks represented on a drafted roster."""

    bye_week_counts = defaultdict(int)

    position_bye_weeks = {
        "QB": set(),
        "RB": set(),
        "WR": set(),
        "TE": set(),
        "K": set(),
        "DEF": set(),
    }

    if roster_id is None:
        return {
            "bye_week_counts": {},
            "position_bye_weeks": position_bye_weeks,
        }

    for pick in completed_picks or []:
        if str(pick.get("roster_id")) != str(roster_id):
            continue

        metadata = pick.get("metadata") or {}

        player_id = str(
            pick.get("player_id") or ""
        )

        position = normalize_position(
            metadata.get("position"),
            player_id,
        )

        team = (
            metadata.get("team")
            or (
                player_id
                if position == "DEF"
                else ""
            )
        )

        bye_week = get_bye_week(team)

        if bye_week is None:
            continue

        bye_week_counts[bye_week] += 1

        if position in position_bye_weeks:
            position_bye_weeks[position].add(
                bye_week
            )

    return {
        "bye_week_counts": dict(bye_week_counts),
        "position_bye_weeks": position_bye_weeks,
    }
def build_my_team_rows(
    completed_picks: list[dict] | None,
    roster_id: int | str | None,
) -> list[dict]:
    """Build the detailed drafted-player rows for one roster."""

    team_rows = []

    if roster_id is None:
        return team_rows

    for pick in completed_picks or []:
        if str(pick.get("roster_id")) != str(roster_id):
            continue

        metadata = pick.get("metadata") or {}

        player_id = str(
            pick.get("player_id") or ""
        )

        first_name = metadata.get("first_name") or ""
        last_name = metadata.get("last_name") or ""

        player_name = f"{first_name} {last_name}".strip()

        position = normalize_position(
            metadata.get("position"),
            player_id,
        )
        team = (
                metadata.get("team")
                or (
                    player_id
                    if position == "DEF"
                    else ""
                )
        )

        bye_week = get_bye_week(team)
        team_rows.append(
            {
                "Overall Pick": pick.get("pick_no"),
                "Round": pick.get("round"),
                "Player Name": (
                    player_name
                    or metadata.get("name")
                    or player_id
                ),
                "Position": position,
                "NFL Team": team,
                "Bye Week": (
                    bye_week
                    if bye_week is not None
                    else "N/A"
                ),
                "Player ID": player_id,
            }
        )

    def sort_key(player: dict) -> int:
        try:
            return int(player.get("Overall Pick"))
        except (TypeError, ValueError):
            return 9999

    team_rows.sort(key=sort_key)

    return team_rows
def get_current_overall_pick(
    completed_picks: list[dict] | None,
) -> int:
    """Return the highest completed overall draft pick."""

    valid_pick_numbers = []

    for pick in completed_picks or []:
        try:
            valid_pick_numbers.append(int(pick.get("pick_no", 0)))
        except (TypeError, ValueError):
            continue

    return max(valid_pick_numbers, default=0)


def get_next_pick_information(
    completed_picks: list[dict] | None,
    draft_position: int,
    number_of_teams: int,
    number_of_rounds: int,
) -> dict[str, Any]:
    """Calculate the user's next expected draft selection."""

    current_overall = get_current_overall_pick(completed_picks)

    user_picks = calculate_snake_picks(
        draft_position=draft_position,
        number_of_teams=number_of_teams,
        number_of_rounds=number_of_rounds,
    )

    next_pick = next(
        (
            pick
            for pick in user_picks
            if pick["Overall Pick"] > current_overall
        ),
        None,
    )

    if next_pick is None:
        return {
            "current_overall": current_overall,
            "next_overall": None,
            "next_round": None,
            "picks_before_turn": 0,
            "status": "Your draft is complete",
        }

    next_overall = next_pick["Overall Pick"]
    picks_before_turn = max(
        next_overall - current_overall - 1,
        0,
    )

    if current_overall + 1 == next_overall:
        status = "YOU ARE ON THE CLOCK"
    elif current_overall + 2 == next_overall:
        status = "YOU ARE NEXT"
    else:
        status = f"{picks_before_turn} picks before your turn"

    return {
        "current_overall": current_overall,
        "next_overall": next_overall,
        "next_round": next_pick["Round"],
        "picks_before_turn": picks_before_turn,
        "status": status,
    }


def calculate_lineup_progress(
    position_counts: dict[str, int],
) -> list[dict]:
    """Calculate whether the current roster can fill each starter."""

    required_qb = STARTING_LINEUP["QB"]
    required_rb = STARTING_LINEUP["RB"]
    required_wr = STARTING_LINEUP["WR"]
    required_te = STARTING_LINEUP["TE"]
    required_flex = STARTING_LINEUP["FLEX"]
    required_k = STARTING_LINEUP["K"]
    required_def = STARTING_LINEUP["DEF"]

    extra_rb = max(position_counts.get("RB", 0) - required_rb, 0)
    extra_wr = max(position_counts.get("WR", 0) - required_wr, 0)
    extra_te = max(position_counts.get("TE", 0) - required_te, 0)

    available_flex = extra_rb + extra_wr + extra_te

    requirements = [
        (
            "Starting QB",
            position_counts.get("QB", 0),
            required_qb,
        ),
        (
            "Starting RB",
            position_counts.get("RB", 0),
            required_rb,
        ),
        (
            "Starting WR",
            position_counts.get("WR", 0),
            required_wr,
        ),
        (
            "Starting TE",
            position_counts.get("TE", 0),
            required_te,
        ),
        (
            "FLEX",
            available_flex,
            required_flex,
        ),
        (
            "Starting K",
            position_counts.get("K", 0),
            required_k,
        ),
        (
            "Starting DEF",
            position_counts.get("DEF", 0),
            required_def,
        ),
    ]

    progress = []

    for lineup_slot, available, required in requirements:
        filled = min(available, required)

        progress.append(
            {
                "Lineup Slot": lineup_slot,
                "Available": available,
                "Required": required,
                "Filled": filled,
                "Status": (
                    "FILLED"
                    if available >= required
                    else "OPEN"
                ),
            }
        )

    return progress

def build_user_draft_context(
    draft: dict | None,
    user_id: str,
    league_rosters: list[dict] | None,
    completed_picks: list[dict] | None,
    fallback_draft_position: int,
) -> dict:
    """Build reusable roster and draft information for one user."""

    empty_position_counts = {
        position: 0
        for position in ROSTER_LIMITS
    }

    empty_next_pick_information = {
        "current_overall": 0,
        "next_overall": None,
        "next_round": None,
        "picks_before_turn": 0,
        "status": "",
    }

    if not draft:
        return {
            "roster_id": None,
            "position_counts": empty_position_counts,
            "draft_slot": int(fallback_draft_position),
            "number_of_teams": 12,
            "number_of_rounds": 16,
            "next_pick_information": (
                empty_next_pick_information
            ),
        }

    draft_settings = draft.get("settings") or {}

    try:
        number_of_teams = int(
            draft_settings.get("teams", 12)
        )
    except (TypeError, ValueError):
        number_of_teams = 12

    try:
        number_of_rounds = int(
            draft_settings.get("rounds", 16)
        )
    except (TypeError, ValueError):
        number_of_rounds = 16

    if number_of_rounds < 1:
        number_of_rounds = 16

    if number_of_teams < 1:
        number_of_teams = 12

    roster_id = find_user_roster_id(
        draft=draft,
        user_id=user_id,
        league_rosters=league_rosters,
    )

    position_counts = build_position_counts(
        completed_picks=completed_picks,
        roster_id=roster_id,
    )

    draft_slot = find_user_draft_slot(
        draft=draft,
        user_id=user_id,
        fallback_slot=fallback_draft_position,
    )

    next_pick_information = get_next_pick_information(
        completed_picks=completed_picks,
        draft_position=draft_slot,
        number_of_teams=number_of_teams,
        number_of_rounds=number_of_rounds,
    )

    if draft.get("status") == "complete":
        next_pick_information["status"] = (
            "Your draft is complete"
        )

    return {
        "roster_id": roster_id,
        "position_counts": position_counts,
        "draft_slot": draft_slot,
        "number_of_teams": number_of_teams,
        "number_of_rounds": number_of_rounds,
        "next_pick_information": (
            next_pick_information
        ),
    }
