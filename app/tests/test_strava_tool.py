"""
Integration test for the Strava API Tool - connects to real Strava API
"""

import ast

import pytest
from dotenv import load_dotenv

from app.tools.strava_tool import StravaStatsTool

# Load environment variables
load_dotenv()


class TestStravaIntegration:
    """Integration tests for the Strava Stats Tool"""

    @pytest.fixture(scope="class")
    def strava_tool(self):
        """Create and return an instance of StravaStatsTool"""
        tool = StravaStatsTool()
        yield tool

    def test_fetch_athlete_stats(self, strava_tool):
        """Test fetching athlete stats from the Strava API"""
        # Run the tool to fetch athlete stats
        result = strava_tool._run(
            include_recent_ride_totals=True,
            include_recent_run_totals=True,
            include_recent_swim_totals=True,
            include_ytd_totals=True,
            include_all_time_totals=True,
        )

        # Print the result for debugging
        print(f"\nStrava Athlete Stats Analysis Result:\n{result}\n")

        # Check if we got a valid response
        assert result is not None
        assert "error" not in result.lower()

        try:
            # Try to parse the result as a dictionary
            analysis_dict = ast.literal_eval(result)

            # Verify top-level structure of the response
            assert "athlete_info" in analysis_dict
            assert "stats_analysis" in analysis_dict

            # Check athlete info
            athlete_info = analysis_dict["athlete_info"]
            assert "id" in athlete_info
            assert "firstname" in athlete_info
            assert "lastname" in athlete_info

            # Check stats analysis
            stats = analysis_dict["stats_analysis"]

            # Check for training insights
            assert "training_insights" in stats
            insights = stats["training_insights"]
            assert "fitness_level" in insights
            assert "primary_sport" in insights
            assert "weekly_training_load_hours" in insights
            assert "training_frequency" in insights

            # Log some stats
            print(f"Athlete: {athlete_info['firstname']} {athlete_info['lastname']}")
            print(f"Primary sport: {insights['primary_sport']}")
            print(f"Fitness level: {insights['fitness_level']}")
            print(
                f"Weekly training load: {insights['weekly_training_load_hours']} hours"
            )

        except Exception as e:
            pytest.fail(f"Failed to parse result as dictionary: {e}")

    def test_selective_stats_fetching(self, strava_tool):
        """Test fetching only specific stats categories"""
        # Get only recent ride stats
        ride_result = strava_tool._run(
            include_recent_ride_totals=True,
            include_recent_run_totals=False,
            include_recent_swim_totals=False,
            include_ytd_totals=False,
            include_all_time_totals=False,
        )

        # Get only YTD stats
        ytd_result = strava_tool._run(
            include_recent_ride_totals=False,
            include_recent_run_totals=False,
            include_recent_swim_totals=False,
            include_ytd_totals=True,
            include_all_time_totals=False,
        )

        # Both should return valid results
        assert ride_result is not None
        assert ytd_result is not None

        # Parse results
        ride_data = ast.literal_eval(ride_result)
        ytd_data = ast.literal_eval(ytd_result)

        # Verify ride-only result has ride stats but not YTD stats
        stats_analysis = ride_data["stats_analysis"]
        has_ride_stats = any("ride_totals" in key for key in stats_analysis.keys())
        has_ytd_stats = any("ytd_" in key for key in stats_analysis.keys())
        assert has_ride_stats, "Should have ride stats when requested"
        assert not has_ytd_stats, "Should not have YTD stats when not requested"

        # Verify YTD-only result has YTD stats but not recent ride stats
        stats_analysis = ytd_data["stats_analysis"]
        has_ytd_stats = any("ytd_" in key for key in stats_analysis.keys())
        has_recent_stats = any("recent_" in key for key in stats_analysis.keys())
        assert has_ytd_stats, "Should have YTD stats when requested"
        assert not has_recent_stats, "Should not have recent stats when not requested"

    def test_training_insights(self, strava_tool):
        """Test the training insights generation"""
        result = strava_tool._run()
        data = ast.literal_eval(result)

        # Verify training insights
        insights = data["stats_analysis"]["training_insights"]

        # Check fitness level is one of the expected values
        fitness_level = insights["fitness_level"]
        assert fitness_level in [
            "Beginner",
            "Intermediate",
            "Advanced",
            "Elite",
        ], f"Unexpected fitness level: {fitness_level}"

        # Check training frequency is one of the expected values
        training_frequency = insights["training_frequency"]
        assert training_frequency in [
            "Low",
            "Moderate",
            "High",
        ], f"Unexpected training frequency: {training_frequency}"

        # Check weekly training hours is a reasonable number
        weekly_hours = insights["weekly_training_load_hours"]
        assert (
            0 <= weekly_hours <= 168
        ), "Weekly training hours should be between 0 and 168"

        print(
            f"\nTraining Insights:\n - Fitness level: {fitness_level}\n - Training frequency: {training_frequency}\n - Weekly hours: {weekly_hours}"
        )
