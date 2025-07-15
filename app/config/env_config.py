"""
Environment configuration for the Strava Training Planner Agent
"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Strava-Training-Planner")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")

# Strava API Configuration
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_ACCESS_TOKEN = os.getenv("STRAVA_ACCESS_TOKEN")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

# Tavily API Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Model Configuration
DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-4o")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
