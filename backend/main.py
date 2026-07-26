import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# --------------------------------------------------
# ENVIRONMENT VARIABLES
# --------------------------------------------------

ENV_PATH = Path(__file__).parent / ".env"

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

FOOTBALL_DATA_API_KEY = (
    os.getenv(
        "FOOTBALL_DATA_API_KEY",
        "",
    )
    .strip()
)

FOOTBALL_DATA_BASE_URL = (
    "https://api.football-data.org/v4"
)

SPORTS_DB_BASE_URL = (
    "https://www.thesportsdb.com/api/v1/json/123"
)

print(
    "Football API key loaded:",
    bool(FOOTBALL_DATA_API_KEY),
    "Length:",
    len(FOOTBALL_DATA_API_KEY),
)


# --------------------------------------------------
# FASTAPI SETUP
# --------------------------------------------------

app = FastAPI(
    title="AI Match Analyst API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------

DATABASE_PATH = (
    Path(__file__).parent
    / "match_history.db"
)


def get_database_connection():
    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def create_database():
    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                final_score TEXT NOT NULL,
                winner TEXT NOT NULL,
                match_type TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                report TEXT NOT NULL
            )
            """
        )

        connection.commit()


create_database()


# --------------------------------------------------
# PYDANTIC MODELS
# --------------------------------------------------

class MatchData(BaseModel):
    homeTeam: str
    awayTeam: str
    finalScore: str
    goalscorers: str = ""
    manOfTheMatch: str = ""
    playerPerformances: str = ""
    possession: str = ""
    shots: str = ""
    keyMoments: str = ""


class TeamRequest(BaseModel):
    teamName: str
    competitionCode: str = "PL"


# --------------------------------------------------
# BASIC ROUTE
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": (
            "AI Match Analyst backend is running"
        ),
        "database": (
            "SQLite match history is enabled"
        ),
        "footballApiConfigured": bool(
            FOOTBALL_DATA_API_KEY
        ),
        "footballApiKeyLength": len(
            FOOTBALL_DATA_API_KEY
        ),
    }


# --------------------------------------------------
# TEAM LOGO ROUTE
# --------------------------------------------------

@app.get("/team-logo/{team_name}")
def get_team_logo(team_name: str):
    clean_team_name = team_name.strip()

    if not clean_team_name:
        raise HTTPException(
            status_code=400,
            detail="Team name is required.",
        )

    encoded_name = quote(clean_team_name)

    url = (
        f"{SPORTS_DB_BASE_URL}/"
        f"searchteams.php?t={encoded_name}"
    )

    try:
        response = requests.get(
            url,
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return {
            "team": clean_team_name,
            "logo": None,
            "message": (
                "The team badge service "
                "could not be reached."
            ),
        }

    except ValueError:
        return {
            "team": clean_team_name,
            "logo": None,
            "message": (
                "The badge service returned "
                "invalid information."
            ),
        }

    teams = data.get("teams")

    if not teams:
        return {
            "team": clean_team_name,
            "logo": None,
            "message": (
                "No team badge was found."
            ),
        }

    selected_team = next(
        (
            team
            for team in teams
            if team.get(
                "strTeam",
                "",
            ).casefold()
            == clean_team_name.casefold()
        ),
        teams[0],
    )

    return {
        "team": selected_team.get(
            "strTeam",
            clean_team_name,
        ),
        "logo": selected_team.get(
            "strBadge"
        ),
    }


# --------------------------------------------------
# FOOTBALL-DATA API HELPERS
# --------------------------------------------------

def get_football_api_headers():
    if not FOOTBALL_DATA_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "Football API key is missing. "
                "Open backend/.env and add "
                "FOOTBALL_DATA_API_KEY="
                "your_real_key."
            ),
        )

    return {
        "X-Auth-Token":
            FOOTBALL_DATA_API_KEY
    }


def make_football_api_request(
    endpoint: str
):
    headers = get_football_api_headers()

    url = (
        f"{FOOTBALL_DATA_BASE_URL}"
        f"{endpoint}"
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not connect to "
                "football-data.org."
            ),
        ) from error

    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail=(
                "The football API key was "
                "rejected. Check the token "
                "inside backend/.env."
            ),
        )

    if response.status_code == 403:
        raise HTTPException(
            status_code=403,
            detail=(
                "Your football-data.org plan "
                "does not allow this request."
            ),
        )

    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail=(
                "The football API request limit "
                "has been reached. Wait before "
                "trying again."
            ),
        )

    if not response.ok:
        try:
            error_data = response.json()

            api_message = error_data.get(
                "message",
                "Unknown football API error.",
            )

        except ValueError:
            api_message = (
                response.text
                or "Unknown football API error."
            )

        raise HTTPException(
            status_code=502,
            detail=(
                "Football API error: "
                f"{api_message}"
            ),
        )

    try:
        return response.json()

    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "The football API returned "
                "invalid JSON data."
            ),
        ) from error


def normalise_team_name(
    team_name: str
):
    name = team_name.casefold().strip()

    removable_words = {
        "fc",
        "afc",
        "cf",
        "football",
        "club",
    }

    words = [
        word
        for word in re.findall(
            r"[a-z0-9]+",
            name,
        )
        if word not in removable_words
    ]

    return " ".join(words)


def find_team_by_name(
    team_name: str,
    competition_code: str,
):
    clean_team_name = team_name.strip()

    if not clean_team_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "A team name is required."
            ),
        )

    clean_competition_code = (
        competition_code
        .strip()
        .upper()
        or "PL"
    )

    data = make_football_api_request(
        (
            "/competitions/"
            f"{clean_competition_code}"
            "/teams"
        )
    )

    teams = data.get("teams", [])

    requested_name = normalise_team_name(
        clean_team_name
    )

    matching_team = next(
        (
            team
            for team in teams
            if requested_name
            in {
                normalise_team_name(
                    team.get("name", "")
                ),
                normalise_team_name(
                    team.get("shortName", "")
                ),
                normalise_team_name(
                    team.get("tla", "")
                ),
            }
        ),
        None,
    )

    if matching_team is None:
        matching_team = next(
            (
                team
                for team in teams
                if requested_name
                in normalise_team_name(
                    team.get("name", "")
                )
                or requested_name
                in normalise_team_name(
                    team.get(
                        "shortName",
                        "",
                    )
                )
            ),
            None,
        )

    if matching_team is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No team called "
                f"'{clean_team_name}' was found "
                f"in competition "
                f"'{clean_competition_code}'."
            ),
        )

    return matching_team


# --------------------------------------------------
# LOAD SQUAD ROUTE
# --------------------------------------------------

@app.post("/load-squad")
def load_squad(request: TeamRequest):
    team = find_team_by_name(
        team_name=request.teamName,
        competition_code=(
            request.competitionCode
        ),
    )

    team_id = team.get("id")

    if not team_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "The selected team does not "
                "have a valid team ID."
            ),
        )

    team_data = make_football_api_request(
        f"/teams/{team_id}"
    )

    squad = []

    for player in team_data.get(
        "squad",
        [],
    ):
        player_name = player.get("name")

        if not player_name:
            continue

        squad.append(
            {
                "id": player.get("id"),
                "name": player_name,
                "position": (
                    player.get("position")
                    or "Unknown"
                ),
                "nationality": (
                    player.get("nationality")
                    or "Unknown"
                ),
                "dateOfBirth": (
                    player.get("dateOfBirth")
                ),
            }
        )

    position_order = {
        "Goalkeeper": 1,
        "Defence": 2,
        "Defender": 2,
        "Midfield": 3,
        "Midfielder": 3,
        "Offence": 4,
        "Forward": 4,
        "Unknown": 5,
    }

    squad.sort(
        key=lambda player: (
            position_order.get(
                player["position"],
                5,
            ),
            player["name"],
        )
    )

    return {
        "team": {
            "id": team_data.get("id"),
            "name": team_data.get(
                "name"
            ),
            "shortName": team_data.get(
                "shortName"
            ),
            "tla": team_data.get("tla"),
            "crest": team_data.get(
                "crest"
            ),
            "venue": team_data.get(
                "venue"
            ),
        },
        "squad": squad,
        "playerCount": len(squad),
    }


# --------------------------------------------------
# MATCH ANALYSIS HELPERS
# --------------------------------------------------

def get_numbers(text: str):
    return [
        int(number)
        for number in re.findall(
            r"\d+",
            text,
        )
    ]


def analyse_match(match: MatchData):
    score_numbers = get_numbers(
        match.finalScore
    )

    shot_numbers = get_numbers(
        match.shots
    )

    possession_numbers = get_numbers(
        match.possession
    )

    home_goals = (
        score_numbers[-2]
        if len(score_numbers) >= 2
        else 0
    )

    away_goals = (
        score_numbers[-1]
        if len(score_numbers) >= 2
        else 0
    )

    home_shots = (
        shot_numbers[-2]
        if len(shot_numbers) >= 2
        else 0
    )

    away_shots = (
        shot_numbers[-1]
        if len(shot_numbers) >= 2
        else 0
    )

    home_possession = (
        possession_numbers[-2]
        if len(possession_numbers) >= 2
        else 50
    )

    away_possession = (
        possession_numbers[-1]
        if len(possession_numbers) >= 2
        else 50
    )

    if home_goals > away_goals:
        winner = match.homeTeam
        loser = match.awayTeam
        loser_goals = away_goals

    elif away_goals > home_goals:
        winner = match.awayTeam
        loser = match.homeTeam
        loser_goals = home_goals

    else:
        winner = None
        loser = None
        loser_goals = None

    total_goals = (
        home_goals + away_goals
    )

    goal_difference = abs(
        home_goals - away_goals
    )

    shot_difference = abs(
        home_shots - away_shots
    )

    possession_difference = abs(
        home_possession
        - away_possession
    )

    if (
        winner is None
        and total_goals == 0
    ):
        match_type = "Goalless Draw"

    elif winner is None:
        match_type = "Scoring Draw"

    elif goal_difference >= 3:
        match_type = "Dominant Win"

    elif goal_difference == 1:
        match_type = "Narrow Win"

    else:
        match_type = "Controlled Win"

    clean_sheet = (
        winner is not None
        and loser_goals == 0
    )

    rating = min(
        10,
        (
            5
            + total_goals
            + (
                1
                if goal_difference == 1
                else 0
            )
        ),
    )

    if total_goals == 0:
        rating = 4

    if winner is None:
        confidence_percent = 50
    else:
        confidence_percent = 52
        confidence_percent += min(goal_difference * 9, 27)
        confidence_percent += min(shot_difference * 1.4, 14)
        confidence_percent += min(possession_difference * 0.45, 9)
        confidence_percent = round(
            max(35, min(confidence_percent, 96))
        )

    confidence = get_confidence_label(
        confidence_percent=confidence_percent,
        is_draw=winner is None,
    )

    return {
        "winner": winner,
        "loser": loser,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_possession":
            home_possession,
        "away_possession":
            away_possession,
        "total_goals": total_goals,
        "goal_difference":
            goal_difference,
        "shot_difference":
            shot_difference,
        "possession_difference":
            possession_difference,
        "match_type": match_type,
        "clean_sheet": clean_sheet,
        "rating": rating,
        "confidence": confidence,
        "confidence_percent": confidence_percent,
    }


def generate_key_insight(
    match: MatchData,
    analysis: dict,
):
    home_team = match.homeTeam
    away_team = match.awayTeam

    home_shots = analysis[
        "home_shots"
    ]

    away_shots = analysis[
        "away_shots"
    ]

    home_possession = analysis[
        "home_possession"
    ]

    away_possession = analysis[
        "away_possession"
    ]

    if (
        home_possession > away_possession
        and home_shots > away_shots
    ):
        return (
            f"{home_team} controlled "
            "possession and created more "
            "shooting opportunities, "
            "suggesting sustained pressure."
        )

    if (
        away_possession > home_possession
        and away_shots > home_shots
    ):
        return (
            f"{away_team} controlled "
            "possession and produced more "
            "shots, showing the stronger "
            "attacking periods."
        )

    if (
        home_possession < away_possession
        and home_shots > away_shots
    ):
        return (
            f"{home_team} had less "
            "possession but created more "
            "chances, suggesting danger "
            "on transitions."
        )

    if (
        away_possession < home_possession
        and away_shots > home_shots
    ):
        return (
            f"{away_team} had less "
            "possession but generated more "
            "shots, showing a strong "
            "counter-attacking threat."
        )

    return (
        "The statistics suggest a balanced "
        "contest, with neither side clearly "
        "dominating every major area."
    )


# --------------------------------------------------
# PLAYER RATINGS
# --------------------------------------------------

def normalise_player_position(position: str):
    clean_position = position.strip().casefold()

    if "goalkeeper" in clean_position or clean_position == "gk":
        return "Goalkeeper"

    if (
        "defence" in clean_position
        or "defender" in clean_position
        or clean_position in {"df", "cb", "lb", "rb", "lwb", "rwb"}
    ):
        return "Defence"

    if (
        "midfield" in clean_position
        or "midfielder" in clean_position
        or clean_position in {"mf", "cm", "dm", "am", "lm", "rm"}
    ):
        return "Midfield"

    if (
        "offence" in clean_position
        or "forward" in clean_position
        or "striker" in clean_position
        or "winger" in clean_position
        or clean_position in {"fw", "st", "cf", "lw", "rw"}
    ):
        return "Offence"

    return "Unknown"


def clamp_rating(rating: float):
    return round(
        max(1.0, min(rating, 10.0)),
        1,
    )


def get_confidence_label(confidence_percent: int, is_draw: bool):
    if is_draw:
        if confidence_percent <= 52:
            return "Too Close To Call"
        return "Evenly Matched"

    if confidence_percent >= 90:
        return "Extremely Confident"

    if confidence_percent >= 80:
        return "High Confidence"

    if confidence_percent >= 70:
        return "Strong Prediction"

    if confidence_percent >= 60:
        return "Moderate Confidence"

    return "Too Close To Call"


def choose_summary_template(player_name: str, templates: list[str]):
    if not templates:
        return ""

    seed = sum(ord(character) for character in player_name.casefold())
    return templates[seed % len(templates)]


def get_int_stat(stats: dict, key: str):
    try:
        return max(0, int(stats.get(key, 0)))
    except (TypeError, ValueError):
        return 0


def get_bool_stat(stats: dict, key: str):
    value = stats.get(key, False)

    if isinstance(value, bool):
        return value

    return str(value).strip().casefold() in {
        "true",
        "1",
        "yes",
        "on",
    }


def calculate_goalkeeper_rating(stats: dict):
    saves = get_int_stat(stats, "saves")
    goals_conceded = get_int_stat(
        stats,
        "goalsConceded",
    )
    penalty_saves = get_int_stat(
        stats,
        "penaltySaves",
    )
    clean_sheet = get_bool_stat(
        stats,
        "cleanSheet",
    )

    rating = 6.0
    rating += min(saves, 10) * 0.22
    rating += penalty_saves * 1.2

    if clean_sheet:
        rating += 0.8

    rating -= goals_conceded * 0.32

    if saves >= 5 and goals_conceded <= 1:
        rating += 0.3

    return clamp_rating(rating)


def calculate_defender_rating(stats: dict):
    tackles = get_int_stat(stats, "tackles")
    interceptions = get_int_stat(
        stats,
        "interceptions",
    )
    clearances = get_int_stat(
        stats,
        "clearances",
    )
    defensive_errors = get_int_stat(
        stats,
        "defensiveErrors",
    )
    goals = get_int_stat(stats, "goals")
    assists = get_int_stat(stats, "assists")
    clean_sheet = get_bool_stat(
        stats,
        "cleanSheet",
    )

    rating = 6.0
    rating += min(tackles, 10) * 0.16
    rating += min(interceptions, 10) * 0.14
    rating += min(clearances, 15) * 0.07
    rating += goals * 1.0
    rating += assists * 0.55

    if clean_sheet:
        rating += 0.65

    rating -= defensive_errors * 0.9

    if (
        tackles + interceptions >= 10
        and defensive_errors == 0
    ):
        rating += 0.25

    return clamp_rating(rating)


def calculate_midfielder_rating(stats: dict):
    goals = get_int_stat(stats, "goals")
    assists = get_int_stat(stats, "assists")
    key_passes = get_int_stat(
        stats,
        "keyPasses",
    )
    chances_created = get_int_stat(
        stats,
        "chancesCreated",
    )
    tackles = get_int_stat(stats, "tackles")

    rating = 6.0
    rating += goals * 1.0
    rating += assists * 0.85
    rating += min(key_passes, 10) * 0.16
    rating += min(chances_created, 10) * 0.12
    rating += min(tackles, 10) * 0.09

    if key_passes >= 4 or chances_created >= 4:
        rating += 0.2

    return clamp_rating(rating)


def calculate_forward_rating(stats: dict):
    goals = get_int_stat(stats, "goals")
    assists = get_int_stat(stats, "assists")
    shots = get_int_stat(stats, "shots")
    shots_on_target = get_int_stat(
        stats,
        "shotsOnTarget",
    )
    big_chances_missed = get_int_stat(
        stats,
        "bigChancesMissed",
    )

    rating = 6.0
    rating += goals * 1.25
    rating += assists * 0.75
    rating += min(shots_on_target, 8) * 0.14
    rating += min(shots, 10) * 0.03
    rating -= big_chances_missed * 0.35

    off_target_shots = max(
        0,
        shots - shots_on_target,
    )

    if goals == 0 and shots >= 5:
        rating -= min(
            0.6,
            off_target_shots * 0.08,
        )

    if goals >= 2:
        rating += 0.25

    return clamp_rating(rating)


def calculate_unknown_position_rating(stats: dict):
    goals = get_int_stat(stats, "goals")
    assists = get_int_stat(stats, "assists")
    shots = get_int_stat(stats, "shots")
    tackles = get_int_stat(stats, "tackles")

    rating = (
        6.0
        + goals * 1.0
        + assists * 0.7
        + shots * 0.08
        + tackles * 0.1
    )

    return clamp_rating(rating)


def calculate_position_aware_rating(
    position: str,
    stats: dict,
):
    if position == "Goalkeeper":
        return calculate_goalkeeper_rating(stats)

    if position == "Defence":
        return calculate_defender_rating(stats)

    if position == "Midfield":
        return calculate_midfielder_rating(stats)

    if position == "Offence":
        return calculate_forward_rating(stats)

    return calculate_unknown_position_rating(stats)


def parse_player_performances(
    player_performances: str,
):
    clean_data = player_performances.strip()

    if not clean_data:
        return []

    try:
        parsed_data = json.loads(clean_data)

        if isinstance(parsed_data, list):
            return [
                player
                for player in parsed_data
                if isinstance(player, dict)
            ]

    except json.JSONDecodeError:
        pass

    # Backward compatibility for the earlier CSV format:
    # name, position, goals, assists, shots, tackles
    players = []

    for line in clean_data.splitlines():
        parts = [
            part.strip()
            for part in line.split(",")
        ]

        if len(parts) != 6:
            continue

        try:
            goals = max(0, int(parts[2]))
            assists = max(0, int(parts[3]))
            shots = max(0, int(parts[4]))
            tackles = max(0, int(parts[5]))
        except ValueError:
            continue

        players.append(
            {
                "name": parts[0],
                "position": parts[1],
                "side": "",
                "team": "",
                "stats": {
                    "goals": goals,
                    "assists": assists,
                    "shots": shots,
                    "tackles": tackles,
                },
            }
        )

    return players


def get_losing_side(
    analysis: dict,
):
    home_goals = analysis["home_goals"]
    away_goals = analysis["away_goals"]

    if home_goals > away_goals:
        return "away"

    if away_goals > home_goals:
        return "home"

    return None


def apply_result_adjustment(
    rating: float,
    player_side: str,
    losing_side: str | None,
):
    if (
        losing_side
        and player_side.strip().casefold()
        == losing_side
    ):
        rating -= 0.25

    return clamp_rating(rating)


def create_player_performance_summary(
    player_name: str,
    position: str,
    rating: float,
    stats: dict,
    is_man_of_the_match: bool = False,
):
    goals = get_int_stat(stats, "goals")
    assists = get_int_stat(stats, "assists")

    if is_man_of_the_match:
        opening = choose_summary_template(
            player_name,
            [
                "A match-defining display that set the standard",
                "The standout individual performance of the match",
                "A decisive contribution worthy of the top honour",
            ],
        )
    elif rating >= 8.5:
        opening = choose_summary_template(
            player_name,
            [
                "An outstanding all-round performance",
                "A commanding display from start to finish",
                "A high-impact performance in the key phases",
            ],
        )
    elif rating >= 7.2:
        opening = choose_summary_template(
            player_name,
            [
                "A strong and effective performance",
                "A consistently positive contribution",
                "A reliable display with several important actions",
            ],
        )
    elif rating >= 6.0:
        opening = choose_summary_template(
            player_name,
            [
                "A steady contribution across the match",
                "A composed performance with useful involvement",
                "A solid display without dominating the contest",
            ],
        )
    else:
        opening = choose_summary_template(
            player_name,
            [
                "A difficult performance with limited influence",
                "A below-par display in a demanding match",
                "A challenging outing with room for improvement",
            ],
        )

    if position == "Goalkeeper":
        saves = get_int_stat(stats, "saves")
        conceded = get_int_stat(stats, "goalsConceded")
        penalties = get_int_stat(stats, "penaltySaves")
        clean_sheet = get_bool_stat(stats, "cleanSheet")
        details = []

        if clean_sheet:
            details.append("preserved a clean sheet")
        if saves:
            details.append(f"made {saves} save{'s' if saves != 1 else ''}")
        if penalties:
            details.append(
                f"stopped {penalties} "
                f"penalt{'ies' if penalties != 1 else 'y'}"
            )
        if conceded and not clean_sheet:
            details.append(f"conceded {conceded}")

        ending = (
            ", ".join(details)
            or "provided a composed presence behind the defence"
        )

        return (
            f"{opening}. The goalkeeper {ending}. "
            "The rating reflects shot-stopping, composure and command "
            "of the penalty area."
        )

    if position == "Defence":
        tackles = get_int_stat(stats, "tackles")
        interceptions = get_int_stat(stats, "interceptions")
        clearances = get_int_stat(stats, "clearances")
        errors = get_int_stat(stats, "defensiveErrors")
        clean_sheet = get_bool_stat(stats, "cleanSheet")
        actions = tackles + interceptions + clearances
        details = []

        if actions:
            details.append(f"completed {actions} defensive actions")
        else:
            details.append("showed positional discipline")
        if goals:
            details.append(f"scored {goals} goal{'s' if goals != 1 else ''}")
        if assists:
            details.append(
                f"provided {assists} assist{'s' if assists != 1 else ''}"
            )
        if clean_sheet:
            details.append("helped secure a clean sheet")
        if errors:
            details.append(
                f"was affected by {errors} defensive "
                f"error{'s' if errors != 1 else ''}"
            )

        return f"{opening}. The defender " + ", ".join(details) + "."

    if position == "Midfield":
        key_passes = get_int_stat(stats, "keyPasses")
        chances = get_int_stat(stats, "chancesCreated")
        tackles = get_int_stat(stats, "tackles")
        creative_actions = key_passes + chances

        if creative_actions >= 6:
            influence = "dictated several attacking phases"
        elif goals or assists:
            influence = "made a direct contribution in the final third"
        elif tackles >= 4:
            influence = "added valuable defensive work in midfield"
        else:
            influence = "kept the midfield functioning with measured involvement"

        return (
            f"{opening}. The midfielder recorded {goals} "
            f"goal{'s' if goals != 1 else ''}, {assists} "
            f"assist{'s' if assists != 1 else ''}, {key_passes} key "
            f"pass{'es' if key_passes != 1 else ''}, {chances} chance"
            f"{'s' if chances != 1 else ''} created and {tackles} "
            f"tackle{'s' if tackles != 1 else ''}. They {influence}."
        )

    if position == "Offence":
        shots = get_int_stat(stats, "shots")
        on_target = get_int_stat(stats, "shotsOnTarget")
        missed = get_int_stat(stats, "bigChancesMissed")
        efficiency = (on_target / shots * 100) if shots else 0

        if goals >= 2:
            impact = "delivered a decisive scoring performance"
        elif goals or assists:
            impact = "made a clear contribution to the attacking output"
        elif on_target >= 3:
            impact = "remained a regular threat despite not scoring"
        else:
            impact = "found it difficult to consistently trouble the defence"

        return (
            f"{opening}. The attacker produced {goals} "
            f"goal{'s' if goals != 1 else ''}, {assists} "
            f"assist{'s' if assists != 1 else ''} and {on_target} shot"
            f"{'s' if on_target != 1 else ''} on target from {shots} "
            f"attempt{'s' if shots != 1 else ''} "
            f"({efficiency:.0f}% accuracy), with {missed} big chance"
            f"{'s' if missed != 1 else ''} missed. They {impact}."
        )

    return (
        f"{opening}. The submitted statistics produced a "
        f"{rating:.1f}/10 position-aware rating."
    )


def calculate_player_ratings(
    player_performances: str,
    man_of_the_match: str,
    analysis: dict,
):
    player_ratings = []

    motm_name = (
        man_of_the_match
        .strip()
        .casefold()
    )

    losing_side = get_losing_side(analysis)

    for player_data in parse_player_performances(
        player_performances
    ):
        player_name = str(
            player_data.get("name", "")
        ).strip()

        if not player_name:
            continue

        position = normalise_player_position(
            str(
                player_data.get(
                    "position",
                    "Unknown",
                )
            )
        )

        stats = player_data.get("stats", {})

        if not isinstance(stats, dict):
            stats = {}

        rating = calculate_position_aware_rating(
            position=position,
            stats=stats,
        )

        rating = apply_result_adjustment(
            rating=rating,
            player_side=str(
                player_data.get("side", "")
            ),
            losing_side=losing_side,
        )

        is_man_of_the_match = (
            bool(motm_name)
            and player_name.casefold()
            == motm_name
        )

        player_ratings.append(
            {
                "name": player_name,
                "team": str(
                    player_data.get("team", "")
                ).strip(),
                "side": str(
                    player_data.get("side", "")
                ).strip(),
                "position": position,
                "rating": rating,
                "stats": stats,
                "isManOfTheMatch":
                    is_man_of_the_match,
                "isMotm": is_man_of_the_match,
            }
        )

    make_motm_highest(
        player_ratings
    )

    for player in player_ratings:
        player["summary"] = create_player_performance_summary(
            player_name=player["name"],
            position=player["position"],
            rating=player["rating"],
            stats=player["stats"],
            is_man_of_the_match=player["isManOfTheMatch"],
        )

    return sorted(
        player_ratings,
        key=lambda player: (
            player["rating"],
            player["isManOfTheMatch"],
            player["name"],
        ),
        reverse=True,
    )


def make_motm_highest(
    player_ratings: list,
):
    if not player_ratings:
        return

    motm_player = next(
        (
            player
            for player in player_ratings
            if player[
                "isManOfTheMatch"
            ]
        ),
        None,
    )

    if motm_player is None:
        return

    other_players = [
        player
        for player in player_ratings
        if player is not motm_player
    ]

    if not other_players:
        return

    highest_other_rating = max(
        player["rating"]
        for player in other_players
    )

    if (
        motm_player["rating"]
        > highest_other_rating
    ):
        return

    if highest_other_rating < 10:
        motm_player["rating"] = round(
            highest_other_rating + 0.1,
            1,
        )
        return

    for player in other_players:
        if player["rating"] >= 10:
            player["rating"] = 9.9

    motm_player["rating"] = 10.0


def format_stat_label(stat_name: str):
    labels = {
        "goals": "goals",
        "assists": "assists",
        "shots": "shots",
        "shotsOnTarget": "shots on target",
        "bigChancesMissed": "big chances missed",
        "tackles": "tackles",
        "interceptions": "interceptions",
        "clearances": "clearances",
        "defensiveErrors": "defensive errors",
        "keyPasses": "key passes",
        "chancesCreated": "chances created",
        "saves": "saves",
        "goalsConceded": "goals conceded",
        "penaltySaves": "penalty saves",
    }

    return labels.get(stat_name, stat_name)


def create_player_stat_summary(player: dict):
    stats = player.get("stats", {})
    summary_parts = []

    preferred_order = {
        "Goalkeeper": [
            "saves",
            "goalsConceded",
            "penaltySaves",
        ],
        "Defence": [
            "goals",
            "assists",
            "tackles",
            "interceptions",
            "clearances",
            "defensiveErrors",
        ],
        "Midfield": [
            "goals",
            "assists",
            "keyPasses",
            "chancesCreated",
            "tackles",
        ],
        "Offence": [
            "goals",
            "assists",
            "shots",
            "shotsOnTarget",
            "bigChancesMissed",
        ],
    }

    for stat_name in preferred_order.get(
        player["position"],
        list(stats.keys()),
    ):
        if stat_name in stats:
            summary_parts.append(
                f'{get_int_stat(stats, stat_name)} '
                f'{format_stat_label(stat_name)}'
            )

    if "cleanSheet" in stats:
        summary_parts.append(
            "clean sheet"
            if get_bool_stat(stats, "cleanSheet")
            else "no clean sheet"
        )

    return " · ".join(summary_parts)


def create_player_ratings_section(
    player_ratings: list,
):
    if not player_ratings:
        return """
        <h3>Player Ratings</h3>

        <p>
            No valid player performance data
            was provided.
        </p>
        """

    player_cards = ""

    for player in player_ratings:
        motm_badge = ""

        if player["isManOfTheMatch"]:
            motm_badge = """
            <span class="motm-badge">
                Man of the Match
            </span>
            """

        team_text = ""

        if player["team"]:
            team_text = (
                f'<span class="player-team-name">'
                f'{player["team"]}'
                f'</span>'
            )

        stat_summary = create_player_stat_summary(
            player
        )

        player_cards += f"""
        <div class="player-rating-card">
            <div class="player-rating-info">
                <div class="player-name-row">
                    <strong>
                        {player["name"]}
                    </strong>

                    {motm_badge}
                </div>

                <span>
                    {player["position"]}
                    {f" · {stat_summary}" if stat_summary else ""}
                </span>

                {team_text}
            </div>

            <div class="rating-score">
                {player["rating"]}
            </div>
        </div>
        """

    return f"""
    <h3>Player Ratings</h3>

    <div class="player-ratings-grid">
        {player_cards}
    </div>
    """


# --------------------------------------------------
# DATABASE FUNCTIONS
# --------------------------------------------------

def save_match_to_database(
    match: MatchData,
    winner: str | None,
    match_type: str,
    rating: int,
    report: str,
):
    with get_database_connection() as connection:
        connection.execute(
            """
            INSERT INTO match_history (
                home_team,
                away_team,
                final_score,
                winner,
                match_type,
                rating,
                created_at,
                report
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match.homeTeam,
                match.awayTeam,
                match.finalScore,
                (
                    winner
                    if winner
                    else "Draw"
                ),
                match_type,
                rating,
                datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                ),
                report,
            ),
        )

        connection.commit()


def get_all_match_history():
    with get_database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                home_team,
                away_team,
                final_score,
                winner,
                match_type,
                rating,
                created_at,
                report
            FROM match_history
            ORDER BY id DESC
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "homeTeam":
                row["home_team"],
            "awayTeam":
                row["away_team"],
            "finalScore":
                row["final_score"],
            "winner":
                row["winner"],
            "matchType":
                row["match_type"],
            "rating":
                row["rating"],
            "createdAt":
                row["created_at"],
            "report":
                row["report"],
        }
        for row in rows
    ]


# --------------------------------------------------
# REPORT GENERATION
# --------------------------------------------------

@app.post("/generate-report")
def generate_report(match: MatchData):
    analysis = analyse_match(match)

    player_ratings = (
        calculate_player_ratings(
            match.playerPerformances,
            match.manOfTheMatch,
            analysis,
        )
    )

    player_ratings_section = (
        create_player_ratings_section(
            player_ratings
        )
    )

    winner = analysis["winner"]
    loser = analysis["loser"]
    match_type = analysis[
        "match_type"
    ]

    if (
        winner is None
        and analysis["total_goals"] == 0
    ):
        summary = f"""
        <strong>{match.homeTeam}</strong>
        and
        <strong>{match.awayTeam}</strong>
        played out a tense
        <strong>{match.finalScore}</strong>
        draw. Neither side found the
        breakthrough.
        """

        verdict = (
            "This was a disciplined defensive "
            "match where structure mattered "
            "more than attacking quality."
        )

    elif winner is None:
        summary = f"""
        <strong>{match.homeTeam}</strong>
        and
        <strong>{match.awayTeam}</strong>
        shared the points in an entertaining
        <strong>{match.finalScore}</strong>
        draw.
        """

        verdict = (
            "Both teams showed attacking "
            "threat, but neither side had "
            "enough control to win."
        )

    elif match_type == "Dominant Win":
        summary = f"""
        <strong>{winner}</strong>
        produced a dominant performance
        against
        <strong>{loser}</strong>, winning
        <strong>{match.finalScore}</strong>.
        """

        verdict = (
            f"{winner} were clearly the "
            "stronger side and controlled "
            "the biggest moments."
        )

    elif match_type == "Narrow Win":
        summary = f"""
        <strong>{winner}</strong>
        edged past
        <strong>{loser}</strong>
        with a narrow
        <strong>{match.finalScore}</strong>
        victory.
        """

        verdict = (
            f"{winner} showed composure "
            "under pressure and were more "
            "clinical in decisive moments."
        )

    else:
        summary = f"""
        <strong>{winner}</strong>
        secured a controlled win over
        <strong>{loser}</strong>, with the
        match finishing
        <strong>{match.finalScore}</strong>.
        """

        verdict = (
            f"{winner} deserved the win "
            "after showing better balance "
            "between control and attacking "
            "threat."
        )

    if match.manOfTheMatch.strip():
        motm_section = f"""
        <h3>Man of the Match</h3>

        <p>
            <strong>
                {match.manOfTheMatch}
            </strong>
            was selected as Man of the Match
            after a standout performance.
        </p>
        """

    else:
        motm_section = """
        <h3>Man of the Match</h3>

        <p>
            No clear Man of the Match was
            selected.
        </p>
        """

    clean_sheet_text = ""

    if (
        analysis["clean_sheet"]
        and winner
    ):
        clean_sheet_text = f"""
        <p>
            <strong>{winner}</strong>
            recorded a clean sheet, showing
            strong defensive discipline.
        </p>
        """

    key_insight = generate_key_insight(
        match,
        analysis,
    )

    key_moments = (
        match.keyMoments.strip()
        or "No key moments were provided."
    )

    goalscorers_text = (
        match.goalscorers.strip()
        or "No goalscorers were provided."
    )

    report = f"""
    <h3>Match Summary</h3>
    <p>{summary}</p>

    <h3>Key Moments</h3>
    <p>{key_moments}</p>

    <h3>Goalscorers</h3>
    <p>{goalscorers_text}</p>

    <h3>Attacking Analysis</h3>
    <p>
        The shot numbers were
        <strong>{match.shots}</strong>.
        The shot difference was
        <strong>
            {analysis["shot_difference"]}
        </strong>.
    </p>

    <h3>Possession Analysis</h3>
    <p>
        Possession was recorded as
        <strong>{match.possession}</strong>,
        with a difference of
        <strong>
            {analysis["possession_difference"]}%
        </strong>.
    </p>

    <h3>Match Intelligence</h3>

    <div class="intelligence-grid">
        <div>
            <span>Match Type</span>
            <strong>
                {analysis["match_type"]}
            </strong>
        </div>

        <div>
            <span>Winner</span>
            <strong>
                {winner if winner else "Draw"}
            </strong>
        </div>

        <div>
            <span>Goal Difference</span>
            <strong>
                {analysis["goal_difference"]}
            </strong>
        </div>

        <div>
            <span>Shot Difference</span>
            <strong>
                {analysis["shot_difference"]}
            </strong>
        </div>

        <div>
            <span>
                Possession Difference
            </span>

            <strong>
                {analysis["possession_difference"]}%
            </strong>
        </div>

        <div>
            <span>Clean Sheet</span>

            <strong>
                {
                    "Yes"
                    if analysis["clean_sheet"]
                    else "No"
                }
            </strong>
        </div>
    </div>

    <h3>Key Insight</h3>
    <p>{key_insight}</p>

    <h3>Match Rating</h3>
    <p>
        <strong>
            {analysis["rating"]}/10
        </strong>
        entertainment rating.
    </p>

    <h3>Result Confidence</h3>
    <p>
        <strong>
            {analysis["confidence"]}
        </strong>
    </p>

    <h3>Tactical Verdict</h3>
    <p>{verdict}</p>

    {clean_sheet_text}

    {player_ratings_section}

    {motm_section}
    """

    save_match_to_database(
        match=match,
        winner=winner,
        match_type=match_type,
        rating=analysis["rating"],
        report=report,
    )

    return {
        "report": report,
        "history":
            get_all_match_history(),
        "playerRatings":
            player_ratings,
        "analysis": {
            "winner": winner if winner else "Draw",
            "matchType": analysis["match_type"],
            "rating": analysis["rating"],
            "confidence": analysis["confidence"],
            "confidencePercent": analysis["confidence_percent"],
            "goalDifference": analysis["goal_difference"],
            "shotDifference": analysis["shot_difference"],
            "possessionDifference": analysis["possession_difference"],
            "cleanSheet": analysis["clean_sheet"],
        },
    }


# --------------------------------------------------
# MATCH HISTORY ROUTE
# --------------------------------------------------

@app.get("/history")
def get_history():
    return {
        "history":
            get_all_match_history()
    }