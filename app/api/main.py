"""
FastAPI server for the Strava Training Planner Agent
"""

import asyncio
import os

# Import our agent
from typing import Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.models.strava_agent import create_agent, format_training_plan_input


# Define API models
class TrainingPlanRequest(BaseModel):
    """Request model for training plan generation."""

    athlete_name: str = Field(
        ..., description="Name of the athlete", example="Jane Doe"
    )
    goals: Optional[str] = Field(
        None,
        description="Training goals of the athlete",
        example="Improve 10k running time and build endurance",
    )

    class Config:
        schema_extra = {
            "example": {
                "athlete_name": "Jane Doe",
                "goals": "Improve 10k running time and build endurance",
            }
        }


class TrainingPlanResponse(BaseModel):
    """Response model for training plan generation."""

    message: str = Field(..., description="Response message from the agent")
    excel_file_path: Optional[str] = Field(
        None, description="Path to the generated Excel file"
    )

    class Config:
        schema_extra = {
            "example": {
                "message": "Training plan generation started. Please check the status endpoint for updates.",
                "excel_file_path": None,
            }
        }


class TrainingPlanStatus(BaseModel):
    """Status model for training plan generation."""

    status: str = Field(
        ..., description="Status of the training plan generation", example="completed"
    )
    message: str = Field(..., description="Status message")
    excel_file_path: Optional[str] = Field(
        None, description="Path to the generated Excel file"
    )


# Initialize FastAPI app
app = FastAPI(
    title="Strava Training Planner API",
    description="API for generating personalized training plans based on Strava data and internet workout research",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1
    },  # Collapse the models section by default
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create agent instance
agent = create_agent()

# In-memory storage for tracking agent responses
training_plans = {}


@app.get(
    "/",
    summary="API Health Check",
    description="Check if the API is running correctly",
    response_description="Simple health status message",
)
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "message": "Strava Training Planner API is running"}


@app.post(
    "/training-plan",
    response_model=TrainingPlanResponse,
    summary="Generate Training Plan",
    description="Start the generation of a personalized training plan based on Strava data",
    response_description="Initial response confirming the plan generation has started",
)
async def generate_training_plan(
    request: TrainingPlanRequest, background_tasks: BackgroundTasks
):
    """
    Generate a personalized training plan based on Strava data.

    The plan generation happens asynchronously. Check the status endpoint to
    know when your plan is ready for download.

    Args:
        request: TrainingPlanRequest object containing athlete name and optional goals
        background_tasks: FastAPI background tasks for async processing

    Returns:
        TrainingPlanResponse with message and Excel file path
    """
    try:
        # Format the input for the agent
        agent_input = format_training_plan_input(
            athlete_name=request.athlete_name, goals=request.goals
        )

        # Run the agent in a background task to avoid timeouts
        # (since the agent might take some time to generate the plan)
        background_tasks.add_task(
            run_agent_and_store_result, request.athlete_name, agent_input
        )

        # Return an immediate response
        return TrainingPlanResponse(
            message="Training plan generation started. Please check the status endpoint for updates."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating training plan: {str(e)}"
        )


@app.get(
    "/training-plan/{athlete_name}/status",
    response_model=TrainingPlanStatus,
    summary="Check Training Plan Status",
    description="Check the status of a training plan generation process",
    response_description="Status information about the requested training plan",
)
async def check_training_plan_status(athlete_name: str):
    """
    Check the status of a training plan generation.

    Args:
        athlete_name: The name of the athlete to check status for

    Returns:
        JSON response with status and any available details
    """
    # Replace spaces with underscores for consistent keys
    key = athlete_name.replace(" ", "_")

    if key not in training_plans:
        return JSONResponse(
            status_code=404,
            content={
                "status": "not_found",
                "message": f"No training plan found for athlete: {athlete_name}",
            },
        )

    plan_data = training_plans[key]

    if plan_data.get("status") == "completed":
        return {
            "status": "completed",
            "message": plan_data.get("message", "Training plan generated successfully"),
            "excel_file_path": plan_data.get("excel_file_path"),
        }
    elif plan_data.get("status") == "failed":
        return {
            "status": "failed",
            "message": plan_data.get("error", "Unknown error occurred"),
        }
    else:
        return {
            "status": "processing",
            "message": "Training plan is still being generated",
        }


@app.get(
    "/training-plan/{athlete_name}/download",
    summary="Download Training Plan Excel File",
    description="Download the Excel file for a completed training plan",
    response_description="Excel file as a downloadable attachment",
    response_class=FileResponse,
)
async def download_training_plan(athlete_name: str):
    """
    Download the Excel file for a generated training plan.

    Args:
        athlete_name: The name of the athlete whose plan to download

    Returns:
        Excel file as a downloadable attachment
    """
    key = athlete_name.replace(" ", "_")

    if key not in training_plans:
        raise HTTPException(
            status_code=404,
            detail=f"No training plan found for athlete: {athlete_name}",
        )

    plan_data = training_plans[key]

    if plan_data.get("status") != "completed":
        raise HTTPException(
            status_code=400, detail=f"Training plan for {athlete_name} is not ready yet"
        )

    excel_path = plan_data.get("excel_file_path")

    if not excel_path or not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Excel file not found")

    # Generate a more user-friendly filename
    filename = os.path.basename(excel_path)

    # Return the file as a downloadable attachment
    return FileResponse(
        path=excel_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


async def run_agent_and_store_result(athlete_name: str, agent_input: dict):
    """
    Run the agent and store the result for later retrieval.

    Args:
        athlete_name: Name of the athlete
        agent_input: Formatted input for the agent
    """
    key = athlete_name.replace(" ", "_")

    # Mark as processing
    training_plans[key] = {"status": "processing"}

    try:
        # Run the agent
        result = agent.invoke(agent_input)

        # Extract the message and Excel file path
        message = (
            result["messages"][-1].content
            if result.get("messages")
            else "No response from agent"
        )
        excel_path = result.get("excel_export_path")

        # Store the result
        training_plans[key] = {
            "status": "completed",
            "message": message,
            "excel_file_path": excel_path,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        # Store the error
        training_plans[key] = {
            "status": "failed",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


# Cleanup old results periodically (not implemented in this version)
# You might want to add a task that runs periodically to clean up old results


if __name__ == "__main__":
    # Run the FastAPI app
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)
