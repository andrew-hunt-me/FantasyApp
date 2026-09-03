import streamlit as st

from config import (
    DEFAULT_SLEEPER_USERNAME,
    DRAFT_POSITION,
    LEAGUE_FORMAT,
    ROSTER_LIMITS,
    SEASON,
    STARTING_LINEUP,
)
from draft_logic import (
    build_position_counts,
    calculate_lineup_progress,
    calculate_snake_picks,
    build_my_team_rows,
    build_user_draft_context,
    build_roster_bye_context,
)
from recommendations import (
    add_sleeper_rank_scores,
    add_vbd_scores,
    build_fixed_positional_ranks,
    normalize_rank_weights,
    build_available_player_pool,
    build_position_statistics,
    build_draft_recommendations,
    filter_recommendations,
)
from sleeper_api import (
    get_draft_picks,
    get_league_drafts,
    get_league_rosters,
    get_nfl_players,
    get_sleeper_user,
    get_user_leagues,
    get_trending_players,
)
from ui_helpers import (
    display_bye_week_summary,
    display_next_pick_summary,
    display_position_summary,
    display_recommendation_table,
    display_roster_summary,
    display_top_recommendations,
    render_recommendation_filters,
    render_recommendation_weights,
    render_vbd_settings,
    display_draft_summary,
    filter_available_players,
    render_available_player_filters,
)

from waiver_logic import build_waiver_watch_rows
# ---------------------------------------------------------
# PAGE SETUP
# You do not need to change this section.
# ---------------------------------------------------------

st.set_page_config(
    page_title="Fantasy Football Assistant",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 Andrew's Fantasy Football Assistant")

st.write(
    "Connect to Sleeper, select your league, "
    "and review your draft information."
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.header("Your Information")

    sleeper_username = st.text_input(
        "Sleeper username",
        value=DEFAULT_SLEEPER_USERNAME,
        key="sleeper_username",
    )

    selected_season = st.text_input(
        "NFL season",
        value=SEASON,
        key="selected_season",
    )

    draft_position = st.number_input(
        "Draft position",
        min_value=1,
        max_value=12,
        value=DRAFT_POSITION,
        key="draft_position",
    )

    number_of_rounds = st.number_input(
        "Draft rounds",
        min_value=10,
        max_value=25,
        value=16,
        key="number_of_rounds",
    )


# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------

if not sleeper_username:

    st.info(
        "Enter your Sleeper username in the sidebar."
    )

    st.stop()


if sleeper_username == "PUT_YOUR_SLEEPER_USERNAME_HERE":

    st.warning(
        "Replace PUT_YOUR_SLEEPER_USERNAME_HERE "
        "with your actual Sleeper username."
    )

    st.stop()


with st.spinner("Looking for your Sleeper account..."):

    user = get_sleeper_user(sleeper_username)


if not user:

    st.error(
        "Sleeper could not find that username. "
        "Check the spelling and try again."
    )

    st.stop()


user_id = user.get("user_id")
display_name = user.get("display_name")
avatar = user.get("avatar")


st.success("Sleeper account connected successfully.")

account_column1, account_column2 = st.columns(2)

account_column1.metric(
    "Sleeper Display Name",
    display_name or sleeper_username,
)

account_column2.metric(
    "Sleeper User ID",
    user_id,
)


with st.spinner("Loading your Sleeper leagues..."):

    leagues = get_user_leagues(
        user_id=user_id,
        season=selected_season,
    )


if leagues is None:

    st.error(
        "The app connected to Sleeper, but it could not "
        "retrieve your leagues."
    )

    st.stop()


if len(leagues) == 0:

    st.warning(
        f"No Sleeper NFL leagues were found for "
        f"the {selected_season} season."
    )

    st.stop()


league_options = {}

for league in leagues:

    league_name = league.get(
        "name",
        "Unnamed League",
    )

    league_id = league.get("league_id")
    league_status = league.get("status", "Unknown")

    option_label = (
        f"{league_name} | "
        f"Status: {league_status}"
    )

    league_options[option_label] = league_id


selected_league_label = st.selectbox(
    "Select your league",
    options=list(league_options.keys()),
    key="selected_league",
)

selected_league_id = league_options[
    selected_league_label
]


selected_league = next(
    league
    for league in leagues
    if league.get("league_id") == selected_league_id
)


st.divider()

st.header("Selected League")

league_column1, league_column2, league_column3 = (
    st.columns(3)
)

league_column1.metric(
    "League Name",
    selected_league.get("name", "Unknown"),
)

league_column2.metric(
    "League Status",
    selected_league.get("status", "Unknown"),
)

league_column3.metric(
    "Number of Teams",
    selected_league.get("total_rosters", 12),
)


st.write(
    "League ID:",
    selected_league_id,
)

st.write(
    "Scoring Format:",
    LEAGUE_FORMAT,
)

st.write(
    "Your Draft Position:",
    f"#{draft_position}",
)


# ---------------------------------------------------------
# LOAD DRAFT DATA (shared between tabs)
# ---------------------------------------------------------

with st.spinner("Loading draft information..."):
    drafts = get_league_drafts(selected_league_id)

selected_draft = None
selected_draft_id = None
completed_picks = None

if drafts is not None and len(drafts) > 0:
    if len(drafts) == 1:
        selected_draft = drafts[0]
    else:
        draft_options = {}
        for draft in drafts:
            draft_id = draft.get("draft_id")
            draft_status = draft.get("status", "Unknown")
            draft_season = draft.get("season", "Unknown")
            option_label = (
                f"Draft ID: {draft_id} | "
                f"Status: {draft_status} | "
                f"Season: {draft_season}"
            )
            draft_options[option_label] = draft

        selected_draft_label = st.selectbox(
            "Select a draft",
            options=list(draft_options.keys()),
            key="selected_draft",
        )
        selected_draft = draft_options[selected_draft_label]

    if selected_draft:
        selected_draft_id = selected_draft.get("draft_id")
        with st.spinner("Loading draft picks..."):
            completed_picks = get_draft_picks(selected_draft_id)

shared_nfl_players = None
shared_available_players = []

with st.spinner("Loading NFL player directory..."):
    shared_nfl_players = get_nfl_players()

if shared_nfl_players:
    shared_fixed_positional_ranks = (
        build_fixed_positional_ranks(
            shared_nfl_players
        )
    )

    shared_available_players = (
        build_available_player_pool(
            nfl_players=shared_nfl_players,
            completed_picks=completed_picks,
            fixed_positional_ranks=(
                shared_fixed_positional_ranks
            ),
        )
    )

    shared_available_players = (
        add_sleeper_rank_scores(
            shared_available_players
        )
    )

# ---------------------------------------------------------
# SHARED USER DRAFT AND ROSTER CONTEXT
# ---------------------------------------------------------

shared_league_rosters = []

shared_user_roster_id = None

shared_position_counts = {
    "QB": 0,
    "RB": 0,
    "WR": 0,
    "TE": 0,
    "K": 0,
    "DEF": 0,
}

shared_user_draft_slot = int(draft_position)

shared_next_pick_information = {
    "current_overall": 0,
    "next_overall": None,
    "next_round": None,
    "picks_before_turn": 0,
    "status": "",
}

if selected_draft:
    shared_league_rosters = (
        get_league_rosters(selected_league_id)
        or []
    )

    shared_draft_context = build_user_draft_context(
        draft=selected_draft,
        user_id=user_id,
        league_rosters=shared_league_rosters,
        completed_picks=completed_picks,
        fallback_draft_position=int(draft_position),
    )

    shared_user_roster_id = shared_draft_context[
        "roster_id"
    ]

    shared_position_counts = shared_draft_context[
        "position_counts"
    ]

    shared_user_draft_slot = shared_draft_context[
        "draft_slot"
    ]

    shared_number_of_teams = shared_draft_context[
        "number_of_teams"
    ]

    shared_number_of_rounds = shared_draft_context[
        "number_of_rounds"
    ]

    shared_next_pick_information = shared_draft_context[
        "next_pick_information"
    ]
    shared_bye_context = build_roster_bye_context(
        completed_picks=completed_picks,
        roster_id=shared_user_roster_id,
    )

    shared_bye_week_counts = shared_bye_context[
        "bye_week_counts"
    ]

    shared_position_bye_weeks = shared_bye_context[
        "position_bye_weeks"
    ]

    if selected_draft.get("status") == "complete":
        shared_next_pick_information["status"] = (
            "Your draft is complete"
        )

draft_tab, lineup_tab, roster_tab, details_tab, live_draft_tab, available_players_tab, my_team_tab, recommendations_tab, waiver_watch_tab = st.tabs(
    [
        "Draft Picks",
        "Starting Lineup",
        "Roster Limits",
        "League Details",
        "Live Draft Board",
        "Available Players",
        "My Team",
        "Recommendations",
        "Waiver Watch",
    ]
)

with draft_tab:
    st.subheader("Your Snake-Draft Picks")

    number_of_teams = selected_league.get(
        "total_rosters",
        12,
    )

    draft_picks = calculate_snake_picks(
        draft_position=int(draft_position),
        number_of_teams=int(number_of_teams),
        number_of_rounds=int(number_of_rounds),
    )

    st.dataframe(
        draft_picks,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "These selections assume a standard snake draft "
        "without traded draft picks."
    )


with lineup_tab:
    st.subheader("Starting Lineup")

    lineup_rows = []

    for position, quantity in STARTING_LINEUP.items():
        lineup_rows.append(
            {
                "Position": position,
                "Required Starters": quantity,
            }
        )

    st.dataframe(
        lineup_rows,
        use_container_width=True,
        hide_index=True,
    )


with roster_tab:
    st.subheader("Maximum Roster Limits")

    roster_rows = []

    for position, quantity in ROSTER_LIMITS.items():
        roster_rows.append(
            {
                "Position": position,
                "Maximum Allowed": quantity,
            }
        )

    st.dataframe(
        roster_rows,
        use_container_width=True,
        hide_index=True,
    )


with details_tab:
    st.subheader("Sleeper League Information")

    st.write(
        "League ID:",
        selected_league.get("league_id"),
    )

    st.write(
        "Season:",
        selected_league.get("season"),
    )

    st.write(
        "Season Type:",
        selected_league.get("season_type"),
    )

    st.write(
        "Draft ID:",
        selected_league.get("draft_id"),
    )

    with st.expander("View raw league settings"):
        st.json(selected_league)

    st.subheader("Scoring Settings")

    scoring_settings = selected_league.get(
        "scoring_settings",
        {},
    )

    if scoring_settings:
        scoring_rows = [
            {
                "Sleeper Setting": setting,
                "Points": points,
            }
            for setting, points in sorted(
                scoring_settings.items()
            )
        ]

        st.dataframe(
            scoring_rows,
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Copy Raw Scoring Settings"):
            st.json(scoring_settings)
    else:
        st.warning(
            "No scoring settings were returned by Sleeper."
        )

with live_draft_tab:
    st.subheader("Live Draft Board")

    if drafts is None:
        st.error(
            "Could not retrieve draft information. "
            "Please check your connection and try again."
        )
    elif len(drafts) == 0:
        st.warning(
            "No draft has been created for this league yet."
        )
    elif selected_draft:
        st.divider()
        st.subheader("Draft Information")

        draft_id = selected_draft.get("draft_id")
        draft_status = selected_draft.get("status", "Unknown")
        draft_type = selected_draft.get("type", "Unknown")
        num_teams = selected_draft.get("settings", {}).get("teams", 0)
        num_rounds = selected_draft.get("settings", {}).get("rounds", 0)
        pick_timer = selected_draft.get("settings", {}).get("pick_timer", 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Draft ID", draft_id)
        col2.metric("Status", draft_status)
        col3.metric("Draft Type", draft_type)

        col4, col5, col6 = st.columns(3)
        col4.metric("Number of Teams", num_teams)
        col5.metric("Number of Rounds", num_rounds)
        col6.metric("Pick Timer (seconds)", pick_timer)

        st.divider()
        st.subheader("Completed Picks")

        if completed_picks is None:
            st.error(
                "Could not retrieve draft picks. "
                "Please check your connection and try again."
            )
        elif len(completed_picks) == 0:
            st.info(
                "The draft has not started yet. "
                "No picks have been made."
            )
        else:
            picks_rows = []

            for pick in completed_picks:
                pick_no = pick.get("pick_no")
                round_num = pick.get("round")
                draft_slot = pick.get("draft_slot")
                roster_id = pick.get("roster_id")
                metadata = pick.get("metadata", {})
                first_name = metadata.get("first_name", "")
                last_name = metadata.get("last_name", "")
                player_name = f"{first_name} {last_name}".strip()
                position = metadata.get("position", "")
                team = metadata.get("team", "")

                picks_rows.append(
                    {
                        "Overall Pick": pick_no,
                        "Round": round_num,
                        "Draft Slot": draft_slot,
                        "Player Name": player_name,
                        "Position": position,
                        "NFL Team": team,
                        "Roster ID": roster_id,
                    }
                )

            picks_rows.sort(key=lambda x: x["Overall Pick"])

            st.dataframe(
                picks_rows,
                use_container_width=True,
                hide_index=True,
            )


with available_players_tab:
    st.subheader("Available Players")

    if not shared_nfl_players:
        st.error(
            "Could not load the NFL player directory."
        )
    else:
        available_players = [
            player.copy()
            for player in shared_available_players
        ]

        # Filters
        col1, col2, col3 = st.columns(3)

        filter_settings = render_available_player_filters()

        selected_positions = filter_settings[
            "selected_positions"
        ]

        search_name = filter_settings[
            "player_search"
        ]

        active_only = filter_settings[
            "active_only"
        ]

        # Apply filters
        filtered_players = filter_available_players(
            players=available_players,
            selected_positions=selected_positions,
            player_search=search_name,
            active_only=active_only,
        )

        st.write(f"Showing {len(filtered_players)} available players")

        # Display limited to 200 for performance
        display_players = filtered_players[:200]

        st.dataframe(
            display_players,
            use_container_width=True,
            hide_index=True,
        )

        if len(filtered_players) > 200:
            st.caption(
                f"Showing first 200 of {len(filtered_players)} matching players. "
                "Use filters to narrow results."
            )


with my_team_tab:
    st.subheader("My Team")

    if not selected_draft:
        st.warning(
            "No draft selected. Please select a draft in the Live Draft Board tab."
        )
    else:
        # Identify the user's roster ID.


        user_roster_id = shared_user_roster_id

        
        # Manual entry fallback
        if not user_roster_id:
            st.warning(
                "Could not automatically identify your roster. "
                "Please enter your roster ID manually."
            )
            user_roster_id = st.number_input(
                "Roster ID",
                min_value=0,
                value=0,
                step=1,
                key="manual_roster_id",
            )
            if user_roster_id == 0:
                st.stop()

            position_counts = build_position_counts(
                completed_picks = completed_picks,
                roster_id = user_roster_id,
            )

            manual_bye_context = build_roster_bye_context(
                completed_picks=completed_picks,
                roster_id=user_roster_id,
            )

            my_team_bye_week_counts = manual_bye_context[
                "bye_week_counts"
            ]
        else:
            position_counts = shared_position_counts.copy()
            my_team_bye_week_counts = (
                shared_bye_week_counts.copy()
            )

        # Build user's team dataframe
        # Build the user's drafted-player table.
        my_team_df = build_my_team_rows(
            completed_picks=completed_picks,
            roster_id=user_roster_id,
        )
        st.divider()
        st.subheader("My Drafted Players")
        
        if len(my_team_df) == 0:
            st.info("You have not drafted any players yet.")
        else:
            st.dataframe(
                my_team_df,
                use_container_width=True,
                hide_index=True,
            )
        
        # Roster summary
        st.divider()

        display_roster_summary(
            position_counts=position_counts,
        )

        st.divider()

        display_bye_week_summary(
            bye_week_counts=my_team_bye_week_counts,
        )

        # Starting lineup progress
        st.divider()
        st.subheader("Starting Lineup Progress")

        lineup_progress = calculate_lineup_progress(
            position_counts=position_counts,
        )

        st.dataframe(
            lineup_progress,
            use_container_width=True,
            hide_index=True,
        )

        # Next pick calculation
        st.divider()

        next_pick_information = (
            shared_next_pick_information.copy()
        )

        display_next_pick_summary(
            next_pick_information=next_pick_information,
        )

        if selected_draft.get("status") == "complete":
            next_pick_information["status"] = (
                "Your draft is complete"
            )


with recommendations_tab:
    st.subheader("Draft Recommendations")
    
    if not selected_draft:
        st.warning(
            "No draft selected. Please select a draft in the Live Draft Board tab."
        )
    else:
        # Get current draft state
        num_teams = shared_number_of_teams
        num_rounds = shared_number_of_rounds
        user_draft_slot = shared_user_draft_slot

        next_pick_information = (
            shared_next_pick_information.copy()
        )

        current_overall = next_pick_information[
            "current_overall"
        ]

        current_round = (
            (current_overall // num_teams) + 1
            if current_overall > 0
            else 1
        )

        current_round = max(
            1,
            min(current_round, num_rounds),
        )

        user_roster_id = shared_user_roster_id

        position_counts = shared_position_counts.copy()

        # Display summary
        display_draft_summary(
            current_round=current_round,
            next_pick_information=next_pick_information,
            position_counts=position_counts,
        )

        # Load NFL players
        if not shared_nfl_players:
            st.error(
                "Recommendations are unavailable because the "
                "Sleeper player directory could not be loaded."
            )
        else:
            

            
            # VBD Settings
            st.divider()
            replacement_levels = render_vbd_settings()
            weight_settings = render_recommendation_weights()

            sleeper_weight_percent = weight_settings[
                "sleeper_weight_percent"
            ]

            vbd_weight_percent = weight_settings[
                "vbd_weight_percent"
            ]

            position_need_percent = weight_settings[
                "position_need_percent"
            ]

            scarcity_percent = weight_settings[
                "scarcity_percent"
            ]

            flex_percent = weight_settings[
                "flex_percent"
            ]

            sleeper_weight, vbd_weight, weights_normalized = (
                normalize_rank_weights(
                    sleeper_weight_percent,
                    vbd_weight_percent,
                )
            )

            position_need_multiplier = position_need_percent / 100.0
            scarcity_multiplier = scarcity_percent / 100.0
            flex_multiplier = flex_percent / 100.0

            if weights_normalized:
                st.info(
                    "Sleeper Rank and VBD weights exceeded 100%. "
                    "The app normalized them proportionally."
                )

            recommendation_players = [
                player.copy()
                for player in shared_available_players
            ]

            recommendation_players = add_vbd_scores(
                recommendation_players,
                replacement_levels,
            )

            
            # Filters
            filter_settings = render_recommendation_filters()

            selected_positions = filter_settings[
                "selected_positions"
            ]

            search_name = filter_settings[
                "player_search"
            ]

            include_inactive = filter_settings[
                "include_inactive"
            ]

            num_recommendations = filter_settings[
                "result_count"
            ]
            
            # Apply filters


            position_statistics = build_position_statistics(
                players=recommendation_players,
                replacement_levels=replacement_levels,
                active_only=True,
            )

            all_recommendations = build_draft_recommendations(
                players=recommendation_players,
                position_statistics=position_statistics,
                position_counts=position_counts,
                replacement_levels=replacement_levels,
                current_round=current_round,
                number_of_teams=num_teams,
                sleeper_weight=sleeper_weight,
                vbd_weight=vbd_weight,
                position_need_multiplier=(
                    position_need_multiplier
                ),
                scarcity_multiplier=scarcity_multiplier,
                flex_multiplier=flex_multiplier,
                bye_week_counts=shared_bye_week_counts,
                position_bye_weeks=shared_position_bye_weeks,
                include_inactive=include_inactive,
            )

            # Top five always reflects the complete recommendation board.
            top_recommendations = all_recommendations[:5]

            filtered_recommendations = filter_recommendations(
                recommendations=all_recommendations,
                selected_positions=selected_positions,
                player_search=search_name,
                maximum_results=num_recommendations,
            )

            
            # Display top 5 as cards
            display_position_summary(
                position_statistics=position_statistics,
                position_counts=position_counts,
                replacement_levels=replacement_levels,
            )

            display_top_recommendations(
                recommendations=top_recommendations,
                maximum_players=5,
            )

            display_recommendation_table(
                recommendations=filtered_recommendations,
            )

            if st.button(
                    "Refresh Draft Data",
                    key="refresh_draft_data",
            ):
                st.rerun()

with waiver_watch_tab:
    st.subheader("Waiver Watch")

    st.write(
        "Trending players who are currently unrostered "
        "in your selected Sleeper league."
    )

    control_column1, control_column2, control_column3 = (
        st.columns(3)
    )

    trend_type = control_column1.selectbox(
        "Trend Type",
        options=["add", "drop"],
        format_func=lambda value: value.title(),
        key="waiver_trend_type",
    )

    lookback_hours = control_column2.selectbox(
        "Lookback Period",
        options=[24, 48, 72, 168],
        index=2,
        format_func=lambda hours: (
            f"{hours} hours"
            if hours < 168
            else "7 days"
        ),
        key="waiver_lookback_hours",
    )

    waiver_result_count = control_column3.selectbox(
        "Number of Players",
        options=[10, 25, 50, 100],
        index=1,
        key="waiver_result_count",
    )

    waiver_positions = st.multiselect(
        "Positions",
        options=["QB", "RB", "WR", "TE", "K", "DEF"],
        default=["QB", "RB", "WR", "TE"],
        key="waiver_position_filter",
    )

    trending_players = get_trending_players(
        trend_type=trend_type,
        lookback_hours=int(lookback_hours),
        limit=100,
    )

    if trending_players is None:
        st.error(
            "Sleeper trending-player data could not be loaded."
        )

    elif not shared_nfl_players:
        st.error(
            "The NFL player directory could not be loaded."
        )

    else:
        sleeper_rank_scores = {
            str(player.get("Player ID")): float(
                player.get(
                    "Sleeper Rank Score",
                    0.0,
                )
            )
            for player in shared_available_players
        }

        waiver_rows = build_waiver_watch_rows(
            trending_players=trending_players,
            nfl_players=shared_nfl_players,
            league_rosters=shared_league_rosters,
            position_counts=shared_position_counts,
            sleeper_rank_scores=sleeper_rank_scores,
            trend_type=trend_type,
        )

        if waiver_positions:
            waiver_rows = [
                player
                for player in waiver_rows
                if player["Position"] in waiver_positions
            ]

        waiver_rows = waiver_rows[
            :int(waiver_result_count)
        ]

        if not waiver_rows:
            st.info(
                "No unrostered trending players match "
                "the current filters."
            )
        else:
            st.caption(
                "FAAB ranges are preliminary estimates. "
                "Verify role, injury news, and team context "
                "before submitting a claim."
            )

            st.dataframe(
                waiver_rows,
                use_container_width=True,
                hide_index=True,
                height=900,
            )