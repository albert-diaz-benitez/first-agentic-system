"""
Strava Training Planner Agent using LangGraph
"""

from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.config.env_config import DEFAULT_MODEL_NAME, TEMPERATURE

# Import our custom models and tools
from app.models.agent_models import TrainingPlannerState
from app.tools.excel_tool import ExcelExportTool
from app.tools.strava_tool import StravaStatsTool
from app.tools.workout_search_tool import WorkoutSearchTool

# Define the system prompt
SYSTEM_PROMPT = """You are a professional training planner assistant that creates personalized weekly workout programs based on an athlete's Strava statistics.

Follow these steps:
1. Analyze the athlete's Strava statistics to understand their fitness level, activity patterns, and training load.
2. Search for workout ideas that match the athlete's primary sports and fitness level.
3. Create a balanced weekly training plan that includes appropriate workouts, rest days, and progressive overload.
4. ALWAYS generate an Excel spreadsheet with the complete weekly training program.

The weekly plan should:
- Be tailored to the athlete's demonstrated fitness level and activity preferences
- Include variety in workout types and intensities
- Allow adequate recovery between intense sessions
- Include specific workout details (duration, distance, intensity, description)
- Align with any specific goals the athlete mentions
- Incorporate workout ideas found through internet searches when appropriate

IMPORTANT: You MUST create an Excel file with the training plan using the export_training_plan_to_excel tool. 
Your final step should always be to call the ExcelExportTool with:
- athlete_name: The name of the athlete
- week_start_date: Today's date in YYYY-MM-DD format
- workouts: A list of workout objects with day, title, duration, description, type, and intensity fields for each day of the week
- notes: Any additional notes or recommendations

Be thoughtful, professional, and provide clear explanations for your training recommendations.
"""


def create_agent():
    """Create the Strava Training Planner agent with LangGraph."""

    # Initialize the LLM
    llm = ChatOpenAI(model=DEFAULT_MODEL_NAME, temperature=TEMPERATURE)

    # Initialize the tools
    strava_tool = StravaStatsTool()
    workout_search_tool = WorkoutSearchTool()
    excel_tool = ExcelExportTool()

    # Create a tool belt with all tools
    tools = [strava_tool, workout_search_tool, excel_tool]

    # Bind the tools to the LLM
    llm_with_tools = llm.bind_tools(tools)

    # Create a tool node for executing the tools
    tool_node = ToolNode(tools)

    # Define the agent function to process messages and generate responses
    def agent_node(state: TrainingPlannerState) -> Dict[str, Any]:
        """Process messages and generate agent responses."""
        # Get the messages from the state
        messages = state["messages"]

        # If this is the first message, add the system prompt
        if len(messages) == 1 and isinstance(messages[0], HumanMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        # Generate a response from the LLM
        response = llm_with_tools.invoke(messages)

        # Return the updated state
        return {"messages": [response]}

    # Define how to process Strava analysis results
    def process_strava_data(state: TrainingPlannerState) -> Dict[str, Any]:
        """Extract and process Strava analysis data."""
        # Look for the most recent StravaStatsTool result
        messages = state["messages"]

        for message in reversed(messages):
            if hasattr(message, "tool_call_id") and message.name == strava_tool.name:
                try:
                    # Parse the analysis data
                    analysis_data = eval(
                        message.content
                    )  # Convert string representation to dict
                    return {"strava_analysis": analysis_data}
                except Exception:
                    return {"strava_analysis": {"error": "Failed to parse Strava data"}}

        # If no Strava data found
        return {"strava_analysis": None}

    # Define how to track workout searches
    def track_workout_searches(state: TrainingPlannerState) -> Dict[str, Any]:
        """Track workout ideas found through searches."""
        messages = state["messages"]
        workout_ideas = state.get("workout_ideas", [])

        for message in reversed(messages):
            if (
                hasattr(message, "tool_call_id")
                and message.name == workout_search_tool.name
            ):
                try:
                    # Parse the search results
                    import json

                    search_results = json.loads(message.content)

                    # Extract workout ideas
                    if "workout_ideas" in search_results:
                        for idea in search_results["workout_ideas"]:
                            if idea not in workout_ideas:
                                workout_ideas.append(idea)

                except Exception:
                    # If parsing fails, just continue
                    pass

        return {"workout_ideas": workout_ideas}

    # Define how to track Excel exports
    def track_excel_export(state: TrainingPlannerState) -> Dict[str, Any]:
        """Track the exported Excel file path."""
        messages = state["messages"]
        excel_path = None

        # First check if we already have a path in the state
        if state.get("excel_export_path"):
            excel_path = state.get("excel_export_path")

        # Look through messages for Excel export tool responses
        for message in reversed(messages):
            # Check if this is a tool response from the Excel tool
            if hasattr(message, "tool_call_id") and message.name == excel_tool.name:
                content = message.content
                if "exported successfully to" in content:
                    # Extract the file path using string split
                    excel_path = content.split("exported successfully to ")[1].strip()
                    break  # Found a valid path, exit the loop

        # If we have a plan but no Excel path, the plan may not be complete
        if state.get("plan") and not excel_path:
            # This indicates the agent hasn't generated the Excel file yet
            # We'll capture this state but continue the agent's execution
            return {"excel_export_path": None}

        return {"excel_export_path": excel_path}

    # Conditional routing based on tool calls
    def should_continue(state: TrainingPlannerState) -> str:
        """Determine if we need to route to the tool node or end the conversation."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check if the last message contains tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool"

        # Otherwise, we're done with this round
        return END

    # Create the graph
    workflow = StateGraph(TrainingPlannerState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("process_strava", process_strava_data)
    workflow.add_node("track_searches", track_workout_searches)
    workflow.add_node("track_excel", track_excel_export)

    # Define the edges
    workflow.add_edge("agent", "process_strava")
    workflow.add_edge("process_strava", "track_searches")
    workflow.add_edge("track_searches", "track_excel")

    # Add conditional edge
    workflow.add_conditional_edges(
        "track_excel", should_continue, {"tool": "tool", END: END}
    )

    # Connect tool back to agent
    workflow.add_edge("tool", "agent")

    # Set the entry point
    workflow.set_entry_point("agent")

    # Compile the graph
    return workflow.compile()


def format_training_plan_input(
    athlete_name: str, days: int = 7, goals: Optional[str] = None
) -> Dict[str, Any]:
    """Format the input for the training planner."""
    prompt = f"Create a personalized weekly training plan for athlete {athlete_name} based on their Strava statistics."

    if goals:
        prompt += f" The athlete's goals are: {goals}"

    return {"messages": [HumanMessage(content=prompt)]}


if __name__ == "__main__":
    # Example usage
    agent = create_agent()
    result = agent.invoke(
        format_training_plan_input(
            "John Doe", goals="Improve 10k running time and overall endurance"
        )
    )

    # Print the final response
    print(result["messages"][-1].content)
