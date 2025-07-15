"""
Tavily Search Tool for finding workout ideas
"""

import json
from typing import Any, Dict, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tavily import TavilyClient

from app.config.env_config import TAVILY_API_KEY


class WorkoutSearchParams(BaseModel):
    """Parameters for searching workout ideas."""

    sport_type: str = Field(..., description="Type of sport (Run, Bike, Swim, etc.)")
    fitness_level: str = Field(
        ...,
        description="Athlete's fitness level (Beginner, Intermediate, Advanced, Elite)",
    )
    duration_minutes: Optional[int] = Field(
        default=None, description="Target duration in minutes"
    )
    goal: Optional[str] = Field(
        default=None,
        description="Training goal (e.g., 'speed', 'endurance', 'recovery')",
    )
    max_results: int = Field(
        default=5, description="Maximum number of workout ideas to return"
    )


class WorkoutSearchTool(BaseTool):
    name: str = "search_workout_ideas"
    description: str = (
        "Searches the internet for workout ideas based on sport type and fitness level"
    )
    args_schema: type[BaseModel] = WorkoutSearchParams

    def _run(
        self,
        sport_type: str,
        fitness_level: str,
        duration_minutes: Optional[int] = None,
        goal: Optional[str] = None,
        max_results: int = 5,
    ) -> str:
        """
        Search for workout ideas based on provided parameters.

        Args:
            sport_type: Type of sport (Run, Bike, Swim, etc.)
            fitness_level: Athlete's fitness level (Beginner, Intermediate, Advanced, Elite)
            duration_minutes: Target workout duration in minutes
            goal: Training goal (e.g., 'speed', 'endurance', 'recovery')
            max_results: Maximum number of workout ideas to return

        Returns:
            A structured list of workout ideas
        """
        # Construct search query based on parameters
        if not TAVILY_API_KEY:
            raise ValueError("Missing Tavily API key")

        client = TavilyClient(api_key=TAVILY_API_KEY)

        query_parts = [f"{fitness_level} {sport_type} workout"]

        if duration_minutes:
            query_parts.append(f"{duration_minutes} minute")

        if goal:
            query_parts.append(goal)

        query = " ".join(query_parts)

        try:
            # Execute the search
            search_result = client.search(
                query=query,
                search_depth="advanced",  # Get more comprehensive results
                max_results=max_results,
            )

            # Process and structure the results
            workout_ideas = []

            for result in search_result.get("results", []):
                # Extract title and content from each result
                title = result.get("title", "Untitled Workout")
                content = result.get("content", "").strip()
                url = result.get("url", "")

                # Skip if content is too short
                if len(content) < 50:
                    continue

                # Create workout idea entry
                workout = {
                    "title": title,
                    "summary": content[:1000]
                    + ("..." if len(content) > 1000 else ""),  # Limit summary length
                    "source": url,
                }

                workout_ideas.append(workout)

            # Structure the final response
            response = {"query": query, "workout_ideas": workout_ideas[:max_results]}

            return json.dumps(response, indent=2)

        except Exception as e:
            return f"Error searching for workout ideas: {str(e)}"

    def _extract_workout_details(self, content: str) -> Dict[str, Any]:
        """Extract structured workout details from the content."""
        # This is a simplified extraction - you might want to use more advanced parsing
        details = {}

        if "warm-up" in content.lower() or "warm up" in content.lower():
            details["includes_warmup"] = True

        if "cool-down" in content.lower() or "cool down" in content.lower():
            details["includes_cooldown"] = True

        if "interval" in content.lower():
            details["workout_type"] = "Interval"
        elif "tempo" in content.lower():
            details["workout_type"] = "Tempo"
        elif "steady" in content.lower():
            details["workout_type"] = "Steady State"
        elif "hill" in content.lower():
            details["workout_type"] = "Hill"

        return details
