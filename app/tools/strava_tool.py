"""
Strava API Tool for fetching athlete stats
"""

import datetime
from typing import Any, Dict

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from stravalib.client import Client
from stravalib.exc import AccessUnauthorized

from app.config.env_config import (
    STRAVA_ACCESS_TOKEN,
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_REFRESH_TOKEN,
)

# Define required scopes for Strava API
STRAVA_SCOPES = ["read", "activity:read_all", "profile:read_all"]


class StravaStatsParams(BaseModel):
    """Parameters for fetching Strava athlete stats."""

    include_recent_ride_totals: bool = Field(
        default=True, description="Include recent ride stats"
    )
    include_recent_run_totals: bool = Field(
        default=True, description="Include recent run stats"
    )
    include_recent_swim_totals: bool = Field(
        default=True, description="Include recent swim stats"
    )
    include_ytd_totals: bool = Field(
        default=True, description="Include year to date stats"
    )
    include_all_time_totals: bool = Field(
        default=True, description="Include all time stats"
    )


class StravaStatsTool(BaseTool):
    name: str = "strava_athlete_stats_analysis"
    description: str = (
        "Retrieves and analyzes athlete statistics from Strava for workout planning"
    )
    args_schema: type[BaseModel] = StravaStatsParams

    def _authenticate(self) -> Client:
        """Authenticate with the Strava API."""
        client = Client()

        if not all(
            [
                STRAVA_CLIENT_ID,
                STRAVA_CLIENT_SECRET,
                STRAVA_ACCESS_TOKEN,
                STRAVA_REFRESH_TOKEN,
            ]
        ):
            raise ValueError("Missing Strava API credentials")

        try:
            # Set credentials
            client.access_token = STRAVA_ACCESS_TOKEN
            client.refresh_token = STRAVA_REFRESH_TOKEN
            client.token_expires_at = datetime.datetime.now() + datetime.timedelta(
                hours=1
            )

        except Exception as e:
            raise ConnectionError(f"Failed to authenticate with Strava: {e}")

        return client

    def _run(
        self,
        include_recent_ride_totals: bool = True,
        include_recent_run_totals: bool = True,
        include_recent_swim_totals: bool = True,
        include_ytd_totals: bool = True,
        include_all_time_totals: bool = True,
    ) -> str:
        """
        Retrieve and analyze athlete statistics from Strava.

        Args:
            include_recent_ride_totals: Whether to include recent ride statistics
            include_recent_run_totals: Whether to include recent run statistics
            include_recent_swim_totals: Whether to include recent swim statistics
            include_ytd_totals: Whether to include year-to-date statistics
            include_all_time_totals: Whether to include all-time statistics

        Returns:
            A structured analysis of the athlete's statistics
        """
        try:
            # Authenticate with Strava
            client = self._authenticate()

            # Get the authenticated athlete
            athlete = client.get_athlete()

            # Get athlete stats
            stats = client.get_athlete_stats(athlete.id)

            # Process stats into a useful format for planning
            analysis = self._analyze_athlete_stats(
                stats,
                include_recent_ride_totals,
                include_recent_run_totals,
                include_recent_swim_totals,
                include_ytd_totals,
                include_all_time_totals,
            )

            # Include athlete profile information
            athlete_info = {
                "id": athlete.id,
                "firstname": athlete.firstname,
                "lastname": athlete.lastname,
                "username": getattr(athlete, "username", None),
                "city": getattr(athlete, "city", None),
                "state": getattr(athlete, "state", None),
                "country": getattr(athlete, "country", None),
                "sex": getattr(athlete, "sex", None),
                "weight": getattr(athlete, "weight", None),  # in kg
                "profile": getattr(athlete, "profile", None),
            }

            # Combine athlete info with stats
            complete_analysis = {
                "athlete_info": athlete_info,
                "stats_analysis": analysis,
            }

            return str(complete_analysis)

        except AccessUnauthorized as e:
            return f"Authorization error with Strava API: {e}. Please ensure you have the required permissions: {', '.join(STRAVA_SCOPES)}"
        except Exception as e:
            return f"Error fetching Strava athlete stats: {e}"

    def _analyze_athlete_stats(
        self,
        stats,
        include_recent_ride_totals: bool,
        include_recent_run_totals: bool,
        include_recent_swim_totals: bool,
        include_ytd_totals: bool,
        include_all_time_totals: bool,
    ) -> Dict[str, Any]:
        """
        Process and analyze athlete statistics from Strava.

        Args:
            stats: The athlete stats object from Strava
            include_*: Boolean flags for which stats to include

        Returns:
            A dictionary with processed stats
        """
        analysis = {}

        # Process recent ride totals (last 4 weeks)
        if include_recent_ride_totals and hasattr(stats, "recent_ride_totals"):
            recent_ride = stats.recent_ride_totals
            analysis["recent_ride_totals"] = {
                "count": getattr(recent_ride, "count", 0),
                "distance_km": round(getattr(recent_ride, "distance", 0) / 1000, 2),
                "moving_time_hours": round(
                    getattr(recent_ride, "moving_time", 0) / 3600, 2
                ),
                "elevation_gain_m": round(getattr(recent_ride, "elevation_gain", 0), 2),
            }

        # Process recent run totals (last 4 weeks)
        if include_recent_run_totals and hasattr(stats, "recent_run_totals"):
            recent_run = stats.recent_run_totals
            analysis["recent_run_totals"] = {
                "count": getattr(recent_run, "count", 0),
                "distance_km": round(getattr(recent_run, "distance", 0) / 1000, 2),
                "moving_time_hours": round(
                    getattr(recent_run, "moving_time", 0) / 3600, 2
                ),
                "elevation_gain_m": round(getattr(recent_run, "elevation_gain", 0), 2),
            }

        # Process recent swim totals (last 4 weeks)
        if include_recent_swim_totals and hasattr(stats, "recent_swim_totals"):
            recent_swim = stats.recent_swim_totals
            analysis["recent_swim_totals"] = {
                "count": getattr(recent_swim, "count", 0),
                "distance_km": round(getattr(recent_swim, "distance", 0) / 1000, 2),
                "moving_time_hours": round(
                    getattr(recent_swim, "moving_time", 0) / 3600, 2
                ),
            }

        # Process year to date totals
        if include_ytd_totals:
            # YTD ride totals
            if hasattr(stats, "ytd_ride_totals"):
                ytd_ride = stats.ytd_ride_totals
                analysis["ytd_ride_totals"] = {
                    "count": getattr(ytd_ride, "count", 0),
                    "distance_km": round(getattr(ytd_ride, "distance", 0) / 1000, 2),
                    "moving_time_hours": round(
                        getattr(ytd_ride, "moving_time", 0) / 3600, 2
                    ),
                    "elevation_gain_m": round(
                        getattr(ytd_ride, "elevation_gain", 0), 2
                    ),
                }

            # YTD run totals
            if hasattr(stats, "ytd_run_totals"):
                ytd_run = stats.ytd_run_totals
                analysis["ytd_run_totals"] = {
                    "count": getattr(ytd_run, "count", 0),
                    "distance_km": round(getattr(ytd_run, "distance", 0) / 1000, 2),
                    "moving_time_hours": round(
                        getattr(ytd_run, "moving_time", 0) / 3600, 2
                    ),
                    "elevation_gain_m": round(getattr(ytd_run, "elevation_gain", 0), 2),
                }

            # YTD swim totals
            if hasattr(stats, "ytd_swim_totals"):
                ytd_swim = stats.ytd_swim_totals
                analysis["ytd_swim_totals"] = {
                    "count": getattr(ytd_swim, "count", 0),
                    "distance_km": round(getattr(ytd_swim, "distance", 0) / 1000, 2),
                    "moving_time_hours": round(
                        getattr(ytd_swim, "moving_time", 0) / 3600, 2
                    ),
                }

        # Process all time totals
        if include_all_time_totals:
            # All-time ride totals
            if hasattr(stats, "all_ride_totals"):
                all_ride = stats.all_ride_totals
                analysis["all_ride_totals"] = {
                    "count": getattr(all_ride, "count", 0),
                    "distance_km": round(getattr(all_ride, "distance", 0) / 1000, 2),
                    "moving_time_hours": round(
                        getattr(all_ride, "moving_time", 0) / 3600, 2
                    ),
                    "elevation_gain_m": round(
                        getattr(all_ride, "elevation_gain", 0), 2
                    ),
                }

            # All-time run totals
            if hasattr(stats, "all_run_totals"):
                all_run = stats.all_run_totals
                analysis["all_run_totals"] = {
                    "count": getattr(all_run, "count", 0),
                    "distance_km": round(getattr(all_run, "distance", 0) / 1000, 2),
                    "moving_time_hours": round(
                        getattr(all_run, "moving_time", 0) / 3600, 2
                    ),
                    "elevation_gain_m": round(getattr(all_run, "elevation_gain", 0), 2),
                }

            # All-time swim totals
            if hasattr(stats, "all_swim_totals"):
                all_swim = stats.all_swim_totals
                analysis["all_swim_totals"] = {
                    "count": getattr(all_swim, "count", 0),
                    "distance_km": round(getattr(all_swim, "distance", 0) / 1000, 2),
                    "moving_time_hours": round(
                        getattr(all_swim, "moving_time", 0) / 3600, 2
                    ),
                }

        # Calculate weekly averages based on recent 4 weeks
        analysis["weekly_averages"] = {}

        # Weekly ride average
        if "recent_ride_totals" in analysis:
            recent_ride = analysis["recent_ride_totals"]
            analysis["weekly_averages"]["ride"] = {
                "avg_rides_per_week": round(recent_ride["count"] / 4, 1),
                "avg_distance_km_per_week": round(recent_ride["distance_km"] / 4, 1),
                "avg_time_hours_per_week": round(
                    recent_ride["moving_time_hours"] / 4, 1
                ),
            }

        # Weekly run average
        if "recent_run_totals" in analysis:
            recent_run = analysis["recent_run_totals"]
            analysis["weekly_averages"]["run"] = {
                "avg_runs_per_week": round(recent_run["count"] / 4, 1),
                "avg_distance_km_per_week": round(recent_run["distance_km"] / 4, 1),
                "avg_time_hours_per_week": round(
                    recent_run["moving_time_hours"] / 4, 1
                ),
            }

        # Weekly swim average
        if "recent_swim_totals" in analysis:
            recent_swim = analysis["recent_swim_totals"]
            analysis["weekly_averages"]["swim"] = {
                "avg_swims_per_week": round(recent_swim["count"] / 4, 1),
                "avg_distance_km_per_week": round(recent_swim["distance_km"] / 4, 1),
                "avg_time_hours_per_week": round(
                    recent_swim["moving_time_hours"] / 4, 1
                ),
            }

        # Calculate training load and fitness insights
        analysis["training_insights"] = self._calculate_training_insights(analysis)

        return analysis

    def _calculate_training_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate training load and fitness insights based on athlete stats."""
        insights = {}

        # Calculate primary sport based on recent activity counts
        primary_sport = "Unknown"
        max_count = 0

        for sport in ["ride", "run", "swim"]:
            sport_key = f"recent_{sport}_totals"
            if sport_key in analysis and analysis[sport_key]["count"] > max_count:
                max_count = analysis[sport_key]["count"]
                primary_sport = sport.capitalize()

        insights["primary_sport"] = primary_sport

        # Calculate weekly training load (in hours)
        weekly_training_hours = 0
        if "weekly_averages" in analysis:
            for sport in ["ride", "run", "swim"]:
                if sport in analysis["weekly_averages"]:
                    weekly_training_hours += analysis["weekly_averages"][sport][
                        "avg_time_hours_per_week"
                    ]

        insights["weekly_training_load_hours"] = round(weekly_training_hours, 1)

        # Determine fitness level based on weekly volume
        if weekly_training_hours < 3:
            insights["fitness_level"] = "Beginner"
        elif weekly_training_hours < 7:
            insights["fitness_level"] = "Intermediate"
        elif weekly_training_hours < 12:
            insights["fitness_level"] = "Advanced"
        else:
            insights["fitness_level"] = "Elite"

        # Determine training frequency
        total_weekly_sessions = 0
        for sport in ["ride", "run", "swim"]:
            if sport in analysis.get("weekly_averages", {}):
                total_weekly_sessions += analysis["weekly_averages"][sport][
                    f"avg_{sport}s_per_week"
                ]

        insights["avg_weekly_sessions"] = round(total_weekly_sessions, 1)

        if total_weekly_sessions < 3:
            insights["training_frequency"] = "Low"
        elif total_weekly_sessions < 6:
            insights["training_frequency"] = "Moderate"
        else:
            insights["training_frequency"] = "High"

        return insights
