"""
Core models for the Strava Training Planner agent
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TrainingPlannerState(TypedDict):
    """State for the Strava Training Planner agent."""

    messages: Annotated[List[BaseMessage], add_messages]  # Conversation history
    strava_analysis: Optional[Dict[str, Any]]  # Analyzed Strava data
    plan: Optional[Dict[str, Any]]  # Generated training plan
    calendar_events: List[str]  # IDs of created calendar events
    excel_export_path: Optional[str]  # Path to the exported Excel file
