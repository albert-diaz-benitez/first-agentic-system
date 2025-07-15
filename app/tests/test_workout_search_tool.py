"""
Integration test for the Workout Search Tool - connects to Tavily API
"""

import json

import pytest
from dotenv import load_dotenv

from app.tools.workout_search_tool import WorkoutSearchTool

# Load environment variables
load_dotenv()


class TestWorkoutSearchIntegration:
    """Integration tests for the Workout Search Tool"""

    @pytest.fixture(scope="class")
    def search_tool(self):
        """Create and return an instance of WorkoutSearchTool"""
        tool = WorkoutSearchTool()
        yield tool

    def test_basic_search(self, search_tool):
        """Test basic workout search functionality"""
        # Run search for a beginner running workout
        result = search_tool._run(
            sport_type="Running", fitness_level="Beginner", max_results=3
        )

        # Print the result for debugging
        print(f"\nBasic Search Result:\n{result}\n")

        # Check if we got a valid response
        assert result is not None
        assert "Error" not in result

        try:
            # Parse the result as JSON
            data = json.loads(result)

            # Verify structure of the response
            assert "query" in data
            assert "workout_ideas" in data
            assert len(data["workout_ideas"]) > 0

            # Check first workout idea
            first_idea = data["workout_ideas"][0]
            assert "title" in first_idea
            assert "summary" in first_idea
            assert "source" in first_idea

            # Log some details
            print(f"Query: {data['query']}")
            print(f"Number of results: {len(data['workout_ideas'])}")
            print(f"First result title: {first_idea['title']}")

        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse result as JSON: {e}")

    def test_advanced_search_parameters(self, search_tool):
        """Test search with advanced parameters"""
        # Run search with more specific parameters
        result = search_tool._run(
            sport_type="Cycling",
            fitness_level="Advanced",
            duration_minutes=45,
            goal="hill climbing",
            max_results=2,
        )

        print(f"\nAdvanced Search Result:\n{result}\n")

        # Check response
        assert result is not None
        assert "Error" not in result

        data = json.loads(result)

        # Verify query contains all parameters
        query = data["query"].lower()
        assert "advanced" in query
        assert "cycling" in query
        assert "45" in query
        assert "hill climbing" in query

    def test_different_sports(self, search_tool):
        """Test search across different sport types"""
        sport_types = ["Swimming", "Strength Training", "Yoga"]

        for sport in sport_types:
            result = search_tool._run(
                sport_type=sport, fitness_level="Intermediate", max_results=1
            )

            print(f"\n{sport} Search Result:\n{result}\n")

            # Check response
            assert result is not None
            assert "Error" not in result

            data = json.loads(result)
            assert len(data["workout_ideas"]) > 0

            # Check that sport type is in query
            assert sport.lower() in data["query"].lower()

    def test_extract_workout_details(self, search_tool):
        """Test the workout details extraction"""
        # Sample workout content
        sample_content = """
        This interval workout begins with a 10-minute warm-up at an easy pace.
        Then, do 6 x 400m repeats at 5K pace with 200m recovery jogs.
        Finish with a 10-minute cool-down at an easy pace.
        """

        # Extract details
        details = search_tool._extract_workout_details(sample_content)

        # Verify extraction
        assert details["includes_warmup"] is True
        assert details["includes_cooldown"] is True
        assert details["workout_type"] == "Interval"

        print(f"\nExtracted details: {details}")


if __name__ == "__main__":
    # For manual execution, load environment variables
    load_dotenv()

    # Create and run the tool manually
    tool = WorkoutSearchTool()
    result = tool._run(sport_type="Running", fitness_level="Intermediate", goal="speed")
    print(f"Workout search result:\n{result}")
