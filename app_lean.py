"""Lean fantasy football lineup and waiver assistant."""

import streamlit as st

from config import DEFAULT_SLEEPER_USERNAME, SEASON

from lineup_logic import (
    build_lineup_change_rows,
    build_projection_lookup,
    build_recent_performance_lookup,
    build_weekly_lineup_rows,
    build_weekly_points_lookup,
    find_opponent_matchup,
    find_roster_matchup,
    optimize_weekly_lineup,
    split_starters_and_bench,
)

from sleeper_api import (
    get_league_matchups,
    get_league_rosters,
    get_nfl_players,
    get_sleeper_user,
    get_trending_players,
    get_user_leagues,
    get_weekly_projections,
    get_weekly_stats,
    get_game_weather,
    get_nfl_schedule,
    get_nfl_week_schedule,
)

from ui_helpers import (
    display_matchup_summary,
    display_start_sit_advisor,
    display_weekly_lineup,
)

from waiver_logic import build_waiver_watch_rows
from datetime import datetime
from zoneinfo import ZoneInfo
from stadium_data import (
    get_stadium,
    is_weather_protected,
)
from weather_logic import (
    calculate_weather_adjustment,
    classify_weather_risk,
    find_nearest_forecast_hour,
    find_team_schedule_game,
    get_team_weather_location,
    parse_sleeper_kickoff,
    build_team_game_context,
    build_game_weather_context,
)


st.set_page_config(
    page_title="Fantasy Lineup Assistant",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 Fantasy Lineup Assistant")

st.caption(
    "Weekly lineup and waiver recommendations using "
    "Sleeper projections, player performance, injuries, "
    "schedule context, and weather."
)

with st.sidebar:
    st.header("League Settings")

    sleeper_username = st.text_input(
        "Sleeper Username",
        value=DEFAULT_SLEEPER_USERNAME,
        key="lean_sleeper_username",
    )

    selected_season = st.text_input(
        "NFL Season",
        value=SEASON,
        key="lean_selected_season",
    )

    selected_week = st.number_input(
        "NFL Week",
        min_value=1,
        max_value=18,
        value=1,
        step=1,
        key="lean_selected_week",
    )

    if st.button(
        "Refresh Data",
        key="lean_refresh_data",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

if not sleeper_username.strip():
    st.info(
        "Enter your Sleeper username in the sidebar."
    )
    st.stop()

with st.spinner("Connecting to Sleeper..."):
    sleeper_user = get_sleeper_user(
        sleeper_username.strip()
    )

if not sleeper_user:
    st.error(
        "Sleeper could not find that username. "
        "Check the spelling and try again."
    )
    st.stop()

user_id = sleeper_user.get("user_id")

with st.spinner("Loading Sleeper leagues..."):
    leagues = get_user_leagues(
        user_id=user_id,
        season=selected_season,
    )

if leagues is None:
    st.error(
        "The app connected to Sleeper but could not "
        "retrieve league information."
    )
    st.stop()

if not leagues:
    st.warning(
        f"No NFL leagues were found for "
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
    league_status = league.get(
        "status",
        "Unknown",
    )

    label = (
        f"{league_name} | "
        f"Status: {league_status}"
    )

    league_options[label] = league

selected_league_label = st.selectbox(
    "League",
    options=list(league_options.keys()),
    key="lean_selected_league",
)

selected_league = league_options[
    selected_league_label
]

selected_league_id = selected_league.get(
    "league_id"
)

scoring_settings = selected_league.get(
    "scoring_settings",
    {},
)

with st.spinner("Loading league and player data..."):
    league_rosters = (
        get_league_rosters(selected_league_id)
        or []
    )

    nfl_players = get_nfl_players()




if not nfl_players:
    st.error(
        "The NFL player directory could not be loaded."
    )
    st.stop()



user_roster = None

for roster in league_rosters:
    if str(roster.get("owner_id")) == str(user_id):
        user_roster = roster
        break

if user_roster is None:
    st.error(
        "The app could not identify your roster "
        "in the selected league."
    )
    st.stop()

user_roster_id = user_roster.get("roster_id")

lineup_tab, waiver_tab = st.tabs(
    [
        "Lineup Advisor",
        "Waiver Watch",
    ]
)


with lineup_tab:
    st.subheader(f"Week {int(selected_week)} Lineup Advisor")

    st.caption(
        "Recommendations use weekly projections, recent performance, "
        "injury status, bye weeks, and Sleeper player rankings."
    )

    with st.spinner(
        f"Loading Week {int(selected_week)} lineup data..."
    ):
        weekly_matchups = get_league_matchups(
            league_id=selected_league_id,
            week=int(selected_week),
        )

    if weekly_matchups is None:
        st.error(
            "Sleeper matchup data could not be loaded."
        )

    elif not weekly_matchups:
        st.info(
            f"No matchup information is currently available "
            f"for Week {int(selected_week)}."
        )

    else:
        user_matchup = find_roster_matchup(
            matchups=weekly_matchups,
            roster_id=user_roster_id,
        )

        if user_matchup is None:
            st.warning(
                "Your weekly matchup record could not be found."
            )

        else:
            opponent_matchup = find_opponent_matchup(
                matchups=weekly_matchups,
                user_matchup=user_matchup,
            )

            display_matchup_summary(
                user_matchup=user_matchup,
                opponent_matchup=opponent_matchup,
            )

            with st.spinner(
                "Loading weekly projections..."
            ):
                weekly_projections = get_weekly_projections(
                    season=selected_season,
                    week=int(selected_week),
                )

            projection_lookup = {}

            if weekly_projections:
                projection_lookup = build_projection_lookup(
                    projection_rows=weekly_projections,
                    scoring_settings=scoring_settings,
                )

            weekly_points_lookups = []

            first_recent_week = max(
                1,
                int(selected_week) - 3,
            )

            with st.spinner(
                "Loading recent player performance..."
            ):
                for previous_week in range(
                    first_recent_week,
                    int(selected_week),
                ):
                    weekly_stats = get_weekly_stats(
                        season=selected_season,
                        week=previous_week,
                    )

                    weekly_points_lookup = (
                        build_weekly_points_lookup(
                            stats_rows=weekly_stats,
                            scoring_settings=scoring_settings,
                        )
                    )

                    weekly_points_lookups.append(
                        (
                            previous_week,
                            weekly_points_lookup,
                        )
                    )

            performance_lookup = (
                build_recent_performance_lookup(
                    weekly_points_lookups
                )
            )

            lineup_rows = build_weekly_lineup_rows(
                matchup=user_matchup,
                nfl_players=nfl_players,
                selected_week=int(selected_week),
                projection_lookup=projection_lookup,
                performance_lookup=performance_lookup,
            )
            with st.spinner(
                    f"Loading Week {int(selected_week)} NFL schedule..."
            ):
                weekly_schedule_events = get_nfl_week_schedule(
                    season=selected_season,
                    week=int(selected_week),
                )

            if weekly_schedule_events is None:
                st.warning(
                    "The NFL schedule could not be loaded. "
                    "Lineup recommendations will continue without "
                    "game-location context."
                )

                weekly_schedule_events = []

            team_game_contexts = {}

            # Identify each unique NFL team represented on the roster.
            roster_teams = {
                str(player.get("NFL Team") or "")
                for player in lineup_rows
                if player.get("NFL Team")
            }

            # Build schedule and venue context before requesting weather.
            for nfl_team in roster_teams:
                team_game_contexts[nfl_team] = (
                    build_team_game_context(
                        team=nfl_team,
                        schedule_events=weekly_schedule_events,
                    )
                )

            # Display schedule matching diagnostics only after contexts exist.
            with st.expander("Schedule Status"):
                st.write(
                    f"Week {int(selected_week)} games loaded: "
                    f"{len(weekly_schedule_events)}"
                )

                unmatched_teams = sorted(
                    team
                    for team, context in team_game_contexts.items()
                    if not context.get("Scheduled Game")
                )

                if unmatched_teams:
                    st.warning(
                        "No schedule match found for: "
                        + ", ".join(unmatched_teams)
                    )
                else:
                    st.success(
                        "All roster teams were matched to scheduled games."
                    )

            # Build one weather context per unique home venue.
            game_weather_contexts = {}

            current_utc = datetime.now(
                ZoneInfo("UTC")
            )

            for game_context in team_game_contexts.values():
                scheduled_game = game_context.get(
                    "Scheduled Game"
                )

                if not scheduled_game:
                    continue

                home_team = game_context.get(
                    "Home Team",
                    "",
                )

                if not home_team:
                    continue

                # Several roster players may be in the same NFL game.
                if home_team in game_weather_contexts:
                    continue

                kickoff_utc = game_context.get(
                    "Kickoff UTC"
                )

                if kickoff_utc is None:
                    game_weather_contexts[home_team] = (
                        build_game_weather_context(
                            game_context=game_context,
                            weather_data=None,
                        )
                    )
                    continue

                hours_until_kickoff = (
                                              kickoff_utc - current_utc
                                      ).total_seconds() / 3600.0

                indoor_game = bool(
                    game_context.get("Indoor", False)
                )

                weather_data = None

                if (
                        not indoor_game
                        and -24 <= hours_until_kickoff <= 384
                ):
                    coordinates = get_team_weather_location(
                        home_team
                    )

                    if coordinates is not None:
                        latitude, longitude = coordinates

                        weather_data = get_game_weather(
                            latitude=latitude,
                            longitude=longitude,
                        )

                game_weather_contexts[home_team] = (
                    build_game_weather_context(
                        game_context=game_context,
                        weather_data=weather_data,
                    )
                )
            with st.expander("Schedule Status"):
                st.write(
                    f"Week {int(selected_week)} games loaded: "
                    f"{len(weekly_schedule_events)}"
                )

                unmatched_teams = sorted(
                    team
                    for team, context in team_game_contexts.items()
                    if not context.get("Scheduled Game")
                )

                if unmatched_teams:
                    st.warning(
                        "No schedule match found for: "
                        + ", ".join(unmatched_teams)
                    )
                else:
                    st.success(
                        "All roster teams were matched to scheduled games."
                    )

            with st.expander("Venue Diagnostics"):
                unknown_roof_teams = sorted(
                    {
                        context.get("Home Team", "")
                        for context in team_game_contexts.values()
                        if context.get("Scheduled Game")
                           and context.get("Roof Type") == "Unknown"
                    }
                )

                unknown_roof_teams = [
                    team
                    for team in unknown_roof_teams
                    if team
                ]

                if unknown_roof_teams:
                    st.warning(
                        "Missing roof metadata for home teams: "
                        + ", ".join(unknown_roof_teams)
                    )
                else:
                    st.success(
                        "All scheduled games have roof metadata."
                    )

            for player in lineup_rows:
                nfl_team = str(
                    player.get("NFL Team") or ""
                )

                game_context = team_game_contexts.get(
                    nfl_team,
                    {},
                )

                player["Opponent"] = game_context.get(
                    "Opponent",
                    "",
                )

                player["Matchup"] = game_context.get(
                    "Matchup",
                    "",
                )

                player["Home or Away"] = game_context.get(
                    "Home or Away",
                    "",
                )

                player["Kickoff Houston"] = game_context.get(
                    "Kickoff Houston",
                    "",
                )

                player["Game Location"] = game_context.get(
                    "Stadium City",
                    "",
                )

                player["Stadium"] = game_context.get(
                    "Stadium",
                    "",
                )

                player["Roof Type"] = game_context.get(
                    "Roof Type",
                    "Unknown",
                )

                home_team = game_context.get(
                    "Home Team",
                    "",
                )

                weather_context = game_weather_contexts.get(
                    home_team,
                    {},
                )

                player["Weather Risk"] = weather_context.get(
                    "Weather Risk",
                    "N/A",
                )

                player["Weather Summary"] = weather_context.get(
                    "Weather Summary",
                    "Weather forecast unavailable",
                )

                player["Temperature F"] = weather_context.get(
                    "Temperature F",
                )

                player["Wind Speed MPH"] = weather_context.get(
                    "Wind Speed MPH",
                )

                player["Wind Gust MPH"] = weather_context.get(
                    "Wind Gust MPH",
                )

                player["Precipitation Probability"] = (
                    weather_context.get(
                        "Precipitation Probability"
                    )
                )
                weather_available = weather_context.get(
                    "Weather Available",
                    False,
                )

                weather_protected = weather_context.get(
                    "Weather Protected",
                    False,
                )

                if weather_available:
                    temperature_f = weather_context.get(
                        "Temperature F"
                    )

                    wind_speed_mph = weather_context.get(
                        "Wind Speed MPH"
                    )

                    wind_gust_mph = weather_context.get(
                        "Wind Gust MPH"
                    )

                    precipitation_probability = (
                        weather_context.get(
                            "Precipitation Probability"
                        )
                    )

                    weather_adjustment, weather_reason = (
                        calculate_weather_adjustment(
                            position=player.get(
                                "Position",
                                "",
                            ),
                            temperature_f=(
                                temperature_f
                                if temperature_f is not None
                                else 70.0
                            ),
                            precipitation_probability=(
                                precipitation_probability
                                if precipitation_probability
                                   is not None
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
                    weather_reason = weather_context.get(
                    "Weather Unavailable Reason",
                    "Weather forecast unavailable",
                    )

                player["Base Lineup Value"] = player.get(
                    "Lineup Value",
                    0.0,
                )

                player["Weather Adjustment"] = (
                    weather_adjustment
                )

                player["Weather Reason"] = weather_reason

                player["Lineup Value"] = round(
                    float(
                        player.get(
                            "Base Lineup Value",
                            0.0,
                        )
                    )
                    + weather_adjustment,
                    1,
                )
            if not lineup_rows:
                st.info(
                    "No lineup players were returned for this week."
                )

            else:
                starters, bench = (
                    split_starters_and_bench(
                        lineup_rows
                    )
                )

                recommended_starters, _ = (
                    optimize_weekly_lineup(
                        lineup_rows=lineup_rows
                    )
                )

                lineup_changes = build_lineup_change_rows(
                    current_starters=starters,
                    recommended_starters=(
                        recommended_starters
                    ),
                )

                with st.expander(
                        "This Week's NFL Games",
                        expanded=False,
                ):
                    game_rows = []

                    seen_games = set()

                    for nfl_team, game_context in (
                            team_game_contexts.items()
                    ):
                        home_team = game_context.get(
                            "Home Team",
                            "",
                        )

                        away_team = game_context.get(
                            "Away Team",
                            "",
                        )

                        game_key = (
                            away_team,
                            home_team,
                        )

                        if not home_team or game_key in seen_games:
                            continue

                        seen_games.add(game_key)

                        game_rows.append(
                            {
                                "Matchup": (
                                    f"{away_team} at {home_team}"
                                ),
                                "Houston Kickoff": game_context.get(
                                    "Kickoff Houston",
                                    "",
                                ),
                                "Location": game_context.get(
                                    "Stadium City",
                                    "",
                                ),
                                "Stadium": game_context.get(
                                    "Stadium",
                                    "",
                                ),
                                "Roof Type": game_context.get(
                                    "Roof Type",
                                    "",
                                ),
                            }
                        )

                    if game_rows:
                        st.dataframe(
                            game_rows,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "No NFL schedule information is available "
                            "for the selected week."
                        )

                display_start_sit_advisor(
                    recommended_starters=(
                        recommended_starters
                    ),
                    lineup_changes=lineup_changes,
                )

                with st.expander(
                    "Current Sleeper Lineup and Bench"
                ):
                    display_weekly_lineup(
                        starters=starters,
                        bench=bench,
                    )

                with st.expander(
                    "Lineup Data Diagnostics"
                ):
                    diagnostic_column1, diagnostic_column2 = (
                        st.columns(2)
                    )

                    diagnostic_column1.metric(
                        "Players Loaded",
                        len(lineup_rows),
                    )

                    diagnostic_column2.metric(
                        "Weekly Projections Loaded",
                        len(projection_lookup),
                    )



with waiver_tab:
    st.subheader("Waiver Watch")

    st.caption(
        "Trending players who are currently unrostered "
        "in the selected Sleeper league."
    )

    waiver_control1, waiver_control2 = st.columns(2)

    trend_type = waiver_control1.selectbox(
        "Trend",
        options=["add", "drop"],
        format_func=lambda value: value.title(),
        key="lean_waiver_trend_type",
    )

    lookback_hours = waiver_control2.selectbox(
        "Lookback",
        options=[24, 48, 72, 168],
        index=2,
        format_func=lambda hours: (
            f"{hours} hours"
            if hours < 168
            else "7 days"
        ),
        key="lean_waiver_lookback",
    )

    waiver_filter1, waiver_filter2 = st.columns(2)

    waiver_positions = waiver_filter1.multiselect(
        "Positions",
        options=["QB", "RB", "WR", "TE", "K", "DEF"],
        default=["QB", "RB", "WR", "TE"],
        key="lean_waiver_positions",
    )

    waiver_result_count = waiver_filter2.selectbox(
        "Results",
        options=[10, 25, 50],
        index=1,
        key="lean_waiver_result_count",
    )

    waiver_search = st.text_input(
        "Search Player",
        key="lean_waiver_search",
        placeholder="Enter part of a player's name",
    )

    with st.spinner(
        f"Loading trending {trend_type}s..."
    ):
        trending_players = get_trending_players(
            trend_type=trend_type,
            lookback_hours=int(lookback_hours),
            limit=100,
        )

    if trending_players is None:
        st.error(
            "Sleeper trending-player data could not be loaded."
        )

    else:
        sleeper_rank_scores = {}

        for player_id, player_data in nfl_players.items():
            if not isinstance(player_data, dict):
                continue

            try:
                sleeper_rank = float(
                    player_data.get("search_rank")
                )
            except (TypeError, ValueError):
                sleeper_rank_scores[str(player_id)] = 0.0
                continue

            if sleeper_rank < 1:
                sleeper_rank_score = 0.0
            else:
                sleeper_rank_score = 100.0 * (
                    300.0 - sleeper_rank
                ) / 299.0

            sleeper_rank_scores[str(player_id)] = round(
                max(
                    min(sleeper_rank_score, 100.0),
                    0.0,
                ),
                1,
            )

        position_counts = {
            "QB": 0,
            "RB": 0,
            "WR": 0,
            "TE": 0,
            "K": 0,
            "DEF": 0,
        }

        for player_id in user_roster.get(
            "players",
            [],
        ) or []:
            player_data = nfl_players.get(
                str(player_id),
                {},
            )

            position = str(
                player_data.get("position") or ""
            ).upper()

            if position in {"D/ST", "DST"}:
                position = "DEF"

            if position in position_counts:
                position_counts[position] += 1

        waiver_projection_lookup = {}

        with st.spinner(
                "Loading weekly waiver projections..."
        ):
            waiver_projections = get_weekly_projections(
                season=selected_season,
                week=int(selected_week),
            )

        if waiver_projections:
            waiver_projection_lookup = build_projection_lookup(
                projection_rows=waiver_projections,
                scoring_settings=scoring_settings,
            )

        waiver_weekly_points_lookups = []

        first_waiver_recent_week = max(
            1,
            int(selected_week) - 3,
        )

        with st.spinner(
                "Loading recent waiver performance..."
        ):
            for previous_week in range(
                    first_waiver_recent_week,
                    int(selected_week),
            ):
                previous_week_stats = get_weekly_stats(
                    season=selected_season,
                    week=previous_week,
                )

                previous_week_points = (
                    build_weekly_points_lookup(
                        stats_rows=previous_week_stats,
                        scoring_settings=scoring_settings,
                    )
                )

                waiver_weekly_points_lookups.append(
                    (
                        previous_week,
                        previous_week_points,
                    )
                )

        waiver_performance_lookup = (
            build_recent_performance_lookup(
                waiver_weekly_points_lookups
            )
        )

        waiver_projection_lookup = {}

        with st.spinner(
                "Loading weekly waiver projections..."
        ):
            waiver_projections = get_weekly_projections(
                season=selected_season,
                week=int(selected_week),
            )

        if waiver_projections:
            waiver_projection_lookup = (
                build_projection_lookup(
                    projection_rows=waiver_projections,
                    scoring_settings=scoring_settings,
                )
            )

        waiver_weekly_points_lookups = []

        first_waiver_recent_week = max(
            1,
            int(selected_week) - 3,
        )

        with st.spinner(
                "Loading recent waiver performance..."
        ):
            for previous_week in range(
                    first_waiver_recent_week,
                    int(selected_week),
            ):
                previous_week_stats = get_weekly_stats(
                    season=selected_season,
                    week=previous_week,
                )

                previous_week_points = (
                    build_weekly_points_lookup(
                        stats_rows=previous_week_stats,
                        scoring_settings=scoring_settings,
                    )
                )

                waiver_weekly_points_lookups.append(
                    (
                        previous_week,
                        previous_week_points,
                    )
                )

        waiver_performance_lookup = (
            build_recent_performance_lookup(
                waiver_weekly_points_lookups
            )
        )

        waiver_candidate_teams = set()

        for trend_entry in trending_players or []:
            player_id = str(
                trend_entry.get("player_id") or ""
            )

            if not player_id:
                continue

            player_data = nfl_players.get(
                player_id,
                {},
            )

            if not isinstance(player_data, dict):
                continue

            nfl_team = str(
                player_data.get("team") or ""
            ).upper().strip()

            if nfl_team:
                waiver_candidate_teams.add(
                    nfl_team
                )

        with st.spinner(
                f"Loading Week {int(selected_week)} waiver schedule..."
        ):
            waiver_schedule_events = (
                get_nfl_week_schedule(
                    season=selected_season,
                    week=int(selected_week),
                )
            )

        if waiver_schedule_events is None:
            waiver_schedule_events = []

            st.warning(
                "NFL schedule data could not be loaded. "
                "Waiver rankings will continue without "
                "game and weather context."
            )

        waiver_team_contexts = {}

        for nfl_team in waiver_candidate_teams:
            waiver_team_contexts[nfl_team] = (
                build_team_game_context(
                    team=nfl_team,
                    schedule_events=waiver_schedule_events,
                )
            )

        waiver_game_weather_contexts = {}

        current_utc = datetime.now(
            ZoneInfo("UTC")
        )

        for game_context in waiver_team_contexts.values():
            scheduled_game = game_context.get(
                "Scheduled Game"
            )

            if not scheduled_game:
                continue

            home_team = game_context.get(
                "Home Team",
                "",
            )

            if not home_team:
                continue

            if home_team in waiver_game_weather_contexts:
                continue

            kickoff_utc = game_context.get(
                "Kickoff UTC"
            )

            weather_data = None

            if kickoff_utc is not None:
                hours_until_kickoff = (
                                              kickoff_utc - current_utc
                                      ).total_seconds() / 3600.0

                indoor_game = bool(
                    game_context.get(
                        "Indoor",
                        False,
                    )
                )

                if (
                        not indoor_game
                        and -24 <= hours_until_kickoff <= 384
                ):
                    coordinates = (
                        get_team_weather_location(
                            home_team
                        )
                    )

                    if coordinates is not None:
                        latitude, longitude = coordinates

                        weather_data = get_game_weather(
                            latitude=latitude,
                            longitude=longitude,
                        )

            waiver_game_weather_contexts[home_team] = (
                build_game_weather_context(
                    game_context=game_context,
                    weather_data=weather_data,
                )
            )
        waiver_player_game_contexts = {}

        for nfl_team, game_context in (
                waiver_team_contexts.items()
        ):
            home_team = game_context.get(
                "Home Team",
                "",
            )

            weather_context = (
                waiver_game_weather_contexts.get(
                    home_team,
                    {},
                )
            )

            waiver_player_game_contexts[nfl_team] = {
                **game_context,
                **weather_context,
            }
        waiver_rows = build_waiver_watch_rows(
            trending_players=trending_players,
            nfl_players=nfl_players,
            league_rosters=league_rosters,
            position_counts=position_counts,
            sleeper_rank_scores=sleeper_rank_scores,
            trend_type=trend_type,
            projection_lookup=waiver_projection_lookup,
            performance_lookup=waiver_performance_lookup,
            player_game_contexts=(
                waiver_player_game_contexts
            ),
        )

        if waiver_positions:
            waiver_rows = [
                player
                for player in waiver_rows
                if player.get("Position")
                in waiver_positions
            ]

        normalized_waiver_search = (
            waiver_search.strip().lower()
        )

        if normalized_waiver_search:
            waiver_rows = [
                player
                for player in waiver_rows
                if normalized_waiver_search
                in player.get(
                    "Player Name",
                    "",
                ).lower()
            ]

        waiver_rows = waiver_rows[
            :int(waiver_result_count)
        ]

        if not waiver_rows:
            st.info(
                "No unrostered trending players match "
                "the selected filters."
            )

        else:
            st.subheader("Top Waiver Options")

            priority_adds = [
                player
                for player in waiver_rows
                if player.get("Waiver Tier")
                   in {"TIER 1", "TIER 2"}
            ]

            if priority_adds:
                st.success(
                    f"{len(priority_adds)} priority or strong "
                    f"waiver option(s) found."
                )
            else:
                st.info(
                    "No high-priority waiver additions were found. "
                    "The current options are primarily depth or "
                    "watch-list candidates."
                )

            for waiver_player in waiver_rows[:5]:
                with st.container(border=True):
                    player_name = waiver_player.get(
                        "Player Name",
                        "Unknown Player",
                    )

                    position = waiver_player.get(
                        "Position",
                        "",
                    )

                    nfl_team = waiver_player.get(
                        "NFL Team",
                        "",
                    )

                    waiver_rank = waiver_player.get(
                        "Waiver Rank",
                        "",
                    )

                    st.markdown(
                        f"### #{waiver_rank} {player_name}"
                    )

                    waiver_tier = waiver_player.get(
                        "Waiver Tier",
                        "TIER 5",
                    )

                    waiver_label = waiver_player.get(
                        "Waiver Label",
                        "Watch List",
                    )

                    st.caption(
                        f"{waiver_tier} | {waiver_label} | "
                        f"{position} | {nfl_team}"
                    )


                    card_column1, card_column2 = st.columns(2)

                    card_column1.metric(
                        "Waiver Score",
                        waiver_player.get(
                            "Waiver Score",
                            0,
                        ),
                    )

                    card_column2.metric(
                        "Suggested FAAB",
                        waiver_player.get(
                            "Suggested FAAB",
                            "0-1%",
                        ),
                    )

                    waiver_reason = waiver_player.get(
                        "Waiver Reason",
                        "",
                    )

                    if waiver_reason:
                        st.write(
                            f"**Why consider this player:** "
                            f"{waiver_reason}"
                        )

                    card_column1.write(
                        "**Trend Count:** "
                        f"{waiver_player.get('Trend Count', 0)}"
                    )

                    card_column2.write(
                        "**Bye Week:** "
                        f"{waiver_player.get('Bye Week', 'N/A')}"
                    )
                    card_column1.write(
                        "**Projected Points:** "
                        f"{float(
                            waiver_player.get(
                                'Projected Points',
                                0.0,
                            )
                        ):.1f}"
                    )

                    card_column2.write(
                        "**3-Week Average:** "
                        f"{float(
                            waiver_player.get(
                                'Three Week Average',
                                0.0,
                            )
                        ):.1f}"
                    )

                    weather_risk = waiver_player.get(
                        "Weather Risk",
                        "N/A",
                    )

                    weather_adjustment = float(
                        waiver_player.get(
                            "Weather Adjustment",
                            0.0,
                        )
                    )

                    if (
                            weather_risk in {"MEDIUM", "HIGH"}
                            or weather_adjustment != 0.0
                    ):
                        st.write(
                            f"**Weather:** {weather_risk} "
                            f"({weather_adjustment:+.1f})"
                        )

                        st.caption(
                            waiver_player.get(
                                "Weather Reason",
                                "",
                            )
                        )
                    recent_trend = waiver_player.get(
                        "Recent Trend",
                        "No trend",
                    )

                    st.caption(
                        f"Recent trend: {recent_trend}"
                    )
                    injury_status = waiver_player.get(
                        "Injury Status",
                        "",
                    )

                    if injury_status:
                        st.warning(
                            f"Injury Status: {injury_status}"
                        )

            with st.expander(
                "Full Waiver Rankings",
                expanded=False,
            ):
                waiver_display_columns = [
                    "Waiver Rank",
                    "Waiver Tier",
                    "Waiver Label",
                    "Player Name",
                    "Position",
                    "NFL Team",
                    "Opponent",
                    "Kickoff Houston",
                    "Projected Points",
                    "Three Week Average",
                    "Recent Trend",
                    "Weather Risk",
                    "Weather Adjustment",
                    "Waiver Score",
                    "Suggested FAAB",
                    "Injury Status",
                    "Waiver Reason",
                ]

                waiver_display_rows = [
                    {
                        column: player.get(column, "")
                        for column in waiver_display_columns
                    }
                    for player in waiver_rows
                ]

                st.dataframe(
                    waiver_display_rows,
                    use_container_width=True,
                    hide_index=True,
                    height=min(
                        max(
                            len(waiver_display_rows) * 36 + 40,
                            350,
                        ),
                        1000,
                    ),
                )

            st.caption(
                "FAAB ranges are preliminary estimates. "
                "Review role changes, injuries, and team news "
                "before submitting a claim."
            )
