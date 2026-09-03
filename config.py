"""Application configuration for the Fantasy Football Assistant."""

DEFAULT_SLEEPER_USERNAME = "andrewlhunt"

SEASON = "2026"
DRAFT_POSITION = 7
LEAGUE_FORMAT = "PPR"

SLEEPER_API = "https://api.sleeper.app/v1"

ROSTER_LIMITS = {
    "QB": 3,
    "RB": 6,
    "WR": 6,
    "TE": 3,
    "K": 2,
    "DEF": 2,
}

STARTING_LINEUP = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 2,
    "K": 1,
    "DEF": 1,
}

FLEX_POSITIONS = {"RB", "WR", "TE"}

FANTASY_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
    "K",
    "DEF",
}

DEFAULT_REPLACEMENT_LEVELS = {
    "QB": 12,
    "RB": 36,
    "WR": 36,
    "TE": 12,
    "K": 0,
    "DEF": 0,
}

NFL_TEAM_ABBREVIATIONS = {
    "ARI",
    "ATL",
    "BAL",
    "BUF",
    "CAR",
    "CHI",
    "CIN",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GB",
    "HOU",
    "IND",
    "JAX",
    "KC",
    "LV",
    "LAC",
    "LAR",
    "MIA",
    "MIN",
    "NE",
    "NO",
    "NYG",
    "NYJ",
    "PHI",
    "PIT",
    "SEA",
    "SF",
    "TB",
    "TEN",
    "WAS",
}