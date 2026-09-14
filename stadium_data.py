"""NFL stadium metadata used for weather analysis."""

NFL_STADIUMS = {
    "ARI": {
        "stadium": "State Farm Stadium",
        "city": "Glendale, AZ",
        "latitude": 33.5276,
        "longitude": -112.2626,
        "roof_type": "retractable",
    },
    "ATL": {
        "stadium": "Mercedes-Benz Stadium",
        "city": "Atlanta, GA",
        "latitude": 33.7554,
        "longitude": -84.4009,
        "roof_type": "retractable",
    },
    "BAL": {
        "stadium": "M&T Bank Stadium",
        "city": "Baltimore, MD",
        "latitude": 39.2780,
        "longitude": -76.6227,
        "roof_type": "outdoor",
    },
    "BUF": {
        "stadium": "Highmark Stadium",
        "city": "Orchard Park, NY",
        "latitude": 42.7738,
        "longitude": -78.7868,
        "roof_type": "outdoor",
    },
    "DAL": {
        "stadium": "AT&T Stadium",
        "city": "Arlington, TX",
        "latitude": 32.7473,
        "longitude": -97.0945,
        "roof_type": "retractable",
    },
    "DET": {
        "stadium": "Ford Field",
        "city": "Detroit, MI",
        "latitude": 42.3400,
        "longitude": -83.0456,
        "roof_type": "dome",
    },
    "HOU": {
        "stadium": "NRG Stadium",
        "city": "Houston, TX",
        "latitude": 29.6847,
        "longitude": -95.4107,
        "roof_type": "retractable",
    },
    "IND": {
        "stadium": "Lucas Oil Stadium",
        "city": "Indianapolis, IN",
        "latitude": 39.7601,
        "longitude": -86.1639,
        "roof_type": "retractable",
    },
    "KC": {
        "stadium": "Arrowhead Stadium",
        "city": "Kansas City, MO",
        "latitude": 39.0489,
        "longitude": -94.4839,
        "roof_type": "outdoor",
    },
    "MIA": {
        "stadium": "Hard Rock Stadium",
        "city": "Miami Gardens, FL",
        "latitude": 25.9580,
        "longitude": -80.2389,
        "roof_type": "outdoor",
    },
    "MIN": {
        "stadium": "U.S. Bank Stadium",
        "city": "Minneapolis, MN",
        "latitude": 44.9738,
        "longitude": -93.2575,
        "roof_type": "dome",
    },
    "NO": {
        "stadium": "Caesars Superdome",
        "city": "New Orleans, LA",
        "latitude": 29.9509,
        "longitude": -90.0812,
        "roof_type": "dome",
    },
    "PHI": {
        "stadium": "Lincoln Financial Field",
        "city": "Philadelphia, PA",
        "latitude": 39.9008,
        "longitude": -75.1675,
        "roof_type": "outdoor",
    },
    "SEA": {
        "stadium": "Lumen Field",
        "city": "Seattle, WA",
        "latitude": 47.5952,
        "longitude": -122.3316,
        "roof_type": "outdoor",
    },
    "SF": {
        "stadium": "Levi's Stadium",
        "city": "Santa Clara, CA",
        "latitude": 37.4030,
        "longitude": -121.9700,
        "roof_type": "outdoor",
    },
}
def get_stadium(team: str) -> dict | None:
    """Return stadium information for a team."""

    return NFL_STADIUMS.get(
        str(team or "").upper().strip()
    )


def is_weather_protected(team: str) -> bool:
    """Return True if weather should have little impact."""

    stadium = get_stadium(team)

    if not stadium:
        return False

    return stadium.get(
        "roof_type"
    ) in {
        "dome",
    }