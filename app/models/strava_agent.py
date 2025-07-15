"""
Strava Training Planner Agent using LangGraph
"""

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.config.env_config import DEFAULT_MODEL_NAME, TEMPERATURE

# Import our custom models and tools
from app.models.agent_models import TrainingPlannerState
from app.tools.calendar_tool import GoogleCalendarTool
from app.tools.excel_tool import ExcelExportTool
from app.tools.strava_tool import StravaAnalysisTool

# Define the system prompt
SYSTEM_PROMPT = """You are a professional training planner assistant that creates personalized weekly workout programs based on an athlete's recent Strava activities.

Follow these steps:
1. Analyze the athlete's recent Strava data to understand their fitness level, activity patterns, and training load.
2. Create a balanced weekly training plan that includes appropriate workouts, rest days, and progressive overload.
3. Create calendar events for each workout session in the athlete's Google Calendar.
4. Generate an Excel spreadsheet with the complete weekly training program.

The weekly plan should:
- Be tailored to the athlete's demonstrated fitness level and activity preferences
- Include variety in workout types and intensities
- Allow adequate recovery between intense sessions
- Include specific workout details (duration, distance, intensity, description)
- Align with any specific goals the athlete mentions

Be thoughtful, professional, and provide clear explanations for your training recommendations.
"""


def create_agent():
    """Create the Strava Training Planner agent with LangGraph."""

    # Initialize the LLM
    llm = ChatOpenAI(model=DEFAULT_MODEL_NAME, temperature=TEMPERATURE)

    # Initialize the tools
    strava_tool = StravaAnalysisTool()
    calendar_tool = GoogleCalendarTool()
    excel_tool = ExcelExportTool()

    # Create a tool belt with all tools
    tools = [strava_tool, calendar_tool, excel_tool]

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
        # Look for the most recent StravaAnalysisTool result
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

    # Define how to track calendar events
    def track_calendar_events(state: TrainingPlannerState) -> Dict[str, Any]:
        """Track created Google Calendar events."""
        messages = state["messages"]
        calendar_events = state.get("calendar_events", [])

        for message in reversed(messages):
            if hasattr(message, "tool_call_id") and message.name == calendar_tool.name:
                if "Event ID:" in message.content:
                    # Extract the event ID from the message
                    event_id = message.content.split("Event ID: ")[1].strip()
                    if event_id not in calendar_events:
                        calendar_events.append(event_id)

        return {"calendar_events": calendar_events}

    # Define how to track Excel exports
    def track_excel_export(state: TrainingPlannerState) -> Dict[str, Any]:
        """Track the exported Excel file path."""
        messages = state["messages"]

        for message in reversed(messages):
            if hasattr(message, "tool_call_id") and message.name == excel_tool.name:
                if "exported successfully to" in message.content:
                    # Extract the file path
                    file_path = message.content.split("exported successfully to ")[
                        1
                    ].strip()
                    return {"excel_export_path": file_path}

        return {"excel_export_path": None}

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
    workflow.add_node("track_calendar", track_calendar_events)
    workflow.add_node("track_excel", track_excel_export)

    # Define the edges
    workflow.add_edge("agent", "process_strava")
    workflow.add_edge("process_strava", "track_calendar")
    workflow.add_edge("track_calendar", "track_excel")

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
    athlete_name: str, days: int = 7, goals: str = None
) -> Dict[str, Any]:
    """Format the input for the training planner."""
    prompt = f"Create a personalized weekly training plan for athlete {athlete_name} based on their Strava activities from the past {days} days."

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
