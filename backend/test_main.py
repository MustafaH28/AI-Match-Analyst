"""
Unit and API tests for the AI Match Analyst backend.

Run from the backend folder:
    python -m unittest discover -v

External services (football-data.org and TheSportsDB) are mocked, so the
tests need no API key or internet connection, and use a temporary SQLite
database instead of match_history.db.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Point the app at a throwaway database BEFORE importing it,
# because main.py creates the database when it is imported.
TEST_DB_DIR = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(TEST_DB_DIR.name, "test_history.db")

import requests  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


def make_match(**overrides):
    """Build a MatchData object with sensible defaults."""
    data = {
        "homeTeam": "Arsenal",
        "awayTeam": "Chelsea",
        "finalScore": "2-1",
        "shots": "10-8",
        "possession": "55-45",
    }
    data.update(overrides)
    return main.MatchData(**data)


# --------------------------------------------------
# MATCH ANALYSIS
# --------------------------------------------------

class TestAnalyseMatch(unittest.TestCase):

    def test_narrow_home_win(self):
        result = main.analyse_match(make_match())

        self.assertEqual(result["winner"], "Arsenal")
        self.assertEqual(result["loser"], "Chelsea")
        self.assertEqual(result["match_type"], "Narrow Win")
        self.assertEqual(result["goal_difference"], 1)
        self.assertEqual(result["confidence"], "Low")
        self.assertFalse(result["clean_sheet"])

    def test_goalless_draw(self):
        result = main.analyse_match(
            make_match(finalScore="0-0", shots="5-5", possession="50-50")
        )

        self.assertIsNone(result["winner"])
        self.assertEqual(result["match_type"], "Goalless Draw")
        self.assertEqual(result["rating"], 4)
        self.assertEqual(result["confidence"], "Evenly Matched")
        self.assertEqual(result["confidence_percent"], 50)

    def test_dominant_away_win_with_clean_sheet(self):
        result = main.analyse_match(
            make_match(finalScore="0-4", shots="3-15", possession="40-60")
        )

        self.assertEqual(result["winner"], "Chelsea")
        self.assertEqual(result["match_type"], "Dominant Win")
        self.assertTrue(result["clean_sheet"])
        self.assertEqual(result["confidence"], "High")

    def test_missing_stats_use_safe_defaults(self):
        result = main.analyse_match(
            make_match(finalScore="", shots="", possession="")
        )

        self.assertEqual(result["home_goals"], 0)
        self.assertEqual(result["away_goals"], 0)
        self.assertEqual(result["home_possession"], 50)
        self.assertEqual(result["away_possession"], 50)

    def test_match_rating_never_exceeds_ten(self):
        result = main.analyse_match(make_match(finalScore="6-5"))

        self.assertLessEqual(result["rating"], 10)


# --------------------------------------------------
# PLAYER RATINGS
# --------------------------------------------------

class TestPlayerRatingHelpers(unittest.TestCase):

    def test_clamp_rating_keeps_ratings_between_1_and_10(self):
        self.assertEqual(main.clamp_rating(15), 10.0)
        self.assertEqual(main.clamp_rating(-3), 1.0)
        self.assertEqual(main.clamp_rating(7.26), 7.3)

    def test_position_names_are_normalised(self):
        self.assertEqual(main.normalise_player_position("GK"), "Goalkeeper")
        self.assertEqual(main.normalise_player_position("cb"), "Defence")
        self.assertEqual(main.normalise_player_position("Midfielder"), "Midfield")
        self.assertEqual(main.normalise_player_position("Striker"), "Offence")
        self.assertEqual(main.normalise_player_position("Coach"), "Unknown")

    def test_invalid_stats_are_treated_safely(self):
        self.assertEqual(main.get_int_stat({"goals": "abc"}, "goals"), 0)
        self.assertEqual(main.get_int_stat({"goals": -4}, "goals"), 0)
        self.assertEqual(main.get_int_stat({}, "goals"), 0)
        self.assertTrue(main.get_bool_stat({"cleanSheet": "yes"}, "cleanSheet"))
        self.assertFalse(main.get_bool_stat({"cleanSheet": "no"}, "cleanSheet"))

    def test_goalkeeper_rating(self):
        rating = main.calculate_goalkeeper_rating(
            {"saves": 5, "goalsConceded": 1, "cleanSheet": False}
        )
        # 6.0 + 5*0.22 - 1*0.32 + 0.3 bonus = 7.08
        self.assertEqual(rating, 7.1)

    def test_forward_rating_rewards_goals(self):
        two_goals = main.calculate_forward_rating(
            {"goals": 2, "shots": 4, "shotsOnTarget": 3}
        )
        no_goals = main.calculate_forward_rating(
            {"goals": 0, "shots": 4, "shotsOnTarget": 3}
        )
        # 6.0 + 2*1.25 + 3*0.14 + 4*0.03 + 0.25 bonus = 9.29
        self.assertEqual(two_goals, 9.3)
        self.assertGreater(two_goals, no_goals)

    def test_defensive_errors_lower_defender_rating(self):
        clean = main.calculate_defender_rating({"tackles": 4})
        with_errors = main.calculate_defender_rating(
            {"tackles": 4, "defensiveErrors": 2}
        )
        self.assertLess(with_errors, clean)

    def test_losing_side_loses_a_quarter_point(self):
        self.assertEqual(main.apply_result_adjustment(7.0, "Home", "away"), 7.0)
        self.assertLess(main.apply_result_adjustment(7.0, "Away", "away"), 7.0)


class TestParsePlayerPerformances(unittest.TestCase):

    def test_parses_json_list(self):
        raw = json.dumps([
            {"name": "Saka", "position": "Forward", "stats": {"goals": 1}},
            "not a player",
        ])
        players = main.parse_player_performances(raw)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["name"], "Saka")

    def test_parses_legacy_csv_and_skips_bad_lines(self):
        raw = "Saka, Forward, 1, 0, 4, 1\nbad line\nRice, Midfield, x, 0, 1, 3"
        players = main.parse_player_performances(raw)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["stats"]["goals"], 1)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(main.parse_player_performances("   "), [])


class TestCalculatePlayerRatings(unittest.TestCase):

    def test_man_of_the_match_is_always_ranked_first(self):
        performances = json.dumps([
            {"name": "Striker", "position": "Forward",
             "stats": {"goals": 2, "shots": 4, "shotsOnTarget": 3}},
            {"name": "Playmaker", "position": "Midfield", "stats": {}},
        ])
        draw = {"home_goals": 1, "away_goals": 1}

        ratings = main.calculate_player_ratings(performances, "Playmaker", draw)

        self.assertEqual(ratings[0]["name"], "Playmaker")
        self.assertTrue(ratings[0]["isManOfTheMatch"])
        self.assertGreater(ratings[0]["rating"], ratings[1]["rating"])
        self.assertIn("summary", ratings[0])


# --------------------------------------------------
# TEAM LOOKUP (football-data.org mocked)
# --------------------------------------------------

SAMPLE_TEAMS = {
    "teams": [
        {"id": 57, "name": "Arsenal FC", "shortName": "Arsenal", "tla": "ARS"},
        {"id": 65, "name": "Manchester City FC", "shortName": "Man City", "tla": "MCI"},
    ]
}


class TestTeamLookup(unittest.TestCase):

    def test_normalise_team_name_removes_club_words(self):
        self.assertEqual(main.normalise_team_name("Arsenal FC"), "arsenal")
        self.assertEqual(main.normalise_team_name("AFC Bournemouth"), "bournemouth")

    @patch("main.make_football_api_request", return_value=SAMPLE_TEAMS)
    def test_finds_team_by_short_name_or_code(self, mock_api):
        self.assertEqual(main.find_team_by_name("man city", "pl")["id"], 65)
        self.assertEqual(main.find_team_by_name("ARS", "PL")["id"], 57)
        mock_api.assert_called_with("/competitions/PL/teams")

    @patch("main.make_football_api_request", return_value=SAMPLE_TEAMS)
    def test_unknown_team_raises_404(self, _mock_api):
        with self.assertRaises(HTTPException) as context:
            main.find_team_by_name("Real Madrid", "PL")

        self.assertEqual(context.exception.status_code, 404)

    def test_blank_team_name_raises_400(self):
        with self.assertRaises(HTTPException) as context:
            main.find_team_by_name("   ", "PL")

        self.assertEqual(context.exception.status_code, 400)


# --------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------

class TestEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)

        # Start every test with an empty match history.
        with main.get_database_connection() as connection:
            connection.execute("DELETE FROM match_history")
            connection.commit()

    def test_home_route_is_running(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("running", response.json()["message"])

    def test_generate_report_saves_to_history(self):
        payload = {
            "homeTeam": "Arsenal",
            "awayTeam": "Chelsea",
            "finalScore": "3-0",
            "shots": "14-6",
            "possession": "60-40",
            "manOfTheMatch": "Saka",
            "playerPerformances": json.dumps([
                {"name": "Saka", "position": "Forward", "side": "home",
                 "stats": {"goals": 2, "shots": 5, "shotsOnTarget": 4}},
            ]),
        }

        response = self.client.post("/generate-report", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["analysis"]["winner"], "Arsenal")
        self.assertEqual(body["analysis"]["matchType"], "Dominant Win")
        self.assertTrue(body["analysis"]["cleanSheet"])
        self.assertEqual(body["playerRatings"][0]["name"], "Saka")

        history = self.client.get("/history").json()["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["homeTeam"], "Arsenal")

    def test_generate_report_rejects_missing_required_fields(self):
        response = self.client.post("/generate-report", json={"homeTeam": "Arsenal"})

        self.assertEqual(response.status_code, 422)

    @patch("main.requests.get")
    def test_team_logo_returns_badge(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"teams": [{"strTeam": "Arsenal", "strBadge": "badge.png"}]}
        )

        response = self.client.get("/team-logo/Arsenal")

        self.assertEqual(response.json()["logo"], "badge.png")

    @patch("main.requests.get", side_effect=requests.RequestException)
    def test_team_logo_handles_service_outage(self, _mock_get):
        response = self.client.get("/team-logo/Arsenal")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["logo"])

    @patch("main.FOOTBALL_DATA_API_KEY", "")
    def test_load_squad_without_api_key_returns_500(self):
        response = self.client.post("/load-squad", json={"teamName": "Arsenal"})

        self.assertEqual(response.status_code, 500)

    @patch("main.make_football_api_request")
    def test_load_squad_sorts_players_by_position(self, mock_api):
        mock_api.side_effect = [
            SAMPLE_TEAMS,
            {
                "id": 57,
                "name": "Arsenal FC",
                "squad": [
                    {"id": 3, "name": "Saka", "position": "Offence"},
                    {"id": 1, "name": "Raya", "position": "Goalkeeper"},
                    {"id": 2, "name": "Saliba", "position": "Defence"},
                    {"id": 4, "name": ""},
                ],
            },
        ]

        response = self.client.post("/load-squad", json={"teamName": "Arsenal"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["playerCount"], 3)
        self.assertEqual(
            [player["name"] for player in body["squad"]],
            ["Raya", "Saliba", "Saka"],
        )


if __name__ == "__main__":
    unittest.main()
