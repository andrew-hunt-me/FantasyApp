"""Reusable Streamlit display functions."""

from typing import Any

import streamlit as st

from config import ROSTER_LIMITS


def display_position_summary(
    position_statistics: dict[str, dict[str, int]],
    position_counts: dict[str, int],
    replacement_levels: dict[str, int],
) -> None:
    """Display available-player and roster information by position."""

    st.divider()
    st.subheader("Position Summary")

    position_summary = []

    for position in ["QB", "RB", "WR", "TE", "K", "DEF"]:
        roster_count = position_counts.get(position, 0)
        maximum_allowed = ROSTER_LIMITS.get(position, 0)

        statistics = position_statistics.get(
            position,
            {},
        )

        position_summary.append(
            {
                "Position": position,
                "Available Players": statistics.get(
                    "available",
                    0,
                ),
                "Above-Replacement Players": statistics.get(
                    "above_replacement",
                    0,
                ),
                "Replacement Level": replacement_levels.get(
                    position,
                    0,
                ),
                "User Roster Count": roster_count,
                "Maximum Allowed": maximum_allowed,
                "Spots Remaining": max(
                    maximum_allowed - roster_count,
                    0,
                ),
            }
        )

    st.dataframe(
        position_summary,
        use_container_width=True,
        hide_index=True,
    )


def display_top_recommendations(
    recommendations: list[dict[str, Any]],
    maximum_players: int = 5,
) -> None:
    """Display the highest-ranked recommendations as cards."""

    if not recommendations:
        return

    st.divider()
    st.subheader("Top Recommendations")

    top_recommendations = recommendations[
        :maximum_players
    ]

    for recommendation_rank, recommendation in enumerate(
        top_recommendations,
        start=1,
    ):
        with st.container(border=True):
            player_name = recommendation.get(
                "Player Name",
                "Unknown Player",
            )

            st.markdown(
                f"### #{recommendation_rank} {player_name}"
            )

            column1, column2, column3 = st.columns(3)

            position = recommendation.get(
                "Position",
                "",
            )

            nfl_team = recommendation.get(
                "NFL Team",
                "",
            )

            column1.write(
                f"**Position:** {position} | {nfl_team}"
            )

            column1.write(
                "**Sleeper Rank:** "
                f"{recommendation.get('Sleeper Rank', 'N/A')}"
            )

            column1.write(
                "**Positional Rank:** "
                f"{recommendation.get('Positional Rank', 'N/A')}"
            )

            column1.write(
                "**Bye Week:** "
                f"{recommendation.get('Bye Week', 'N/A')}"
            )

            column2.metric(
                "Recommendation Score",
                recommendation.get(
                    "Recommendation Score",
                    0,
                ),
            )

            column2.metric(
                "VBD Score",
                recommendation.get(
                    "VBD Score",
                    0,
                ),

            )

            column2.metric(
                "Bye Week Penalty",
                recommendation.get(
                    "Bye Week Penalty",
                    0,
                ),
            )

            column3.write(
                "**Why this player:**"
            )

            column3.write(
                recommendation.get(
                    "Recommendation Reason",
                    "Available roster value",
                )
            )


def display_recommendation_table(
    recommendations: list[dict[str, Any]],
) -> None:
    """Display the complete recommendation dataframe."""

    st.divider()
    st.subheader("All Recommendations")

    if not recommendations:
        st.info(
            "No recommendations match the selected filters."
        )
        return

    display_columns = [
        "Recommendation Rank",
        "Player Name",
        "Position",
        "NFL Team",
        "Bye Week",
        "Players on Same Bye",
        "Bye Week Penalty",
        "Bye Week Warning",
        "Sleeper Rank",
        "Positional Rank",
        "Replacement Level",
        "Sleeper Rank Score",
        "Raw VBD Score",
        "VBD Score",
        "Position Need Score",
        "Position Scarcity Score",
        "Two FLEX Bonus",
        "Base Recommendation Score",
        "Recommendation Score",
        "Recommendation Reason",
        "Injury Status",
        "Player ID",
    ]

    recommendation_rows = [
        {
            column: recommendation.get(column, "")
            for column in display_columns
        }
        for recommendation in recommendations
    ]

    st.dataframe(
        recommendation_rows,
        use_container_width=True,
        hide_index=True,
        height=1200,
    )


def display_roster_summary(
    position_counts: dict[str, int],
) -> None:
    """Display current position counts and remaining roster capacity."""

    st.subheader("Roster Summary")

    roster_rows = []

    for position in ["QB", "RB", "WR", "TE", "K", "DEF"]:
        drafted = position_counts.get(position, 0)
        maximum = ROSTER_LIMITS.get(position, 0)

        spots_remaining = max(
            maximum - drafted,
            0,
        )

        if drafted > maximum:
            status = "OVER LIMIT"
        elif drafted == maximum:
            status = "FULL"
        else:
            status = "OPEN"

        roster_rows.append(
            {
                "Position": position,
                "Players Drafted": drafted,
                "Maximum Allowed": maximum,
                "Spots Remaining": spots_remaining,
                "Status": status,
            }
        )

    st.dataframe(
        roster_rows,
        use_container_width=True,
        hide_index=True,
    )

def display_bye_week_summary(
    bye_week_counts: dict[int, int],
) -> None:
    """Display the number of drafted players on each bye week."""

    st.subheader("Bye Week Summary")

    if not bye_week_counts:
        st.info(
            "No bye-week conflicts yet because you have not "
            "drafted any players."
        )
        return

    bye_rows = []

    for bye_week in sorted(bye_week_counts):
        player_count = bye_week_counts[bye_week]

        if player_count >= 5:
            status = "SEVERE"
        elif player_count == 4:
            status = "HIGH"
        elif player_count == 3:
            status = "WATCH"
        else:
            status = "OK"

        bye_rows.append(
            {
                "Bye Week": bye_week,
                "Players on Bye": player_count,
                "Status": status,
            }
        )

    st.dataframe(
        bye_rows,
        use_container_width=True,
        hide_index=True,
    )

    highest_count = max(bye_week_counts.values())

    crowded_weeks = [
        week
        for week, count in bye_week_counts.items()
        if count >= 3
    ]

    if highest_count >= 5:
        st.error(
            "Your roster has a severe bye-week concentration. "
            f"Review Week {', '.join(map(str, crowded_weeks))}."
        )
    elif highest_count == 4:
        st.warning(
            "Your roster has four players sharing a bye week. "
            "Consider bye-week balance when comparing similar players."
        )
    elif highest_count == 3:
        st.info(
            "Three players share a bye week. This is manageable, "
            "but additional players on that bye will receive a penalty."
        )
    else:
        st.success(
            "Your roster currently has good bye-week distribution."
        )
def display_next_pick_summary(
    next_pick_information: dict[str, Any],
) -> None:
    """Display the user's upcoming draft selection."""

    st.subheader("Next Pick")

    current_overall = next_pick_information.get(
        "current_overall",
        0,
    )

    next_overall = next_pick_information.get(
        "next_overall",
    )

    next_round = next_pick_information.get(
        "next_round",
    )

    picks_before_turn = next_pick_information.get(
        "picks_before_turn",
        0,
    )

    status = next_pick_information.get(
        "status",
        "",
    )

    column1, column2, column3, column4 = st.columns(4)

    column1.metric(
        "Current Overall Pick",
        current_overall,
    )

    column2.metric(
        "Your Next Pick",
        next_overall if next_overall is not None else "Complete",
    )

    column3.metric(
        "Picks Before Your Turn",
        picks_before_turn,
    )

    column4.metric(
        "Next Round",
        next_round if next_round is not None else "Complete",
    )

    if status == "YOU ARE ON THE CLOCK":
        st.error(status)
    elif status == "YOU ARE NEXT":
        st.warning(status)
    elif status == "Your draft is complete":
        st.success(status)
    elif status:
        st.info(status)

def render_vbd_settings() -> dict[str, int]:
    """Render VBD replacement-level controls."""

    with st.expander("VBD Settings"):
        column1, column2, column3 = st.columns(3)
        column4, column5, column6 = st.columns(3)

        quarterback_level = column1.number_input(
            "QB Replacement Level",
            min_value=0,
            max_value=50,
            value=12,
            key="vbd_replacement_qb",
        )

        running_back_level = column2.number_input(
            "RB Replacement Level",
            min_value=0,
            max_value=100,
            value=36,
            key="vbd_replacement_rb",
        )

        wide_receiver_level = column3.number_input(
            "WR Replacement Level",
            min_value=0,
            max_value=100,
            value=36,
            key="vbd_replacement_wr",
        )

        tight_end_level = column4.number_input(
            "TE Replacement Level",
            min_value=0,
            max_value=50,
            value=12,
            key="vbd_replacement_te",
        )

        kicker_level = column5.number_input(
            "K Replacement Level",
            min_value=0,
            max_value=50,
            value=0,
            key="vbd_replacement_k",
        )

        defense_level = column6.number_input(
            "DEF Replacement Level",
            min_value=0,
            max_value=50,
            value=0,
            key="vbd_replacement_def",
        )

    return {
        "QB": int(quarterback_level),
        "RB": int(running_back_level),
        "WR": int(wide_receiver_level),
        "TE": int(tight_end_level),
        "K": int(kicker_level),
        "DEF": int(defense_level),
    }

def render_recommendation_weights() -> dict[str, int]:
    """Render recommendation-scoring weight controls."""

    with st.expander("Recommendation Weights"):
        column1, column2 = st.columns(2)
        column3, column4, column5 = st.columns(3)

        sleeper_weight = column1.slider(
            "Sleeper Rank Weight (%)",
            min_value=0,
            max_value=100,
            value=45,
            step=5,
            key="weight_sleeper_rank",
        )

        vbd_weight = column2.slider(
            "VBD Weight (%)",
            min_value=0,
            max_value=100,
            value=25,
            step=5,
            key="weight_vbd",
        )

        position_need_multiplier = column3.slider(
            "Position Need Multiplier (%)",
            min_value=0,
            max_value=200,
            value=100,
            step=10,
            key="weight_position_need",
        )

        scarcity_multiplier = column4.slider(
            "Scarcity Multiplier (%)",
            min_value=0,
            max_value=200,
            value=100,
            step=10,
            key="weight_scarcity",
        )

        flex_multiplier = column5.slider(
            "FLEX Bonus Multiplier (%)",
            min_value=0,
            max_value=200,
            value=100,
            step=10,
            key="weight_flex",
        )

    return {
        "sleeper_weight_percent": sleeper_weight,
        "vbd_weight_percent": vbd_weight,
        "position_need_percent": position_need_multiplier,
        "scarcity_percent": scarcity_multiplier,
        "flex_percent": flex_multiplier,
    }

def render_recommendation_filters() -> dict[str, Any]:
    """Render controls used to filter the recommendation table."""

    column1, column2, column3, column4 = st.columns(4)

    selected_positions = column1.multiselect(
        "Filter by Position",
        options=["QB", "RB", "WR", "TE", "K", "DEF"],
        default=["QB", "RB", "WR", "TE"],
        key="recommendation_position_filter",
    )

    player_search = column2.text_input(
        "Search by Player Name",
        key="recommendation_player_search",
    )

    include_inactive = column3.checkbox(
        "Include inactive players",
        value=False,
        key="recommendation_include_inactive",
    )

    result_count = column4.selectbox(
        "Number of Recommendations",
        options=[10, 25, 50, 100],
        index=1,
        key="recommendation_result_count",
    )

    return {
        "selected_positions": selected_positions,
        "player_search": player_search,
        "include_inactive": include_inactive,
        "result_count": int(result_count),
    }

def display_draft_summary(
    current_round: int,
    next_pick_information: dict[str, Any],
    position_counts: dict[str, int],
) -> None:
    """Display the current draft state and roster counts."""

    current_overall = next_pick_information.get(
        "current_overall",
        0,
    )

    next_overall = next_pick_information.get(
        "next_overall",
    )

    picks_before_turn = next_pick_information.get(
        "picks_before_turn",
        0,
    )

    status = next_pick_information.get(
        "status",
        "",
    )

    st.divider()
    st.subheader("Draft Summary")

    column1, column2, column3, column4 = st.columns(4)

    column1.metric(
        "Current Round",
        current_round,
    )

    column2.metric(
        "Current Overall Pick",
        current_overall,
    )

    column3.metric(
        "Your Next Pick",
        (
            next_overall
            if next_overall is not None
            else "Complete"
        ),
    )

    column4.metric(
        "Picks Before Your Turn",
        picks_before_turn,
    )

    st.write(
        f"**Roster Counts:** "
        f"QB: {position_counts.get('QB', 0)} | "
        f"RB: {position_counts.get('RB', 0)} | "
        f"WR: {position_counts.get('WR', 0)} | "
        f"TE: {position_counts.get('TE', 0)} | "
        f"K: {position_counts.get('K', 0)} | "
        f"DEF: {position_counts.get('DEF', 0)}"
    )

    if status == "YOU ARE ON THE CLOCK":
        st.error("⏰ YOU ARE ON THE CLOCK")
    elif status == "YOU ARE NEXT":
        st.warning("🎯 YOU ARE NEXT")
    elif status == "Your draft is complete":
        st.success(status)

def render_available_player_filters() -> dict[str, Any]:
    """Render controls used to filter available players."""

    column1, column2, column3 = st.columns(3)

    selected_positions = column1.multiselect(
        "Filter by Position",
        options=["QB", "RB", "WR", "TE", "K", "DEF"],
        default=["QB", "RB", "WR", "TE"],
        key="available_position_filter",
    )

    player_search = column2.text_input(
        "Search by Player Name",
        key="available_player_search",
    )

    active_only = column3.checkbox(
        "Show active players only",
        value=True,
        key="available_active_only",
    )

    return {
        "selected_positions": selected_positions,
        "player_search": player_search,
        "active_only": active_only,
    }

def filter_available_players(
    players: list[dict[str, Any]],
    selected_positions: list[str] | None = None,
    player_search: str = "",
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Filter available players without modifying the source list."""

    filtered_players = [
        player.copy()
        for player in players
    ]

    if selected_positions:
        filtered_players = [
            player
            for player in filtered_players
            if player.get("Position")
            in selected_positions
        ]

    normalized_search = player_search.strip().lower()

    if normalized_search:
        filtered_players = [
            player
            for player in filtered_players
            if normalized_search
            in player.get(
                "Player Name",
                "",
            ).lower()
        ]

    if active_only:
        filtered_players = [
            player
            for player in filtered_players
            if player.get("Active", False)
        ]

    return filtered_players